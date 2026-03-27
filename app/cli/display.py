"""Rich live display for the voice booking agent.

Shows real-time status, waveform visualization, and conversation state.
"""

import numpy as np
from rich.console import Console
from rich.layout import Layout
from rich.live import Live
from rich.panel import Panel
from rich.text import Text

console = Console()

# Waveform characters (low → high energy)
WAVEFORM_CHARS = " ░▒▓█"


class VoiceDisplay:
    """Real-time CLI display using Rich Live."""

    def __init__(self, business_name: str, agent_name: str, category: str):
        self._business_name = business_name
        self._agent_name = agent_name
        self._category = category
        self._state = "READY"
        self._waveform = ""
        self._last_transcript = ""
        self._live: Live | None = None

    def start(self) -> Live:
        """Start the live display and return the Live context."""
        self._live = Live(
            self._render(),
            console=console,
            refresh_per_second=8,
            transient=True,
        )
        return self._live

    def update_state(self, state: str):
        """Update the current state: LISTENING, YOU_SPEAKING, AGENT_SPEAKING, THINKING."""
        self._state = state
        self._refresh()

    def update_waveform(self, audio_chunk: bytes):
        """Update the waveform visualization from audio data."""
        try:
            audio = np.frombuffer(audio_chunk, dtype=np.int16)
            # Downsample to 40 bars
            chunk_size = max(1, len(audio) // 40)
            bars = []
            for i in range(0, min(len(audio), 40 * chunk_size), chunk_size):
                segment = audio[i:i + chunk_size]
                energy = np.abs(segment).mean() / 3276.8  # normalize to 0-10
                level = min(int(energy), len(WAVEFORM_CHARS) - 1)
                bars.append(WAVEFORM_CHARS[level])
            self._waveform = "".join(bars)
        except Exception:
            self._waveform = ""
        self._refresh()

    def update_transcript(self, text: str):
        """Update the live transcript being recognized."""
        self._last_transcript = text
        self._refresh()

    def clear_waveform(self):
        self._waveform = " " * 40
        self._refresh()

    def _refresh(self):
        if self._live:
            self._live.update(self._render())

    def _render(self) -> Panel:
        """Render the current display state."""
        content = Text()

        # State indicator
        state_styles = {
            "READY": ("dim white", "Ready"),
            "LISTENING": ("bold green", "Listening..."),
            "YOU_SPEAKING": ("bold yellow", "You're speaking..."),
            "AGENT_SPEAKING": ("bold cyan", f"{self._agent_name} is speaking..."),
            "THINKING": ("bold magenta", "Thinking..."),
        }
        style, label = state_styles.get(self._state, ("white", self._state))
        content.append(f"  {label}", style=style)
        content.append("\n\n")

        # Waveform
        if self._waveform:
            content.append("  ", style="dim")
            content.append(self._waveform, style="green" if "SPEAKING" in self._state else "dim")
            content.append("\n\n")

        # Live transcript
        if self._last_transcript:
            content.append(f"  {self._last_transcript}", style="dim italic")
            content.append("\n")

        return Panel(
            content,
            title=f"[bold]{self._business_name}[/bold] — {self._agent_name}",
            subtitle=f"[dim]{self._category} | Ctrl+C to exit[/dim]",
            border_style="blue",
            padding=(0, 1),
        )


def print_voice_banner(business_name: str, agent_name: str, category: str):
    """Print a one-time startup banner for voice mode."""
    banner = Text()
    banner.append(f"\n  {business_name.upper()}  \n", style="bold white on blue")
    banner.append(f"  Voice Booking Agent v2.0  \n", style="bold cyan")
    banner.append(f"  Agent: {agent_name} | Category: {category}  \n", style="dim")
    banner.append(f"  Speak naturally — {agent_name} is listening  \n", style="dim green")
    console.print(Panel(banner, border_style="blue", padding=(0, 2)))
    console.print()
