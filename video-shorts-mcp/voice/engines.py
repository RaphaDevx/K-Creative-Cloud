"""Engine-Adapter (alle lokal). Jede Engine: synth(text, voice, params) -> (samples float32, sr)
und fingerprint(voice, params) -> dict, damit eine Persona nachweisbar dieselbe Stimme behält."""
import hashlib
import os
import wave
import io
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
MODELS = Path(os.environ.get("K_CREATIVE_VOICE_MODELS", ROOT / "voice-models"))
KOKORO_DIR = Path(os.environ.get("K_CREATIVE_KOKORO_DIR", ROOT / "kokoro-tts"))


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


_cache: dict = {}


class Piper:
    name = "piper"

    def _path(self, voice):
        return MODELS / "piper" / f"{voice}.onnx"

    def synth(self, text, voice, params):
        from piper import PiperVoice, SynthesisConfig
        if voice not in _cache:
            _cache[voice] = PiperVoice.load(str(self._path(voice)))
        cfg = SynthesisConfig(length_scale=1.0 / float(params.get("speed", 1.0)),
                              noise_scale=params.get("noise_scale"), noise_w_scale=params.get("noise_w_scale"))
        buf = io.BytesIO()
        with wave.open(buf, "wb") as w:
            _cache[voice].synthesize_wav(text, w, syn_config=cfg)
        buf.seek(0)
        with wave.open(buf, "rb") as r:
            sr = r.getframerate()
            data = np.frombuffer(r.readframes(r.getnframes()), dtype=np.int16).astype(np.float32) / 32768
        return data, sr

    def fingerprint(self, voice, params):
        return {"engine": "piper", "voice": voice, "model_sha256": sha256_file(self._path(voice)), "params": params}


class Kokoro:
    name = "kokoro"

    def _k(self):
        if "kokoro" not in _cache:
            from kokoro_onnx import Kokoro as K
            _cache["kokoro"] = K(str(KOKORO_DIR / "kokoro-v1.0.int8.onnx"), str(KOKORO_DIR / "voices-v1.0.bin"))
        return _cache["kokoro"]

    def synth(self, text, voice, params):
        s, sr = self._k().create(text, voice=voice, speed=float(params.get("speed", 1.0)), lang=params.get("lang", "en-us"))
        return np.asarray(s, dtype=np.float32), sr

    def fingerprint(self, voice, params):
        return {"engine": "kokoro", "voice": voice, "model_sha256": sha256_file(KOKORO_DIR / "kokoro-v1.0.int8.onnx"),
                "voices_sha256": sha256_file(KOKORO_DIR / "voices-v1.0.bin"), "params": params}


ENGINES = {"piper": Piper(), "kokoro": Kokoro()}
# Klon-Engines (XTTS-v2/F5-TTS) werden hier als weiterer Adapter ergänzt; Referenzsample liegt dann in voice-data/samples/.
