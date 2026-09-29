#!/usr/bin/env python3
"""
Finds all "Official Video" YouTube downloads in downloads/ and replaces them
with SoundCloud audio versions (no video sound effects, cleaner audio).

Strategy per track:
1. Extract artist + title from filename
2. Try scsearch3 on SoundCloud
3. If clean (no DRM, no bad-title, min 2MB), download & delete old file
4. If SC fails, keep the original (no regression)
"""
import json
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

DOWNLOADS = Path(__file__).parent.parent / "downloads"
COOKIES_FILE = Path(__file__).parent.parent / "yt_cookies.txt"
LOG_FILE = Path("/tmp/replace_official_videos.log")

VIDEO_TITLE_PATTERNS = re.compile(
    r'\(Official\s*(Music\s*)?Video\)|'
    r'\[Official\s*(Music\s*)?Video\]|'
    r'\(Official\s*HD\s*Video\)|'
    r'\[Official\s*HD\s*Video\]|'
    r'\(Official\s*(Lyric|Audio|Visualis[ae]r|Clip)\)|'
    r'\[Official\s*(Lyric|Audio|Visualis[ae]r|Clip)\]|'
    r'Official\s*Video\s*[|\|]|'
    r'\(Video\s*Oficial\)|'
    r'\(offiziell[ae]s?\s*Video\)|'
    r'\bOfficial\s*Video\b',
    re.IGNORECASE
)

BAD_PATTERNS = re.compile(
    r'\b(slowed|reverb|lofi|lo-fi|nightcore|1\s*hour|loop|cover|karaoke|'
    r'instrumental|sped up|speed up|pitched|dj set|live set|radio show|'
    r'radio episode|mixed by|full mix|podcast|rave set|festival set)\b',
    re.IGNORECASE
)


def log(msg: str):
    ts = time.strftime('%H:%M:%S')
    line = f"[{ts}] {msg}"
    print(line, flush=True)
    with open(LOG_FILE, 'a') as f:
        f.write(line + '\n')


def clean_title(filename: str) -> str:
    """Strip video indicators, clean up the title for search."""
    name = Path(filename).stem
    name = VIDEO_TITLE_PATTERNS.sub('', name)
    # Remove trailing junk
    name = re.sub(r'[\|\[\(].*$', '', name).strip()
    name = re.sub(r'\s+', ' ', name).strip()
    return name


def extract_artist_title(filename: str) -> tuple[str, str]:
    """Try to split 'Artist - Title' from filename."""
    clean = clean_title(filename)
    if ' - ' in clean:
        parts = clean.split(' - ', 1)
        return parts[0].strip(), parts[1].strip()
    return '', clean.strip()


def try_soundcloud(query: str, old_path: Path) -> bool:
    """Try downloading from SoundCloud. Returns True if replacement succeeded."""
    out_tmpl = str(DOWNLOADS / "%(title).80s.%(ext)s")
    before = set(DOWNLOADS.iterdir())

    for attempt in range(1, 4):
        sc_url = f"scsearch3:{query}"

        # Pre-check metadata
        skip = False
        try:
            meta_cmd = ["yt-dlp", "--no-warnings", "--dump-json", "--no-download",
                        "--playlist-items", str(attempt)]
            if COOKIES_FILE.exists():
                meta_cmd += ["--cookies", str(COOKIES_FILE)]
            meta_cmd.append(sc_url)
            meta = subprocess.run(meta_cmd, capture_output=True, text=True, timeout=30)
            if meta.returncode == 0:
                for line in meta.stdout.strip().split('\n'):
                    if line.startswith('{'):
                        data = json.loads(line)
                        title = data.get('title', '')
                        duration = data.get('duration', 0) or 0
                        if BAD_PATTERNS.search(title):
                            log(f"    SC #{attempt}: skip bad title '{title[:50]}'")
                            skip = True
                        if duration < 90:
                            log(f"    SC #{attempt}: skip short ({duration}s) '{title[:40]}'")
                            skip = True
                        break
        except Exception:
            pass

        if skip:
            time.sleep(0.3)
            continue

        cmd = [
            "yt-dlp", "--no-warnings",
            "--format", "bestaudio/best",
            "--extract-audio", "--audio-format", "mp3", "--audio-quality", "0",
            "--output", out_tmpl,
            "--playlist-items", str(attempt),
            "--min-filesize", "2M",
        ]
        if COOKIES_FILE.exists():
            cmd += ["--cookies", str(COOKIES_FILE)]
        cmd.append(sc_url)

        try:
            proc = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
            after = set(DOWNLOADS.iterdir())
            new_files = [
                f for f in (after - before)
                if f.suffix.lower() in {".mp3", ".wav", ".flac"}
                and f.stat().st_size > 2_000_000
                and not BAD_PATTERNS.search(f.stem)
            ]
            if new_files:
                new_file = new_files[0]
                log(f"    ✓ SC found: {new_file.name[:60]}")
                # Delete the old official video file
                try:
                    old_path.unlink()
                    log(f"    ✗ Deleted: {old_path.name[:55]}")
                except Exception as e:
                    log(f"    ! Could not delete old file: {e}")
                return True

            if "DRM" in (proc.stdout + proc.stderr):
                log(f"    SC #{attempt}: DRM protected")
        except subprocess.TimeoutExpired:
            log(f"    SC #{attempt}: timeout")
        except Exception as e:
            log(f"    SC #{attempt}: error {e}")

        time.sleep(0.5)

    return False


def main():
    log(f"=== Official Video Replacement ===")
    log(f"Scanning {DOWNLOADS}...")

    # Find all official video files
    official_files = [
        f for f in DOWNLOADS.iterdir()
        if f.suffix.lower() == '.mp3'
        and VIDEO_TITLE_PATTERNS.search(f.stem)
        and f.stat().st_size > 1_000_000
    ]

    log(f"Found {len(official_files)} Official Video files to replace\n")

    replaced = 0
    failed = 0

    for i, old_file in enumerate(sorted(official_files), 1):
        artist, title = extract_artist_title(old_file.name)
        query = f"{artist} {title}".strip() if artist else title
        # Fallback: use clean name directly
        if not query:
            query = clean_title(old_file.name)

        log(f"[{i:2d}/{len(official_files)}] {old_file.name[:65]}")
        log(f"    Query: {query[:60]}")

        if try_soundcloud(query, old_file):
            replaced += 1
        else:
            failed += 1
            log(f"    → Keeping original (no SC match)")

        time.sleep(1.0)  # anti-bot pause between tracks

    log(f"\n{'='*60}")
    log(f"  Replaced: {replaced}  |  Kept as-is: {failed}")
    log(f"{'='*60}")


if __name__ == "__main__":
    if not DOWNLOADS.exists():
        print(f"Downloads dir not found: {DOWNLOADS}")
        sys.exit(1)
    main()
