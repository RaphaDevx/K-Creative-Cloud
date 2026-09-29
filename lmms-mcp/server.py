"""
LMMS MCP Server — CLI-based, controls LMMS via command line.
Renders .mmp projects, lists presets, launches LMMS GUI.
"""
import json
import os
import subprocess
from pathlib import Path

from mcp.server.fastmcp import FastMCP

mcp = FastMCP("lmms-mcp")

PROJECTS_DIR = Path.home() / "Music" / "lmms" / "projects"
RENDERS_DIR = Path.home() / "renders"
LMMS_DATA_DIR = Path("/usr/share/lmms")


def _lmms_bin() -> str:
    result = subprocess.run(["which", "lmms"], capture_output=True, text=True)
    return result.stdout.strip() or "lmms"


@mcp.tool()
def list_projects() -> str:
    """List LMMS projects (.mmp files) in the default projects directory.

    Returns: JSON list of projects
    """
    search_dirs = [
        PROJECTS_DIR,
        Path.home() / "lmms" / "projects",
        Path.home() / "Documents" / "lmms" / "projects",
    ]
    projects = []
    for d in search_dirs:
        if d.exists():
            for f in sorted(d.glob("**/*.mmp")):
                projects.append({"name": f.stem, "file": str(f), "size_bytes": f.stat().st_size})
    return json.dumps({"projects": projects, "count": len(projects)})


@mcp.tool()
def list_presets(instrument: str = "") -> str:
    """List available LMMS instrument presets.

    Args:
        instrument: Filter by instrument name (e.g. 'TripleOscillator', 'ZynAddSubFX')

    Returns: JSON list of preset files
    """
    preset_dirs = [
        LMMS_DATA_DIR / "presets",
        Path.home() / "lmms" / "presets",
    ]
    presets = []
    for d in preset_dirs:
        if d.exists():
            pattern = f"**/*{instrument}*" if instrument else "**/*.xpf"
            for f in sorted(d.glob(pattern)):
                if f.suffix in {".xpf", ".xiz"}:
                    presets.append({"name": f.stem, "instrument": f.parent.name, "file": str(f)})
    return json.dumps({"presets": presets[:100], "count": len(presets)})


@mcp.tool()
def render_project(project_file: str, output_filename: str = "", format: str = "wav") -> str:
    """Render an LMMS project to audio.

    Args:
        project_file: Path to .mmp project file
        output_filename: Output filename (default: project name + format)
        format: Output format — 'wav' or 'ogg' (default: wav)

    Returns: JSON with render result and output path
    """
    RENDERS_DIR.mkdir(parents=True, exist_ok=True)
    project_path = Path(project_file)
    if not project_path.exists():
        return json.dumps({"error": f"Project not found: {project_file}"})
    if not output_filename:
        output_filename = f"{project_path.stem}.{format}"
    output_path = RENDERS_DIR / output_filename

    lmms = _lmms_bin()
    cmd = [lmms, "-r", str(project_path), "--output", str(output_path)]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        return json.dumps({
            "success": result.returncode == 0,
            "output_file": str(output_path),
            "stdout": result.stdout[-300:],
            "stderr": result.stderr[-300:],
        })
    except subprocess.TimeoutExpired:
        return json.dumps({"error": "Render timed out after 120 seconds"})
    except FileNotFoundError:
        return json.dumps({"error": "lmms binary not found"})


@mcp.tool()
def get_lmms_info() -> str:
    """Get LMMS version and available features.

    Returns: JSON with version info and paths
    """
    lmms = _lmms_bin()
    version_result = subprocess.run([lmms, "--version"], capture_output=True, text=True)
    return json.dumps({
        "binary": lmms,
        "version": version_result.stdout.strip() or version_result.stderr.strip(),
        "data_dir": str(LMMS_DATA_DIR),
        "presets_exist": (LMMS_DATA_DIR / "presets").exists(),
        "samples_exist": (LMMS_DATA_DIR / "samples").exists(),
        "default_projects_dir": str(PROJECTS_DIR),
        "renders_dir": str(RENDERS_DIR),
    })


@mcp.tool()
def launch_lmms(project_file: str = "") -> str:
    """Open LMMS GUI, optionally with a specific project.

    Args:
        project_file: Path to .mmp file (optional)

    Returns: Status message
    """
    lmms = _lmms_bin()
    cmd = [lmms]
    if project_file:
        cmd.append(project_file)
    subprocess.Popen(cmd, start_new_session=True)
    return json.dumps({"launched": True, "command": " ".join(cmd)})


@mcp.tool()
def list_samples(category: str = "") -> str:
    """List available LMMS audio samples.

    Args:
        category: Filter by category folder (e.g. 'drums', 'bass', 'misc')

    Returns: JSON list of sample files
    """
    samples_dir = LMMS_DATA_DIR / "samples"
    if not samples_dir.exists():
        return json.dumps({"error": "LMMS samples directory not found", "tried": str(samples_dir)})
    pattern = f"**/{category}*/**/*" if category else "**/*"
    extensions = {".wav", ".ogg", ".flac", ".mp3"}
    samples = []
    for f in sorted(samples_dir.glob("**/*")):
        if f.suffix.lower() in extensions:
            samples.append({
                "name": f.name,
                "category": f.parent.name,
                "file": str(f),
            })
    return json.dumps({"samples": samples[:100], "count": len(samples)})


def main():
    mcp.run()


if __name__ == "__main__":
    main()
