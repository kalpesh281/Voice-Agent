"""LiveKit Agents worker — browser voice over WebRTC.

This replaces the raw-PCM-over-WebSocket pipeline (app/api/websocket.py +
deepgram_stt.py + deepgram_tts.py + the frontend audio hooks) with LiveKit's
production WebRTC transport and its built-in turn detection / barge-in / VAD.

The agent *brain* is unchanged: we plug the existing compiled LangGraph in as
the session LLM via livekit-plugins-langchain, so all booking tools, the system
prompt, and the Mongo checkpointer keep working exactly as before.

Run it as its own process alongside the FastAPI server:

    uv run python -m app.livekit_agent dev      # hot-reload dev mode
    uv run python -m app.livekit_agent start     # production

A browser joins a room named "voice-<client_id>" (token minted by the
/api/v1/livekit/token endpoint); this worker is dispatched into that room,
reads the client_id from the room name, builds that client's graph, and talks.
"""

import logging
from uuid import uuid4

from dotenv import load_dotenv
from langchain_core.messages import AIMessage, AIMessageChunk
from livekit import agents
from livekit.agents import AgentServer, AgentSession, Agent
from livekit.agents.tokenize import TokenData, WordStream, WordTokenizer
from livekit.agents.types import DEFAULT_API_CONNECT_OPTIONS, NOT_GIVEN
from livekit.plugins import deepgram, silero, langchain
from livekit.plugins.langchain import langgraph as _lclg

from app.agent.graph import build_graph
from app.config import settings
from app.db.mongo import connect_client, connect_platform
from app.db.repositories.client_repo import ClientRepository
from app.utils.prompt_builder import build_greeting

# Load .env from the project root (same anchor Settings uses).
load_dotenv(dotenv_path=settings.model_config["env_file"])

logger = logging.getLogger(__name__)

ROOM_PREFIX = "voice-"
# Must match the agent_name the token's RoomConfiguration dispatches (see
# /api/v1/livekit/token). Explicit dispatch is reliable; auto-dispatch is not,
# because our room name is fixed — the room persists between calls, so the
# "new room" event that auto-dispatch relies on never fires for the 2nd call on.
AGENT_NAME = "booking-agent"

# Curated Indian-English / Indian-origin vocabulary that US-English STT models
# routinely mishear ("Maharaja" -> "Maha raja"/"my roger"). Keyterm prompting
# biases nova-3 toward these spellings. Domain (hotel) terms live here too so the
# booking words come through cleanly regardless of which client is loaded.
_BASE_KEYTERMS = [
    "Maharaja", "Haveli", "Sahyadri", "Rajasthani", "Mughal", "Nawab",
    "Rani", "Raja", "Diwan", "Durbar", "Mahal", "Palace", "Heritage",
    "Marine Drive", "Mumbai", "Bengaluru", "Rupees", "INR", "lakh",
    # booking domain
    "suite", "penthouse", "deluxe", "villa", "check-in", "check-out",
    "booking", "availability", "amenities", "occupancy",
]


async def _build_stt_keyterms(config) -> list[str]:
    """Assemble nova-3 keyterms: the client's real proper nouns + Indian set.

    Pulls the actual resource names / types / views from the client's DB (e.g.
    "Maharaja Deluxe King", "Sahyadri Mountain Suite") and the business name, so
    STT is primed with the exact phrases a caller will say. Individual notable
    words inside multi-word names are added too ("Maharaja" on its own), since a
    caller rarely says the full room name. Failures here are non-fatal — STT just
    falls back to the base list.
    """
    terms: list[str] = list(_BASE_KEYTERMS)

    try:
        biz = getattr(config, "business", None)
        if biz is not None:
            if getattr(biz, "name", None):
                terms.append(biz.name)
            if getattr(biz, "location", None):
                terms.append(biz.location)

        dm = config.db_mapping
        collection = dm.resources_collection
        name_field = dm.resource_name_field
        # Bias toward the searchable string fields too (type/view/bed_type), but
        # skip numeric ones (max_guests) which aren't spoken as keyterms.
        fields = [name_field] + [f for f in (dm.searchable_fields or []) if f]

        from app.db.repositories.resource_repo import ResourceRepository

        repo = ResourceRepository(collection)
        for field in dict.fromkeys(fields):  # de-dupe, preserve order
            try:
                values = await repo.distinct(field)
            except Exception:
                continue
            for v in values:
                if not isinstance(v, str) or not v.strip():
                    continue
                terms.append(v)
                # Add capitalized multi-word names split into notable words so a
                # caller saying just "Maharaja" still gets the boost.
                if " " in v and v[:1].isupper():
                    terms += [w for w in v.split() if len(w) > 3]
    except Exception as e:
        logger.debug("keyterm build failed, using base list only: %s", e)

    # De-dupe (case-insensitive), preserve order, cap at Deepgram's practical
    # keyterm budget so the request stays small.
    seen: set[str] = set()
    out: list[str] = []
    for t in terms:
        key = t.lower()
        if key in seen:
            continue
        seen.add(key)
        out.append(t)
    return out[:100]

def _resolve_tts_voice(voice: str | None) -> str:
    """Pick the TTS model, preferring the client's voice but upgrading legacy ones.

    Only Aura-2 voices (`aura-2-*`) sound like the warm cadence we tuned for. A
    blank field — or a legacy Aura-1 id (e.g. "aura-asteria-en") left over from
    before the Aura-2 switch — falls back to the platform default so no client is
    stuck on the flatter voice until they re-save their settings.
    """
    v = (voice or "").strip()
    if v.startswith("aura-2-"):
        return v
    return settings.deepgram_tts_model


server = AgentServer()


# ── Whole-sentence TTS tokenizer ────────────────────────────────────────────
# The Deepgram TTS plugin sends ONE WebSocket "Speak" message per token it pulls
# from its word tokenizer. The plugin's default (basic WordTokenizer) yields one
# WORD at a time, so each word is handed to the model with almost no phrase
# context — producing audible micro-gaps between words (the "choppy" speech).
# Emitting each sentence as a SINGLE token lets Deepgram synthesize it as one
# continuous, naturally coarticulated unit. The upstream AgentSession already
# splits the LLM stream into sentences (with flush boundaries), so each segment
# fed here is one sentence: smooth joins, negligible added latency.
class _WholeSentenceWordStream(WordStream):
    def __init__(self) -> None:
        super().__init__()
        self._buf = ""

    def push_text(self, text: str) -> None:
        self._check_not_closed()
        self._buf += text

    def _emit(self) -> None:
        text = self._buf.strip()
        self._buf = ""
        if text:
            self._event_ch.send_nowait(TokenData(token=text))

    def flush(self) -> None:
        self._check_not_closed()
        self._emit()

    def end_input(self) -> None:
        self._emit()
        self._do_close()

    async def aclose(self) -> None:
        self._do_close()


class WholeSentenceWordTokenizer(WordTokenizer):
    """Yields each flushed segment (one sentence) as a single token — see above."""

    def tokenize(self, text: str, *, language: str | None = None) -> list[str]:
        text = text.strip()
        return [text] if text else []

    def stream(self, *, language: str | None = None) -> WordStream:
        return _WholeSentenceWordStream()


# ── Assistant-only LangGraph adapter ────────────────────────────────────────
# LiveKit's stock LLMAdapter streams the graph with stream_mode="messages",
# which emits EVERY message the graph produces — including the `tools` node's
# ToolMessage, whose content is the raw search JSON ({"results": [], ...}). The
# stock adapter then speaks/displays that JSON as if it were the agent's reply
# (the "weird msg"). We only ever want the assistant's own tokens (the
# AIMessageChunks from the `respond` node) to reach TTS/transcript, so we filter
# the stream by message type and drop anything that isn't assistant output.
def _is_assistant_token(token) -> bool:
    if isinstance(token, (AIMessageChunk, AIMessage)):
        return True
    # Plain string tokens only ever come from the LLM token stream — keep them.
    return isinstance(token, str)


class _AssistantOnlyStream(_lclg.LangGraphStream):
    async def _run(self) -> None:
        state = self._chat_ctx_to_state()
        is_multi_mode = isinstance(self._stream_mode, list)
        try:
            aiter = self._graph.astream(
                state, self._config, context=self._context,
                stream_mode=self._stream_mode, subgraphs=self._subgraphs,
            )
        except TypeError:
            aiter = self._graph.astream(state, self._config, stream_mode=self._stream_mode)

        async for item in aiter:
            token = None
            if is_multi_mode and isinstance(item, tuple) and len(item) == 2 and isinstance(item[0], str):
                mode, data = item
                token = _lclg._extract_message_chunk(data) if mode == "messages" else (
                    data if mode == "custom" else None
                )
            elif self._stream_mode == "messages":
                token = _lclg._extract_message_chunk(item)
            elif self._stream_mode == "custom":
                token = item

            if token is None or not _is_assistant_token(token):
                continue
            chunk = _lclg._to_chat_chunk(token)
            if chunk:
                self._event_ch.send_nowait(chunk)


class AssistantOnlyLLMAdapter(langchain.LLMAdapter):
    """LLMAdapter that never surfaces tool output — only assistant tokens."""

    def chat(self, *, chat_ctx, tools=None, conn_options=DEFAULT_API_CONNECT_OPTIONS,
             parallel_tool_calls=NOT_GIVEN, tool_choice=NOT_GIVEN, extra_kwargs=NOT_GIVEN):
        return _AssistantOnlyStream(
            self, chat_ctx=chat_ctx, tools=tools or [], graph=self._graph,
            conn_options=conn_options, config=self._config, context=self._context,
            subgraphs=self._subgraphs, stream_mode=self._stream_mode,
        )


# Named agent → EXPLICIT dispatch. The browser's join token carries a
# RoomConfiguration that dispatches this exact `agent_name` (see the token
# endpoint), so the worker is reliably pulled into the room on every call — even
# though the room name is fixed and the room already exists from a prior call.
# (Auto-dispatch only fires on room creation, which is why the 2nd+ call hung.)
@server.rtc_session(agent_name=AGENT_NAME)
async def entrypoint(ctx: agents.JobContext):
    """Handle one browser voice session (one LiveKit room)."""
    # Join the room. Without this the worker accepts the job but never actually
    # connects/publishes, so the caller hears nothing (no greeting).
    try:
        await ctx.connect()
    except Exception as e:
        # Some runtimes auto-connect before the entrypoint; don't fail on that.
        logger.debug("ctx.connect() skipped/failed (may be auto-connected): %s", e)

    # Room name carries which client the caller is talking to, plus a unique
    # per-call suffix: "voice-<client_id>-<uuid8>". Strip the prefix, then drop
    # the trailing "-<uuid8>" segment to recover the client_id (which itself may
    # contain hyphens, e.g. "grand-meridian-palace"). The suffix is hex with no
    # hyphens, so rsplit on the last hyphen is safe.
    room_name = ctx.room.name or ""
    if room_name.startswith(ROOM_PREFIX):
        client_id = room_name[len(ROOM_PREFIX):].rsplit("-", 1)[0] or settings.client_id
    else:
        client_id = settings.client_id
    logger.info("LiveKit session starting for client_id=%s (room=%s)", client_id, room_name)

    # Platform DB holds client configs + bookings + checkpoints; the booking
    # tools resolve the client's own DB through the global connection. The worker
    # is a separate process from the API server, so connect both here.
    await connect_platform(settings.mongodb_uri, settings.mongodb_database)

    config = await ClientRepository().get_by_id(client_id)
    if config is None:
        logger.error("Unknown client_id=%s — cannot start session", client_id)
        return

    client_uri = config.database.connection_uri or settings.client_db_uri or settings.mongodb_uri
    client_db_name = config.database.database_name or settings.client_db_name or settings.mongodb_database
    try:
        await connect_client(client_uri, client_db_name)
    except Exception as e:
        logger.error("Client DB connect failed for %s: %s", client_id, e)

    # The existing LangGraph agent, unchanged — tools/system-prompt baked in from
    # config, Mongo checkpointer for memory. LLMAdapter feeds it the live chat
    # context and streams the reply back to TTS.
    graph = build_graph(config, settings)

    # Prime STT with the client's real proper nouns ("Maharaja Deluxe King",
    # "Sahyadri Mountain Suite") + an Indian-English vocabulary set, so accented
    # speech and Indian-origin words transcribe correctly.
    keyterms = await _build_stt_keyterms(config)
    logger.info("STT keyterms (%d): %s ...", len(keyterms), ", ".join(keyterms[:12]))

    session = AgentSession(
        stt=deepgram.STT(
            model=settings.deepgram_stt_model,   # nova-3
            language="en-US",
            # nova-3 keyterm prompting — biases recognition toward these exact
            # phrases (proper nouns + Indian-English terms the US model misses).
            keyterms=keyterms,
            # Accuracy: format numbers/dates, punctuate, and don't litter the
            # transcript with "uh"/"um". The plugin default smart_format=False
            # noticeably hurts readability for a booking context.
            smart_format=True,
            punctuate=True,
            numerals=True,
            filler_words=False,
            # The plugin default endpointing_ms=25 finalizes after 25ms of
            # silence, shredding a sentence into many fragments (garbled words,
            # one bubble each, and a turn detector that never sees a whole
            # sentence). Wait ~0.4s so each "final" is a complete phrase; the
            # session's turn detector still decides the actual end of turn.
            endpointing_ms=400,
        ),
        # The graph is compiled WITH a MongoDB checkpointer, which REQUIRES a
        # `configurable.thread_id` on every invocation. The adapter forwards this
        # `config` straight into graph.astream(); without it astream raises
        # "Checkpointer requires ... thread_id" the moment the agent tries to
        # think — which is why the agent never produced a single reply on this
        # branch. One thread per room keeps each call's memory separate.
        # One fresh checkpointer thread PER CALL. Keying on the (fixed) room name
        # made every caller share — and keep growing — a single history, leaking
        # stale context (a previous call's botched booking) into new sessions.
        # A per-session id gives each call a clean slate while still persisting
        # memory for the duration of that call.
        llm=AssistantOnlyLLMAdapter(
            graph=graph,
            config={"configurable": {"thread_id": f"{room_name or client_id}-{uuid4().hex[:8]}"}},
        ),
        # Feed Deepgram whole sentences (one Speak msg each) instead of the
        # plugin default of one word per Speak msg — eliminates the inter-word
        # micro-gaps that made the voice sound choppy.
        tts=deepgram.TTS(
            # Per-client voice — each business picks its own Aura-2 voice in
            # Settings/Onboarding (stored on config.voice.tts_voice). Older clients
            # may still have a legacy Aura-1 id (aura-asteria-en) stored from before
            # the Aura-2 switch; those sound flatter, so fall back to the platform
            # default unless the client explicitly chose an Aura-2 voice.
            model=_resolve_tts_voice(config.voice.tts_voice),
            word_tokenizer=WholeSentenceWordTokenizer(),
        ),
        # VAD sensitivity is a balance: too high and soft/quiet speech never
        # crosses the bar so the agent ignores you (you have to raise your
        # voice); too low and room hum reads as endless speech so end-of-turn
        # never fires. 0.6 was too deaf to soft voices — 0.45 picks up a normal
        # indoor speaking volume while staying above typical background noise.
        # Hysteresis (lower deactivation, 0.25) keeps a turn from dropping out on
        # brief dips mid-sentence. The browser mic already runs noise
        # suppression + auto-gain, which cleans up the lower threshold.
        vad=silero.VAD.load(
            activation_threshold=0.45,
            deactivation_threshold=0.25,
            min_silence_duration=0.55,
            # Require a brief sustained burst (0.25s) before a turn STARTS, so a
            # momentary background-noise blip during "thinking" doesn't get
            # treated as the user starting to speak (which kept re-opening the
            # mic mid-turn). Real speech easily clears 0.25s; a click/cough won't.
            min_speech_duration=0.25,
        ),
        # All turn/interruption tuning lives in turn_handling (the old top-level
        # kwargs are deprecated). turn_detection="vad" because the ML turn
        # detector needs PyTorch/transformers, which isn't installed.
        turn_handling={
            "turn_detection": "vad",
            # Bound end-of-turn: wait >=0.5s of silence before replying (so brief
            # mid-sentence pauses don't trigger a premature response), at most ~5s
            # (so the agent ALWAYS replies even if unsure — fixes "never responds").
            "endpointing": {"min_delay": 0.5, "max_delay": 5.0},
            "interruption": {
                # Only let ACTUAL recognized words barge in on the agent — not raw
                # VAD energy. Background noise / the agent's own audio leak produce
                # energy but no words, so with min_words>0 they can no longer
                # falsely interrupt while the agent is speaking. A real interjection
                # ("stop", "wait, actually...") still cuts in.
                "min_words": 2,
                # And require the speech to be sustained, not a transient blip.
                "min_duration": 0.6,
                # If a false interruption slips through (brief noise), resume the
                # agent's speech automatically after a short silence.
                "resume_false_interruption": True,
                "false_interruption_timeout": 1.5,
            },
        },
    )

    # ── Turn-lifecycle logging ──────────────────────────────────────────────
    # Surfaces exactly what happens each turn: did the user's speech finalize?
    # did the agent transition listening→thinking→speaking? did the LLM reply or
    # error? This is the difference between "end-of-turn never fired" and "the
    # LLM/graph errored" when the agent doesn't respond.
    @session.on("user_input_transcribed")
    def _on_user_input(ev):
        logger.info("USER transcribed (final=%s): %s",
                    getattr(ev, "is_final", "?"), getattr(ev, "transcript", ev))

    @session.on("user_state_changed")
    def _on_user_state(ev):
        logger.info("USER state: %s -> %s",
                    getattr(ev, "old_state", "?"), getattr(ev, "new_state", "?"))

    @session.on("agent_state_changed")
    def _on_agent_state(ev):
        logger.info("AGENT state: %s -> %s",
                    getattr(ev, "old_state", "?"), getattr(ev, "new_state", "?"))

    @session.on("conversation_item_added")
    def _on_item(ev):
        item = getattr(ev, "item", ev)
        content = getattr(item, "text_content", None) or getattr(item, "content", "")
        logger.info("CONVO item: role=%s text=%s", getattr(item, "role", "?"), str(content)[:160])

    @session.on("close")
    def _on_close(ev):
        logger.info("SESSION closed: %s", getattr(ev, "error", ev))

    await session.start(room=ctx.room, agent=Agent(instructions=""))
    logger.info("AgentSession started in room=%s — waiting for caller", room_name)

    # Wait until the browser participant is actually in the room before greeting,
    # otherwise the greeting audio is spoken into an empty room and lost.
    try:
        await ctx.wait_for_participant()
    except Exception as e:
        logger.debug("wait_for_participant failed (continuing): %s", e)

    greeting = build_greeting(config)
    logger.info("Greeting caller: %s", greeting[:80])
    try:
        # Not interruptible: mic echo / background noise must not cancel the
        # greeting before it's heard (which also drops its transcript).
        handle = session.say(greeting, allow_interruptions=False)
        await handle.wait_for_playout()
        logger.info("Greeting playout complete")
    except Exception as e:
        logger.error("Greeting failed: %s", e)


if __name__ == "__main__":
    agents.cli.run_app(server)
