"""yt-dlp download manager — YouTube, SoundCloud, Bandcamp (playlists + singles)."""
import subprocess
import threading
import time
import uuid
from pathlib import Path

DOWNLOADS_DIR = Path(__file__).parent.parent / "downloads"
DOWNLOADS_DIR.mkdir(parents=True, exist_ok=True)

_jobs: dict[str, dict] = {}


def start_download(url: str, fmt: str = "mp3") -> str:
    job_id = str(uuid.uuid4())[:8]
    _jobs[job_id] = {
        "status": "queued",
        "progress": "Startet...",
        "error": None,
        "files": [],
        "url": url,
        "fmt": fmt,
        "started": time.time(),
    }
    threading.Thread(target=_run, args=(job_id, url, fmt), daemon=True).start()
    return job_id


def _run(job_id: str, url: str, fmt: str):
    job = _jobs[job_id]
    job["status"] = "downloading"

    out_tmpl = str(DOWNLOADS_DIR / "%(title).80s.%(ext)s")
    base_flags = ["yt-dlp", "--no-warnings", "--js-runtimes", "node", "--output", out_tmpl]

    if fmt == "wav":
        cmd = base_flags + ["--extract-audio", "--audio-format", "wav", url]
    elif fmt == "flac":
        cmd = base_flags + ["--extract-audio", "--audio-format", "flac", url]
    else:
        cmd = base_flags + ["--extract-audio", "--audio-format", "mp3", "--audio-quality", "0", url]

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
            job["status"] = "done"
            job["progress"] = "Fertig"
        else:
            job["status"] = "error"
            job["error"] = "\n".join(lines[-8:]) if lines else "Unbekannter Fehler"
    except Exception as e:
        job["status"] = "error"
        job["error"] = str(e)


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
