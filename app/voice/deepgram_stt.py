"""Deepgram streaming Speech-to-Text via WebSocket.

Uses Deepgram Nova-3 with server-side VAD for real-time transcription.
Audio chunks from the microphone are streamed in, final transcripts come out.
"""

import asyncio
import logging

from deepgram import AsyncDeepgramClient
from deepgram.core.events import EventType
from deepgram.listen.v1.types import (
    ListenV1Finalize,
    ListenV1Results,
    ListenV1SpeechStarted,
    ListenV1UtteranceEnd,
)

logger = logging.getLogger(__name__)


class StreamingSTT:
    """Async streaming speech-to-text using Deepgram WebSocket."""

    def __init__(
        self,
        api_key: str,
        model: str = "nova-3",
        language: str = "en",
        sample_rate: int = 16000,
        encoding: str = "linear16",
    ):
        self._client = AsyncDeepgramClient(api_key=api_key)
        self._model = model
        self._language = language
        self._sample_rate = sample_rate
        self._encoding = encoding
        self._connection = None
        self._listen_task: asyncio.Task | None = None

        # Queues for results
        self._transcript_queue: asyncio.Queue[str] = asyncio.Queue()
        self._is_speaking = False
        self._connected = False

    async def start(self):
        """Open the WebSocket connection and start listening for events."""
        self._connection = self._client.listen.v1.connect(
            model=self._model,
            language=self._language,
            encoding=self._encoding,
            sample_rate=self._sample_rate,
            smart_format=True,
            interim_results=True,
            utterance_end_ms=1500,
            vad_events=True,
            endpointing=300,
            punctuate=True,
        )

        # Enter the async context manager
        self._ws = await self._connection.__aenter__()

        # Register event handlers
        self._ws.on(EventType.MESSAGE, self._on_message)
        self._ws.on(EventType.ERROR, self._on_error)
        self._ws.on(EventType.CLOSE, self._on_close)

        # Start background listener
        self._listen_task = asyncio.create_task(self._ws.start_listening())
        self._connected = True
        logger.info("Deepgram STT connected (model=%s)", self._model)

    async def send_audio(self, chunk: bytes):
        """Send raw PCM audio chunk to Deepgram for transcription."""
        if self._ws and self._connected:
            try:
                await self._ws.send_media(chunk)
            except Exception as e:
                logger.error("Failed to send audio: %s", e)

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

            if data.is_final and transcript.strip():
                self._transcript_queue.put_nowait(transcript.strip())
                logger.debug("Final transcript: %s", transcript.strip())

        elif isinstance(data, ListenV1SpeechStarted):
            self._is_speaking = True
            logger.debug("Speech started")

        elif isinstance(data, ListenV1UtteranceEnd):
            self._is_speaking = False
            logger.debug("Utterance ended")

    def _on_error(self, error):
        logger.error("Deepgram STT error: %s", error)

    def _on_close(self, _data):
        self._connected = False
        logger.info("Deepgram STT connection closed")

    async def finalize(self):
        """Signal end of audio stream (flush remaining transcript)."""
        if self._ws and self._connected:
            try:
                await self._ws.send_finalize(ListenV1Finalize())
            except Exception as e:
                logger.error("Failed to finalize: %s", e)

    async def stop(self):
        """Close the WebSocket connection and clean up."""
        self._connected = False

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
