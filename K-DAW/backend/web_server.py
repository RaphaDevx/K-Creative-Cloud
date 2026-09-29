"""FastAPI web server — KI-DAW backend."""
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import uvicorn
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

# ── Path resolution (dev vs. PyInstaller bundle) ──────────────────────────────
# When frozen by PyInstaller, __file__ lives in a temp dir (_MEIPASS).
# Bundled assets (web UI) live there; user data (renders, downloads) go to ~/K-DAW.
if getattr(sys, "frozen", False):
    _BUNDLE = Path(sys._MEIPASS)
    _DATA   = Path.home() / "K-DAW"
else:
    _BUNDLE = Path(__file__).parent
    _DATA   = Path(__file__).parent.parent
    sys.path.insert(0, str(_BUNDLE.parent / "scripts"))

WEB_DIR      = _DATA   / "web"
RENDERS_DIR  = _DATA   / "renders"
DOWNLOADS_DIR = _DATA  / "downloads"

from music_ai import generate_music
from midi_generator import list_renders, midi_to_wav, music_to_midi
from downloader import start_download, get_job, list_downloads
from bandcamp_free import get_bandcamp_info, is_bandcamp
from midi_learn import (
    INTERNAL_EVENTS, ALL_EVENTS,
    load_mapping, save_mapping, delete_mapping, list_mappings,
)

try:
    if not getattr(sys, "frozen", False):
        from analyze_quality import analyze_file as _analyze_file, grade_ceiling, GRADE_EMOJI
    else:
        raise ImportError
except ImportError:
    _analyze_file = None

app = FastAPI(title="KI-DAW")

RENDERS_DIR.mkdir(parents=True, exist_ok=True)
DOWNLOADS_DIR.mkdir(parents=True, exist_ok=True)
app.mount("/renders", StaticFiles(directory=str(RENDERS_DIR)), name="renders")
app.mount("/downloads", StaticFiles(directory=str(DOWNLOADS_DIR)), name="downloads")
_novnc = Path("/usr/share/novnc")
if _novnc.exists():
    app.mount("/novnc", StaticFiles(directory=str(_novnc)), name="novnc")


@app.get("/")
async def index():
    return FileResponse(str(WEB_DIR / "index.html"))


@app.get("/api/renders")
async def api_renders():
    return {"files": list_renders()}


@app.post("/api/download/start")
async def api_download_start(body: dict):
    url = body.get("url", "").strip()
    fmt = body.get("format", "mp3")
    if not url:
        return JSONResponse({"error": "Keine URL angegeben"}, status_code=400)
    job_id = start_download(url, fmt)
    return {"job_id": job_id}


@app.get("/api/download/status/{job_id}")
async def api_download_status(job_id: str):
    job = get_job(job_id)
    if not job:
        return JSONResponse({"error": "Job nicht gefunden"}, status_code=404)
    return job


_GRADE_ORDER = {"CLUB-READY": 0, "GOOD": 1, "MEDIUM": 2, "LOW": 3, None: 4, "unknown": 4}

@app.get("/api/downloads")
async def api_downloads(sort: str = "date", order: str = "desc"):
    files = list_downloads()

    # Attach quality from cache (fast) or ID3 tags (MP3 fallback)
    try:
        sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))
        from analyze_quality import get_cached, CACHE_FILE
        cache = {}
        try:
            import json as _json
            cache = _json.loads(CACHE_FILE.read_text())
        except Exception:
            pass
    except Exception:
        cache = {}

    for f in files:
        cached = cache.get(f["name"])
        if cached:
            f["quality"] = cached.get("grade")
            f["freq_ceiling"] = f'{cached.get("ceiling_khz", "")} kHz' if cached.get("ceiling_khz") else ""
        else:
            # Fallback: try ID3 tag for MP3
            try:
                from mutagen.id3 import ID3
                tags = ID3(str(DOWNLOADS_DIR / f["name"]))
                q = tags.get("TXXX:QUALITY")
                f["quality"] = str(q) if q else None
                fc = tags.get("TXXX:FREQ_CEILING")
                f["freq_ceiling"] = str(fc) if fc else None
            except Exception:
                f["quality"] = None
                f["freq_ceiling"] = None

    # Sort
    rev = order == "desc"
    if sort == "quality":
        files.sort(key=lambda x: _GRADE_ORDER.get(x.get("quality"), 4), reverse=not rev)
    elif sort == "name":
        files.sort(key=lambda x: x["name"].lower(), reverse=rev)
    elif sort == "size":
        files.sort(key=lambda x: x["size"], reverse=rev)
    elif sort == "type":
        files.sort(key=lambda x: x["type"], reverse=rev)
    else:  # date (default)
        files.sort(key=lambda x: x["mtime"], reverse=rev)

    return {"files": files}


USB_MOUNT = Path("/mnt/kdj")

@app.post("/api/usb/copy")
async def api_usb_copy(body: dict = {}):
    """Copy selected files (or all) to mounted K-DJ USB stick."""
    import asyncio, shutil
    filenames = body.get("files")  # None = copy all
    if not USB_MOUNT.exists() or not USB_MOUNT.is_mount():
        return JSONResponse({"error": "K-DJ Stick nicht eingehängt (/mnt/kdj)"}, status_code=503)

    files = list_downloads()
    if filenames:
        files = [f for f in files if f["name"] in filenames]

    copied, skipped = [], []
    for f in files:
        src = DOWNLOADS_DIR / f["name"]
        dst = USB_MOUNT / f["name"]
        if not src.exists():
            continue
        if dst.exists() and dst.stat().st_size == src.stat().st_size:
            skipped.append(f["name"])
            continue
        shutil.copy2(src, dst)
        copied.append(f["name"])

    return {"copied": len(copied), "skipped": len(skipped), "files": copied}

@app.get("/api/usb/status")
async def api_usb_status():
    if not USB_MOUNT.exists() or not USB_MOUNT.is_mount():
        return {"mounted": False}
    stat = shutil.disk_usage(str(USB_MOUNT))
    return {
        "mounted": True,
        "total_gb": round(stat.total / 1e9, 1),
        "used_gb":  round(stat.used  / 1e9, 1),
        "free_gb":  round(stat.free  / 1e9, 1),
    }

@app.get("/api/bandcamp/info")
async def api_bandcamp_info(url: str):
    """Gibt Infos über eine Bandcamp-URL zurück (Titel, ob Free/NaYP, Tracks)."""
    if not is_bandcamp(url):
        return JSONResponse({"error": "Keine Bandcamp-URL"}, status_code=400)
    import asyncio
    loop = asyncio.get_event_loop()
    info = await loop.run_in_executor(None, get_bandcamp_info, url)
    return info


@app.post("/api/analyze/{filename}")
async def api_analyze(filename: str):
    if not _analyze_file:
        return JSONResponse({"error": "Spectral analysis not available in this build"}, status_code=501)
    import asyncio
    path = DOWNLOADS_DIR / filename
    if not path.exists():
        return JSONResponse({"error": "Datei nicht gefunden"}, status_code=404)
    try:
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(None, _analyze_file, path)
        return result
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


# ─── MIDI-Learn API ───────────────────────────────────────────────────────────

@app.get("/api/midi/events")
async def api_midi_events():
    """Return the full internal event catalog (sections + flat list)."""
    return {"sections": INTERNAL_EVENTS, "all": ALL_EVENTS}


@app.get("/api/midi/mappings")
async def api_midi_mappings():
    """List all saved controller mapping files."""
    return {"mappings": list_mappings()}


@app.get("/api/midi/mappings/{filename}")
async def api_midi_mapping_get(filename: str):
    data = load_mapping(filename)
    if not data:
        return JSONResponse({"error": "Not found"}, status_code=404)
    return data


@app.post("/api/midi/mappings")
async def api_midi_mapping_save(body: dict):
    """
    Save a controller mapping.
    Body: { filename, controller_name, created, mappings: { "cc:0:1": "crossfader", ... } }
    """
    filename = body.get("filename", "").strip()
    if not filename:
        return JSONResponse({"error": "filename required"}, status_code=400)
    data = {
        "controller_name": body.get("controller_name", "Unknown Controller"),
        "created": body.get("created", ""),
        "version": "1.0",
        "mappings": body.get("mappings", {}),
    }
    path = save_mapping(filename, data)
    return {"saved": Path(path).name}


@app.delete("/api/midi/mappings/{filename}")
async def api_midi_mapping_delete(filename: str):
    if delete_mapping(filename):
        return {"deleted": filename}
    return JSONResponse({"error": "Not found"}, status_code=404)


@app.post("/api/launch-lmms")
async def launch_lmms(body: dict = {}):
    project = body.get("project", "")
    cmd = ["lmms"] + ([project] if project else [])
    subprocess.Popen(cmd, start_new_session=True)
    return {"launched": True}


@app.websocket("/ws")
async def ws_endpoint(ws: WebSocket):
    await ws.accept()
    try:
        while True:
            raw = await ws.receive_text()
            data = json.loads(raw)
            action = data.get("action", "")

            if action == "generate":
                prompt = data.get("prompt", "")
                if not prompt:
                    await ws.send_json({"type": "error", "message": "Kein Prompt angegeben"})
                    continue

                await ws.send_json({"type": "status", "message": "Claude generiert Musik..."})
                try:
                    music = generate_music(prompt)
                except Exception as e:
                    await ws.send_json({"type": "error", "message": f"Generierung fehlgeschlagen: {e}"})
                    continue

                await ws.send_json({"type": "music_data", "data": music})
                await ws.send_json({"type": "status", "message": "Schreibe MIDI-File..."})

                try:
                    midi_path = music_to_midi(music)
                except Exception as e:
                    await ws.send_json({"type": "error", "message": f"MIDI-Fehler: {e}"})
                    continue

                wav_path = None
                await ws.send_json({"type": "status", "message": "Rendere Audio via FluidSynth..."})
                try:
                    wav_path = midi_to_wav(midi_path)
                except Exception:
                    pass

                await ws.send_json({
                    "type": "complete",
                    "music": music,
                    "midi": Path(midi_path).name,
                    "audio": Path(wav_path).name if wav_path else None,
                })

            elif action == "list_renders":
                await ws.send_json({"type": "renders", "files": list_renders()})

    except WebSocketDisconnect:
        pass
    except Exception as e:
        try:
            await ws.send_json({"type": "error", "message": str(e)})
        except Exception:
            pass


if __name__ == "__main__":
    port = int(os.environ.get("KDAW_PORT", "9879"))
    host = os.environ.get("KDAW_HOST", "127.0.0.1")
    uvicorn.run(app, host=host, port=port, reload=False)
