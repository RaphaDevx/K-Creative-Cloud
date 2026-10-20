"""TTS-Kompatibilitätsschicht — rein lokal. Delegiert an voice/ (Piper DE, Kokoro EN, Persona-Lock).

Alt-Aufrufe ohne channel/persona nutzen die Persona "default" (wird beim ersten Aufruf angelegt).
Edge TTS (Cloud) ist entfernt.
"""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def _default_persona(voice: str) -> str:
    from voice import registry
    pid = f"default-{voice}"
    try:
        registry.resolve(persona=pid)
    except FileNotFoundError:
        registry.create_persona(pid, f"Default ({voice})", {
            "de": {"engine": "piper", "voice": "de_DE-thorsten-medium", "params": {}},
            "en": {"engine": "kokoro", "voice": voice, "params": {}}})
    return pid


def synthesize(text: str, out_path: str, voice: str = "af_heart", speed: float = 1.2, lang: str = "auto",
               channel: str | None = None, persona: str | None = None) -> float:
    """Gibt die Dauer in Sekunden zurück. lang/speed bleiben für Alt-Code akzeptiert, Sprache wird je Segment erkannt."""
    from voice import synthesize as _s
    if not channel and not persona:
        persona = _default_persona(voice)
    return _s(text, out_path, channel=channel, persona=persona)["duration"]
