#!/usr/bin/env python3
"""
Queued alle DJ-Set Tracks + Apple Music Playlists zum Download.
Läuft einmalig, stellt alle Jobs in die KI-DAW Download-Queue.
"""
import sys
import time
import requests
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from dj_set_tracks import all_tracks, PHASES

API = "http://localhost:9879"
DOWNLOAD_DIR = Path(__file__).parent / "downloads"

# ── Apple Music Playlists (bereits extrahiert) ─────────────────────────────
APPLE_MUSIC_TRACKS = [
    # Blow Playlist
    ("EMSKI",           "Calm Down",            "EMSKI_BLOW"),
    ("Trbl",            "Blackcypher",           "EMSKI_BLOW"),
    ("Gaston fiore",    "Deep Inside Me",        "EMSKI_BLOW"),
    ("Sara Landry",     "Interesting",           "EMSKI_BLOW"),
    ("Sasha",           "Xpander",               "EMSKI_BLOW"),
    ("Ram",             "Ramsterdam Jorn Van Deynhoven Remix", "EMSKI_BLOW"),
    ("Barthezz",        "On The Move",           "EMSKI_BLOW"),
    ("JKS Lacchesi",    "L'orologio",            "EMSKI_BLOW"),
    ("Sander Kleinenberg","My Lexicon",          "EMSKI_BLOW"),
    ("KUKO Tokio Hotel","Catharsis",             "EMSKI_BLOW"),
    ("1LINE N1RVAAN",   "Belong",                "EMSKI_BLOW"),
    # French Techno Playlist
    ("Chris El Greco MEDUN Ambre Vallet", "Je Veux",        "FRENCH_TECHNO"),
    ("Chris El Greco",  "So Jump",               "FRENCH_TECHNO"),
    ("Neptunica Ely Oaks Ambre Vallet", "Ella Elle L'a",   "FRENCH_TECHNO"),
    ("Chris El Greco",  "Move Like That",        "FRENCH_TECHNO"),
    ("Ambre Vallet PS1","Femme Like You",        "FRENCH_TECHNO"),
    ("SMACK JKRS Ambre Vallet","Je Veux Danser","FRENCH_TECHNO"),
    ("Niklas Dee Ambre Vallet","Autour Du Monde","FRENCH_TECHNO"),
]


def already_downloaded(artist: str, title: str) -> bool:
    """Grobe Prüfung ob Track schon existiert."""
    keyword = title.split()[0].lower()
    for f in DOWNLOAD_DIR.iterdir():
        if keyword in f.name.lower():
            return True
    return False


def queue_track(artist: str, title: str, query: str, fmt: str = "mp3") -> str | None:
    try:
        search = f"ytsearch1:{query}"
        r = requests.post(f"{API}/api/download/start",
                          json={"url": search, "format": fmt}, timeout=5)
        return r.json().get("job_id")
    except Exception as e:
        print(f"  ✗ API Fehler: {e}")
        return None


def main():
    # Server check
    try:
        requests.get(f"{API}/", timeout=3)
    except Exception:
        print("✗ KI-DAW Server nicht erreichbar — starte ihn zuerst.")
        sys.exit(1)

    DOWNLOAD_DIR.mkdir(exist_ok=True)

    # ── DJ Set Tracks ────────────────────────────────────────────────────────
    dj_tracks = all_tracks()
    print(f"\n{'='*60}")
    print(f" DJ Set Queue: {len(dj_tracks)} Tracks + {len(APPLE_MUSIC_TRACKS)} Playlist-Tracks")
    print(f"{'='*60}")

    total = 0
    skipped = 0

    current_phase = None
    for phase_key, artist, title, query in dj_tracks:
        if phase_key != current_phase:
            current_phase = phase_key
            print(f"\n── {PHASES[phase_key]['label']} ──")

        if already_downloaded(artist, title):
            print(f"  ⏭  {artist} — {title}")
            skipped += 1
            continue

        job_id = queue_track(artist, title, query)
        if job_id:
            print(f"  ▶  [{job_id}] {artist} — {title}")
            total += 1
        time.sleep(0.3)  # API nicht überlasten

    # ── Apple Music Playlists ────────────────────────────────────────────────
    print(f"\n── Apple Music Playlists ──")
    for artist, title, playlist in APPLE_MUSIC_TRACKS:
        if already_downloaded(artist, title):
            print(f"  ⏭  {artist} — {title}")
            skipped += 1
            continue
        query = f"{artist} {title}"
        job_id = queue_track(artist, title, query)
        if job_id:
            print(f"  ▶  [{job_id}] [{playlist}] {artist} — {title}")
            total += 1
        time.sleep(0.3)

    print(f"\n{'='*60}")
    print(f" {total} Jobs gestartet · {skipped} bereits vorhanden")
    print(f" Downloads laufen parallel im Hintergrund.")
    print(f" Status: http://localhost:9879 → Downloader Tab")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    main()
