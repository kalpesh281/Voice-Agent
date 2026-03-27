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
from uuid import uuid4

from fastapi import WebSocket, WebSocketDisconnect
from langchain_core.messages import AIMessage, HumanMessage

from app.agent.graph import build_graph
from app.config import settings
from app.db.models import ClientConfig
from app.db.mongo import connect_client
from app.db.repositories.client_repo import ClientRepository
from app.utils.prompt_builder import build_greeting
from app.voice.deepgram_stt import StreamingSTT
from app.voice.deepgram_tts import StreamingTTS

logger = logging.getLogger(__name__)


class WebSocketVoiceSession:
    """Manages a single voice conversation session over WebSocket."""

    def __init__(self, ws: WebSocket, config: ClientConfig, graph):
        self.ws = ws
        self.config = config
        self.graph = graph
        self.thread_id = str(uuid4())
        self.graph_config = {"configurable": {"thread_id": self.thread_id}}
        self.running = False

        self.stt = StreamingSTT(
            api_key=settings.deepgram_api_key,
            model=settings.deepgram_stt_model,
            language=settings.deepgram_stt_language,
            sample_rate=16000,
        )
        self.tts = StreamingTTS(
            api_key=settings.deepgram_api_key,
            model=settings.deepgram_tts_model,
            sample_rate=24000,
        )

    async def send_json(self, msg_type: str, data: dict = {}):
        try:
            await self.ws.send_json({"type": msg_type, **data})
        except Exception:
            pass

    async def run(self):
        """Start the voice session — all tasks run concurrently including greeting."""
        self.running = True

        await self.stt.start()
        await self.tts.start()

        # Run ALL tasks concurrently — greeting is inside _greeting_then_listen
        try:
            await asyncio.gather(
                self._receive_audio_loop(),
                self._greeting_then_listen(),
                self._tts_to_browser_loop(),
            )
        except WebSocketDisconnect:
            logger.info("WebSocket disconnected")
        except Exception as e:
            logger.error("Session error: %s", e)
        finally:
            self.running = False
            await self.stt.stop()
            await self.tts.stop()

    async def _receive_audio_loop(self):
        """Receive audio chunks from browser mic and send to Deepgram STT."""
        while self.running:
            try:
                data = await self.ws.receive()
                if data.get("type") == "websocket.disconnect":
                    break
                if "bytes" in data:
                    await self.stt.send_audio(data["bytes"])
                elif "text" in data:
                    msg = json.loads(data["text"])
                    if msg.get("type") == "stop":
                        break
            except WebSocketDisconnect:
                break
            except Exception as e:
                logger.error("Receive error: %s", e)
                break

        self.running = False

    async def _greeting_then_listen(self):
        """Speak greeting first (TTS audio loop is already running), then listen for transcripts."""
        # Greeting — TTS audio will be picked up by _tts_to_browser_loop running in parallel
        greeting = build_greeting(self.config)
        await self.send_json("state", {"state": "agent_speaking"})
        await self.send_json("agent_message", {"text": greeting})

        await self.tts.synthesize(greeting)
        await self.tts.flush()

        # Wait for TTS audio to drain
        while self.tts.has_audio:
            await asyncio.sleep(0.05)
        await asyncio.sleep(0.5)

        await self.send_json("state", {"state": "listening"})

        # Now enter the main transcript loop
        await self._transcript_loop()

    async def _transcript_loop(self):
        """Wait for STT transcripts, invoke agent, send response to TTS."""
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

            await self.send_json("user_transcript", {"text": transcript})
            await self.send_json("state", {"state": "thinking"})

            try:
                result = await self.graph.ainvoke(
                    {
                        "messages": [HumanMessage(content=transcript)],
                        "client_id": self.config.client_id,
                        "client_config": self.config.model_dump(mode="json"),
                        "pending_booking": None,
                    },
                    config=self.graph_config,
                )

                for msg in result.get("messages", []):
                    if hasattr(msg, "tool_calls") and msg.tool_calls:
                        for tc in msg.tool_calls:
                            await self.send_json("tool_call", {
                                "tool": tc["name"],
                                "args": tc.get("args", {}),
                            })

                    if hasattr(msg, "name") and msg.name:
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
                        except (json.JSONDecodeError, AttributeError):
                            pass

                last_msg = result["messages"][-1]
                if isinstance(last_msg, AIMessage) and last_msg.content:
                    response_text = last_msg.content
                    await self.send_json("state", {"state": "agent_speaking"})
                    await self.send_json("agent_message", {"text": response_text})

                    await self.tts.synthesize(response_text)
                    await self.tts.flush()

                    # Wait for audio to drain
                    while self.tts.has_audio:
                        await asyncio.sleep(0.05)
                    await asyncio.sleep(0.3)

                await self.send_json("state", {"state": "listening"})

            except Exception as e:
                logger.error("Agent error: %s", e)
                await self.send_json("error", {"message": "Something went wrong. Please try again."})
                await self.send_json("state", {"state": "listening"})

    async def _tts_to_browser_loop(self):
        """Forward TTS audio chunks to the browser via WebSocket binary frames."""
        while self.running:
            try:
                chunk = await asyncio.wait_for(
                    self.tts.get_audio_chunk(), timeout=1.0
                )
                await self.ws.send_bytes(chunk)
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

    try:
        client_uri = config.database.connection_uri or settings.client_db_uri or settings.mongodb_uri
        client_db_name = config.database.database_name or settings.client_db_name or settings.mongodb_database
        await connect_client(client_uri, client_db_name)
    except Exception as e:
        await websocket.send_json({"type": "error", "message": f"Failed to connect to client DB: {e}"})
        await websocket.close()
        return

    graph = build_graph(config, settings)

    await websocket.send_json({
        "type": "session_start",
        "client_id": client_id,
        "business_name": config.business.name,
        "agent_name": config.voice.agent_name,
        "category": config.business.category,
    })

    session = WebSocketVoiceSession(websocket, config, graph)
    await session.run()
