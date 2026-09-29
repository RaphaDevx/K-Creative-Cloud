#!/usr/bin/env python3
"""
Kokoro TTS Audio Generator
Usage: python3 generate_audio.py "Your text here" [output.wav] [voice] [speed]
Default: voice=af_heart, speed=1.15, output=output.wav
"""

import sys
import os
import soundfile as sf
from kokoro_onnx import Kokoro

# Paths (relative to this script)
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
MODEL_PATH  = os.path.join(SCRIPT_DIR, "kokoro-v1.0.int8.onnx")
VOICES_PATH = os.path.join(SCRIPT_DIR, "voices-v1.0.bin")

# Defaults
DEFAULT_VOICE = "af_heart"   # Warm, expressive female – great for fast-paced content
DEFAULT_SPEED = 1.15         # Slightly faster = energetic feel
DEFAULT_OUT   = os.path.join(SCRIPT_DIR, "output.wav")

def generate(text: str, out_path: str = DEFAULT_OUT, voice: str = DEFAULT_VOICE, speed: float = DEFAULT_SPEED):
    print(f"[TTS] Voice: {voice}  |  Speed: {speed}x  |  → {out_path}")
    kokoro = Kokoro(MODEL_PATH, VOICES_PATH)
    samples, sample_rate = kokoro.create(text, voice=voice, speed=speed, lang="en-us")
    sf.write(out_path, samples, sample_rate)
    duration = len(samples) / sample_rate
    print(f"[TTS] Done! Duration: {duration:.1f}s  |  Sample rate: {sample_rate}Hz")
    return out_path, duration

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 generate_audio.py \"Your text\" [output.wav] [voice] [speed]")
        print(f"\nAvailable voices (sample):")
        from kokoro_onnx import Kokoro as K
        k = K(MODEL_PATH, VOICES_PATH)
        voices = k.get_voices()
        en = [v for v in voices if v.startswith(('a', 'b'))]
        for v in en:
            print(f"  {v}")
        sys.exit(1)

    text      = sys.argv[1]
    out_path  = sys.argv[2] if len(sys.argv) > 2 else DEFAULT_OUT
    voice     = sys.argv[3] if len(sys.argv) > 3 else DEFAULT_VOICE
    speed     = float(sys.argv[4]) if len(sys.argv) > 4 else DEFAULT_SPEED

    generate(text, out_path, voice, speed)
