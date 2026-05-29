"""
TTS wrapper using Kokoro ONNX (local, offline).
Model lives in /home/raphael/notebooklm-shorts-generator/
"""
import os
import sys
import soundfile as sf

KOKORO_DIR = "/home/raphael/notebooklm-shorts-generator"
MODEL_PATH = os.path.join(KOKORO_DIR, "kokoro-v1.0.int8.onnx")
VOICES_PATH = os.path.join(KOKORO_DIR, "voices-v1.0.bin")

# Lazy-loaded singleton
_kokoro = None


def _get_kokoro():
    global _kokoro
    if _kokoro is None:
        sys.path.insert(0, KOKORO_DIR)
        from kokoro_onnx import Kokoro
        _kokoro = Kokoro(MODEL_PATH, VOICES_PATH)
    return _kokoro


def synthesize(text: str, out_path: str, voice: str = "af_heart", speed: float = 1.2) -> float:
    """
    Generate speech audio.
    speed=1.2 gives energetic fast-paced feel for shorts.
    Returns duration in seconds.
    """
    kokoro = _get_kokoro()
    samples, sample_rate = kokoro.create(text, voice=voice, speed=speed, lang="en-us")
    sf.write(out_path, samples, sample_rate)
    return len(samples) / sample_rate


AVAILABLE_VOICES = {
    "af_heart": "Warm expressive female (recommended for educational)",
    "af_nova": "Bright energetic female",
    "am_adam": "Deep authoritative male",
    "am_echo": "Clear neutral male",
    "bf_emma": "British female, formal",
    "bm_george": "British male, professor-style",
}
