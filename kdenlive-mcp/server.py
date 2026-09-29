"""
Kdenlive MCP Server — MLT-XML based, no patched Kdenlive required.
Controls Kdenlive via its native MLT-XML project format + CLI rendering.
"""
import json
import os
import subprocess
import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path

from mcp.server.fastmcp import FastMCP

mcp = FastMCP("kdenlive-mcp")

PROJECTS_DIR = Path.home() / "Videos" / "kdenlive-projects"
RENDERS_DIR = Path.home() / "renders"


def _find_kdenlive_bin() -> str:
    for candidate in ["/usr/bin/kdenlive", "/snap/bin/kdenlive"]:
        if Path(candidate).exists():
            return candidate
    result = subprocess.run(["which", "kdenlive"], capture_output=True, text=True)
    return result.stdout.strip() or "kdenlive"


def _mlt_render(project_file: str, output_file: str, profile: str = "mp4") -> dict:
    """Render a Kdenlive project using melt (MLT framework)."""
    melt = subprocess.run(["which", "melt"], capture_output=True, text=True).stdout.strip()
    if not melt:
        return {"error": "melt not found — install kdenlive for melt CLI"}
    cmd = [melt, project_file, "-consumer", f"avformat:{output_file}", "acodec=aac", "vcodec=libx264"]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
    return {
        "success": result.returncode == 0,
        "output_file": output_file,
        "stderr": result.stderr[-500:] if result.stderr else "",
    }


@mcp.tool()
def create_project(name: str, fps: float = 25.0, width: int = 1920, height: int = 1080) -> str:
    """Create a new empty Kdenlive project (MLT XML).

    Args:
        name: Project name (used as filename)
        fps: Frames per second (default 25)
        width: Video width in pixels
        height: Video height in pixels

    Returns: Path to created .kdenlive project file
    """
    PROJECTS_DIR.mkdir(parents=True, exist_ok=True)
    project_path = PROJECTS_DIR / f"{name}.kdenlive"

    mlt = ET.Element("mlt", {
        "LC_ALL": "en_US.UTF-8",
        "version": "7.0.0",
        "title": name,
        "producer": "main_bin",
    })
    profile = ET.SubElement(mlt, "profile", {
        "description": f"{width}x{height} {fps}fps",
        "width": str(width),
        "height": str(height),
        "frame_rate_num": str(int(fps)),
        "frame_rate_den": "1",
        "colorspace": "709",
        "progressive": "1",
        "sample_aspect_num": "1",
        "sample_aspect_den": "1",
        "display_aspect_num": str(width),
        "display_aspect_den": str(height),
    })
    bin_producer = ET.SubElement(mlt, "producer", {"id": "main_bin"})
    ET.SubElement(bin_producer, "property", {"name": "GETXML"}).text = "1"

    tractor = ET.SubElement(mlt, "tractor", {"id": "maintractor", "global_feed": "1"})
    track = ET.SubElement(tractor, "track", {"producer": "black_track"})

    tree = ET.ElementTree(mlt)
    ET.indent(tree, space="  ")
    tree.write(str(project_path), encoding="unicode", xml_declaration=True)
    return json.dumps({"project_file": str(project_path), "name": name, "fps": fps, "resolution": f"{width}x{height}"})


@mcp.tool()
def get_project_info(project_file: str) -> str:
    """Get information about a Kdenlive project.

    Args:
        project_file: Path to .kdenlive file

    Returns: JSON with project metadata, tracks, and clip count
    """
    path = Path(project_file)
    if not path.exists():
        return json.dumps({"error": f"File not found: {project_file}"})
    try:
        tree = ET.parse(str(path))
        root = tree.getroot()
        profile = root.find("profile")
        info = {
            "file": str(path),
            "size_bytes": path.stat().st_size,
            "title": root.get("title", ""),
        }
        if profile is not None:
            info["width"] = profile.get("width")
            info["height"] = profile.get("height")
            info["fps"] = profile.get("frame_rate_num")
        producers = root.findall(".//producer")
        info["clip_count"] = len([p for p in producers if p.get("id") != "main_bin"])
        tractors = root.findall(".//tractor")
        info["track_count"] = len(tractors)
        return json.dumps(info, indent=2)
    except ET.ParseError as e:
        return json.dumps({"error": f"XML parse error: {e}"})


@mcp.tool()
def list_projects() -> str:
    """List all Kdenlive projects in the default projects directory.

    Returns: JSON list of project files with metadata
    """
    PROJECTS_DIR.mkdir(parents=True, exist_ok=True)
    projects = []
    for f in sorted(PROJECTS_DIR.glob("*.kdenlive")):
        projects.append({
            "name": f.stem,
            "file": str(f),
            "size_bytes": f.stat().st_size,
            "modified": f.stat().st_mtime,
        })
    return json.dumps({"projects_dir": str(PROJECTS_DIR), "projects": projects})


@mcp.tool()
def render_project(project_file: str, output_filename: str = "") -> str:
    """Render a Kdenlive project to MP4 using the MLT framework.

    Args:
        project_file: Path to .kdenlive file
        output_filename: Output filename (default: project name + .mp4)

    Returns: JSON with render result and output path
    """
    RENDERS_DIR.mkdir(parents=True, exist_ok=True)
    project_path = Path(project_file)
    if not project_path.exists():
        return json.dumps({"error": f"Project not found: {project_file}"})
    if not output_filename:
        output_filename = project_path.stem + ".mp4"
    output_path = RENDERS_DIR / output_filename
    result = _mlt_render(str(project_path), str(output_path))
    return json.dumps(result)


@mcp.tool()
def add_clip_to_project(project_file: str, media_file: str, track: int = 0, position: int = 0) -> str:
    """Add a media clip to a Kdenlive project timeline.

    Args:
        project_file: Path to .kdenlive file
        media_file: Path to media file (video, audio, image)
        track: Track index (0 = first video track)
        position: Position in frames

    Returns: JSON confirming the clip was added
    """
    project_path = Path(project_file)
    media_path = Path(media_file)
    if not project_path.exists():
        return json.dumps({"error": f"Project not found: {project_file}"})
    if not media_path.exists():
        return json.dumps({"error": f"Media file not found: {media_file}"})
    try:
        tree = ET.parse(str(project_path))
        root = tree.getroot()
        clip_id = f"clip_{len(root.findall('.//producer'))}"
        producer = ET.Element("producer", {"id": clip_id})
        ET.SubElement(producer, "property", {"name": "resource"}).text = str(media_path)
        ET.SubElement(producer, "property", {"name": "mlt_service"}).text = "avformat"
        root.append(producer)
        tractors = root.findall(".//tractor")
        if tractors:
            tractor = tractors[0]
            entry = ET.SubElement(tractor, "entry", {
                "producer": clip_id,
                "in": "0",
                "out": "99",
            })
        ET.indent(tree, space="  ")
        tree.write(str(project_path), encoding="unicode", xml_declaration=True)
        return json.dumps({"success": True, "clip_id": clip_id, "media": str(media_path)})
    except Exception as e:
        return json.dumps({"error": str(e)})


@mcp.tool()
def launch_kdenlive(project_file: str = "") -> str:
    """Open Kdenlive GUI, optionally with a specific project.

    Args:
        project_file: Path to .kdenlive file (optional)

    Returns: Status message
    """
    bin_path = _find_kdenlive_bin()
    cmd = [bin_path]
    if project_file:
        cmd.append(project_file)
    subprocess.Popen(cmd, start_new_session=True)
    return json.dumps({"launched": True, "command": " ".join(cmd)})


def main():
    mcp.run()


if __name__ == "__main__":
    main()
