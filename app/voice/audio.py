"""Async audio I/O using sounddevice.

MicStream: Callback-based mic capture → async queue of PCM bytes.
Speaker: Buffered async playback — accumulates TTS chunks into larger
         buffers before playing for smooth, gapless audio output.
"""

import asyncio
import logging
from collections import deque

import numpy as np
import sounddevice as sd

logger = logging.getLogger(__name__)

# Accumulate at least this much audio before playing (in seconds)
PLAYBACK_BUFFER_SECONDS = 0.5


class MicStream:
    """Async microphone capture using sounddevice callback."""

    def __init__(
        self,
        sample_rate: int = 16000,
        channels: int = 1,
        chunk_size: int = 4096,
        dtype: str = "int16",
    ):
        self._sample_rate = sample_rate
        self._channels = channels
        self._chunk_size = chunk_size
        self._dtype = dtype
        self._stream: sd.InputStream | None = None
        self._queue: asyncio.Queue[bytes] = asyncio.Queue()
        self._loop: asyncio.AbstractEventLoop | None = None
        self._running = False

    def start(self):
        self._loop = asyncio.get_event_loop()
        self._running = True

        self._stream = sd.InputStream(
            samplerate=self._sample_rate,
            channels=self._channels,
            dtype=self._dtype,
            blocksize=self._chunk_size,
            callback=self._audio_callback,
        )
        self._stream.start()
        logger.info("Mic started: %dHz, %dch, chunk=%d", self._sample_rate, self._channels, self._chunk_size)

    def _audio_callback(self, indata: np.ndarray, frames: int, time_info, status):
        if status:
            logger.warning("Mic status: %s", status)
        if self._running and self._loop:
            self._loop.call_soon_threadsafe(self._queue.put_nowait, indata.tobytes())

    async def read_chunk(self) -> bytes:
        return await self._queue.get()

    @property
    def is_active(self) -> bool:
        return self._running and self._stream is not None and self._stream.active

    def stop(self):
        self._running = False
        if self._stream:
            try:
                self._stream.stop()
                self._stream.close()
            except Exception as e:
                logger.debug("Mic stop: %s", e)
            self._stream = None
        logger.info("Mic stopped")


class Speaker:
    """Buffered async speaker — accumulates small TTS chunks into larger
    buffers before playing, eliminating gaps between chunks.

    Uses sounddevice OutputStream with callback for gapless playback.
    """

    def __init__(self, sample_rate: int = 24000, channels: int = 1):
        self._sample_rate = sample_rate
        self._channels = channels
        self._buffer = bytearray()
        self._playing = False
        self._interrupted = False
        self._min_buffer_bytes = int(PLAYBACK_BUFFER_SECONDS * sample_rate * 2)  # 2 bytes per sample (int16)

    async def play_chunk(self, audio_bytes: bytes):
        """Add audio to buffer. Plays when buffer is large enough."""
        if self._interrupted:
            return

        self._buffer.extend(audio_bytes)

        # Only play when we have enough buffered audio
        if len(self._buffer) >= self._min_buffer_bytes:
            await self._flush_buffer()

    async def flush_remaining(self):
        """Play whatever is left in the buffer (call after TTS flush)."""
        if self._buffer and not self._interrupted:
            await self._flush_buffer()

    async def _flush_buffer(self):
        """Play the accumulated buffer as one continuous block."""
        if not self._buffer or self._interrupted:
            return

        self._playing = True
        audio_data = bytes(self._buffer)
        self._buffer.clear()

        try:
            audio_array = np.frombuffer(audio_data, dtype=np.int16).astype(np.float32) / 32768.0
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                None,
                lambda: sd.play(audio_array, samplerate=self._sample_rate, blocking=True),
            )
        except Exception as e:
            if not self._interrupted:
                logger.error("Speaker error: %s", e)
        finally:
            self._playing = False

    def stop_playback(self):
        self._interrupted = True
        self._playing = False
        self._buffer.clear()
        try:
            sd.stop()
        except Exception:
            pass

    def reset(self):
        self._interrupted = False
        self._playing = False
        self._buffer.clear()

    @property
    def is_playing(self) -> bool:
        return self._playing

    @property
    def is_interrupted(self) -> bool:
        return self._interrupted
