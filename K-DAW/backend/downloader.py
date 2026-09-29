"""yt-dlp download manager — multi-source chain: SC → free links → YT.
Anti-bot: randomised delays + reduced concurrency prevent IP bans.
"""
from __future__ import annotations
import json
import random
import re
import subprocess
import sys
import threading
import time
import uuid
from pathlib import Path

from bandcamp_free import is_bandcamp, try_bandcamp_free

DOWNLOADS_DIR = Path(__file__).parent.parent / "downloads"
DOWNLOADS_DIR.mkdir(parents=True, exist_ok=True)

COOKIES_FILE = Path(__file__).parent.parent / "yt_cookies.txt"

_jobs: dict[str, dict] = {}
# Reduced to 3 concurrent — fewer parallel requests = less bot-detection risk
_download_sem = threading.Semaphore(3)


def start_download(url: str, fmt: str = "mp3") -> str:
    job_id = str(uuid.uuid4())[:8]
    _jobs[job_id] = {
        "status": "queued",
        "progress": "Warte auf freien Slot...",
        "error": None,
        "files": [],
        "url": url,
        "fmt": fmt,
        "started": time.time(),
        "source": None,
    }
    threading.Thread(target=_run, args=(job_id, url, fmt), daemon=True).start()
    return job_id


def _run(job_id: str, url: str, fmt: str):
    # Stagger start times to spread server load and avoid burst detection
    time.sleep(random.uniform(0.5, 2.5))
    with _download_sem:
        job = _jobs[job_id]
        job["status"] = "downloading"
        _run_inner(job_id, url, fmt)


def _run_inner(job_id: str, url: str, fmt: str):
    job = _jobs[job_id]

    # ── Stufe 1: Bandcamp direkt → FLAC ─────────────────────────────────────
    if is_bandcamp(url):
        job["progress"] = "Bandcamp — prüfe Free Download (FLAC)..."
        if try_bandcamp_free(url, fmt, job):
            return

    # Extrahiere Suchquery aus ytsearch-URLs
    query = re.sub(r'^ytsearch\d+:', '', url).strip() if url.startswith("ytsearch") else None

    # ── Stufe 2: SoundCloud — kein IP-Ban, viele DJ-Tracks ──────────────────
    if query:
        job["progress"] = f"Suche SoundCloud: {query[:50]}..."
        if _try_soundcloud(job, query, fmt):
            return
        _anti_bot_pause(1.5, 3.5)

    # ── Stufe 3: YouTube — Beschreibung auf Free-Links scannen ──────────────
    yt_url = url if not query else f"ytsearch1:{query}"
    job["progress"] = "YouTube — prüfe Free-Download-Links in Beschreibung..."
    info = _get_yt_info(yt_url)
    if info:
        desc = info.get("description", "")
        title = info.get("title", "")
        safe_title = re.sub(r'[^\w\s\-]', '', title).strip()[:60]
        from free_dl_finder import try_free_download
        if try_free_download(desc, fmt, safe_title, job):
            job["status"] = "done"
            job["progress"] = "Fertig (Free Download)"
            _auto_analyze(dict(job))
            return
        override = job.pop("_yt_override_url", None)
        if override:
            yt_url = override

    _anti_bot_pause(1.0, 2.5)

    # ── Stufe 4: YouTube yt-dlp direktdownload ───────────────────────────────
    job["progress"] = "YouTube — lade direkt..."
    if _run_ytdlp(job, yt_url, fmt):
        return

    # ── Stufe 5: SoundCloud mit Remix/Edit-Suche — findet DJ-Versionen ohne DRM ─
    if query:
        remix_query = f"{query} remix edit bootleg"
        job["progress"] = f"Fallback SC remix-Suche: {remix_query[:50]}..."
        if _try_soundcloud(job, remix_query, fmt, n=3):
            return

    job["status"] = "error"
    job["error"] = job.get("error") or "Alle Quellen fehlgeschlagen (SC DRM + YT 403)"


# ─────────────────────────────────────────────────────────────────────────────


_BAD_TITLE_PATTERNS = re.compile(
    r'\b(slowed|reverb|lofi|lo-fi|nightcore|1\s*hour|loop|cover|karaoke|instrumental|sped up|speed up|pitched'
    r'|dj set|live set|radio show|radio episode|mixed by|full mix|full closing|podcast|rave set'
    r'|festival set|club space|sunrise set)\b',
    re.IGNORECASE
)


def _try_soundcloud(job: dict, query: str, fmt: str, n: int = 3) -> bool:
    """Probiert bis zu n SoundCloud-Suchergebnisse einzeln, überspringt DRM und schlechte Versionen."""
    out_tmpl = str(DOWNLOADS_DIR / "%(title).80s.%(ext)s")

    for i in range(1, n + 1):
        # playlist-items i = genau das i-te Suchergebnis, keine anderen
        sc_url = f"scsearch{n}:{query}"

        # Erst Metadaten holen um Titel zu prüfen — schlechte Versionen überspringen
        skip_this = False
        try:
            meta_cmd = ["yt-dlp", "--no-warnings", "--dump-json", "--no-download",
                        "--playlist-items", str(i)]
            if COOKIES_FILE.exists():
                meta_cmd += ["--cookies", str(COOKIES_FILE)]
            meta_cmd.append(sc_url)
            meta_result = subprocess.run(meta_cmd, capture_output=True, text=True, timeout=30)
            if meta_result.returncode == 0:
                for line in meta_result.stdout.strip().split('\n'):
                    if line.startswith('{'):
                        meta = json.loads(line)
                        title = meta.get('title', '')
                        if _BAD_TITLE_PATTERNS.search(title):
                            job["progress"] = f"SoundCloud #{i}: Skip '{title[:50]}' (schlechte Version)"
                            skip_this = True
                        break
        except Exception:
            pass
        if skip_this:
            _anti_bot_pause(0.2, 0.5)
            continue

        before = set(DOWNLOADS_DIR.iterdir())
        cmd = [
            "yt-dlp", "--no-warnings",
            "--format", "bestaudio/best",
            "--extract-audio", "--audio-format", "mp3", "--audio-quality", "0",
            "--output", out_tmpl,
            "--playlist-items", str(i),
            "--min-filesize", "2M",    # Previews / Snippets überspringen
        ]
        if COOKIES_FILE.exists():
            cmd += ["--cookies", str(COOKIES_FILE)]
        cmd.append(sc_url)

        try:
            proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1)
            lines = []
            is_drm = False
            start = time.time()
            for line in proc.stdout:
                if time.time() - start > 90:  # 90s Timeout pro SC-Versuch
                    proc.kill()
                    break
                line = line.strip()
                if not line:
                    continue
                lines.append(line)
                job["progress"] = f"SoundCloud #{i}: {line[:70]}"
                if "DRM protected" in line or "drm" in line.lower():
                    is_drm = True
            proc.wait(timeout=5)

            if is_drm:
                job["progress"] = f"SoundCloud #{i}: DRM, nächster Treffer..."
                _anti_bot_pause(0.5, 1.5)
                continue

            if proc.returncode == 0:
                after = set(DOWNLOADS_DIR.iterdir())
                new = [f for f in (after - before)
                       if f.suffix.lower() in {".mp3", ".wav", ".flac", ".ogg", ".m4a"}
                       and f.stat().st_size > 2_000_000
                       and not _BAD_TITLE_PATTERNS.search(f.stem)]
                if new:
                    job["files"].extend(f.name for f in new)
                    job["status"] = "done"
                    job["progress"] = f"Fertig via SoundCloud (#{i})"
                    job["source"] = "soundcloud"
                    threading.Thread(target=_auto_analyze, args=(dict(job),), daemon=True).start()
                    return True
                # If bad-version file downloaded, delete it and continue
                bad = [f for f in (after - before)
                       if f.suffix.lower() in {".mp3", ".wav", ".flac", ".ogg", ".m4a"}
                       and _BAD_TITLE_PATTERNS.search(f.stem)]
                for f in bad:
                    try:
                        f.unlink()
                    except Exception:
                        pass

        except Exception as e:
            job["progress"] = f"SoundCloud #{i} Fehler: {e}"

        _anti_bot_pause(0.5, 1.5)

    job["progress"] = f"SoundCloud: alle {n} Treffer DRM oder leer → YouTube..."
    return False


def _get_yt_info(url: str) -> dict | None:
    """Holt YouTube-Metadaten (für Free-Link-Scan in Beschreibung)."""
    try:
        cmd = ["yt-dlp", "--dump-json", "--no-download", "--no-warnings",
               "--extractor-args", "youtube:player_client=android"]
        if COOKIES_FILE.exists():
            cmd += ["--cookies", str(COOKIES_FILE)]
        cmd.append(url)
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        if result.returncode == 0:
            first_line = next((l for l in result.stdout.strip().split('\n') if l.startswith('{')), None)
            if first_line:
                return json.loads(first_line)
    except Exception:
        pass
    return None


def _run_ytdlp(job: dict, url: str, fmt: str) -> bool:
    """Lädt via yt-dlp herunter, gibt True bei Erfolg."""
    out_tmpl = str(DOWNLOADS_DIR / "%(title).80s.%(ext)s")
    # android client umgeht 403 auf DASH-Audio-Streams (Server-IP-Ban)
    base = [
        "yt-dlp", "--no-warnings",
        "--extractor-args", "youtube:player_client=android",
        "--format", "bestaudio[ext=webm]/bestaudio[ext=m4a]/bestaudio/best",
        "--output", out_tmpl,
        "--retries", "3",
        "--fragment-retries", "3",
        "--sleep-requests", "2",
    ]
    if COOKIES_FILE.exists():
        base += ["--cookies", str(COOKIES_FILE)]

    if fmt == "wav":
        cmd = base + ["--extract-audio", "--audio-format", "wav", url]
    elif fmt == "flac":
        cmd = base + ["--extract-audio", "--audio-format", "flac", url]
    else:
        cmd = base + ["--extract-audio", "--audio-format", "mp3", "--audio-quality", "0", url]

    before = set(DOWNLOADS_DIR.iterdir())
    try:
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1)
        lines = []
        for line in proc.stdout:
            line = line.strip()
            if line:
                lines.append(line)
                job["progress"] = line
        proc.wait()

        if proc.returncode == 0:
            after = set(DOWNLOADS_DIR.iterdir())
            new_files = [f for f in (after - before) if f.suffix.lower() in {".mp3", ".wav", ".flac", ".ogg", ".m4a"}]
            good = [f for f in new_files if not _BAD_TITLE_PATTERNS.search(f.stem)]
            bad = [f for f in new_files if _BAD_TITLE_PATTERNS.search(f.stem)]
            for f in bad:
                try:
                    f.unlink()
                except Exception:
                    pass
            if good:
                job["files"].extend(f.name for f in good)
                job["status"] = "done"
                job["progress"] = "Fertig"
                job["source"] = "youtube"
                threading.Thread(target=_auto_analyze, args=(dict(job),), daemon=True).start()
                return True

        job["error"] = "\n".join(lines[-6:]) if lines else "Unbekannter Fehler"
    except Exception as e:
        job["error"] = str(e)

    return False


def _auto_analyze(job: dict):
    try:
        _scripts = str(Path(__file__).parent.parent / "scripts")
        if _scripts not in sys.path:
            sys.path.insert(0, _scripts)
        from analyze_quality import analyze_file
        for name in job.get("files", []):
            path = DOWNLOADS_DIR / name
            if path.exists() and path.suffix.lower() in {".mp3", ".wav", ".flac", ".ogg", ".m4a"}:
                try:
                    analyze_file(path)
                except Exception:
                    pass
    except Exception:
        pass


def _anti_bot_pause(lo: float, hi: float):
    """Zufällige Pause zwischen Quellen — verhindert Bot-Erkennung."""
    time.sleep(random.uniform(lo, hi))


def get_job(job_id: str) -> dict | None:
    return _jobs.get(job_id)


def list_downloads() -> list[dict]:
    DOWNLOADS_DIR.mkdir(parents=True, exist_ok=True)
    files = []
    for f in DOWNLOADS_DIR.iterdir():
        if f.suffix.lower() in {".mp3", ".wav", ".flac", ".ogg", ".m4a", ".opus"}:
            files.append({
                "name": f.name,
                "size": f.stat().st_size,
                "mtime": f.stat().st_mtime,
                "type": f.suffix[1:].lower(),
            })
    return sorted(files, key=lambda x: x["mtime"], reverse=True)[:100]
