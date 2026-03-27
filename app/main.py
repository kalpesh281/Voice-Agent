"""Voice Booking Agent v2.0 — Main entry point.

Supports two modes:
  - text: CLI text chat (for testing without mic/speaker)
  - voice: Full voice conversation (requires Deepgram + PyAudio) [Phase 4]

Usage:
    poetry run python -m app.main              # text mode (default)
    poetry run python -m app.main --mode voice # voice mode (Phase 4)
"""

import asyncio
import logging
import sys
from uuid import uuid4

from langchain_core.messages import AIMessage, HumanMessage

from app.cli.logger import (
    console,
    log_booking_confirmed,
    log_event,
    log_tool_call,
    print_banner,
    print_separator,
)
from app.config import settings
from app.db.mongo import connect_platform, connect_client, disconnect
from app.db.repositories.client_repo import ClientRepository
from app.agent.graph import build_graph
from app.utils.prompt_builder import build_greeting

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    handlers=[logging.StreamHandler()],
)
logger = logging.getLogger(__name__)

# Suppress noisy loggers
for noisy in ["httpx", "httpcore", "openai", "urllib3"]:
    logging.getLogger(noisy).setLevel(logging.WARNING)


async def run_text_mode():
    """Text-based CLI loop for testing the agent without voice."""

    # Connect to platform DB (our data: client configs, bookings)
    try:
        await connect_platform(settings.mongodb_uri, settings.mongodb_database)
    except Exception as e:
        console.print(f"\n  [bold red]Failed to connect to Platform DB:[/bold red] {e}")
        console.print("  Check your MONGODB_URI in .env\n")
        return

    # Load client config from platform DB
    client_repo = ClientRepository()
    config = await client_repo.get_by_id(settings.client_id)
    if not config:
        console.print(f"\n  [bold red]Client '{settings.client_id}' not found.[/bold red]")
        console.print("  Run: [cyan]make seed[/cyan] or use the API to add a client.\n")
        await disconnect()
        return

    # Connect to client's DB (their data: rooms, tables, etc.)
    # Use client's DB config if provided, otherwise fall back to env vars or platform DB
    client_db_uri = config.database.connection_uri or settings.client_db_uri or settings.mongodb_uri
    client_db_name = config.database.database_name or settings.client_db_name or settings.mongodb_database
    try:
        await connect_client(client_db_uri, client_db_name)
    except Exception as e:
        console.print(f"\n  [bold red]Failed to connect to Client DB:[/bold red] {e}")
        console.print(f"  URI: {client_db_uri[:30]}... DB: {client_db_name}\n")
        await disconnect()
        return

    # Build agent graph
    graph = build_graph(config, settings)
    thread_id = str(uuid4())
    graph_config = {"configurable": {"thread_id": thread_id}}

    # Display banner
    print_banner(config.business.name, config.voice.agent_name, config.business.category)

    # Agent greeting
    greeting = build_greeting(config)
    log_event("AGENT", greeting)
    print_separator()

    # Conversation loop
    console.print(
        "\n  [dim]Type your message and press Enter. Type 'quit' or 'exit' to end.[/dim]\n"
    )

    while True:
        try:
            user_input = console.input("  [bold yellow]  YOU  >[/bold yellow]  ")
        except (KeyboardInterrupt, EOFError):
            break

        if user_input.strip().lower() in ("quit", "exit", "q"):
            break

        if not user_input.strip():
            continue

        log_event("USER", user_input.strip())

        try:
            result = await graph.ainvoke(
                {
                    "messages": [HumanMessage(content=user_input.strip())],
                    "client_id": config.client_id,
                    "client_config": config.model_dump(mode="json"),
                    "pending_booking": None,
                },
                config=graph_config,
            )

            # Process messages to find agent response and tool calls
            for msg in result.get("messages", []):
                if hasattr(msg, "tool_calls") and msg.tool_calls:
                    for tc in msg.tool_calls:
                        log_tool_call(tc["name"], tc.get("args", {}))

                if hasattr(msg, "name") and msg.name:
                    # Tool result message — check for booking confirmation
                    try:
                        import json
                        data = json.loads(msg.content)
                        if data.get("success") and data.get("booking_id"):
                            log_booking_confirmed(
                                data["booking_id"],
                                data.get("customer_name", ""),
                                data.get("resource_name", ""),
                            )
                    except (json.JSONDecodeError, AttributeError):
                        pass

            # Get the final AI response
            last_msg = result["messages"][-1]
            if isinstance(last_msg, AIMessage) and last_msg.content:
                log_event("AGENT", last_msg.content)

            print_separator()

        except Exception as e:
            logger.error("Agent error: %s", e, exc_info=True)
            log_event("ERROR", f"Something went wrong: {e}")
            print_separator()

    # Cleanup
    console.print(f"\n  [dim]Goodbye! Thank you for using {config.business.name}.[/dim]\n")
    await disconnect()


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Voice Booking Agent v2.0")
    parser.add_argument(
        "--mode",
        choices=["text", "voice"],
        default="text",
        help="Run mode: text (CLI chat) or voice (mic+speaker)",
    )
    args = parser.parse_args()

    if args.mode == "voice":
        console.print("\n  [yellow]Voice mode coming in Phase 4. Using text mode for now.[/yellow]\n")

    asyncio.run(run_text_mode())


if __name__ == "__main__":
    main()
