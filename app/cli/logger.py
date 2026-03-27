"""Rich-based CLI event logging for the voice booking agent."""

from datetime import datetime

from rich.console import Console
from rich.panel import Panel
from rich.text import Text

console = Console()

SPEAKER_STYLES = {
    "AGENT": "bold cyan",
    "USER": "bold yellow",
    "TOOL": "bold magenta",
    "SYSTEM": "bold green",
    "BOOKING": "bold white on green",
    "ERROR": "bold red",
    "COST": "bold blue",
}


def log_event(speaker: str, message: str):
    """Log a conversation event with timestamp and color-coded speaker."""
    ts = datetime.now().strftime("%H:%M:%S")
    text = Text()
    text.append(f"  [{ts}]  ", style="dim")
    text.append(f"{speaker:>8}", style=SPEAKER_STYLES.get(speaker, "white"))
    text.append("  >  ", style="dim")
    text.append(message, style="white")
    console.print(text)


def log_tool_call(tool_name: str, args: dict, result_summary: str = ""):
    """Log a tool call with its arguments and optional result."""
    ts = datetime.now().strftime("%H:%M:%S")
    args_str = ", ".join(f"{k}={v!r}" for k, v in args.items() if v is not None)
    text = Text()
    text.append(f"  [{ts}]  ", style="dim")
    text.append(f"    TOOL", style="bold magenta")
    text.append(f"  >  {tool_name}({args_str})", style="magenta")
    if result_summary:
        text.append(f" → {result_summary}", style="dim")
    console.print(text)


def log_booking_confirmed(booking_id: str, customer_name: str, resource_name: str):
    """Display a booking confirmation banner."""
    content = (
        f"[bold]Reference:[/bold] {booking_id}\n"
        f"[bold]Customer:[/bold]  {customer_name}\n"
        f"[bold]Resource:[/bold]  {resource_name}"
    )
    panel = Panel(
        content,
        title="[bold white] BOOKING CONFIRMED [/bold white]",
        border_style="green",
        padding=(1, 2),
    )
    console.print(panel)


def print_banner(business_name: str, agent_name: str, category: str):
    """Display the agent startup banner."""
    banner = Text()
    banner.append(f"\n  {business_name.upper()}  \n", style="bold white on blue")
    banner.append(f"  Voice Booking Agent — {agent_name}  \n", style="bold cyan")
    banner.append(f"  Category: {category}  \n", style="dim")
    console.print(Panel(banner, border_style="blue", padding=(0, 2)))


def print_separator():
    console.print("  " + "─" * 60, style="dim")
