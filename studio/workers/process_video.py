#!/usr/bin/env python3
"""
K-Creative process_video.py — Headless FFmpeg Video Worker

Provides compositing, trimming, color-grading, and subtitle-burn operations
via FFmpeg. All ops are headless — no GUI required.

Usage:
  python3 process_video.py trim --input video.mp4 --start 10 --end 30 --output out.mp4
  python3 process_video.py grade --input video.mp4 --lut lut.cube --output out.mp4
  python3 process_video.py composite --bg bg.mp4 --fg overlay.png --output out.mp4
  python3 process_video.py to_webm --input video.mp4 --output out.webm
"""
import subprocess
import sys
import json
import os
from pathlib import Path

OUTPUT_DIR = os.environ.get("K_OUTPUT", "/home/raphael/K-Creative-Cloud/renders/video")


def run_ffmpeg(args: list[str], dry_run=False) -> dict:
    cmd = ["ffmpeg", "-y"] + args
    print(f"[process_video] {' '.join(cmd)}")
    if dry_run:
        return {"ok": True, "cmd": " ".join(cmd)}
    result = subprocess.run(cmd, capture_output=True, text=True)
    return {
        "ok": result.returncode == 0,
        "returncode": result.returncode,
        "stdout": result.stdout,
        "stderr": result.stderr[-2000:],  # last 2k chars
    }


def trim(input: str, output: str, start: float = 0, end: float = None, duration: float = None) -> dict:
    """Cut a segment from a video."""
    Path(output).parent.mkdir(parents=True, exist_ok=True)
    args = ["-i", input, "-ss", str(start)]
    if end:
        args += ["-to", str(end)]
    elif duration:
        args += ["-t", str(duration)]
    args += ["-c", "copy", output]
    return run_ffmpeg(args)


def color_grade(input: str, output: str,
                brightness: float = 0.0, contrast: float = 1.0,
                saturation: float = 1.0, gamma: float = 1.0,
                lut_path: str = None) -> dict:
    """Apply color grading via ffmpeg eq filter or LUT."""
    Path(output).parent.mkdir(parents=True, exist_ok=True)
    if lut_path and Path(lut_path).exists():
        vf = f"lut3d='{lut_path}'"
    else:
        vf = f"eq=brightness={brightness}:contrast={contrast}:saturation={saturation}:gamma={gamma}"
    return run_ffmpeg(["-i", input, "-vf", vf, "-c:a", "copy", output])


def composite_overlay(bg: str, fg: str, output: str,
                       x: str = "(W-w)/2", y: str = "(H-h)/2",
                       scale: float = 1.0) -> dict:
    """Overlay fg image/video onto bg video."""
    Path(output).parent.mkdir(parents=True, exist_ok=True)
    fg_filter = f"[1:v]scale=iw*{scale}:ih*{scale}[fg]"
    overlay_filter = f"[0:v][fg]overlay={x}:{y}"
    return run_ffmpeg([
        "-i", bg, "-i", fg,
        "-filter_complex", f"{fg_filter};{overlay_filter}",
        "-c:a", "copy", output
    ])


def to_webm(input: str, output: str, quality: int = 30, crf: int = 33) -> dict:
    """Convert to WebM (VP9) for web."""
    Path(output).parent.mkdir(parents=True, exist_ok=True)
    return run_ffmpeg([
        "-i", input,
        "-c:v", "libvpx-vp9", "-b:v", "0", "-crf", str(crf),
        "-c:a", "libopus", "-b:a", "128k",
        output
    ])


def extract_frames(input: str, output_pattern: str, fps: float = 1.0) -> dict:
    """Extract frames at given FPS for thumbnail generation."""
    Path(output_pattern).parent.mkdir(parents=True, exist_ok=True)
    return run_ffmpeg(["-i", input, "-vf", f"fps={fps}", output_pattern])


def add_audio(video: str, audio: str, output: str,
              video_volume: float = 1.0, audio_volume: float = 0.8) -> dict:
    """Mix audio track under video."""
    Path(output).parent.mkdir(parents=True, exist_ok=True)
    return run_ffmpeg([
        "-i", video, "-i", audio,
        "-filter_complex",
        f"[0:a]volume={video_volume}[va];[1:a]volume={audio_volume}[aa];[va][aa]amerge=inputs=2[a]",
        "-map", "0:v", "-map", "[a]", "-c:v", "copy", "-ac", "2",
        output
    ])


def burn_subtitles(input: str, srt: str, output: str,
                   font: str = "Nunito", font_size: int = 28,
                   color: str = "&HFFFFFF&", outline_color: str = "&H6C47FF&") -> dict:
    """Burn SRT subtitles into video."""
    Path(output).parent.mkdir(parents=True, exist_ok=True)
    style = f"FontName={font},FontSize={font_size},PrimaryColour={color},OutlineColour={outline_color}"
    return run_ffmpeg([
        "-i", input,
        "-vf", f"subtitles={srt}:force_style='{style}'",
        "-c:a", "copy", output
    ])


# ── CLI interface ──────────────────────────────────────────────
def main():
    import argparse
    parser = argparse.ArgumentParser(description="K-Creative Video Worker")
    sub = parser.add_subparsers(dest="cmd")

    t = sub.add_parser("trim")
    t.add_argument("--input"); t.add_argument("--output"); t.add_argument("--start", type=float, default=0)
    t.add_argument("--end", type=float); t.add_argument("--duration", type=float)

    g = sub.add_parser("grade")
    g.add_argument("--input"); g.add_argument("--output")
    g.add_argument("--brightness", type=float, default=0); g.add_argument("--contrast", type=float, default=1)
    g.add_argument("--saturation", type=float, default=1); g.add_argument("--lut")

    c = sub.add_parser("composite")
    c.add_argument("--bg"); c.add_argument("--fg"); c.add_argument("--output")
    c.add_argument("--scale", type=float, default=1.0)

    w = sub.add_parser("to_webm")
    w.add_argument("--input"); w.add_argument("--output"); w.add_argument("--crf", type=int, default=33)

    e = sub.add_parser("extract_frames")
    e.add_argument("--input"); e.add_argument("--output"); e.add_argument("--fps", type=float, default=1.0)

    args = parser.parse_args()

    if args.cmd == "trim":
        result = trim(args.input, args.output, args.start, args.end, args.duration)
    elif args.cmd == "grade":
        result = color_grade(args.input, args.output, lut_path=args.lut)
    elif args.cmd == "composite":
        result = composite_overlay(args.bg, args.fg, args.output, scale=args.scale)
    elif args.cmd == "to_webm":
        result = to_webm(args.input, args.output, crf=args.crf)
    elif args.cmd == "extract_frames":
        result = extract_frames(args.input, args.output, args.fps)
    else:
        parser.print_help(); return

    print(json.dumps(result, indent=2))
    sys.exit(0 if result.get("ok") else 1)


if __name__ == "__main__":
    main()
