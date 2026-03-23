#!/usr/bin/env python3
"""
The Grand Meridian Palace — Voice Booking Agent (Real-time Two-Way)
Run: poetry run python run.py

Talk naturally like a phone call. Interrupt Aria anytime.
No buttons needed — just speak.
"""

import json
import tempfile
import time
from datetime import datetime
from pathlib import Path

import numpy as np
import sounddevice as sd
import soundfile as sf
from dotenv import load_dotenv
from openai import OpenAI
from rich.console import Console
from rich.live import Live
from rich.panel import Panel
from rich.text import Text

from agent.config import (
    SYSTEM_PROMPT, TTS_MODEL, TTS_VOICE, TTS_INSTRUCTIONS,
    STT_MODEL, LLM_MODEL, LLM_TEMPERATURE_GREETING,
    LLM_TEMPERATURE_CONVERSATION, MIC_SAMPLE_RATE,
    ENERGY_THRESHOLD, SILENCE_DURATION, MIN_SPEECH_DURATION,
)
from tools.definitions import TOOLS
from tools.executor import execute_tool

load_dotenv()

console = Console()

WAVE_CHARS = " ░▒▓█"
WAVE_WIDTH = 60


# ── Waveform helpers ────────────────────────────────────────────────────

def make_waveform_text(audio_chunk: np.ndarray, width: int = WAVE_WIDTH, color: str = "cyan") -> Text:
    if len(audio_chunk) == 0:
        text = Text()
        text.append("░" * width, style="dim blue")
        return text

    chunk_size = max(1, len(audio_chunk) // width)
    bars_data = []
    for i in range(width):
        start = i * chunk_size
        end = min(start + chunk_size, len(audio_chunk))
        if start < len(audio_chunk):
            amplitude = np.abs(audio_chunk[start:end].astype(np.float32)).mean() / 32768.0
        else:
            amplitude = 0
        bars_data.append(amplitude)

    max_amp = max(bars_data) if max(bars_data) > 0 else 1
    text = Text()
    for amp in bars_data:
        normalized = min(amp / max_amp, 1.0)
        idx = int(normalized * (len(WAVE_CHARS) - 1))
        text.append(WAVE_CHARS[idx], style=f"bold {color}")
    return text


def render_status_panel(state: str, message: str = "", wave_text: Text | None = None) -> Panel:
    content = Text()

    if state == "ARIA_SPEAKING":
        label = "Aria is speaking..."
        color = "cyan"
        border = "cyan"
        hint = "  Speak anytime to interrupt"
    elif state == "YOU_SPEAKING":
        label = "You are speaking..."
        color = "yellow"
        border = "yellow"
        hint = "  Listening..."
    elif state == "THINKING":
        label = "Aria is thinking..."
        color = "magenta"
        border = "magenta"
        hint = ""
    else:
        label = "Listening..."
        color = "blue"
        border = "blue"
        hint = "  Speak naturally — like a phone call"

    content.append(f"\n  {label}\n\n", style=f"bold {color}")

    if wave_text:
        content.append("  ")
        content.append_text(wave_text)
        content.append("\n")
    else:
        content.append("  " + "░" * WAVE_WIDTH + "\n", style="dim blue")

    if message:
        display_msg = message if len(message) <= 100 else "..." + message[-97:]
        content.append(f"\n  {display_msg}\n", style=f"dim {color}")

    if hint:
        content.append(f"\n  {hint}\n", style="dim")

    title_map = {"ARIA_SPEAKING": "ARIA", "YOU_SPEAKING": "YOU", "THINKING": "ARIA", "IDLE": "LIVE"}
    title = title_map.get(state, "LIVE")
    return Panel(content, border_style=border, title=f"[bold {border}] {title} [/]", padding=(0, 1))



# System prompt, tools, and executor imported from agent.config and tools/




# ── Real-time Mic with VAD ──────────────────────────────────────────────

class MicListener:
    """Always-on microphone with energy-based voice activity detection."""

    def __init__(self):
        self.recording = []
        self.is_speaking = False
        self.silence_start = None
        self.speech_start = None
        self.current_energy = 0.0
        self.current_chunk = np.zeros(1024, dtype=np.int16)
        self._interrupted = False
        self._stream = None

    def start(self):
        self._stream = sd.InputStream(
            samplerate=MIC_SAMPLE_RATE,
            channels=1,
            dtype="int16",
            callback=self._callback,
            blocksize=2048,
        )
        self._stream.start()

    def stop(self):
        if self._stream:
            self._stream.stop()
            self._stream.close()

    def _callback(self, indata, frames, time_info, status):
        audio = indata[:, 0]
        self.current_chunk = audio.copy()
        energy = np.abs(audio.astype(np.float32)).mean()
        self.current_energy = energy

        if energy > ENERGY_THRESHOLD:
            if not self.is_speaking:
                self.is_speaking = True
                self.speech_start = time.time()
                self.recording = []
            self.silence_start = None
            self.recording.append(audio.copy())
        elif self.is_speaking:
            self.recording.append(audio.copy())
            if self.silence_start is None:
                self.silence_start = time.time()

    @property
    def interrupted(self):
        return self._interrupted

    @interrupted.setter
    def interrupted(self, value):
        self._interrupted = value

    def check_speech_done(self) -> bool:
        """Returns True if user finished speaking (silence after speech)."""
        if not self.is_speaking:
            return False
        if self.silence_start and (time.time() - self.silence_start) >= SILENCE_DURATION:
            return True
        return False

    def get_audio_and_reset(self) -> np.ndarray | None:
        """Get recorded audio and reset state."""
        if not self.recording:
            self.is_speaking = False
            self.silence_start = None
            return None

        audio = np.concatenate(self.recording)
        duration = len(audio) / MIC_SAMPLE_RATE

        self.recording = []
        self.is_speaking = False
        self.silence_start = None
        self.speech_start = None

        if duration < MIN_SPEECH_DURATION:
            return None
        return audio

    def is_user_speaking(self) -> bool:
        return self.current_energy > ENERGY_THRESHOLD


# ── TTS with interruption support ──────────────────────────────────────

def speak_with_interrupt(client: OpenAI, text: str, mic: MicListener, live: Live) -> bool:
    """Speak text. Returns True if interrupted by user."""
    response = client.audio.speech.create(
        model=TTS_MODEL,
        voice=TTS_VOICE,
        input=text,
        response_format="wav",
        instructions=TTS_INSTRUCTIONS,
    )

    # Decode WAV for clean audio (no raw PCM artifacts)
    import io
    audio_data_raw, wav_sr = sf.read(io.BytesIO(response.content), dtype="int16")
    audio_data = audio_data_raw if audio_data_raw.ndim == 1 else audio_data_raw[:, 0]
    audio_float = audio_data.astype(np.float32) / 32768.0

    chunk_duration = 0.12
    chunk_samples = int(wav_sr * chunk_duration)
    total_chunks = max(1, len(audio_data) // chunk_samples)

    sd.play(audio_float, samplerate=wav_sr)

    interrupted = False
    for i in range(total_chunks + 1):
        # Check if user started speaking — interrupt!
        if mic.is_user_speaking():
            sd.stop()
            interrupted = True
            mic.interrupted = True
            break

        start = i * chunk_samples
        end = min(start + chunk_samples, len(audio_data))
        if start >= len(audio_data):
            break

        chunk = audio_data[start:end]
        wave = make_waveform_text(chunk, color="cyan")
        live.update(render_status_panel("ARIA_SPEAKING", text, wave))
        time.sleep(chunk_duration)

    if not interrupted:
        sd.wait()

    # Log what Aria said
    ts = datetime.now().strftime("%H:%M:%S")
    suffix = " [interrupted]" if interrupted else ""
    log = Text()
    log.append(f"  [{ts}]  ", style="dim")
    log.append("  ARIA", style="bold cyan")
    log.append("  >  ", style="dim")
    log.append(text + suffix, style="white")
    console.print(log)

    return interrupted


# ── STT ─────────────────────────────────────────────────────────────────

def transcribe(client: OpenAI, audio: np.ndarray) -> str:
    tmp = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
    sf.write(tmp.name, audio, MIC_SAMPLE_RATE)

    with open(tmp.name, "rb") as f:
        result = client.audio.transcriptions.create(
            model=STT_MODEL,
            file=f,
            language="en",
        )

    Path(tmp.name).unlink(missing_ok=True)
    return result.text.strip()



# Tool execution imported from tools.executor


# ── Banner ──────────────────────────────────────────────────────────────

def print_banner():
    console.print()
    banner = Text()
    banner.append("\n  THE GRAND MERIDIAN PALACE  \n", style="bold white on blue")
    banner.append("  Marine Drive, Mumbai, India  \n", style="bold white on dark_blue")
    banner.append("\n  Voice Booking Agent  \n", style="bold cyan")
    banner.append("  Talk naturally — like a phone call  \n", style="dim")
    banner.append("  Interrupt Aria anytime. Press Ctrl+C to exit.  \n", style="dim")
    console.print(Panel(banner, border_style="blue", padding=(0, 2)))
    console.print()


# ── Main conversation loop ──────────────────────────────────────────────

def main():
    client = OpenAI()

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": "(Guest just connected. Greet them warmly.)"},
    ]

    print_banner()

    # Start always-on mic
    mic = MicListener()
    mic.start()

    # Get Aria's greeting
    response = client.chat.completions.create(model=LLM_MODEL, messages=messages, tools=TOOLS, temperature=LLM_TEMPERATURE_GREETING)
    assistant_msg = response.choices[0].message
    messages.append(assistant_msg)

    # Speak greeting with live display
    with Live(render_status_panel("IDLE"), console=console, refresh_per_second=10) as live:
        if assistant_msg.content:
            speak_with_interrupt(client, assistant_msg.content, mic, live)

    console.print()

    # Main loop — real-time two-way conversation
    while True:
        # Show listening state with live waveform
        with Live(render_status_panel("IDLE"), console=console, refresh_per_second=10) as live:
            # Wait for user to speak (VAD detects automatically)
            while True:
                wave = make_waveform_text(mic.current_chunk, color="blue" if not mic.is_speaking else "yellow")
                state = "YOU_SPEAKING" if mic.is_speaking else "IDLE"
                live.update(render_status_panel(state, "", wave))
                time.sleep(0.1)

                if mic.check_speech_done():
                    break

        # Get audio and transcribe
        audio = mic.get_audio_and_reset()
        if audio is None:
            continue

        text = transcribe(client, audio)
        if not text:
            continue

        # Log user speech
        ts = datetime.now().strftime("%H:%M:%S")
        user_log = Text()
        user_log.append(f"  [{ts}]  ", style="dim")
        user_log.append("  YOU ", style="bold yellow")
        user_log.append("  >  ", style="dim")
        user_log.append(text, style="white")
        console.print(user_log)
        console.print()

        # Check for exit
        lower = text.lower()
        if any(word in lower for word in ("quit", "exit", "goodbye", "bye bye", "hang up")):
            with Live(render_status_panel("ARIA_SPEAKING"), console=console, refresh_per_second=10) as live:
                speak_with_interrupt(client, "Thank you for calling The Grand Meridian Palace. Wishing you a wonderful day! Namaste!", mic, live)
            break

        messages.append({"role": "user", "content": text})

        # Get Aria's response (handle tool calls)
        with Live(render_status_panel("THINKING"), console=console, refresh_per_second=10) as live:
            while True:
                response = client.chat.completions.create(model=LLM_MODEL, messages=messages, tools=TOOLS, temperature=LLM_TEMPERATURE_CONVERSATION)
                assistant_msg = response.choices[0].message
                messages.append(assistant_msg)

                if assistant_msg.tool_calls:
                    for tc in assistant_msg.tool_calls:
                        result = execute_tool(tc.function.name, json.loads(tc.function.arguments))
                        messages.append({"role": "tool", "tool_call_id": tc.id, "content": result})
                    continue

                # Speak response — can be interrupted
                if assistant_msg.content:
                    interrupted = speak_with_interrupt(client, assistant_msg.content, mic, live)
                    if interrupted:
                        # User interrupted — will be picked up in next loop
                        pass
                break

    mic.stop()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        console.print("\n  [dim]Goodbye! Namaste.[/dim]\n")
