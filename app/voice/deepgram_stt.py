"""Deepgram streaming Speech-to-Text via WebSocket.

Uses Deepgram Nova-3 with server-side VAD for real-time transcription.
Audio chunks from the microphone are streamed in, final transcripts come out.
"""

import asyncio
import logging
import time

from deepgram import AsyncDeepgramClient
from deepgram.core.events import EventType
from deepgram.listen.v1.types import (
    ListenV1Finalize,
    ListenV1KeepAlive,
    ListenV1Results,
    ListenV1SpeechStarted,
    ListenV1UtteranceEnd,
)

logger = logging.getLogger(__name__)


class StreamingSTT:
    """Async streaming speech-to-text using Deepgram WebSocket."""

    # Deepgram closes an idle STT socket after ~10s without audio (code 1011).
    # Send a KeepAlive comfortably inside that window.
    _KEEPALIVE_INTERVAL = 5.0

    # Emit a buffered turn this many seconds after the last final segment, as a
    # robust fallback in case UtteranceEnd doesn't arrive. Also sets how long a
    # mid-sentence pause can be before the turn is considered finished. Kept tight
    # for snappy turn-taking; UtteranceEnd (700ms) usually fires first anyway.
    _FLUSH_DELAY = 0.7

    def __init__(
        self,
        api_key: str,
        model: str = "nova-3",
        language: str = "en",
        sample_rate: int = 16000,
        encoding: str = "linear16",
        on_speech_started=None,
    ):
        self._client = AsyncDeepgramClient(api_key=api_key)
        self._model = model
        self._language = language
        self._sample_rate = sample_rate
        self._encoding = encoding
        self._connection = None
        self._ws = None  # set in start(); guard against audio arriving pre-connect
        self._listen_task: asyncio.Task | None = None
        self._keepalive_task: asyncio.Task | None = None
        self._last_audio_sent = 0.0

        # Queues for results
        self._transcript_queue: asyncio.Queue[str] = asyncio.Queue()
        self._is_speaking = False
        self._connected = False

        # Turn detection: accumulate the final segments of one spoken turn and
        # emit them as a SINGLE complete utterance when the user stops talking
        # (Deepgram's UtteranceEnd). Without this, each ~600ms pause produces a
        # separate final that fires its own agent reply — so one sentence gets
        # split into two messages sent back to back.
        self._utterance_buffer: list[str] = []
        self._flush_timer = None  # asyncio TimerHandle — fallback flush

        # Barge-in: fired (once per utterance) the moment real words are heard,
        # so the caller can interrupt the agent if it's currently speaking.
        self._on_speech_started = on_speech_started
        self._fired_speech_started = False

    async def start(self):
        """Open the WebSocket connection and start listening for events."""
        # Note: SDK v6 requires string 'true' not Python True for boolean params
        self._connection = self._client.listen.v1.connect(
            model=self._model,
            language=self._language,
            encoding=self._encoding,
            sample_rate=self._sample_rate,
            smart_format="true",
            interim_results="true",
            # End-of-turn detection: fire UtteranceEnd after 700ms of silence.
            # We buffer finals until then, so brief mid-sentence pauses don't
            # split a turn, while keeping the response snappy enough to feel live.
            utterance_end_ms="700",
            vad_events="true",
            endpointing=300,
            punctuate="true",
            numerals="true",  # render dates/counts as digits (booking context)
        )

        # Enter the async context manager
        self._ws = await self._connection.__aenter__()

        # Register event handlers
        self._ws.on(EventType.MESSAGE, self._on_message)
        self._ws.on(EventType.ERROR, self._on_error)
        self._ws.on(EventType.CLOSE, self._on_close)

        # Start background listener
        self._listen_task = asyncio.create_task(self._ws.start_listening())
        # Keep the socket warm during silence (greeting, agent turns, user pauses)
        self._last_audio_sent = time.monotonic()
        self._keepalive_task = asyncio.create_task(self._keepalive_loop())
        self._connected = True
        logger.info("Deepgram STT connected (model=%s)", self._model)

    async def send_audio(self, chunk: bytes):
        """Send raw PCM audio chunk to Deepgram for transcription."""
        if self._ws and self._connected:
            try:
                await self._ws.send_media(chunk)
                self._last_audio_sent = time.monotonic()
            except Exception as e:
                logger.error("Failed to send audio: %s", e)

    async def _keepalive_loop(self):
        """Send periodic KeepAlive frames so Deepgram doesn't drop an idle socket.

        Without this, Deepgram closes the STT connection with code 1011
        ("did not receive audio data within the timeout window") whenever no
        mic audio is forwarded for ~10s — which happens during the greeting,
        while the agent is speaking, or when the user simply pauses. A dropped
        socket never recovers, so transcription silently dies mid-session.
        """
        try:
            while self._connected:
                await asyncio.sleep(self._KEEPALIVE_INTERVAL)
                if not self._connected or not self._ws:
                    break
                # If audio is actively flowing, the stream is already kept alive.
                if (time.monotonic() - self._last_audio_sent) < self._KEEPALIVE_INTERVAL:
                    continue
                try:
                    await self._ws.send_keep_alive(ListenV1KeepAlive(type="KeepAlive"))
                    logger.debug("STT keep-alive sent")
                except Exception as e:
                    logger.debug("STT keep-alive failed: %s", e)
        except asyncio.CancelledError:
            pass

    async def get_transcript(self) -> str:
        """Block until a final transcript is available."""
        return await self._transcript_queue.get()

    def get_transcript_nowait(self) -> str | None:
        """Non-blocking: return transcript if available, else None."""
        try:
            return self._transcript_queue.get_nowait()
        except asyncio.QueueEmpty:
            return None

    @property
    def is_speaking(self) -> bool:
        """Whether Deepgram's VAD detects the user is currently speaking."""
        return self._is_speaking

    def _on_message(self, data):
        """Handle incoming messages from Deepgram."""
        if isinstance(data, ListenV1Results):
            transcript = ""
            if data.channel and data.channel.alternatives:
                transcript = data.channel.alternatives[0].transcript or ""
            transcript = transcript.strip()

            # Real words detected (interim or final) → signal barge-in once per
            # turn. Gating on a couple of actual words (not bare VAD, not a
            # single token) makes this robust against the agent's own echo
            # bleeding into the mic and tripping a false interruption.
            if (
                not self._fired_speech_started
                and len(transcript.split()) >= 2
            ):
                self._fired_speech_started = True
                self._is_speaking = True
                self._notify_speech_started()

            # Buffer final segments; the complete turn is emitted on UtteranceEnd
            # or, as a fallback, _FLUSH_DELAY after the last final.
            if data.is_final and transcript:
                self._utterance_buffer.append(transcript)
                self._restart_flush_timer()

        elif isinstance(data, ListenV1SpeechStarted):
            self._is_speaking = True
            logger.debug("Speech started")

        elif isinstance(data, ListenV1UtteranceEnd):
            self._is_speaking = False
            self._flush_utterance()
            logger.debug("Utterance ended")

    def _flush_utterance(self):
        """Join the buffered final segments and emit them as one utterance."""
        self._cancel_flush_timer()
        self._fired_speech_started = False
        if not self._utterance_buffer:
            return
        full = " ".join(self._utterance_buffer).strip()
        self._utterance_buffer = []
        if full:
            self._transcript_queue.put_nowait(full)
            logger.debug("Utterance: %s", full)

    def _restart_flush_timer(self):
        """(Re)arm the fallback flush timer; resets on each new final segment."""
        self._cancel_flush_timer()
        try:
            loop = asyncio.get_running_loop()
            self._flush_timer = loop.call_later(self._FLUSH_DELAY, self._flush_utterance)
        except RuntimeError:
            pass

    def _cancel_flush_timer(self):
        if self._flush_timer is not None:
            self._flush_timer.cancel()
            self._flush_timer = None

    def _notify_speech_started(self):
        """Schedule the barge-in callback on the running event loop."""
        if not self._on_speech_started:
            return
        try:
            asyncio.get_running_loop().create_task(self._on_speech_started())
        except RuntimeError:
            pass

    def _on_error(self, error):
        logger.error("Deepgram STT error: %s", error)

    def _on_close(self, _data):
        self._connected = False
        logger.info("Deepgram STT connection closed")

    async def finalize(self):
        """Signal end of audio stream (flush remaining transcript)."""
        if self._ws and self._connected:
            try:
                await self._ws.send_finalize(ListenV1Finalize(type="Finalize"))
            except Exception as e:
                logger.error("Failed to finalize: %s", e)

    async def stop(self):
        """Close the WebSocket connection and clean up."""
        self._connected = False
        self._cancel_flush_timer()

        if self._keepalive_task and not self._keepalive_task.done():
            self._keepalive_task.cancel()
            try:
                await self._keepalive_task
            except (asyncio.CancelledError, Exception):
                pass

        if self._listen_task and not self._listen_task.done():
            self._listen_task.cancel()
            try:
                await self._listen_task
            except (asyncio.CancelledError, Exception):
                pass

        if self._connection:
            try:
                await self._connection.__aexit__(None, None, None)
            except Exception as e:
                logger.debug("STT cleanup: %s", e)

        self._ws = None
        self._connection = None
        logger.info("Deepgram STT stopped")
