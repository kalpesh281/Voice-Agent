"""Async audio I/O using sounddevice.

MicStream: Callback-based mic capture → async queue of PCM bytes.
Speaker: Async playback of PCM audio chunks via executor.
"""

import asyncio
import logging
from collections.abc import Callable

import numpy as np
import sounddevice as sd

logger = logging.getLogger(__name__)


class MicStream:
    """Async microphone capture using sounddevice callback.

    Audio chunks (raw PCM int16 bytes) are pushed into an async queue
    from the sounddevice audio thread via call_soon_threadsafe.
    """

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
        """Start capturing audio from the default microphone."""
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
        logger.info(
            "Mic started: %dHz, %dch, chunk=%d",
            self._sample_rate, self._channels, self._chunk_size,
        )

    def _audio_callback(self, indata: np.ndarray, frames: int, time_info, status):
        """Called from sounddevice's audio thread — push bytes to async queue."""
        if status:
            logger.warning("Mic status: %s", status)
        if self._running and self._loop:
            pcm_bytes = indata.tobytes()
            self._loop.call_soon_threadsafe(self._queue.put_nowait, pcm_bytes)

    async def read_chunk(self) -> bytes:
        """Block until the next audio chunk is available."""
        return await self._queue.get()

    def read_chunk_nowait(self) -> bytes | None:
        """Non-blocking: return chunk if available, else None."""
        try:
            return self._queue.get_nowait()
        except asyncio.QueueEmpty:
            return None

    @property
    def is_active(self) -> bool:
        return self._running and self._stream is not None and self._stream.active

    def stop(self):
        """Stop the microphone stream."""
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
    """Async speaker output — plays PCM audio chunks.

    Uses run_in_executor for non-blocking playback.
    Supports interruption via stop_playback().
    """

    def __init__(
        self,
        sample_rate: int = 24000,
        channels: int = 1,
        dtype: str = "int16",
    ):
        self._sample_rate = sample_rate
        self._channels = channels
        self._dtype = dtype
        self._playing = False
        self._interrupted = False

    async def play_chunk(self, audio_bytes: bytes):
        """Play a single audio chunk. Runs in executor to avoid blocking."""
        if self._interrupted:
            return

        self._playing = True
        loop = asyncio.get_event_loop()
        try:
            audio_array = np.frombuffer(audio_bytes, dtype=np.int16)
            if self._channels == 1:
                audio_array = audio_array.reshape(-1, 1)

            await loop.run_in_executor(
                None,
                lambda: sd.play(audio_array, samplerate=self._sample_rate, blocking=True),
            )
        except Exception as e:
            if not self._interrupted:
                logger.error("Speaker playback error: %s", e)
        finally:
            self._playing = False

    def stop_playback(self):
        """Immediately stop any playing audio (for barge-in)."""
        self._interrupted = True
        self._playing = False
        try:
            sd.stop()
        except Exception:
            pass

    def reset(self):
        """Reset after interruption — allow playback again."""
        self._interrupted = False
        self._playing = False

    @property
    def is_playing(self) -> bool:
        return self._playing

    @property
    def is_interrupted(self) -> bool:
        return self._interrupted
