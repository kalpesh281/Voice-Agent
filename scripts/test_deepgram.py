"""Test Deepgram STT and TTS connectivity.

Usage:
    poetry run python scripts/test_deepgram.py          # test both
    poetry run python scripts/test_deepgram.py --stt     # test STT only
    poetry run python scripts/test_deepgram.py --tts     # test TTS only
"""

import argparse
import asyncio
import sys
import wave
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.config import settings
from app.voice.deepgram_stt import StreamingSTT
from app.voice.deepgram_tts import StreamingTTS


async def test_stt():
    """Test Deepgram STT by sending a short audio clip."""
    print("\n=== Testing Deepgram STT ===")

    if not settings.deepgram_api_key:
        print("  SKIP: DEEPGRAM_API_KEY not set in .env")
        return False

    stt = StreamingSTT(
        api_key=settings.deepgram_api_key,
        model=settings.deepgram_stt_model,
        language=settings.deepgram_stt_language,
    )

    try:
        await stt.start()
        print("  Connected to Deepgram STT")

        # Generate a short silence to verify the connection works
        # (1 second of silence at 16kHz, 16-bit mono)
        silence = b"\x00\x00" * 16000
        await stt.send_audio(silence)
        print("  Sent 1 second of silence (connection verified)")

        # Try to get a transcript with a short timeout
        try:
            transcript = await asyncio.wait_for(stt.get_transcript(), timeout=3.0)
            print(f"  Transcript: {transcript}")
        except asyncio.TimeoutError:
            print("  No transcript (expected — we sent silence)")

        await stt.stop()
        print("  STT: PASS")
        return True

    except Exception as e:
        print(f"  STT FAILED: {e}")
        await stt.stop()
        return False


async def test_tts():
    """Test Deepgram TTS by synthesizing a short phrase."""
    print("\n=== Testing Deepgram TTS ===")

    if not settings.deepgram_api_key:
        print("  SKIP: DEEPGRAM_API_KEY not set in .env")
        return False

    tts = StreamingTTS(
        api_key=settings.deepgram_api_key,
        model=settings.deepgram_tts_model,
    )

    try:
        await tts.start()
        print("  Connected to Deepgram TTS")

        # Synthesize a short phrase
        test_text = "Hello! Welcome to the Voice Booking Agent. This is a test."
        await tts.synthesize(test_text)
        await tts.flush()
        print(f"  Sent text: '{test_text}'")

        # Collect audio chunks
        audio_data = bytearray()
        try:
            while True:
                chunk = await asyncio.wait_for(tts.get_audio_chunk(), timeout=3.0)
                audio_data.extend(chunk)
        except asyncio.TimeoutError:
            pass

        if audio_data:
            # Save to WAV file for verification
            output_path = Path(__file__).resolve().parent.parent / "data" / "test_tts_output.wav"
            output_path.parent.mkdir(parents=True, exist_ok=True)

            with wave.open(str(output_path), "wb") as wf:
                wf.setnchannels(1)
                wf.setsampwidth(2)  # 16-bit
                wf.setframerate(tts._sample_rate)
                wf.writeframes(bytes(audio_data))

            duration = len(audio_data) / (tts._sample_rate * 2)
            print(f"  Received {len(audio_data)} bytes ({duration:.1f}s audio)")
            print(f"  Saved to: {output_path}")
            print("  TTS: PASS")
        else:
            print("  No audio received")
            print("  TTS: FAIL")

        await tts.stop()
        return bool(audio_data)

    except Exception as e:
        print(f"  TTS FAILED: {e}")
        await tts.stop()
        return False


async def main():
    parser = argparse.ArgumentParser(description="Test Deepgram connectivity")
    parser.add_argument("--stt", action="store_true", help="Test STT only")
    parser.add_argument("--tts", action="store_true", help="Test TTS only")
    args = parser.parse_args()

    # If neither specified, test both
    test_both = not args.stt and not args.tts

    results = {}
    if args.stt or test_both:
        results["STT"] = await test_stt()
    if args.tts or test_both:
        results["TTS"] = await test_tts()

    print("\n=== Results ===")
    for name, passed in results.items():
        status = "PASS" if passed else "FAIL/SKIP"
        print(f"  {name}: {status}")
    print()


if __name__ == "__main__":
    asyncio.run(main())
