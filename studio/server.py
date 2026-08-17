"""
K-Creative Studio — Backend Server
Serves the studio UI and provides APIs for:
- File browser / project context
- Headless tool execution (Blender, Inkscape, LMMS)
- Render output gallery
- WebSocket for terminal relay
"""
import asyncio
import base64
import json
import os
import pty
import select
import subprocess
import termios
import fcntl
import struct
import time
import uuid
import secrets
import sqlite3
from pathlib import Path
from typing import Optional

import aiofiles
import uvicorn
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.responses import FileResponse, JSONResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.cors import CORSMiddleware

app = FastAPI(title="K-Creative Studio")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

import sys as _sys

# Support PyInstaller bundle: __file__ is unreliable in frozen mode
if getattr(_sys, 'frozen', False):
    ROOT = Path(_sys.executable).parent
else:
    ROOT = Path(__file__).parent

HOME         = Path.home()
K_DIR        = Path(os.environ.get("K_CREATIVE_DIR", HOME / "K-Creative"))
ASSETS_DIR   = K_DIR / "assets"
PROJECTS_DIR = K_DIR
RENDERS_DIR  = K_DIR / "renders"
SCRIPTS_DIR  = ROOT / "headless"
DJ_LIBRARY   = Path(os.environ.get("K_MUSIC_DIR", HOME / "Music"))
DJ_DB        = K_DIR / "dj_library.db"
DJ_SC_HOST   = "127.0.0.1"
DJ_SC_PORT   = 57120
RENDERS_DIR.mkdir(parents=True, exist_ok=True)

# ── DJ Engine init ─────────────────────────────────────────────
_api_keys_file = ROOT / "dj_api_keys.json"
_api_keys: dict[str, dict] = {}

def _load_api_keys():
    if _api_keys_file.exists():
        try:
            _api_keys.update(json.loads(_api_keys_file.read_text()))
        except Exception:
            pass

def _save_api_keys():
    _api_keys_file.write_text(json.dumps(_api_keys, indent=2))

def _init_dj_db():
    con = sqlite3.connect(DJ_DB)
    con.execute("""
        CREATE TABLE IF NOT EXISTS tracks (
            id TEXT PRIMARY KEY, path TEXT UNIQUE NOT NULL,
            title TEXT, artist TEXT, album TEXT,
            bpm REAL DEFAULT 0, key TEXT DEFAULT '',
            duration REAL DEFAULT 0, size INTEGER DEFAULT 0,
            modified REAL DEFAULT 0, indexed_at REAL DEFAULT 0
        )
    """)
    con.commit(); con.close()

_load_api_keys()
try:
    _init_dj_db()
except Exception as _e:
    print(f"DJ DB init: {_e}")

# Active PTY sessions and headless jobs
pty_sessions: dict[str, dict] = {}
jobs: dict[str, dict] = {}  # job_id → {status, log, returncode}


# ── Static files ─────────────────────────────────────────────
@app.get("/", response_class=HTMLResponse)
async def serve_index():
    async with aiofiles.open(ROOT / "index.html", "r") as f:
        return await f.read()

@app.get("/live", response_class=HTMLResponse)
async def serve_live():
    async with aiofiles.open(ROOT / "live.html", "r") as f:
        return await f.read()

@app.get("/static/{path:path}")
@app.head("/static/{path:path}")
async def serve_static(path: str):
    file_path = ROOT / "static" / path
    if not file_path.exists():
        raise HTTPException(404)
    return FileResponse(file_path)


# ── Design System API ─────────────────────────────────────────
DS_ROOT = Path("/home/raphael/K-Creative-Cloud/packages/design-system")

@app.get("/api/design-system/tokens")
async def get_all_tokens():
    result = {}
    for category in ["base", "semantic", "components"]:
        cat_dir = DS_ROOT / "tokens" / category
        if cat_dir.exists():
            result[category] = {}
            for f in sorted(cat_dir.glob("*.json")):
                try:
                    result[category][f.stem] = json.loads(f.read_text())
                except Exception:
                    pass
    return JSONResponse(result)

@app.post("/api/design-system/tokens/{category}/{name}")
async def save_token_file(category: str, name: str, request):
    allowed = {"base", "semantic", "components"}
    if category not in allowed:
        raise HTTPException(400, "Invalid category")
    target = DS_ROOT / "tokens" / category / f"{name}.json"
    body = await request.body()
    try:
        parsed = json.loads(body)
    except Exception:
        raise HTTPException(400, "Invalid JSON")
    target.write_text(json.dumps(parsed, indent=2, ensure_ascii=False))
    return {"ok": True, "path": str(target)}

@app.get("/api/design-system/wireframes")
async def list_wireframes():
    wf_dir = DS_ROOT / "wireframes"
    files = []
    if wf_dir.exists():
        for f in sorted(wf_dir.glob("*.layout.json")):
            try:
                data = json.loads(f.read_text())
                files.append({
                    "id": f.stem.replace(".layout", ""),
                    "title": data.get("title", f.stem),
                    "path": str(f)
                })
            except Exception:
                files.append({"id": f.stem, "title": f.stem, "path": str(f)})
    return JSONResponse(files)

@app.get("/api/design-system/wireframes/{name}")
async def get_wireframe(name: str):
    f = DS_ROOT / "wireframes" / f"{name}.layout.json"
    if not f.exists():
        raise HTTPException(404)
    return JSONResponse(json.loads(f.read_text()))

@app.post("/api/design-system/build")
async def build_tokens():
    dist = DS_ROOT / "dist"
    (dist / "css").mkdir(parents=True, exist_ok=True)
    (dist / "tailwind").mkdir(parents=True, exist_ok=True)
    (dist / "ts").mkdir(parents=True, exist_ok=True)

    colors_path = DS_ROOT / "tokens" / "base" / "colors.json"
    spacing_path = DS_ROOT / "tokens" / "base" / "spacing.json"
    typography_path = DS_ROOT / "tokens" / "base" / "typography.json"
    radius_path = DS_ROOT / "tokens" / "base" / "radius.json"

    css_vars = [":root {"]
    tw_colors = {}
    ts_lines = ["export const tokens = {"]

    if colors_path.exists():
        colors = json.loads(colors_path.read_text()).get("color", {})
        ts_lines.append("  color: {")
        for group, shades in colors.items():
            if isinstance(shades, dict):
                for shade, token in shades.items():
                    if isinstance(token, dict) and "$value" in token:
                        key = f"--k-{group}-{shade}".replace(".", "-")
                        css_vars.append(f"  {key}: {token['$value']};")
                        tw_colors.setdefault(group, {})[shade] = token["$value"]
                        ts_lines.append(f"    '{group}-{shade}': '{token['$value']}',")
        ts_lines.append("  },")

    if spacing_path.exists():
        spacing = json.loads(spacing_path.read_text()).get("spacing", {})
        css_vars.append("  /* spacing */")
        ts_lines.append("  spacing: {")
        for name, token in spacing.items():
            if isinstance(token, dict) and "$value" in token:
                css_vars.append(f"  --k-space-{name}: {token['$value']};")
                ts_lines.append(f"    '{name}': '{token['$value']}',")
        ts_lines.append("  },")

    if radius_path.exists():
        radii = json.loads(radius_path.read_text()).get("radius", {})
        css_vars.append("  /* radius */")
        for name, token in radii.items():
            if isinstance(token, dict) and "$value" in token:
                css_vars.append(f"  --k-radius-{name}: {token['$value']};")

    css_vars.append("}")
    css_content = "\n".join(css_vars)
    ts_lines.append("} as const;")
    ts_content = "\n".join(ts_lines)
    tw_content = f"module.exports = {json.dumps({'colors': tw_colors, 'spacing': {k: v['$value'] for k, v in json.loads(spacing_path.read_text()).get('spacing', {}).items() if isinstance(v, dict)}, 'borderRadius': {k: v['$value'] for k, v in json.loads(radius_path.read_text()).get('radius', {}).items() if isinstance(v, dict)}}, indent=2)};"

    (dist / "css" / "variables.css").write_text(css_content)
    (dist / "ts" / "tokens.ts").write_text(ts_content)
    (dist / "tailwind" / "theme.js").write_text(tw_content)

    return {"ok": True, "files": [
        str(dist / "css" / "variables.css"),
        str(dist / "ts" / "tokens.ts"),
        str(dist / "tailwind" / "theme.js")
    ]}


# ── Tool Status / Port Check ──────────────────────────────────
import socket

def port_open(host: str, port: int, timeout: float = 1.0) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False

@app.get("/api/check")
async def check_tools():
    """Check which tool ports are reachable."""
    checks = {
        "blender_vnc":    port_open("localhost", 6080),  # websockify
        "blender_mcp":    port_open("localhost", 9876),  # blender addon
        "gimp":           port_open("localhost", 9877),
        "freecad":        port_open("localhost", 9878),
    }
    # Check Xvfb display :99
    import os
    checks["xvfb"] = os.path.exists("/tmp/.X99-lock")
    # Check x11vnc running
    try:
        r = subprocess.run(["pgrep", "-x", "x11vnc"], capture_output=True)
        checks["x11vnc"] = r.returncode == 0
    except Exception:
        checks["x11vnc"] = False
    # Check Blender process
    try:
        r = subprocess.run(["pgrep", "-x", "blender"], capture_output=True)
        checks["blender_proc"] = r.returncode == 0
    except Exception:
        checks["blender_proc"] = False

    return JSONResponse(checks)


# ── Headless Execution API ────────────────────────────────────
from fastapi import Body

@app.post("/api/exec/blender")
async def exec_blender(payload: dict = Body(...)):
    """
    Run Blender headlessly with a Python script.
    Body: { "script": "<python code>", "blend": "<optional .blend path>",
            "render": true/false, "output": "<optional output dir>" }
    Returns: { "job_id": "...", "status": "queued" }
    """
    job_id = str(uuid.uuid4())[:8]
    script_content = payload.get("script", "")
    blend_file = payload.get("blend", "")
    do_render = payload.get("render", False)
    output_dir = payload.get("output", str(RENDERS_DIR / job_id))

    # Write script to temp file
    script_path = f"/tmp/k-blender-{job_id}.py"
    Path(script_path).write_text(script_content)
    Path(output_dir).mkdir(parents=True, exist_ok=True)

    cmd = ["blender", "-b"]
    if blend_file and Path(blend_file).exists():
        cmd.append(blend_file)
    if do_render:
        cmd += ["-o", output_dir + "/frame####", "-f", "1"]
    cmd += ["-P", script_path]

    jobs[job_id] = {"status": "running", "log": "", "cmd": " ".join(cmd), "output": output_dir}

    async def run():
        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT,
                env={**os.environ, "DISPLAY": ":99"},
            )
            stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=120)
            log = stdout.decode(errors="replace")
            jobs[job_id].update({"status": "done", "log": log, "returncode": proc.returncode})
        except asyncio.TimeoutError:
            jobs[job_id].update({"status": "timeout", "log": "Timeout after 120s"})
        except Exception as e:
            jobs[job_id].update({"status": "error", "log": str(e)})
        finally:
            Path(script_path).unlink(missing_ok=True)

    asyncio.create_task(run())
    return JSONResponse({"job_id": job_id, "status": "queued", "output": output_dir})


@app.post("/api/exec/inkscape")
async def exec_inkscape(payload: dict = Body(...)):
    """
    Run Inkscape headlessly.
    Body: { "input": "<svg path>", "output": "<output path>",
            "actions": "<inkscape actions string>", "export_type": "svg|png|pdf" }
    """
    job_id = str(uuid.uuid4())[:8]
    input_path = payload.get("input", "")
    output_path = payload.get("output", str(RENDERS_DIR / f"{job_id}_out.svg"))
    actions = payload.get("actions", "")
    export_type = payload.get("export_type", "svg")

    if not input_path or not Path(input_path).exists():
        raise HTTPException(400, "input file not found")

    cmd = ["inkscape", input_path,
           f"--export-type={export_type}",
           f"--export-filename={output_path}"]
    if actions:
        cmd += ["--actions", actions]

    jobs[job_id] = {"status": "running", "log": "", "output": output_path}

    async def run():
        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.STDOUT)
            stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=60)
            jobs[job_id].update({"status": "done", "log": stdout.decode(errors="replace"),
                                  "returncode": proc.returncode})
        except Exception as e:
            jobs[job_id].update({"status": "error", "log": str(e)})

    asyncio.create_task(run())
    return JSONResponse({"job_id": job_id, "status": "queued", "output": output_path})


@app.get("/api/jobs")
async def list_jobs():
    return JSONResponse({"jobs": jobs})


@app.get("/api/jobs/{job_id}")
async def get_job(job_id: str):
    if job_id not in jobs:
        raise HTTPException(404, "Job not found")
    return JSONResponse(jobs[job_id])


@app.get("/api/renders")
async def list_renders(dir: Optional[str] = None):
    """List render outputs. Returns newest first."""
    base = Path(dir) if dir else RENDERS_DIR
    if not base.exists():
        return JSONResponse({"files": []})
    files = []
    for f in base.rglob("*"):
        if f.is_file() and f.suffix.lower() in {".png", ".jpg", ".webp", ".glb", ".gltf", ".svg"}:
            stat = f.stat()
            files.append({
                "name": f.name,
                "path": str(f),
                "ext": f.suffix.lower(),
                "size": stat.st_size,
                "modified": stat.st_mtime,
                "job_id": f.parent.name if f.parent != base else None,
            })
    files.sort(key=lambda x: x["modified"], reverse=True)
    return JSONResponse({"files": files[:50]})


@app.get("/api/render-file")
async def get_render_file(path: str):
    p = Path(path)
    if not p.exists() or not p.is_file():
        raise HTTPException(404)
    # Security: must be under RENDERS_DIR or ASSETS_DIR
    allowed = [RENDERS_DIR, ASSETS_DIR, HOME / "K-Creative-Cloud"]
    if not any(str(p).startswith(str(a)) for a in allowed):
        raise HTTPException(403)
    return FileResponse(str(p))


# ── Screenshot API ────────────────────────────────────────────
@app.get("/api/screenshot")
async def take_screenshot(window: Optional[str] = None):
    """Take a screenshot. Returns base64 PNG."""
    tmp = "/tmp/k-creative-screenshot.png"
    try:
        if window:
            # Try to screenshot specific window by title
            result = subprocess.run(
                ["import", "-window", window, tmp],
                capture_output=True, timeout=5
            )
        else:
            # Full screenshot
            result = subprocess.run(
                ["import", "-window", "root", tmp],
                capture_output=True, timeout=5
            )
        if result.returncode == 0 and os.path.exists(tmp):
            async with aiofiles.open(tmp, "rb") as f:
                data = await f.read()
            return JSONResponse({"ok": True, "data": base64.b64encode(data).decode()})
    except Exception as e:
        pass
    # Fallback: try scrot
    try:
        subprocess.run(["scrot", tmp], capture_output=True, timeout=5)
        async with aiofiles.open(tmp, "rb") as f:
            data = await f.read()
        return JSONResponse({"ok": True, "data": base64.b64encode(data).decode()})
    except Exception as e:
        return JSONResponse({"ok": False, "error": str(e)})


# ── File Browser API ──────────────────────────────────────────
@app.get("/api/files")
async def list_files(path: str = "/home/raphael/K-Creative-Cloud/designer/assets"):
    base = Path(path)
    if not base.exists():
        return JSONResponse({"files": [], "error": "Path not found"})
    files = []
    for item in sorted(base.iterdir()):
        stat = item.stat()
        files.append({
            "name": item.name,
            "path": str(item),
            "type": "dir" if item.is_dir() else "file",
            "ext": item.suffix.lower(),
            "size": stat.st_size,
            "modified": stat.st_mtime,
        })
    return JSONResponse({"files": files, "cwd": str(base)})


@app.get("/api/file")
async def read_file(path: str):
    p = Path(path)
    if not p.exists() or not p.is_file():
        raise HTTPException(404, "File not found")
    # Security: stay within allowed dirs
    allowed = [HOME, Path("/home/raphael/K-Creative-Cloud")]
    if not any(str(p).startswith(str(a)) for a in allowed):
        raise HTTPException(403, "Access denied")
    # Serve image directly
    if p.suffix.lower() in {".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg"}:
        return FileResponse(str(p))
    # Serve audio
    if p.suffix.lower() in {".wav", ".mp3", ".ogg"}:
        return FileResponse(str(p))
    # Text files
    try:
        async with aiofiles.open(p, "r", encoding="utf-8", errors="replace") as f:
            content = await f.read()
        return JSONResponse({"content": content})
    except Exception as e:
        raise HTTPException(500, str(e))


# ── Projects API ──────────────────────────────────────────────
@app.get("/api/projects")
async def list_projects():
    """List projects = subdirs of designer/assets with metadata."""
    projects = []
    registry_path = Path("/home/raphael/K-Creative-Cloud/designer/registry/asset-registry.md")
    registry = ""
    if registry_path.exists():
        async with aiofiles.open(registry_path, "r") as f:
            registry = await f.read()

    # Scan K-Learning branding
    klearning = Path("/home/raphael/K-Learning/branding")
    if klearning.exists():
        projects.append({
            "id": "k-learning",
            "name": "K-Learning",
            "path": str(klearning),
            "color": "#6C47FF",
            "type": "app"
        })

    # Scan K-Creative assets
    for d in sorted(ASSETS_DIR.iterdir()) if ASSETS_DIR.exists() else []:
        if d.is_dir():
            files = list(d.iterdir())
            projects.append({
                "id": d.name,
                "name": d.name.title(),
                "path": str(d),
                "fileCount": len(files),
                "type": "asset-folder"
            })

    return JSONResponse({"projects": projects, "registry": registry})


# ── Context API ───────────────────────────────────────────────
@app.get("/api/context")
async def get_context(project: str):
    """Load all context files for a project (tokens, brand guide, logo files)."""
    ctx = {"files": [], "tokens": None, "guide": None}

    if project == "k-learning":
        brand_dir = Path("/home/raphael/K-Learning/branding")
        # Tokens
        tokens_path = brand_dir / "tokens.json"
        if tokens_path.exists():
            async with aiofiles.open(tokens_path, "r") as f:
                ctx["tokens"] = json.loads(await f.read())
        # Brand guide
        guide_path = brand_dir / "guidelines/BRAND_GUIDE.md"
        if guide_path.exists():
            async with aiofiles.open(guide_path, "r") as f:
                ctx["guide"] = (await f.read())[:3000]  # first 3000 chars
        # Logo files
        identity_dir = brand_dir / "identity"
        if identity_dir.exists():
            for f in identity_dir.iterdir():
                if f.suffix.lower() in {".svg", ".png", ".ico"}:
                    ctx["files"].append({"name": f.name, "path": str(f)})

    return JSONResponse(ctx)


# ── Terminal WebSocket ─────────────────────────────────────────
@app.websocket("/ws/terminal/{session_id}")
async def terminal_ws(websocket: WebSocket, session_id: str):
    """
    WebSocket PTY — embeds a real terminal session per tool.
    Frontend sends: {"type":"input","data":"..."} or {"type":"resize","cols":80,"rows":24}
    Server sends: {"type":"output","data":"<base64>"} or {"type":"ready"}
    """
    await websocket.accept()

    # Start PTY with bash in the right directory
    tool_dirs = {
        "blender": "/home/raphael/K-Creative-Cloud/Blender",
        "gimp": "/home/raphael/K-Creative-Cloud",
        "inkscape": "/home/raphael/K-Creative-Cloud",
        "lmms": "/home/raphael/K-Creative-Cloud",
        "designer": "/home/raphael/K-Creative-Cloud/designer",
        "global": "/home/raphael/K-Creative-Cloud",
    }
    cwd = tool_dirs.get(session_id, "/home/raphael/K-Creative-Cloud")

    master_fd, slave_fd = pty.openpty()
    proc = subprocess.Popen(
        ["/bin/bash", "--login"],
        stdin=slave_fd, stdout=slave_fd, stderr=slave_fd,
        cwd=cwd,
        env={**os.environ, "TERM": "xterm-256color", "COLUMNS": "120", "LINES": "40"},
        close_fds=True,
    )
    os.close(slave_fd)

    # Set non-blocking
    fl = fcntl.fcntl(master_fd, fcntl.F_GETFL)
    fcntl.fcntl(master_fd, fcntl.F_SETFL, fl | os.O_NONBLOCK)

    await websocket.send_json({"type": "ready", "cwd": cwd})

    async def read_output():
        while True:
            try:
                r, _, _ = select.select([master_fd], [], [], 0.05)
                if r:
                    try:
                        data = os.read(master_fd, 4096)
                        if data:
                            await websocket.send_json({
                                "type": "output",
                                "data": base64.b64encode(data).decode()
                            })
                    except OSError:
                        break
            except Exception:
                break
            await asyncio.sleep(0.02)

    output_task = asyncio.create_task(read_output())

    try:
        while True:
            msg = await websocket.receive_json()
            if msg["type"] == "input":
                os.write(master_fd, base64.b64decode(msg["data"]))
            elif msg["type"] == "resize":
                cols, rows = msg.get("cols", 120), msg.get("rows", 40)
                size = struct.pack("HHHH", rows, cols, 0, 0)
                fcntl.ioctl(master_fd, termios.TIOCSWINSZ, size)
    except (WebSocketDisconnect, Exception):
        pass
    finally:
        output_task.cancel()
        proc.terminate()
        os.close(master_fd)


# ── Project & Workspace API ───────────────────────────────────
WORKSPACE = Path("/home/raphael/K-Creative-Cloud/workspace")
WORKERS   = Path(__file__).parent / "workers"

@app.get("/api/workspace/projects")
async def list_workspace_projects():
    """List all projects in the workspace."""
    projects_dir = WORKSPACE / "projects"
    if not projects_dir.exists():
        return JSONResponse({"projects": []})
    projects = []
    for d in sorted(projects_dir.iterdir()):
        if d.is_dir():
            manifest = d / "project.json"
            if manifest.exists():
                try:
                    data = json.loads(manifest.read_text())
                    projects.append({
                        "id": data.get("id", d.name),
                        "name": data.get("name", d.name),
                        "status": data.get("status", "unknown"),
                        "path": str(d),
                        "chapters": len(data.get("chapters", [])),
                    })
                except Exception:
                    projects.append({"id": d.name, "name": d.name, "path": str(d)})
    return JSONResponse({"projects": projects})


@app.get("/api/workspace/project/{project_id}")
async def get_workspace_project(project_id: str):
    manifest = WORKSPACE / "projects" / project_id / "project.json"
    if not manifest.exists():
        raise HTTPException(404, "Project not found")
    return JSONResponse(json.loads(manifest.read_text()))


@app.post("/api/workspace/exec/chapter")
async def exec_chapter(payload: dict = Body(...)):
    """
    Execute a chapter render using the appropriate worker.
    Body: { "project_id": "k_learning_brand", "chapter_id": "02_icons" }
    """
    project_id = payload.get("project_id", "")
    chapter_id = payload.get("chapter_id", "")

    project_path = WORKSPACE / "projects" / project_id / "project.json"
    if not project_path.exists():
        raise HTTPException(404, "Project not found")

    project = json.loads(project_path.read_text())
    chapter = next((c for c in project.get("chapters", []) if c["id"] == chapter_id), None)
    if not chapter:
        raise HTTPException(404, "Chapter not found")

    tool = chapter.get("tool", "blender")
    output_dir = str(RENDERS_DIR / project_id / chapter_id)
    Path(output_dir).mkdir(parents=True, exist_ok=True)

    job_id = str(uuid.uuid4())[:8]
    jobs[job_id] = {"status": "running", "log": "", "project": project_id, "chapter": chapter_id, "output": output_dir}

    if "blender" in tool:
        worker_script = (WORKERS / "render_3d.py").read_text()
        cmd = ["blender", "-b", "-P", "/dev/stdin"]
        env = {**os.environ, "DISPLAY": ":99",
               "K_PROJECT": str(project_path),
               "K_OUTPUT": output_dir,
               "K_CHAPTER": chapter_id}
    else:
        return JSONResponse({"job_id": job_id, "status": "unsupported", "tool": tool})

    async def run():
        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT,
                env=env,
            )
            script_bytes = (WORKERS / "render_3d.py").read_bytes()
            stdout, _ = await asyncio.wait_for(proc.communicate(input=script_bytes), timeout=180)
            jobs[job_id].update({"status": "done", "log": stdout.decode(errors="replace"), "returncode": proc.returncode})
        except asyncio.TimeoutError:
            jobs[job_id].update({"status": "timeout", "log": "Timeout after 180s"})
        except Exception as e:
            jobs[job_id].update({"status": "error", "log": str(e)})

    asyncio.create_task(run())
    return JSONResponse({"job_id": job_id, "status": "queued", "output": output_dir})


@app.post("/api/workspace/exec/audio")
async def exec_audio(payload: dict = Body(...)):
    """
    Run audio worker.
    Body: { "cmd": "sound_logo|tts|normalize", "text": "...", "output": "..." }
    """
    cmd_type = payload.get("cmd", "sound_logo")
    output = payload.get("output", str(RENDERS_DIR / "audio" / f"{cmd_type}.wav"))
    Path(output).parent.mkdir(parents=True, exist_ok=True)

    job_id = str(uuid.uuid4())[:8]
    jobs[job_id] = {"status": "running", "log": "", "output": output}

    worker = str(WORKERS / "generate_audio.py")
    args = [sys.executable, worker, cmd_type, "--output", output]

    if cmd_type == "tts":
        args += ["--text", payload.get("text", "K-Learning")]
    elif cmd_type == "normalize":
        args += ["--input", payload.get("input", "")]
    elif cmd_type == "mix":
        args += ["--stems"] + payload.get("stems", [])

    async def run():
        try:
            proc = await asyncio.create_subprocess_exec(
                *args, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.STDOUT)
            stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=60)
            jobs[job_id].update({"status": "done", "log": stdout.decode(errors="replace"), "returncode": proc.returncode})
        except Exception as e:
            jobs[job_id].update({"status": "error", "log": str(e)})

    asyncio.create_task(run())
    return JSONResponse({"job_id": job_id, "status": "queued", "output": output})


# ── Delivery Pipeline API ─────────────────────────────────────
@app.post("/api/deliver")
async def deliver_asset(payload: dict = Body(...)):
    """
    Run tri-tier delivery pipeline on an asset.
    Body: { "input": "<path>", "type": "video|image|audio|vector",
            "output_dir": "<optional>", "project_id": "", "chapter_id": "" }
    Returns: { "job_id": "...", "status": "queued" }
    """
    input_path = payload.get("input", "")
    if not input_path or not Path(input_path).exists():
        raise HTTPException(400, "input file not found")

    asset_type = payload.get("type", "image")
    project_id = payload.get("project_id", "")
    chapter_id = payload.get("chapter_id", "")
    output_dir  = payload.get("output_dir", str(RENDERS_DIR / "delivery" / (project_id or "default")))

    job_id = str(uuid.uuid4())[:8]
    jobs[job_id] = {"status": "running", "log": "", "output": output_dir, "type": "delivery"}

    async def run():
        try:
            proc = await asyncio.create_subprocess_exec(
                sys.executable,
                str(WORKERS / "export_pipeline.py"), "deliver",
                "--input", input_path,
                "--output-dir", output_dir,
                "--type", asset_type,
                "--project-id", project_id,
                "--chapter-id", chapter_id,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT,
            )
            stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=3600)
            log = stdout.decode(errors="replace")
            jobs[job_id].update({"status": "done", "log": log, "returncode": proc.returncode})
            # Parse result JSON from stdout
            try:
                last_json = log[log.rfind('{'):log.rfind('}')+1]
                result = json.loads(last_json)
                jobs[job_id]["delivery_result"] = result
            except Exception:
                pass
        except asyncio.TimeoutError:
            jobs[job_id].update({"status": "timeout", "log": "Timeout after 3600s"})
        except Exception as e:
            jobs[job_id].update({"status": "error", "log": str(e)})

    asyncio.create_task(run())
    return JSONResponse({"job_id": job_id, "status": "queued", "output": output_dir})


@app.get("/api/deliver/report")
async def get_delivery_report(dir: str):
    """Get delivery_report.json for a delivery directory."""
    report_path = Path(dir) / "delivery_report.json"
    if not report_path.exists():
        raise HTTPException(404, "No delivery report found")
    return JSONResponse(json.loads(report_path.read_text()))


import sys

# ── DJ Engine API ─────────────────────────────────────────────────────────────

@app.post("/api/dj/auth")
async def dj_auth(payload: dict = Body(...)):
    """Generate or validate a DJ API key for remote/localhost access."""
    action = payload.get("action", "generate")
    if action == "generate":
        name = payload.get("name", "default")
        key = secrets.token_hex(32)
        _api_keys[key] = {"name": name, "created": time.time()}
        _save_api_keys()
        return JSONResponse({"ok": True, "key": key, "name": name})
    if action == "validate":
        key = payload.get("key", "")
        if key in _api_keys:
            return JSONResponse({"ok": True, "info": _api_keys[key]})
        raise HTTPException(401, "Invalid API key")
    raise HTTPException(400, "action must be 'generate' or 'validate'")


@app.get("/api/dj/status")
async def dj_status():
    """DJ engine status: SuperCollider, Mixxx, Numark MIDI, library size."""
    sc_ok = port_open(DJ_SC_HOST, DJ_SC_PORT)
    try:
        r = subprocess.run(["pgrep", "-x", "mixxx"], capture_output=True)
        mixxx_ok = r.returncode == 0
    except Exception:
        mixxx_ok = False
    try:
        r = subprocess.run(["aconnect", "-i"], capture_output=True, text=True, timeout=2)
        numark_ok = "numark" in r.stdout.lower() or "mixtrack" in r.stdout.lower()
    except Exception:
        numark_ok = False
    try:
        con = sqlite3.connect(DJ_DB)
        track_count = con.execute("SELECT COUNT(*) FROM tracks").fetchone()[0]
        con.close()
    except Exception:
        track_count = 0
    return JSONResponse({
        "sc":      sc_ok,
        "mixxx":   mixxx_ok,
        "numark":  numark_ok,
        "library": track_count,
        "sc_addr": f"{DJ_SC_HOST}:{DJ_SC_PORT}",
    })


@app.get("/api/dj/library")
async def dj_library(search: Optional[str] = None, sort: str = "title",
                      limit: int = 100, offset: int = 0):
    """Query the DJ track library. Supports full-text search and sort."""
    con = sqlite3.connect(DJ_DB)
    con.row_factory = sqlite3.Row
    where, params = "", []
    if search:
        where = " WHERE title LIKE ? OR artist LIKE ? OR path LIKE ?"
        params = [f"%{search}%"] * 3
    safe_sort = sort if sort in ("title","artist","bpm","duration","modified") else "title"
    rows = con.execute(
        f"SELECT * FROM tracks{where} ORDER BY {safe_sort} LIMIT ? OFFSET ?",
        params + [limit, offset]
    ).fetchall()
    total = con.execute(f"SELECT COUNT(*) FROM tracks{where}", params).fetchone()[0]
    con.close()
    return JSONResponse({"tracks": [dict(r) for r in rows], "total": total})


@app.post("/api/dj/library/scan")
async def dj_library_scan(payload: dict = Body({})):
    """Async-scan a music directory and update the track database."""
    scan_dir = payload.get("dir", str(DJ_LIBRARY))
    job_id = str(uuid.uuid4())[:8]
    jobs[job_id] = {"status": "running", "log": "", "type": "dj_scan"}

    async def run():
        try:
            proc = await asyncio.create_subprocess_exec(
                sys.executable, str(WORKERS / "dj_engine.py"), "scan",
                "--dir", scan_dir, "--db", str(DJ_DB),
                stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.STDOUT,
            )
            stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=600)
            jobs[job_id].update({"status": "done", "log": stdout.decode(errors="replace"),
                                   "returncode": proc.returncode})
        except Exception as e:
            jobs[job_id].update({"status": "error", "log": str(e)})

    asyncio.create_task(run())
    return JSONResponse({"job_id": job_id, "status": "queued", "dir": scan_dir})


@app.post("/api/dj/sc/pattern")
async def sc_pattern_swap(payload: dict = Body(...)):
    """
    Hot-swap the rhythm pattern in a slot without touching the sound layer.
    Body: { "slot": 0, "code": "four_to_floor", "bpm": 128.0 }
    """
    code = payload.get("code", "")
    slot = int(payload.get("slot", 0))
    bpm  = float(payload.get("bpm", 120.0))
    if not code:
        raise HTTPException(400, "code required")

    job_id = str(uuid.uuid4())[:8]
    jobs[job_id] = {"status": "running", "log": "", "type": "sc_pattern"}

    async def run():
        try:
            proc = await asyncio.create_subprocess_exec(
                sys.executable, str(WORKERS / "sc_bridge.py"), "pattern",
                "--code", code, "--slot", str(slot), "--bpm", str(bpm),
                stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.STDOUT,
            )
            stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=15)
            jobs[job_id].update({"status": "done", "log": stdout.decode(errors="replace"),
                                   "returncode": proc.returncode})
        except Exception as e:
            jobs[job_id].update({"status": "error", "log": str(e)})

    asyncio.create_task(run())
    return JSONResponse({"job_id": job_id, "status": "queued"})


@app.post("/api/dj/sc/sound")
async def sc_sound_swap(payload: dict = Body(...)):
    """
    Hot-swap the sound layer in a slot (keep rhythm, change synth/sample).
    Body: { "slot": 0, "synthdef": "bass", "sample": "/path/to/kick.wav", "params": {} }
    """
    slot     = int(payload.get("slot", 0))
    synthdef = payload.get("synthdef", "")
    sample   = payload.get("sample", "")
    params   = payload.get("params", {})

    if not synthdef and not sample:
        raise HTTPException(400, "synthdef or sample required")

    job_id = str(uuid.uuid4())[:8]
    jobs[job_id] = {"status": "running", "log": "", "type": "sc_sound"}
    cmd_args = [
        sys.executable, str(WORKERS / "sc_bridge.py"), "sound",
        "--slot", str(slot),
    ]
    if synthdef: cmd_args += ["--synthdef", synthdef]
    if sample:   cmd_args += ["--sample", sample]
    if params:   cmd_args += ["--params", json.dumps(params)]

    async def run():
        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd_args,
                stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.STDOUT,
            )
            stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=15)
            jobs[job_id].update({"status": "done", "log": stdout.decode(errors="replace"),
                                   "returncode": proc.returncode})
        except Exception as e:
            jobs[job_id].update({"status": "error", "log": str(e)})

    asyncio.create_task(run())
    return JSONResponse({"job_id": job_id, "status": "queued"})


@app.post("/api/dj/sc/fx")
async def sc_fx_set(payload: dict = Body(...)):
    """
    Mirror a physical knob value to a SuperCollider FX parameter.
    Body: { "slot": 0, "param": "filter", "value": 0.7 }
    """
    slot  = int(payload.get("slot", 0))
    param = payload.get("param", "filter")
    value = float(payload.get("value", 0.5))

    async def run():
        await asyncio.create_subprocess_exec(
            sys.executable, str(WORKERS / "sc_bridge.py"), "fx",
            "--slot", str(slot), "--param", param, "--value", str(value),
        )

    asyncio.create_task(run())
    return JSONResponse({"ok": True})


@app.post("/api/sync/pipeline")
async def sync_pipeline(payload: dict = Body({})):
    """
    Hot-reload DJ components without restarting scsynth:
      target: "mappings" | "sc_loops" | "dsp" | "all"
    """
    target     = payload.get("target", "all")
    source_dir = payload.get("source_dir", str(ROOT))

    job_id = str(uuid.uuid4())[:8]
    jobs[job_id] = {"status": "running", "log": "", "type": "hot_reload", "target": target}

    async def run():
        lines = []
        try:
            if target in ("mappings", "all"):
                src = Path(source_dir) / "midi_mappings"
                dst = Path.home() / ".mixxx" / "midi"
                if src.exists():
                    dst.mkdir(parents=True, exist_ok=True)
                    proc = await asyncio.create_subprocess_exec(
                        "rsync", "-av", "--delete", str(src) + "/", str(dst) + "/",
                        stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.STDOUT,
                    )
                    out, _ = await proc.communicate()
                    lines.append(f"[mappings] {out.decode(errors='replace').strip()}")
                else:
                    lines.append(f"[mappings] skipped (no {src})")

            if target in ("sc_loops", "all"):
                proc = await asyncio.create_subprocess_exec(
                    sys.executable, str(WORKERS / "sc_bridge.py"), "reload",
                    stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.STDOUT,
                )
                out, _ = await asyncio.wait_for(proc.communicate(), timeout=15)
                lines.append(f"[sc_loops] {out.decode(errors='replace').strip()}")

            jobs[job_id].update({"status": "done", "log": "\n".join(lines), "returncode": 0})
        except Exception as e:
            jobs[job_id].update({"status": "error", "log": str(e)})

    asyncio.create_task(run())
    return JSONResponse({"job_id": job_id, "status": "queued", "target": target})


# MIDI WebSocket — streams Numark events to the browser and forwards SC commands back
@app.websocket("/ws/midi")
async def midi_ws(websocket: WebSocket):
    """
    Bidirectional MIDI bridge:
      browser ← JSON MIDI events from Numark Mixtrack Quad
      browser → { type:"sc_cmd", data:{code:"..."} } → SuperCollider OSC
    """
    await websocket.accept()
    stop = asyncio.Event()
    midi_proc = None

    try:
        midi_proc = await asyncio.create_subprocess_exec(
            sys.executable, str(WORKERS / "dj_engine.py"), "midi-monitor",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
        )

        async def forward_midi():
            while not stop.is_set():
                try:
                    line = await asyncio.wait_for(midi_proc.stdout.readline(), timeout=0.5)
                    if line:
                        await websocket.send_text(line.decode(errors="replace").strip())
                except asyncio.TimeoutError:
                    continue
                except Exception:
                    break

        asyncio.create_task(forward_midi())

        while True:
            try:
                raw = await asyncio.wait_for(websocket.receive_text(), timeout=1.0)
                msg = json.loads(raw)
                if msg.get("type") == "sc_cmd":
                    data = msg.get("data", {})
                    asyncio.create_task(asyncio.create_subprocess_exec(
                        sys.executable, str(WORKERS / "sc_bridge.py"), "cmd",
                        "--msg", json.dumps(data),
                    ))
                elif msg.get("type") == "fx":
                    asyncio.create_task(asyncio.create_subprocess_exec(
                        sys.executable, str(WORKERS / "sc_bridge.py"), "fx",
                        "--slot", str(msg.get("slot", 0)),
                        "--param", msg.get("param", "filter"),
                        "--value", str(msg.get("value", 0.5)),
                    ))
            except asyncio.TimeoutError:
                continue
            except (WebSocketDisconnect, Exception):
                break
    finally:
        stop.set()
        if midi_proc:
            midi_proc.terminate()


if __name__ == "__main__":
    print("K-Creative Studio → http://localhost:7000")
    uvicorn.run(app, host="0.0.0.0", port=7000, log_level="warning")
