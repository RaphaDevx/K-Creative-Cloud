"""
Spectral quality analyzer for DJ tracks.
Detects frequency ceiling via FFT — supports MP3, FLAC, WAV, OGG.

Quality grades:
  CLUB-READY  — ceiling > 19 kHz  (genuine 320kbps / WAV / lossless)
  GOOD        — ceiling 17–19 kHz (256kbps, well-encoded MP3)
  MEDIUM      — ceiling 15–17 kHz (192kbps or re-encoded)
  LOW         — ceiling < 15 kHz  (128kbps, YouTube rip, transcoded)
"""

import json
import sys
import numpy as np
import librosa
from pathlib import Path
from mutagen.id3 import ID3, TXXX, COMM, error as ID3Error


DOWNLOADS_DIR = Path(__file__).parent.parent / "downloads"
CACHE_FILE    = DOWNLOADS_DIR / ".quality_cache.json"


def _load_cache() -> dict:
    try:
        return json.loads(CACHE_FILE.read_text())
    except Exception:
        return {}


def _save_cache(cache: dict):
    CACHE_FILE.write_text(json.dumps(cache, indent=2))

GRADES = [
    (19_000, "CLUB-READY", "Frequenzdecke >19 kHz — clubtauglich"),
    (17_000, "GOOD",       "Frequenzdecke 17–19 kHz — gut"),
    (15_000, "MEDIUM",     "Frequenzdecke 15–17 kHz — mittelmässig, wahrscheinlich re-encoded"),
    (0,      "LOW",        "Frequenzdecke <15 kHz — schlechte Qualität (YouTube-Rip / 128kbps)"),
]

GRADE_EMOJI = {
    "CLUB-READY": "✅",
    "GOOD":       "🟡",
    "MEDIUM":     "🟠",
    "LOW":        "❌",
}


def detect_freq_ceiling(path: Path, threshold_db: float = -60.0) -> float:
    """Return the highest frequency (Hz) with meaningful energy."""
    y, sr = librosa.load(str(path), sr=None, mono=True, duration=60)
    # Use a large FFT for frequency resolution
    n_fft = 8192
    hop = n_fft // 4
    S = np.abs(librosa.stft(y, n_fft=n_fft, hop_length=hop))

    # Average power spectrum (dB), ignore silence frames
    power = S.mean(axis=1)
    power_db = librosa.amplitude_to_db(power, ref=power.max())

    freqs = librosa.fft_frequencies(sr=sr, n_fft=n_fft)

    # Walk down from highest frequency to find where energy rises above threshold
    ceiling_hz = freqs[0]
    for i in range(len(freqs) - 1, -1, -1):
        if power_db[i] > threshold_db:
            ceiling_hz = freqs[i]
            break

    return float(ceiling_hz)


def grade_ceiling(ceiling_hz: float) -> tuple[str, str]:
    for min_hz, grade, comment in GRADES:
        if ceiling_hz >= min_hz:
            return grade, comment
    return GRADES[-1][1], GRADES[-1][2]


def write_tags(path: Path, ceiling_hz: float, grade: str, comment: str):
    """Write quality tags to MP3 ID3 or WAV ID3. FLAC/OGG only use cache."""
    ext = path.suffix.lower()
    if ext not in (".mp3", ".wav"):
        return
    try:
        try:
            tags = ID3(str(path))
        except ID3Error:
            tags = ID3()
        tags.add(TXXX(encoding=3, desc="QUALITY",      text=grade))
        tags.add(TXXX(encoding=3, desc="FREQ_CEILING", text=f"{ceiling_hz/1000:.1f} kHz"))
        tags.add(COMM(encoding=3, lang="deu", desc="", text=f"[{grade}] {ceiling_hz/1000:.1f} kHz"))
        tags.save(str(path))
    except Exception:
        pass


def analyze_file(path: Path, force: bool = False) -> dict:
    # Check cache first (skip re-analysis unless forced)
    cache = _load_cache()
    key = path.name
    if not force and key in cache:
        return cache[key]

    print(f"  Analysiere: {path.name} ...", end=" ", flush=True)
    ceiling_hz = detect_freq_ceiling(path)
    grade, comment = grade_ceiling(ceiling_hz)
    write_tags(path, ceiling_hz, grade, comment)
    emoji = GRADE_EMOJI[grade]
    print(f"{emoji} {grade}  ({ceiling_hz/1000:.1f} kHz)")

    result = {"file": path.name, "ceiling_khz": round(ceiling_hz / 1000, 1), "grade": grade}
    cache[key] = result
    _save_cache(cache)
    return result


def get_cached(filename: str) -> dict | None:
    """Return cached quality result for a filename, or None."""
    return _load_cache().get(filename)


def main():
    target = Path(sys.argv[1]) if len(sys.argv) > 1 else DOWNLOADS_DIR
    files = sorted(target.glob("*.mp3")) + sorted(target.glob("*.wav")) + sorted(target.glob("*.flac"))

    if not files:
        print(f"Keine Audiodateien in {target}")
        return

    print(f"\n{'='*60}")
    print(f" Spektral-Qualitätsanalyse — {len(files)} Track(s)")
    print(f"{'='*60}")

    results = []
    for f in files:
        r = analyze_file(f)
        results.append(r)

    print(f"\n{'─'*60}")
    print(f" Zusammenfassung")
    print(f"{'─'*60}")
    for r in sorted(results, key=lambda x: x["ceiling_khz"], reverse=True):
        emoji = GRADE_EMOJI[r["grade"]]
        print(f"  {emoji} {r['ceiling_khz']:5.1f} kHz  [{r['grade']:<12}]  {r['file']}")
    print(f"{'='*60}\n")

    # Grade stats
    from collections import Counter
    counts = Counter(r["grade"] for r in results)
    for grade, emoji in GRADE_EMOJI.items():
        if counts[grade]:
            print(f"  {emoji} {grade}: {counts[grade]} Track(s)")
    print()


if __name__ == "__main__":
    main()
