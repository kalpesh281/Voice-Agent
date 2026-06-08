"""WebSocket endpoint for browser-based voice conversations.

Flow:
  Browser mic → audio chunks (binary) → WebSocket → Deepgram STT → transcript
  → LangGraph Agent → response text → Deepgram TTS → audio chunks (binary) → WebSocket → Browser speaker

JSON control messages for:
  - transcripts, agent responses, tool calls, booking confirmations
  - state updates (listening, thinking, speaking)
"""

import asyncio
import json
import logging
import re
import time
from uuid import uuid4

from fastapi import WebSocket, WebSocketDisconnect
from langchain_core.messages import AIMessage, AIMessageChunk, HumanMessage

from app.agent.graph import build_graph
from app.config import settings
from app.db.models import ClientConfig
from app.db.mongo import connect_client
from app.db.repositories.client_repo import ClientRepository
from app.utils.prompt_builder import build_greeting
from app.voice.deepgram_stt import StreamingSTT
from app.voice.deepgram_tts import StreamingTTS

logger = logging.getLogger(__name__)

# Break streamed LLM text at sentence boundaries so we can start speaking the
# first sentence while the rest is still being generated.
_SENTENCE_BOUNDARY = re.compile(r"[.!?](\s|$)")


class WebSocketVoiceSession:
    """Manages a single voice conversation session over WebSocket."""

    def __init__(self, ws: WebSocket, config: ClientConfig):
        self.ws = ws
        self.config = config
        self.graph = None  # built in the background by _setup() while greeting plays
        self.setup_error = None
        self.thread_id = str(uuid4())
        self.graph_config = {"configurable": {"thread_id": self.thread_id}}
        self.running = False
        self.agent_speaking = False  # for barge-in: is the agent talking right now?
        self.tts_bytes_sent = 0      # cumulative TTS audio forwarded to the browser
        self._tts_sr = 24000         # TTS sample rate (linear16 → 2 bytes/sample)
        self._speak_bytes_before = 0 # tts_bytes_sent snapshot when current turn began
        self._speak_t_start = 0.0    # monotonic time the current turn began speaking

        self.stt = StreamingSTT(
            api_key=settings.deepgram_api_key,
            model=settings.deepgram_stt_model,
            language=settings.deepgram_stt_language,
            sample_rate=16000,
            on_speech_started=self._handle_barge_in,
        )
        self.tts = StreamingTTS(
            api_key=settings.deepgram_api_key,
            model=settings.deepgram_tts_model,
            sample_rate=24000,
        )

    async def _handle_barge_in(self):
        """User started talking while the agent was speaking → stop the agent.

        Fired from STT the moment real words are detected. We drop the queued
        TTS audio and tell the browser to stop playback immediately, so the
        user can cut in naturally (like a real phone call / Gemini voice).
        """
        if not self.agent_speaking:
            return
        self.agent_speaking = False
        logger.debug("Barge-in: stopping agent speech")
        try:
            await self.tts.clear()  # drop queued + in-flight TTS audio
        except Exception:
            pass
        await self.send_json("interrupt", {})
        await self.send_json("state", {"state": "listening"})

    def _begin_speaking(self):
        """Mark the start of an agent turn (records timing for playback hold)."""
        self.agent_speaking = True
        self._speak_bytes_before = self.tts_bytes_sent
        self._speak_t_start = time.monotonic()

    async def _feed_tts(self, text: str):
        """Send a chunk of text to TTS mid-turn (no-op if barged in)."""
        text = text.strip()
        if not text or not self.agent_speaking:
            return
        await self.tts.synthesize(text)

    async def _finish_speaking(self):
        """Flush TTS and stay 'speaking' for the real playback duration.

        The server-side TTS queue drains to the browser in well under a second,
        but the browser plays that audio in real time (several seconds). If we
        only waited for the queue to empty, barge-in would be impossible for
        most of the utterance — so we hold `agent_speaking` for the actual audio
        duration (derived from bytes streamed), abortable by barge-in.
        """
        if not self.agent_speaking:
            return  # barge-in already stopped us
        await self.tts.flush()

        # Wait until every chunk has been handed to the browser (or barged in).
        while self.tts.has_audio and self.agent_speaking:
            await asyncio.sleep(0.05)
        if not self.agent_speaking:
            return

        # Hold for the remaining real-time playback (+ small pipeline buffer).
        playback_secs = (self.tts_bytes_sent - self._speak_bytes_before) / (self._tts_sr * 2)
        while self.agent_speaking and (time.monotonic() - self._speak_t_start) < playback_secs + 0.3:
            await asyncio.sleep(0.05)
        self.agent_speaking = False

    async def _speak(self, text: str):
        """Speak a complete block of text (used for the greeting)."""
        self._begin_speaking()
        await self._feed_tts(text)
        await self._finish_speaking()

    async def _feed_sentences(self, buffer: str) -> str:
        """Speak any complete sentences in `buffer`; return the trailing partial.

        Called as LLM tokens stream in so the agent starts talking the first
        sentence while later sentences are still being generated.
        """
        if not self.agent_speaking:
            return ""  # barged in — stop accumulating
        while True:
            m = _SENTENCE_BOUNDARY.search(buffer)
            if not m:
                break
            end = m.start() + 1
            sentence = buffer[:end].strip()
            buffer = buffer[end:].lstrip()
            if sentence:
                await self._feed_tts(sentence)
        return buffer

    async def send_json(self, msg_type: str, data: dict = {}):
        try:
            await self.ws.send_json({"type": msg_type, **data})
        except Exception:
            pass

    async def run(self):
        """Start the voice session.

        The greeting is a static template that needs nothing but the config, so
        we bring up TTS and speak immediately. The slow setup — client DB
        connect (Atlas TLS), agent graph build, and STT socket — runs in the
        background while the greeting plays, so the user hears the agent within
        ~2s instead of waiting ~10s for everything to initialize.
        """
        self.running = True

        await self.tts.start()
        setup_task = asyncio.create_task(self._setup())

        try:
            await asyncio.gather(
                self._tts_to_browser_loop(),
                self._greeting_then_listen(setup_task),
                self._receive_audio_loop(),
            )
        except WebSocketDisconnect:
            logger.info("WebSocket disconnected")
        except Exception as e:
            logger.error("Session error: %s", e)
        finally:
            self.running = False
            if not setup_task.done():
                setup_task.cancel()
            await self.stt.stop()
            await self.tts.stop()

    async def _setup(self):
        """Background initialization that the greeting does not depend on.

        STT, the client DB connection, and the agent graph are mutually
        independent (the repos resolve the client DB lazily at call time), so we
        start all three concurrently. This makes the mic live within ~2-3s —
        well before the greeting finishes — instead of ~12s, and roughly halves
        total setup versus doing them serially.
        """

        async def _start_stt():
            try:
                await self.stt.start()
            except Exception as e:
                logger.error("Voice setup — STT start failed: %s", e)
                self.setup_error = "I'm having trouble hearing you right now."

        async def _connect_db():
            cfg = self.config
            client_uri = cfg.database.connection_uri or settings.client_db_uri or settings.mongodb_uri
            client_db_name = cfg.database.database_name or settings.client_db_name or settings.mongodb_database
            try:
                await connect_client(client_uri, client_db_name)
            except Exception as e:
                logger.error("Voice setup — client DB connect failed: %s", e)
                self.setup_error = "I'm having trouble reaching the booking system right now."

        async def _build_graph():
            try:
                # build_graph opens a synchronous Mongo checkpointer — keep it off the loop.
                self.graph = await asyncio.to_thread(build_graph, self.config, settings)
            except Exception as e:
                logger.error("Voice setup — graph build failed: %s", e)
                self.setup_error = "I'm having trouble starting up. Please try again in a moment."

        await asyncio.gather(_start_stt(), _connect_db(), _build_graph())

    async def _receive_audio_loop(self):
        """Receive audio chunks from browser mic and send to Deepgram STT."""
        while self.running:
            try:
                data = await self.ws.receive()
            except WebSocketDisconnect:
                break
            except Exception as e:
                logger.error("Receive error: %s", e)
                break

            if data.get("type") == "websocket.disconnect":
                break
            if "bytes" in data:
                # send_audio guards itself (no-ops until STT is connected) and never
                # raises — a transient send issue must not kill the receive loop.
                await self.stt.send_audio(data["bytes"])
            elif "text" in data:
                try:
                    msg = json.loads(data["text"])
                except (ValueError, TypeError):
                    continue
                if msg.get("type") == "stop":
                    break

        self.running = False

    async def _greeting_then_listen(self, setup_task):
        """Speak greeting first (TTS audio loop is already running), then listen for transcripts."""
        # Greeting — TTS audio will be picked up by _tts_to_browser_loop running in parallel
        greeting = build_greeting(self.config)
        await self.send_json("state", {"state": "agent_speaking"})
        await self.send_json("agent_message", {"text": greeting})

        await self._speak(greeting)

        # Background setup (DB, graph, STT) usually finishes during the greeting;
        # make sure it's done before we start listening for the user.
        try:
            await setup_task
        except Exception as e:
            logger.error("Voice setup task error: %s", e)

        if self.graph is None:
            await self.send_json("error", {"message": self.setup_error or "Setup failed. Please reconnect."})

        await self.send_json("state", {"state": "listening"})

        # Now enter the main transcript loop
        await self._transcript_loop()

    async def _transcript_loop(self):
        """Wait for STT transcripts, invoke agent, send response to TTS.

        STT already emits one complete utterance per turn (buffered until the
        user stops talking), so this only needs a short merge window to catch
        the rare case where a turn spans two UtteranceEnd events.
        """
        DEBOUNCE_SECONDS = 0.2

        while self.running:
            try:
                transcript = await asyncio.wait_for(
                    self.stt.get_transcript(), timeout=1.0
                )
            except asyncio.TimeoutError:
                continue
            except Exception:
                break

            if not transcript:
                continue

            # Debounce: accumulate fragments if user is still speaking
            accumulated = transcript
            while True:
                try:
                    more = await asyncio.wait_for(
                        self.stt.get_transcript(), timeout=DEBOUNCE_SECONDS
                    )
                    if more:
                        accumulated = f"{accumulated} {more}"
                except asyncio.TimeoutError:
                    break

            transcript = accumulated

            await self.send_json("user_transcript", {"text": transcript})

            # Setup may have failed (DB/graph) — don't crash the loop on a None graph.
            if self.graph is None:
                await self.send_json("error", {"message": self.setup_error or "Agent isn't ready yet."})
                await self.send_json("state", {"state": "listening"})
                continue

            await self.send_json("state", {"state": "thinking"})

            try:
                await self._run_agent_streaming(transcript)
                await self.send_json("state", {"state": "listening"})
            except Exception as e:
                logger.error("Agent error: %s", e)
                self.agent_speaking = False
                await self.send_json("error", {"message": "Something went wrong. Please try again."})
                await self.send_json("state", {"state": "listening"})

    async def _run_agent_streaming(self, transcript: str):
        """Stream the agent's reply token-by-token and speak it as it arrives.

        We start synthesizing the first sentence the moment it's complete, so the
        caller hears the agent within ~1s of finishing their turn instead of
        waiting for the whole reply to be generated — the key to a snappy,
        Gemini-like feel. Tool-call / booking side events are emitted from the
        node updates that stream alongside the tokens.
        """
        spoke_state = False
        response_parts: list[str] = []
        sentence_buf = ""

        async for mode, data in self.graph.astream(
            {
                "messages": [HumanMessage(content=transcript)],
                "client_id": self.config.client_id,
                "client_config": self.config.model_dump(mode="json"),
                "pending_booking": None,
            },
            config=self.graph_config,
            stream_mode=["messages", "updates"],
        ):
            if mode == "messages":
                msg_chunk, _meta = data
                if isinstance(msg_chunk, AIMessageChunk) and isinstance(msg_chunk.content, str) and msg_chunk.content:
                    if not spoke_state:
                        self._begin_speaking()
                        await self.send_json("state", {"state": "agent_speaking"})
                        spoke_state = True
                    response_parts.append(msg_chunk.content)
                    sentence_buf += msg_chunk.content
                    sentence_buf = await self._feed_sentences(sentence_buf)
                continue

            # mode == "updates": complete node outputs (tool calls + tool results)
            for _node, payload in (data or {}).items():
                for msg in payload.get("messages", []) if isinstance(payload, dict) else []:
                    if getattr(msg, "tool_calls", None):
                        for tc in msg.tool_calls:
                            await self.send_json("tool_call", {
                                "tool": tc["name"],
                                "args": tc.get("args", {}),
                            })
                    if getattr(msg, "name", None):
                        try:
                            d = json.loads(msg.content)
                            if d.get("success") and d.get("booking_id"):
                                await self.send_json("booking_confirmed", d)
                            elif d.get("results"):
                                await self.send_json("search_results", d)
                            elif d.get("resource"):
                                await self.send_json("resource_details", d)
                            elif d.get("available") is not None:
                                await self.send_json("availability", d)
                        except (json.JSONDecodeError, AttributeError, TypeError):
                            pass

        # Speak whatever's left in the buffer and finalize the turn.
        if sentence_buf.strip() and self.agent_speaking:
            await self._feed_tts(sentence_buf)

        full_text = "".join(response_parts).strip()
        if full_text:
            await self.send_json("agent_message", {"text": full_text})

        if spoke_state:
            await self._finish_speaking()

    async def _tts_to_browser_loop(self):
        """Forward TTS audio chunks to the browser via WebSocket binary frames."""
        while self.running:
            try:
                chunk = await asyncio.wait_for(
                    self.tts.get_audio_chunk(), timeout=1.0
                )
                await self.ws.send_bytes(chunk)
                self.tts_bytes_sent += len(chunk)
            except asyncio.TimeoutError:
                continue
            except Exception:
                break


async def voice_websocket_endpoint(websocket: WebSocket, client_id: str):
    """WebSocket endpoint handler."""
    await websocket.accept()

    repo = ClientRepository()
    config = await repo.get_by_id(client_id)
    if not config:
        await websocket.send_json({"type": "error", "message": f"Client '{client_id}' not found"})
        await websocket.close()
        return

    # Send session_start immediately and let the session greet right away.
    # Client DB connect + graph build happen in the background (see _setup),
    # so the greeting isn't blocked behind ~10s of Atlas/graph startup.
    await websocket.send_json({
        "type": "session_start",
        "client_id": client_id,
        "business_name": config.business.name,
        "agent_name": config.voice.agent_name,
        "category": config.business.category,
    })

    session = WebSocketVoiceSession(websocket, config)
    await session.run()
