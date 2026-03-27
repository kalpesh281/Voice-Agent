"""Rich-based CLI display for the voice booking agent.

Premium terminal UI with:
  - Gradient banner with business branding
  - Typing animation for agent responses
  - Thinking spinner while agent processes
  - Color-coded conversation bubbles
  - Tool call visualization
  - Booking confirmation cards
"""

import time
from datetime import datetime

from rich.console import Console
from rich.columns import Columns
from rich.panel import Panel
from rich.spinner import Spinner
from rich.text import Text
from rich.live import Live
from rich.table import Table
from rich import box

console = Console()

# ── Speaker styles ──
SPEAKER_STYLES = {
    "AGENT": "bold cyan",
    "USER": "bold yellow",
    "TOOL": "bold magenta",
    "SYSTEM": "bold green",
    "BOOKING": "bold white on green",
    "ERROR": "bold red",
}

# ── Waveform characters ──
WAVE_CHARS = "░▒▓█▓▒░"


def print_banner(business_name: str, agent_name: str, category: str):
    """Display premium startup banner."""
    # Top accent line
    console.print()
    console.print("  " + "━" * 64, style="blue")

    # Business name
    name_text = Text(justify="center")
    name_text.append(f"  {business_name.upper()}  ", style="bold white")
    console.print(Panel(
        name_text,
        border_style="bright_blue",
        box=box.DOUBLE,
        padding=(0, 4),
    ))

    # Agent info bar
    info = Table(show_header=False, box=None, padding=(0, 2), expand=True)
    info.add_column(justify="center")
    info.add_column(justify="center")
    info.add_column(justify="center")
    info.add_row(
        f"[cyan]Agent:[/cyan] [bold]{agent_name}[/bold]",
        f"[cyan]Category:[/cyan] [bold]{category.replace('_', ' ').title()}[/bold]",
        f"[cyan]Mode:[/cyan] [bold]Text Chat[/bold]",
    )
    console.print(info)

    # Decorative wave
    wave = ""
    for i in range(64):
        wave += WAVE_CHARS[i % len(WAVE_CHARS)]
    console.print(f"  [dim cyan]{wave}[/dim cyan]")
    console.print()


def print_separator():
    """Subtle separator between conversation turns."""
    console.print()


def log_event(speaker: str, message: str, typing_effect: bool = False):
    """Log a conversation event with styled bubble."""
    ts = datetime.now().strftime("%H:%M:%S")

    if speaker == "AGENT":
        _print_agent_message(ts, message, typing_effect)
    elif speaker == "USER":
        _print_user_message(ts, message)
    elif speaker == "ERROR":
        console.print(f"  [dim]{ts}[/dim]  [bold red]ERROR[/bold red]  {message}")
    else:
        text = Text()
        text.append(f"  [{ts}]  ", style="dim")
        text.append(f"{speaker:>8}", style=SPEAKER_STYLES.get(speaker, "white"))
        text.append("  >  ", style="dim")
        text.append(message, style="white")
        console.print(text)


def _print_agent_message(ts: str, message: str, typing_effect: bool = False):
    """Agent message in a styled panel with optional typing animation."""
    header = Text()
    header.append(" Aria ", style="bold white on cyan")
    header.append(f"  {ts}", style="dim")

    if typing_effect:
        # Typing animation
        with Live(console=console, refresh_per_second=30, transient=True) as live:
            displayed = ""
            for char in message:
                displayed += char
                panel = Panel(
                    Text(displayed, style="white"),
                    title=header,
                    title_align="left",
                    border_style="cyan",
                    padding=(0, 2),
                    width=min(console.width - 4, 80),
                )
                live.update(panel)
                time.sleep(0.015)

        # Final static render
        console.print(Panel(
            Text(message, style="white"),
            title=header,
            title_align="left",
            border_style="cyan",
            padding=(0, 2),
            width=min(console.width - 4, 80),
        ))
    else:
        console.print(Panel(
            Text(message, style="white"),
            title=header,
            title_align="left",
            border_style="cyan",
            padding=(0, 2),
            width=min(console.width - 4, 80),
        ))


def _print_user_message(ts: str, message: str):
    """User message — right-aligned simple style."""
    text = Text()
    text.append(f"  {ts}  ", style="dim")
    text.append(" You ", style="bold black on yellow")
    text.append(f"  {message}", style="white")
    console.print(text)
    console.print()


def log_tool_call(tool_name: str, args: dict, result_summary: str = ""):
    """Tool call visualization with icon."""
    ts = datetime.now().strftime("%H:%M:%S")
    args_str = ", ".join(f"[white]{k}[/white]=[yellow]{v!r}[/yellow]" for k, v in args.items() if v is not None)

    console.print(
        f"  [dim]{ts}[/dim]  [magenta]TOOL[/magenta]  "
        f"[bold magenta]{tool_name}[/bold magenta]([dim]{args_str}[/dim])"
    )
    if result_summary:
        console.print(f"         [dim]> {result_summary}[/dim]")


def log_booking_confirmed(booking_id: str, customer_name: str, resource_name: str):
    """Premium booking confirmation card."""
    table = Table(
        show_header=False,
        box=box.SIMPLE_HEAVY,
        border_style="green",
        padding=(0, 2),
        width=min(console.width - 4, 60),
    )
    table.add_column(style="bold white", width=12)
    table.add_column(style="white")
    table.add_row("Reference", f"[bold green]{booking_id}[/bold green]")
    table.add_row("Customer", customer_name)
    table.add_row("Room", resource_name)
    table.add_row("Status", "[bold green]CONFIRMED[/bold green]")

    console.print()
    console.print(Panel(
        table,
        title="[bold white on green] BOOKING CONFIRMED [/bold white on green]",
        border_style="green",
        padding=(1, 1),
        width=min(console.width - 4, 60),
    ))
    console.print()


class ThinkingSpinner:
    """Shows a spinner while the agent is processing."""

    def __init__(self, agent_name: str = "Aria"):
        self._agent_name = agent_name
        self._live: Live | None = None

    def start(self):
        spinner_text = Text()
        spinner_text.append(f"  {self._agent_name} is thinking", style="dim cyan italic")
        spinner_text.append("  ", style="dim")

        self._live = Live(
            Spinner("dots", text=spinner_text, style="cyan"),
            console=console,
            refresh_per_second=10,
            transient=True,
        )
        self._live.start()

    def stop(self):
        if self._live:
            self._live.stop()
            self._live = None
