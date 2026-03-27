"""Deepgram streaming Text-to-Speech via WebSocket.

Uses Deepgram Aura for real-time TTS.
Text goes in, audio chunks come out as they're synthesized (true streaming).
"""

import asyncio
import logging

from deepgram import AsyncDeepgramClient
from deepgram.core.events import EventType
from deepgram.speak.v1.types import (
    SpeakV1Clear,
    SpeakV1Close,
    SpeakV1Flush,
    SpeakV1Flushed,
    SpeakV1Metadata,
    SpeakV1Text,
    SpeakV1Warning,
)

logger = logging.getLogger(__name__)


class StreamingTTS:
    """Async streaming text-to-speech using Deepgram WebSocket."""

    def __init__(
        self,
        api_key: str,
        model: str = "aura-asteria-en",
        sample_rate: int = 24000,
        encoding: str = "linear16",
    ):
        self._client = AsyncDeepgramClient(api_key=api_key)
        self._model = model
        self._sample_rate = sample_rate
        self._encoding = encoding
        self._connection = None
        self._ws = None
        self._listen_task: asyncio.Task | None = None

        # Queue for audio output chunks
        self._audio_queue: asyncio.Queue[bytes] = asyncio.Queue()
        self._connected = False
        self._flushed_event = asyncio.Event()

    async def start(self):
        """Open the WebSocket connection and start listening for audio."""
        self._connection = self._client.speak.v1.connect(
            model=self._model,
            encoding=self._encoding,
            sample_rate=self._sample_rate,
        )

        self._ws = await self._connection.__aenter__()

        # Register event handlers
        self._ws.on(EventType.MESSAGE, self._on_message)
        self._ws.on(EventType.ERROR, self._on_error)
        self._ws.on(EventType.CLOSE, self._on_close)

        # Start background listener
        self._listen_task = asyncio.create_task(self._ws.start_listening())
        self._connected = True
        logger.info("Deepgram TTS connected (model=%s)", self._model)

    async def synthesize(self, text: str):
        """Send text for synthesis. Audio chunks arrive via _on_message."""
        if not self._ws or not self._connected:
            logger.warning("TTS not connected, skipping synthesis")
            return

        try:
            msg = SpeakV1Text(type="Speak", text=text)
            await self._ws.send_text(msg)
        except Exception as e:
            logger.error("Failed to send text for synthesis: %s", e)

    async def flush(self):
        """Flush pending audio — waits until all queued text is synthesized."""
        if not self._ws or not self._connected:
            return

        try:
            self._flushed_event.clear()
            msg = SpeakV1Flush(type="Flush")
            await self._ws.send_flush(msg)
            try:
                await asyncio.wait_for(self._flushed_event.wait(), timeout=10.0)
            except asyncio.TimeoutError:
                logger.warning("TTS flush timeout")
        except Exception as e:
            logger.error("Failed to flush TTS: %s", e)

    async def clear(self):
        """Clear any buffered audio (used for barge-in/interruption)."""
        if not self._ws or not self._connected:
            return

        try:
            msg = SpeakV1Clear(type="Clear")
            await self._ws.send_clear(msg)
            # Drain the audio queue
            while not self._audio_queue.empty():
                try:
                    self._audio_queue.get_nowait()
                except asyncio.QueueEmpty:
                    break
        except Exception as e:
            logger.error("Failed to clear TTS buffer: %s", e)

    async def get_audio_chunk(self) -> bytes:
        """Block until an audio chunk is available."""
        return await self._audio_queue.get()

    def get_audio_chunk_nowait(self) -> bytes | None:
        """Non-blocking: return audio chunk if available, else None."""
        try:
            return self._audio_queue.get_nowait()
        except asyncio.QueueEmpty:
            return None

    @property
    def has_audio(self) -> bool:
        return not self._audio_queue.empty()

    def _on_message(self, data):
        """Handle incoming messages from Deepgram TTS."""
        if isinstance(data, bytes):
            self._audio_queue.put_nowait(data)
        elif isinstance(data, SpeakV1Flushed):
            self._flushed_event.set()
            logger.debug("TTS flushed")
        elif isinstance(data, SpeakV1Metadata):
            logger.debug("TTS metadata: %s", data)
        elif isinstance(data, SpeakV1Warning):
            logger.warning("TTS warning: %s", data)

    def _on_error(self, error):
        logger.error("Deepgram TTS error: %s", error)

    def _on_close(self, _data):
        self._connected = False
        logger.info("Deepgram TTS connection closed")

    async def stop(self):
        """Close the WebSocket connection and clean up."""
        self._connected = False

        if self._ws:
            try:
                msg = SpeakV1Close(type="Close")
                await self._ws.send_close(msg)
            except Exception:
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
                logger.debug("TTS cleanup: %s", e)

        self._ws = None
        self._connection = None
        logger.info("Deepgram TTS stopped")
