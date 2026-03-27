"""Voice pipeline — orchestrates mic, Deepgram STT/TTS, and LangGraph agent.

Three concurrent async tasks:
  1. Capture loop: mic → Deepgram STT
  2. Agent loop:   transcript → LangGraph → Deepgram TTS
  3. Playback loop: TTS audio → speaker

Supports barge-in: if user speaks while agent is talking,
speaker stops and new input is processed.
"""

import asyncio
import json
import logging
from uuid import uuid4

from langchain_core.messages import AIMessage, HumanMessage

from app.cli.display import VoiceDisplay
from app.cli.logger import log_booking_confirmed, log_event, log_tool_call
from app.config import Settings
from app.db.models import ClientConfig
from app.utils.prompt_builder import build_greeting
from app.voice.audio import MicStream, Speaker
from app.voice.deepgram_stt import StreamingSTT
from app.voice.deepgram_tts import StreamingTTS

logger = logging.getLogger(__name__)


class VoicePipeline:
    """Full-duplex voice conversation pipeline."""

    def __init__(
        self,
        settings: Settings,
        client_config: ClientConfig,
        graph,
    ):
        self._settings = settings
        self._config = client_config
        self._graph = graph
        self._thread_id = str(uuid4())

        # Voice components
        self._stt = StreamingSTT(
            api_key=settings.deepgram_api_key,
            model=settings.deepgram_stt_model,
            language=settings.deepgram_stt_language,
            sample_rate=settings.mic_sample_rate,
        )
        self._tts = StreamingTTS(
            api_key=settings.deepgram_api_key,
            model=settings.deepgram_tts_model,
        )
        self._mic = MicStream(
            sample_rate=settings.mic_sample_rate,
            channels=settings.mic_channels,
            chunk_size=settings.mic_chunk_size,
        )
        self._speaker = Speaker(sample_rate=24000)

        # Display
        self._display = VoiceDisplay(
            business_name=client_config.business.name,
            agent_name=client_config.voice.agent_name,
            category=client_config.business.category,
        )

        # State
        self._running = False
        self._agent_speaking = False
        self._greeting_text = build_greeting(client_config)

    async def run(self):
        """Start all components and run the voice conversation loop."""
        self._running = True

        # Start Deepgram connections
        await self._stt.start()
        await self._tts.start()

        # Start microphone
        self._mic.start()

        # Run all loops concurrently (greeting is handled inside agent loop)
        live = self._display.start()
        try:
            with live:
                self._display.update_state("AGENT_SPEAKING")
                await asyncio.gather(
                    self._capture_loop(),
                    self._greeting_then_agent_loop(),
                    self._playback_loop(),
                )
        except asyncio.CancelledError:
            pass
        finally:
            await self._shutdown()

    async def _capture_loop(self):
        """Continuously reads mic chunks and sends to Deepgram STT."""
        while self._running:
            try:
                chunk = await self._mic.read_chunk()
                await self._stt.send_audio(chunk)

                # Update waveform display
                self._display.update_waveform(chunk)

                # Barge-in detection: user speaks while agent is talking
                if self._agent_speaking and self._stt.is_speaking:
                    logger.info("Barge-in detected — stopping agent speech")
                    self._speaker.stop_playback()
                    await self._tts.clear()
                    self._agent_speaking = False
                    self._display.update_state("YOU_SPEAKING")

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error("Capture loop error: %s", e)
                await asyncio.sleep(0.1)

    async def _greeting_then_agent_loop(self):
        """First speaks the greeting, then enters the main agent loop."""
        # Speak greeting (playback loop is already running in parallel)
        log_event("AGENT", self._greeting_text)
        await self._speak(self._greeting_text)
        self._display.update_state("LISTENING")

        # Now run the agent loop
        await self._agent_loop()

    async def _agent_loop(self):
        """Waits for transcripts, invokes the LangGraph agent, sends response to TTS."""
        graph_config = {"configurable": {"thread_id": self._thread_id}}

        while self._running:
            try:
                # Wait for a final transcript from STT
                transcript = await self._stt.get_transcript()
                if not transcript:
                    continue

                self._display.update_state("THINKING")
                self._display.update_transcript(transcript)
                log_event("USER", transcript)

                # Invoke the LangGraph agent
                result = await self._graph.ainvoke(
                    {
                        "messages": [HumanMessage(content=transcript)],
                        "client_id": self._config.client_id,
                        "client_config": self._config.model_dump(mode="json"),
                        "pending_booking": None,
                    },
                    config=graph_config,
                )

                # Process messages for tool calls and booking confirmations
                for msg in result.get("messages", []):
                    if hasattr(msg, "tool_calls") and msg.tool_calls:
                        for tc in msg.tool_calls:
                            log_tool_call(tc["name"], tc.get("args", {}))

                    if hasattr(msg, "name") and msg.name:
                        try:
                            data = json.loads(msg.content)
                            if data.get("success") and data.get("booking_id"):
                                log_booking_confirmed(
                                    data["booking_id"],
                                    data.get("customer_name", ""),
                                    data.get("resource_name", ""),
                                )
                        except (json.JSONDecodeError, AttributeError):
                            pass

                # Get the final AI response text
                last_msg = result["messages"][-1]
                if isinstance(last_msg, AIMessage) and last_msg.content:
                    response_text = last_msg.content
                    log_event("AGENT", response_text)
                    await self._speak(response_text)

                self._display.update_state("LISTENING")
                self._display.clear_waveform()

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error("Agent loop error: %s", e)
                self._display.update_state("LISTENING")

    async def _playback_loop(self):
        """Reads audio chunks from TTS and plays them through the speaker."""
        while self._running:
            try:
                audio_chunk = await self._tts.get_audio_chunk()

                # Skip if interrupted (barge-in)
                if self._speaker.is_interrupted:
                    continue

                await self._speaker.play_chunk(audio_chunk)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error("Playback loop error: %s", e)
                await asyncio.sleep(0.1)

    async def _speak(self, text: str):
        """Send text to TTS and wait for playback to finish."""
        self._agent_speaking = True
        self._speaker.reset()
        self._display.update_state("AGENT_SPEAKING")

        await self._tts.synthesize(text)
        await self._tts.flush()

        # Wait for TTS queue to drain into speaker buffer
        while self._tts.has_audio:
            if self._speaker.is_interrupted:
                break
            await asyncio.sleep(0.05)

        # Flush any remaining buffered audio in speaker
        await self._speaker.flush_remaining()

        # Wait for playback to finish
        while self._speaker.is_playing:
            if self._speaker.is_interrupted:
                break
            await asyncio.sleep(0.05)

        self._agent_speaking = False

    async def _shutdown(self):
        """Clean shutdown of all components."""
        self._running = False
        self._mic.stop()
        self._speaker.stop_playback()
        await self._stt.stop()
        await self._tts.stop()
        logger.info("Voice pipeline shut down")
