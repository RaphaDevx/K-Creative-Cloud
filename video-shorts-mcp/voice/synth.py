"""synthesize(): Text -> WAV, pro Segment die Engine der Persona-Sprache, Sidecar mit Fingerprint."""
import json
from pathlib import Path

import numpy as np
import soundfile as sf

from .engines import ENGINES
from .registry import resolve
from .segment import apply_pronunciation, load_lexicon, segment

OUT_SR = 24000


def _resample(x: np.ndarray, sr: int) -> np.ndarray:
    if sr == OUT_SR:
        return x
    n = int(len(x) * OUT_SR / sr)
    return np.interp(np.linspace(0, len(x) - 1, n), np.arange(len(x)), x).astype(np.float32)


def synthesize(text: str, out_path: str, channel: str | None = None, persona: str | None = None,
               pause_ms: int = 140) -> dict:
    per = resolve(channel=channel, persona=persona)
    lex = load_lexicon()
    parts, used = [], []
    for seg in segment(text, lex):
        if seg.lang not in per["voices"]:
            raise KeyError(f"Persona {per['id']} hat keine Stimme für '{seg.lang}'")
        v = per["voices"][seg.lang]
        t = apply_pronunciation(seg.text, seg.lang, lex)
        params = dict(v.get("params", {}))
        if v["engine"] == "kokoro":
            params.setdefault("lang", "en-us" if seg.lang == "en" else seg.lang)
        s, sr = ENGINES[v["engine"]].synth(t, v["voice"], params)
        parts.append(_resample(s, sr))
        parts.append(np.zeros(int(OUT_SR * pause_ms / 1000), dtype=np.float32))
        used.append({"lang": seg.lang, "text": seg.text, "engine": v["engine"], "voice": v["voice"]})
    if not parts:
        raise ValueError("Leerer Text")
    audio = np.concatenate(parts)
    peak = float(np.max(np.abs(audio))) or 1.0
    audio = audio * (0.7 / peak)  # einheitlicher Pegel über alle Segmente/Engines
    sf.write(out_path, audio, OUT_SR)
    meta = {"persona": per["id"], "persona_version": per["version"], "channel": channel,
            "fingerprint": per["fingerprint"], "segments": used, "duration": len(audio) / OUT_SR}
    Path(out_path).with_suffix(".voice.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    return meta
