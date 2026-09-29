"""
TTS wrapper — routes German to Microsoft Edge TTS (de-DE-KillianNeural),
English to Kokoro ONNX (local, offline).

German:  edge_tts  → de-DE-KillianNeural  (native German, requires internet)
English: kokoro    → af_heart / am_adam etc. (local, offline)
"""
import os
import sys
import asyncio
import soundfile as sf
from pathlib import Path

KOKORO_DIR = "/home/raphael/K-Creative-Cloud/kokoro-tts"
MODEL_PATH = os.path.join(KOKORO_DIR, "kokoro-v1.0.int8.onnx")
VOICES_PATH = os.path.join(KOKORO_DIR, "voices-v1.0.bin")

DE_VOICE = "de-DE-KillianNeural"   # Microsoft Edge TTS — native German male
DE_RATE  = "+10%"                   # slightly faster, matches ESF reel style

# Lazy-loaded Kokoro singleton
_kokoro = None


def _get_kokoro():
    global _kokoro
    if _kokoro is None:
        sys.path.insert(0, KOKORO_DIR)
        from kokoro_onnx import Kokoro
        _kokoro = Kokoro(MODEL_PATH, VOICES_PATH)
    return _kokoro


def detect_lang(text: str) -> str:
    """Heuristic language detection — German if any German-specific markers found."""
    t = " " + text.lower() + " "
    # Umlaute and ß are unambiguous German — one is enough
    if any(c in t for c in ["ü", "ö", "ä", "ß"]):
        return "de"
    # Common German words; check with word boundary on both sides
    german_words = [
        "und", "die", "der", "das", "ist", "nicht", "von", "mit", "auf",
        "für", "ein", "eine", "wird", "sind", "wir", "du", "ich", "es",
        "aber", "auch", "als", "bei", "nach", "wenn", "dann", "dass",
        "durch", "immer", "also", "oder", "zwischen", "können", "haben",
        "heisst", "bedeutet", "erklärt", "zeigt", "gibt", "kommt",
        "warum", "welche", "welcher", "welches", "jede", "jeder",
        "genau", "einfach", "wichtig", "gross", "klein",
    ]
    score = sum(1 for w in german_words if f" {w} " in t)
    return "de" if score >= 1 else "en-us"


def _synthesize_edge_de(text: str, out_path: str, rate: str = DE_RATE) -> float:
    """Synthesize German text with Microsoft Edge TTS → WAV file."""
    import edge_tts

    mp3_path = out_path.replace(".wav", "_edge_tmp.mp3")

    async def _run():
        comm = edge_tts.Communicate(text, DE_VOICE, rate=rate)
        await comm.save(mp3_path)

    asyncio.run(_run())

    # Convert MP3 → WAV so pipeline stays consistent
    import subprocess
    subprocess.run(
        ["ffmpeg", "-y", "-i", mp3_path, "-ar", "24000", "-ac", "1", out_path],
        check=True, capture_output=True,
    )
    os.remove(mp3_path)

    data, sr = sf.read(out_path)
    return len(data) / sr


def synthesize(text: str, out_path: str, voice: str = "af_heart", speed: float = 1.2, lang: str = "auto") -> float:
    """
    Generate speech audio. Routes automatically by language:
      German  → Microsoft Edge TTS (de-DE-KillianNeural) — native quality
      English → Kokoro ONNX (local, offline)

    lang="auto"  : auto-detect (recommended — reliable for German)
    lang="de"    : force German / Edge TTS
    lang="en-us" : force English / Kokoro
    speed        : only applies to Kokoro (English); Edge uses DE_RATE (+10%)
    voice        : only applies to Kokoro (English)
    Returns duration in seconds.
    """
    resolved_lang = detect_lang(text) if lang == "auto" else lang

    if resolved_lang == "de":
        return _synthesize_edge_de(text, out_path)
    else:
        kokoro = _get_kokoro()
        samples, sample_rate = kokoro.create(text, voice=voice, speed=speed, lang=resolved_lang)
        sf.write(out_path, samples, sample_rate)
        return len(samples) / sample_rate


AVAILABLE_VOICES = {
    # German (Edge TTS — auto-selected when lang="de" or German text detected)
    "de-DE-KillianNeural": "Native German male — used automatically for German text",
    "de-DE-KatjaNeural":   "Native German female — pass lang='de' to use",
    # English (Kokoro — used for English text)
    "af_heart":  "Warm expressive female (Kokoro EN)",
    "af_nova":   "Bright energetic female (Kokoro EN)",
    "am_adam":   "Deep authoritative male (Kokoro EN)",
    "am_echo":   "Clear neutral male (Kokoro EN)",
    "bf_emma":   "British female, formal (Kokoro EN)",
    "bm_george": "British male, professor-style (Kokoro EN)",
}
