from datetime import datetime

from rich.console import Console
from rich.panel import Panel
from rich.text import Text

console = Console()

SPEAKER_STYLES = {
    "AGENT": "bold cyan",
    "GUEST": "bold yellow",
    "TOOL": "bold magenta",
    "SYSTEM": "bold green",
    "BOOKING": "bold white on green",
    "ERROR": "bold red",
}


def _timestamp() -> str:
    return datetime.now().strftime("%H:%M:%S")


def print_banner():
    banner = Text()
    banner.append("  THE GRAND MERIDIAN PALACE  ", style="bold white on blue")
    banner.append("  Mumbai, India  ", style="bold white on dark_blue")
    banner.append("  Voice Booking Agent  ", style="bold cyan")
    console.print()
    console.print(Panel(banner, border_style="blue", padding=(1, 2)))
    console.print()


def print_status(status: str, detail: str = ""):
    ts = _timestamp()
    text = Text()
    text.append(f"  [{ts}]  ", style="dim")
    text.append(f"STATUS", style="bold blue")
    text.append(f"  {status}", style="white")
    if detail:
        text.append(f"  —  {detail}", style="dim")
    console.print(text)


def log_event(speaker: str, message: str):
    ts = _timestamp()
    style = SPEAKER_STYLES.get(speaker, "white")
    text = Text()
    text.append(f"  [{ts}]  ", style="dim")
    text.append(f"{speaker:>7}", style=style)
    text.append(f"  >  ", style="dim")
    text.append(message, style="white")
    console.print(text)


def log_tool_call(tool_name: str, args: dict, result_summary: str = ""):
    ts = _timestamp()
    text = Text()
    text.append(f"  [{ts}]  ", style="dim")
    text.append(f"   TOOL", style="bold magenta")
    text.append(f"  {tool_name}(", style="magenta")

    arg_parts = []
    for k, v in args.items():
        if v is not None:
            arg_parts.append(f"{k}={v!r}")
    text.append(", ".join(arg_parts), style="dim magenta")
    text.append(")", style="magenta")
    console.print(text)

    if result_summary:
        result_text = Text()
        result_text.append(f"  [{ts}]  ", style="dim")
        result_text.append(f"   TOOL", style="bold magenta")
        result_text.append(f"  -> {result_summary}", style="dim")
        console.print(result_text)


def log_booking_confirmed(booking_id: str, guest_name: str, room_name: str):
    console.print()
    panel_text = Text()
    panel_text.append("BOOKING CONFIRMED\n\n", style="bold")
    panel_text.append(f"  Reference:  {booking_id}\n", style="white")
    panel_text.append(f"  Guest:      {guest_name}\n", style="white")
    panel_text.append(f"  Room:       {room_name}\n", style="white")
    console.print(
        Panel(panel_text, border_style="green", title="[bold green]Confirmed[/]", padding=(1, 2))
    )
    console.print()
