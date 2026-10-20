"""Persona-/Kanal-Registry. Ein Kanal zeigt auf eine Persona, die Persona fixiert pro Sprache
Engine + Stimme + Parameter + Modell-Hash (Fingerprint). Weicht etwas ab, bricht die Synthese
ab (VoiceDriftError), statt still eine andere Stimme zu verwenden. Änderungen nur per bump()."""
import json
import os
import sys
import tempfile
import time
from pathlib import Path

from .engines import ENGINES
from .segment import voice_home


class VoiceDriftError(RuntimeError):
    pass


def _write(path: Path, data: dict):
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=path.parent, suffix=".tmp")
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2, sort_keys=True)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, path)  # atomar, nie halb geschrieben


def _read(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _fps(voices: dict) -> dict:
    return {lang: ENGINES[v["engine"]].fingerprint(v["voice"], v.get("params", {})) for lang, v in voices.items()}


def create_persona(pid: str, name: str, voices: dict, notes: str = "") -> dict:
    p = voice_home() / "personas" / f"{pid}.json"
    if p.exists():
        raise FileExistsError(f"Persona {pid} existiert; Änderungen nur per bump()")
    data = {"id": pid, "name": name, "version": 1, "voices": voices, "fingerprint": _fps(voices),
            "notes": notes, "created": time.strftime("%Y-%m-%dT%H:%M:%S")}
    _write(p, data)
    _write(voice_home() / "personas" / f"{pid}.history" / "v1.json", data)
    return data


def bind_channel(channel: str, pid: str) -> dict:
    per = _read(voice_home() / "personas" / f"{pid}.json")
    data = {"id": channel, "persona": pid, "persona_version": per["version"]}
    _write(voice_home() / "channels" / f"{channel}.json", data)
    return data


def resolve(channel: str | None = None, persona: str | None = None) -> dict:
    if channel:
        ch = _read(voice_home() / "channels" / f"{channel}.json")
        persona = ch["persona"]
    per = _read(voice_home() / "personas" / f"{persona}.json")
    if channel and ch["persona_version"] != per["version"]:
        raise VoiceDriftError(f"Kanal {channel} ist auf {persona} v{ch['persona_version']} gepinnt, aktuell v{per['version']}; "
                              f"bewusst per bind_channel() umstellen")
    now = _fps(per["voices"])
    if now != per["fingerprint"]:
        bad = [l for l in now if now[l] != per["fingerprint"].get(l)]
        raise VoiceDriftError(f"Persona {persona}: Stimme für {bad} weicht vom Fingerprint ab (Modell/Parameter geändert)")
    return per


def bump(pid: str, voices: dict | None = None) -> dict:
    """Bewusste Stimmänderung: neue Version, alte bleibt in <id>.history/ erhalten."""
    p = voice_home() / "personas" / f"{pid}.json"
    per = _read(p)
    if voices:
        per["voices"].update(voices)
    per["version"] += 1
    per["fingerprint"] = _fps(per["voices"])
    _write(p, per)
    _write(voice_home() / "personas" / f"{pid}.history" / f"v{per['version']}.json", per)
    return per


def verify_all() -> list[str]:
    errs = []
    for f in sorted((voice_home() / "channels").glob("*.json")):
        try:
            resolve(channel=f.stem)
        except Exception as e:  # noqa: BLE001
            errs.append(f"{f.stem}: {e}")
    return errs


def _selftest():
    with tempfile.TemporaryDirectory() as d:
        os.environ["K_CREATIVE_VOICE_HOME"] = d
        v = {"de": {"engine": "piper", "voice": "de_DE-thorsten-medium", "params": {"speed": 1.0}},
             "en": {"engine": "kokoro", "voice": "am_adam", "params": {"speed": 1.0}}}
        create_persona("prof", "Professor", v)
        bind_channel("lernkanal", "prof")
        assert resolve(channel="lernkanal")["version"] == 1
        pf = Path(d) / "personas" / "prof.json"
        data = _read(pf)
        data["voices"]["de"]["params"]["speed"] = 1.3  # stille Manipulation
        _write(pf, data)
        try:
            resolve(channel="lernkanal")
            raise SystemExit("Drift nicht erkannt")
        except VoiceDriftError:
            pass
        data["voices"]["de"]["params"]["speed"] = 1.0
        _write(pf, data)
        bump("prof", {"de": {"engine": "piper", "voice": "de_DE-kerstin-low", "params": {}}})
        try:
            resolve(channel="lernkanal")
            raise SystemExit("Versions-Pin nicht erkannt")
        except VoiceDriftError:
            pass
        bind_channel("lernkanal", "prof")
        assert resolve(channel="lernkanal")["version"] == 2
        assert (Path(d) / "personas" / "prof.history" / "v1.json").exists()
    print("registry selftest ok")


if __name__ == "__main__":
    a = sys.argv[1:]
    if a[:1] == ["--selftest"]:
        _selftest()
    elif a[:1] == ["verify"]:
        e = verify_all()
        print("\n".join(e) or "alle Kanäle ok")
        sys.exit(1 if e else 0)
    else:
        print("usage: python -m voice.registry --selftest | verify")
