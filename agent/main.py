"""
LiveKit Voice Agent — The Grand Meridian Palace
Run: make dev && make agent
"""

from dotenv import load_dotenv

from livekit import agents
from livekit.agents import AgentSession, AgentServer
from livekit.plugins import openai, silero

from agent.config import TTS_MODEL, TTS_VOICE, TTS_INSTRUCTIONS, STT_MODEL, LLM_MODEL
from agent.hotel_agent import HotelAgent
from agent.cli import log_event, print_banner

load_dotenv()

server = AgentServer()


@server.rtc_session()
async def entrypoint(ctx: agents.JobContext):
    print_banner()
    log_event("SYSTEM", "Agent session starting...")

    vad = silero.VAD.load()

    session = AgentSession(
        stt=openai.STT(model=STT_MODEL),
        llm=openai.LLM(model=LLM_MODEL),
        tts=openai.TTS(
            model=TTS_MODEL,
            voice=TTS_VOICE,
            instructions=TTS_INSTRUCTIONS,
        ),
        vad=vad,
    )

    agent = HotelAgent()
    await session.start(room=ctx.room, agent=agent)

    log_event("SYSTEM", "Connected to LiveKit room. Waiting for guest...")

    await session.generate_reply(
        instructions=(
            "Greet the caller with a warm Namaste. Introduce yourself as Aria from "
            "The Grand Meridian Palace, Mumbai. Then simply ask: How can I help you today? "
            "Do NOT ask for their name yet — wait to hear what they need first."
        )
    )


if __name__ == "__main__":
    agents.cli.run_app(server)
