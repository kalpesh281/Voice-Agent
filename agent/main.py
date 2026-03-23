from dotenv import load_dotenv

from livekit import agents
from livekit.agents import AgentSession, AgentServer
from livekit.plugins import openai, silero

from agent.hotel_agent import HotelAgent
from agent.cli import log_event, print_banner, print_status

load_dotenv()

server = AgentServer()


@server.rtc_session()
async def entrypoint(ctx: agents.JobContext):
    print_banner()
    log_event("SYSTEM", "Agent session starting...")

    vad = silero.VAD.load()

    session = AgentSession(
        stt=openai.STT(model="gpt-4o-transcribe"),
        llm=openai.LLM(model="gpt-4o"),
        tts=openai.TTS(
            model="gpt-4o-mini-tts",
            voice="shimmer",
            instructions=(
                "Speak warmly and clearly like a 5-star Indian luxury hotel concierge. "
                "Use a calm, gracious pace. Never use symbols or abbreviations. "
                "Pronounce Indian names and places naturally."
            ),
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
