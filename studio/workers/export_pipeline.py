#!/usr/bin/env python3
"""
K-Creative export_pipeline.py — Tri-Tier Delivery Engine

Implements the Dual-Delivery + Multi-Platform standard:
  01_CLIENT_PREVIEW   → iPhone/Mac/Windows native compatible
  02_PRO_MASTER       → Lossless archival for print/post/agencies
  03_PLATFORM_PUBLISH → Optimized for web/social/streaming

Usage:
  python3 export_pipeline.py deliver --input master.mov --output-dir ./delivery --type video
  python3 export_pipeline.py deliver --input photo.exr --output-dir ./delivery --type image
  python3 export_pipeline.py deliver --input model.blend --output-dir ./delivery --type 3d
  python3 export_pipeline.py deliver --input audio.wav --output-dir ./delivery --type audio
  python3 export_pipeline.py validate --delivery-dir ./delivery
"""
import subprocess
import sys
import os
import json
import shutil
import argparse
from pathlib import Path
from datetime import datetime, timezone
from typing import Optional

# ── Config ──────────────────────────────────────────────────────
DEFAULT_OUTPUT = Path("/home/raphael/K-Creative-Cloud/renders/delivery")
FORMATS_SPEC = Path(__file__).parent / "delivery_formats.json"
ICC_DIR = Path("/usr/share/color/icc")


def run(cmd: list, timeout: int = 300) -> dict:
    cmd_str = " ".join(str(c) for c in cmd)
    print(f"[export] {cmd_str}")
    try:
        result = subprocess.run(
            [str(c) for c in cmd],
            capture_output=True, text=True, timeout=timeout
        )
        return {
            "ok": result.returncode == 0,
            "returncode": result.returncode,
            "stderr": result.stderr[-2000:],
            "stdout": result.stdout[-500:],
            "cmd": cmd_str,
        }
    except subprocess.TimeoutExpired:
        return {"ok": False, "error": f"Timeout after {timeout}s", "cmd": cmd_str}
    except FileNotFoundError as e:
        return {"ok": False, "error": f"Command not found: {e}", "cmd": cmd_str}


def magick(args: list) -> dict:
    return run(["magick"] + args)


def ffmpeg(args: list, timeout: int = 600) -> dict:
    return run(["ffmpeg", "-y"] + args, timeout=timeout)


# ── Video exports ────────────────────────────────────────────────

def video_client_preview(input: str, out: Path) -> dict:
    out.mkdir(parents=True, exist_ok=True)
    output = out / "preview.mp4"
    return ffmpeg([
        "-i", input,
        "-c:v", "libx264", "-pix_fmt", "yuv420p",
        "-profile:v", "high", "-level", "4.2",
        "-crf", "23", "-preset", "fast",
        "-movflags", "+faststart",
        "-c:a", "aac", "-b:a", "192k", "-ar", "48000",
        "-vf", "scale=trunc(iw/2)*2:trunc(ih/2)*2",  # ensure even dims
        str(output)
    ])


def video_pro_master(input: str, out: Path) -> dict:
    out.mkdir(parents=True, exist_ok=True)
    output = out / "master.mov"
    return ffmpeg([
        "-i", input,
        "-c:v", "prores_ks", "-profile:v", "3",  # ProRes 422 HQ
        "-vendor", "apl0", "-bits_per_mb", "8000",
        "-c:a", "pcm_s24le", "-ar", "48000",
        str(output)
    ], timeout=900)


def video_instagram(input: str, out: Path) -> dict:
    out.mkdir(parents=True, exist_ok=True)
    output = out / "instagram_reel.mp4"
    return ffmpeg([
        "-i", input,
        "-vf", "scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,fps=30",
        "-c:v", "libx264", "-crf", "20", "-preset", "slow",
        "-movflags", "+faststart",
        "-c:a", "aac", "-b:a", "192k", "-ar", "48000",
        "-af", "loudnorm=I=-14:TP=-1:LRA=11",
        str(output)
    ])


def video_youtube_4k(input: str, out: Path) -> dict:
    out.mkdir(parents=True, exist_ok=True)
    output = out / "youtube_4k.mp4"
    return ffmpeg([
        "-i", input,
        "-vf", "scale=3840:2160:force_original_aspect_ratio=decrease",
        "-c:v", "libx265", "-crf", "18", "-preset", "slow",
        "-c:a", "aac", "-b:a", "384k", "-ar", "48000",
        str(output)
    ], timeout=3600)


def video_webm(input: str, out: Path) -> dict:
    out.mkdir(parents=True, exist_ok=True)
    output = out / "web.webm"
    return ffmpeg([
        "-i", input,
        "-c:v", "libvpx-vp9", "-b:v", "0", "-crf", "33",
        "-c:a", "libopus", "-b:a", "128k",
        str(output)
    ], timeout=900)


# ── Image exports ────────────────────────────────────────────────

def image_client_preview(input: str, out: Path) -> dict:
    out.mkdir(parents=True, exist_ok=True)
    output = out / (Path(input).stem + "_preview.jpg")
    return magick([input, "-colorspace", "sRGB", "-strip", "-quality", "95", str(output)])


def image_pro_master_tiff(input: str, out: Path) -> dict:
    out.mkdir(parents=True, exist_ok=True)
    output = out / (Path(input).stem + "_master.tiff")
    return magick([input, "-colorspace", "AdobeRGB", "-depth", "16",
                   "-compress", "LZW", str(output)])


def image_print_cmyk(input: str, out: Path, dpi: int = 300) -> dict:
    out.mkdir(parents=True, exist_ok=True)
    output = out / (Path(input).stem + "_print_cmyk.tiff")
    args = [input, "-colorspace", "CMYK", "-density", str(dpi),
            "-depth", "16", "-compress", "LZW"]
    # Try to embed ICC profile if available
    icc = ICC_DIR / "ISOcoated_v2_300_eci.icc"
    if icc.exists():
        args += ["-profile", str(icc)]
    args.append(str(output))
    return magick(args)


def image_webp(input: str, out: Path, quality: int = 90) -> dict:
    out.mkdir(parents=True, exist_ok=True)
    output = out / (Path(input).stem + ".webp")
    return magick([input, "-colorspace", "sRGB", "-quality", str(quality), str(output)])


def image_avif(input: str, out: Path, quality: int = 85) -> dict:
    out.mkdir(parents=True, exist_ok=True)
    output = out / (Path(input).stem + ".avif")
    # magick >= 7.1 supports AVIF; fallback to webp if not
    result = magick([input, "-colorspace", "sRGB", "-quality", str(quality), str(output)])
    if not result["ok"]:
        print("[export] AVIF not supported, falling back to WebP")
        return image_webp(input, out, quality)
    return result


# ── Audio exports ────────────────────────────────────────────────

def audio_client_preview(input: str, out: Path) -> dict:
    out.mkdir(parents=True, exist_ok=True)
    output = out / (Path(input).stem + "_preview.mp3")
    return ffmpeg(["-i", input, "-c:a", "libmp3lame", "-b:a", "320k", "-cbr", "1", str(output)])


def audio_pro_master(input: str, out: Path) -> dict:
    out.mkdir(parents=True, exist_ok=True)
    output = out / (Path(input).stem + "_master.wav")
    return ffmpeg(["-i", input, "-c:a", "pcm_s24le", "-ar", "48000", str(output)])


def audio_streaming(input: str, out: Path, lufs: float = -14.0) -> dict:
    out.mkdir(parents=True, exist_ok=True)
    output = out / (Path(input).stem + "_streaming.m4a")
    return ffmpeg([
        "-i", input,
        "-c:a", "aac", "-b:a", "192k", "-ar", "48000",
        "-af", f"loudnorm=I={lufs}:TP=-1.0:LRA=11",
        str(output)
    ])


# ── Vector exports ───────────────────────────────────────────────

def svg_optimize(input: str, out: Path) -> dict:
    out.mkdir(parents=True, exist_ok=True)
    output = out / (Path(input).stem + "_opt.svg")
    # Try svgo first, fallback to inkscape
    result = run(["svgo", input, "-o", str(output)])
    if not result["ok"]:
        result = run(["inkscape", input, "--export-plain-svg", "--export-filename", str(output)])
    return result


# ── Delivery Report (QA) ─────────────────────────────────────────

def probe_file(path: str) -> dict:
    """Use ffprobe to extract metadata."""
    r = subprocess.run(
        ["ffprobe", "-v", "quiet", "-print_format", "json",
         "-show_streams", "-show_format", path],
        capture_output=True, text=True
    )
    try:
        return json.loads(r.stdout)
    except Exception:
        return {}


def get_image_info(path: str) -> dict:
    r = subprocess.run(
        ["magick", "identify", "-verbose", path],
        capture_output=True, text=True
    )
    info = {}
    for line in r.stdout.split("\n"):
        if "Geometry:" in line:
            info["geometry"] = line.split(":")[-1].strip()
        if "Colorspace:" in line:
            info["colorspace"] = line.split(":")[-1].strip()
        if "Depth:" in line:
            info["depth"] = line.split(":")[-1].strip()
    return info


def generate_delivery_report(delivery_dir: str, project_id: str = "", chapter_id: str = "") -> dict:
    """Scan a delivery directory and generate a QA manifest."""
    base = Path(delivery_dir)
    report = {
        "$schema": "https://k-creative.local/schemas/delivery-report-v1.json",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "project_id": project_id,
        "chapter_id": chapter_id,
        "delivery_dir": str(base),
        "tiers": {},
        "qa_status": "PASS",
        "issues": [],
    }

    for tier_dir in sorted(base.iterdir()):
        if not tier_dir.is_dir():
            continue
        tier_name = tier_dir.name
        tier_files = []
        for f in sorted(tier_dir.rglob("*")):
            if not f.is_file():
                continue
            ext = f.suffix.lower()
            entry = {
                "file": str(f.relative_to(base)),
                "size_bytes": f.stat().st_size,
                "size_human": f"{f.stat().st_size / 1024 / 1024:.2f} MB",
                "format": ext.lstrip("."),
            }
            # Deep probe for video/audio
            if ext in {".mp4", ".mov", ".webm", ".wav", ".mp3", ".m4a", ".aac"}:
                probe = probe_file(str(f))
                streams = probe.get("streams", [])
                video_streams = [s for s in streams if s.get("codec_type") == "video"]
                audio_streams = [s for s in streams if s.get("codec_type") == "audio"]
                if video_streams:
                    vs = video_streams[0]
                    entry["video"] = {
                        "codec": vs.get("codec_name"),
                        "width": vs.get("width"),
                        "height": vs.get("height"),
                        "fps": vs.get("r_frame_rate"),
                        "bit_rate": vs.get("bit_rate"),
                        "pix_fmt": vs.get("pix_fmt"),
                    }
                if audio_streams:
                    a = audio_streams[0]
                    entry["audio"] = {
                        "codec": a.get("codec_name"),
                        "sample_rate": a.get("sample_rate"),
                        "channels": a.get("channels"),
                    }
                entry["duration_s"] = float(probe.get("format", {}).get("duration", 0))

            elif ext in {".jpg", ".jpeg", ".png", ".tiff", ".webp", ".exr"}:
                entry["image_info"] = get_image_info(str(f))

            tier_files.append(entry)

        report["tiers"][tier_name] = {
            "file_count": len(tier_files),
            "files": tier_files,
        }

    # QA checks
    def check(condition, message):
        if not condition:
            report["issues"].append(message)
            report["qa_status"] = "WARN"

    preview_files = report["tiers"].get("01_CLIENT_PREVIEW", {}).get("files", [])
    master_files = report["tiers"].get("02_PRO_MASTER", {}).get("files", [])

    check(len(preview_files) > 0, "01_CLIENT_PREVIEW is empty")
    check(len(master_files) > 0, "02_PRO_MASTER is empty")

    # Check video codec in preview
    for f in preview_files:
        v = f.get("video", {})
        if v:
            check(v.get("codec") == "h264", f"{f['file']}: expected h264, got {v.get('codec')}")
            check(v.get("pix_fmt") == "yuv420p", f"{f['file']}: expected yuv420p for compatibility")

    return report


# ── Main deliver function ─────────────────────────────────────────

def deliver(input: str, output_dir: str, asset_type: str,
            project_id: str = "", chapter_id: str = "") -> dict:
    """Run all three tiers for an asset."""
    base = Path(output_dir)
    p = Path(input)

    preview = base / "01_CLIENT_PREVIEW"
    master  = base / "02_PRO_MASTER"
    publish = base / "03_PLATFORM_PUBLISH"

    results = {"input": input, "type": asset_type, "outputs": {}, "errors": []}

    if asset_type == "video":
        results["outputs"]["preview_mp4"]    = video_client_preview(input, preview)
        results["outputs"]["master_prores"]  = video_pro_master(input, master)
        results["outputs"]["instagram_reel"] = video_instagram(input, publish)
        results["outputs"]["webm"]           = video_webm(input, publish)

    elif asset_type == "image":
        results["outputs"]["preview_jpg"]  = image_client_preview(input, preview)
        results["outputs"]["master_tiff"]  = image_pro_master_tiff(input, master)
        results["outputs"]["print_cmyk"]   = image_print_cmyk(input, master)
        results["outputs"]["webp"]         = image_webp(input, publish)
        results["outputs"]["avif"]         = image_avif(input, publish)

    elif asset_type == "audio":
        results["outputs"]["preview_mp3"]  = audio_client_preview(input, preview)
        results["outputs"]["master_wav"]   = audio_pro_master(input, master)
        results["outputs"]["streaming"]    = audio_streaming(input, publish)

    elif asset_type == "vector":
        # Copy SVG to all tiers
        for tier in [preview, master, publish]:
            tier.mkdir(parents=True, exist_ok=True)
            shutil.copy2(input, tier / p.name)
            results["outputs"][tier.name] = {"ok": True}
        results["outputs"]["optimized_svg"] = svg_optimize(input, publish)

    else:
        results["errors"].append(f"Unknown asset type: {asset_type}")
        return results

    # Generate QA report
    report = generate_delivery_report(str(base), project_id, chapter_id)
    report_path = base / "delivery_report.json"
    report_path.write_text(json.dumps(report, indent=2, ensure_ascii=False))
    results["delivery_report"] = str(report_path)
    results["qa_status"] = report["qa_status"]
    results["qa_issues"] = report["issues"]

    failed = [k for k, v in results["outputs"].items() if not v.get("ok")]
    results["failed_ops"] = failed
    results["ok"] = len(failed) == 0

    return results


# ── CLI ───────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="K-Creative Tri-Tier Delivery Engine")
    sub = parser.add_subparsers(dest="cmd")

    d = sub.add_parser("deliver", help="Run full delivery pipeline")
    d.add_argument("--input", required=True)
    d.add_argument("--output-dir", default=str(DEFAULT_OUTPUT))
    d.add_argument("--type", required=True, choices=["video", "image", "audio", "vector"])
    d.add_argument("--project-id", default="")
    d.add_argument("--chapter-id", default="")

    v = sub.add_parser("validate", help="Generate delivery report for existing delivery dir")
    v.add_argument("--delivery-dir", required=True)
    v.add_argument("--project-id", default="")

    args = parser.parse_args()

    if args.cmd == "deliver":
        result = deliver(
            args.input, args.output_dir, args.type,
            args.project_id, args.chapter_id
        )
        print(json.dumps(result, indent=2))
        sys.exit(0 if result.get("ok") else 1)

    elif args.cmd == "validate":
        report = generate_delivery_report(args.delivery_dir, args.project_id)
        out_path = Path(args.delivery_dir) / "delivery_report.json"
        out_path.write_text(json.dumps(report, indent=2, ensure_ascii=False))
        print(json.dumps(report, indent=2))
        sys.exit(0 if report["qa_status"] == "PASS" else 1)

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
