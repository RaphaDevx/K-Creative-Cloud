#!/usr/bin/env python3
"""
WAV-Upgrade-Check: für jeden MP3-Track im downloads/ Ordner prüfen ob
eine FLAC/WAV-Quelle (Bandcamp free, SoundCloud FLAC) verfügbar ist.
Läuft nach Abschluss der MP3-Downloads.
"""
import re
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

DOWNLOADS = Path(__file__).parent.parent / "downloads"
AUDIO_EXTS = {".mp3", ".wav", ".flac", ".m4a"}


def already_have_lossless(stem: str) -> bool:
    """Prüft ob bereits eine verlustfreie Version existiert."""
    for ext in (".wav", ".flac"):
        if (DOWNLOADS / f"{stem}{ext}").exists():
            return True
    return False


def try_bandcamp_search(artist: str, title: str) -> str | None:
    """Sucht Track auf Bandcamp via yt-dlp."""
    query = f"{artist} {title} site:bandcamp.com"
    try:
        result = subprocess.run(
            ["yt-dlp", "--no-warnings", "--dump-json", "--no-download",
             f"ytsearch1:{artist} {title} bandcamp"],
            capture_output=True, text=True, timeout=60
        )
        if result.returncode == 0:
            import json
            for line in result.stdout.strip().split('\n'):
                if line.startswith('{'):
                    data = json.loads(line)
                    url = data.get('webpage_url', '')
                    if 'bandcamp.com' in url:
                        return url
    except Exception:
        pass
    return None


def try_sc_flac(query: str) -> bool:
    """Versucht FLAC via SoundCloud (selten, aber möglich)."""
    out = str(DOWNLOADS / "%(title).80s.%(ext)s")
    before = set(DOWNLOADS.iterdir())
    try:
        proc = subprocess.run(
            ["yt-dlp", "--no-warnings",
             "--format", "bestaudio[ext=flac]/bestaudio[ext=wav]/bestaudio",
             "--extract-audio", "--audio-format", "flac",
             "--playlist-items", "1", "--min-filesize", "10M",
             "--output", out, f"scsearch3:{query}"],
            capture_output=True, text=True, timeout=120
        )
        after = set(DOWNLOADS.iterdir())
        new = [f for f in (after - before) if f.suffix.lower() in {".flac", ".wav"}]
        return len(new) > 0
    except Exception:
        return False


def check_track(mp3_path: Path, artist: str, title: str) -> dict:
    """Prüft einen Track auf bessere Qualität."""
    print(f"  Prüfe: {artist} — {title}")

    # Bereits lossless vorhanden?
    if already_have_lossless(mp3_path.stem):
        print(f"    ✓ Lossless bereits vorhanden")
        return {"status": "already_lossless"}

    # Bandcamp-Suche
    from bandcamp_free import try_bandcamp_free
    bc_url = try_bandcamp_search(artist, title)
    if bc_url:
        print(f"    → Bandcamp gefunden: {bc_url[:60]}")
        fake_job = {"status": "downloading", "progress": "", "error": None, "files": []}
        if try_bandcamp_free(bc_url, "flac", fake_job):
            print(f"    ✓ FLAC via Bandcamp")
            return {"status": "upgraded", "source": "bandcamp"}

    # SoundCloud FLAC
    query = f"{artist} {title}"
    if try_sc_flac(query):
        print(f"    ✓ FLAC via SoundCloud")
        return {"status": "upgraded", "source": "soundcloud"}

    print(f"    — Kein Lossless gefunden, MP3 bleibt")
    return {"status": "mp3_only"}


def main():
    from dj_set_tracks import all_tracks

    mp3_files = {f.stem.lower(): f for f in DOWNLOADS.iterdir()
                 if f.suffix.lower() == ".mp3" and f.stat().st_size > 2_000_000}

    print(f"\n{'='*60}")
    print(f" WAV/FLAC Upgrade Check — {len(mp3_files)} MP3s")
    print(f"{'='*60}\n")

    upgraded = 0
    mp3_only = 0

    def norm(s):
        return re.sub(r'[^\w]', '', s.lower())

    for _, artist, title, _ in all_tracks():
        # Finde passendes MP3
        words = [w for w in norm(title).split() if len(w) > 3]
        match = next(
            (f for stem, f in mp3_files.items()
             if any(w in stem for w in words)),
            None
        )
        if not match:
            continue

        result = check_track(match, artist, title)
        if result["status"] == "upgraded":
            upgraded += 1
            # Altes MP3 löschen wenn Lossless erfolgreich
            match.unlink()
            print(f"    (MP3 gelöscht, Lossless behalten)")
        else:
            mp3_only += 1

        time.sleep(1)  # Anti-Bot

    print(f"\n{'='*60}")
    print(f" {upgraded} auf WAV/FLAC hochgestuft  |  {mp3_only} bleiben MP3")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    main()
