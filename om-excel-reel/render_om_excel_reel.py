"""
OM Excel Reel — main orchestrator.
Creates a 1920x1080 landscape tutorial video walking through one exam question step-by-step.

Each "step" = one annotated frame held for the duration of its TTS audio.
Output: ~/Sara_Home/HSG/Bachelor/FS 26/OM/Reels/<output_name>.mp4

Run with: /storage/projekte/ki_pipeline_env_312/bin/python3 render_om_excel_reel.py
"""
from __future__ import annotations
import json, os, shutil, subprocess, sys, tempfile, time
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

# TTS from existing K-Creative-Cloud pipeline
sys.path.insert(0, str(Path(__file__).parent.parent / "video-shorts-mcp"))
from tts_kokoro import synthesize

from excel_renderer import BOMTable

OM_REELS_DIR = Path.home() / "Sara_Home" / "HSG" / "Bachelor" / "FS 26" / "OM" / "Reels"
FONT_DIR = Path("/usr/share/fonts/truetype/dejavu")
FPS = 30


def _font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    name = "DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf"
    path = FONT_DIR / name
    if path.exists():
        return ImageFont.truetype(str(path), size)
    return ImageFont.load_default()


def make_title_card(title: str, subtitle: str, points: int, width=1920, height=1080) -> Image.Image:
    img = Image.new("RGB", (width, height), (12, 12, 22))
    draw = ImageDraw.Draw(img)

    # Accent line top
    draw.rectangle([0, 0, width, 6], fill=(255, 68, 68))

    # Points badge
    badge_x, badge_y = width - 200, height // 2 - 60
    draw.rounded_rectangle([badge_x, badge_y, badge_x + 160, badge_y + 80],
                           radius=12, fill=(255, 68, 68))
    draw.text((badge_x + 80, badge_y + 40), f"{points} pts",
              font=_font(32, bold=True), fill=(255, 255, 255), anchor="mm")

    # Title
    draw.text((width // 2, height // 2 - 60), title,
              font=_font(56, bold=True), fill=(240, 240, 255), anchor="mm")
    draw.text((width // 2, height // 2 + 20), subtitle,
              font=_font(32), fill=(160, 160, 200), anchor="mm")

    # Course tag
    draw.text((width // 2, height // 2 + 90), "HSG Operations Management — Exam Preparation",
              font=_font(22), fill=(100, 100, 140), anchor="mm")

    # Bottom bar
    draw.rectangle([0, height - 6, width, height], fill=(79, 195, 247))
    return img


def make_answer_card(answer: str, value: str, width=1920, height=1080) -> Image.Image:
    img = Image.new("RGB", (width, height), (10, 28, 10))
    draw = ImageDraw.Draw(img)
    draw.rectangle([0, 0, width, 8], fill=(102, 187, 106))
    draw.text((width // 2, height // 2 - 80), "✓ Answer",
              font=_font(42, bold=True), fill=(102, 187, 106), anchor="mm")
    draw.text((width // 2, height // 2), answer,
              font=_font(72, bold=True), fill=(255, 255, 255), anchor="mm")
    draw.text((width // 2, height // 2 + 90), value,
              font=_font(36), fill=(180, 240, 180), anchor="mm")
    draw.rectangle([0, height - 8, width, height], fill=(102, 187, 106))
    return img


def render_video(
    steps: list[dict],      # each: {image: PIL.Image, spoken: str}
    output_name: str,
    voice: str = "bm_george",
    fps: int = FPS,
) -> str:
    """Assemble images + TTS into MP4. Returns output path."""
    OM_REELS_DIR.mkdir(parents=True, exist_ok=True)
    output_path = str(OM_REELS_DIR / output_name)

    with tempfile.TemporaryDirectory(prefix="om_excel_") as tmp:
        tmp = Path(tmp)
        frame_list = []

        print(f"[TTS + frames] {len(steps)} steps...")
        for i, step in enumerate(steps):
            # Save image as PNG
            img_path = str(tmp / f"frame_{i:03d}.png")
            step["image"].save(img_path)

            # TTS
            audio_path = str(tmp / f"audio_{i:03d}.wav")
            duration = synthesize(step["spoken"], audio_path, voice=voice, speed=1.15, lang="auto")
            print(f"      Step {i}: {duration:.1f}s — {step['spoken'][:50]}...")

            frame_list.append({"img": img_path, "audio": audio_path, "duration": duration})

        # Step 1: merge each image+audio into a short clip
        clips = []
        for i, f in enumerate(frame_list):
            dur  = f["duration"] + 0.3
            clip = str(tmp / f"clip_{i:03d}.mp4")
            cmd  = [
                "ffmpeg", "-y",
                "-loop", "1", "-t", str(dur), "-i", f["img"],
                "-i", f["audio"],
                "-c:v", "libx264", "-preset", "fast", "-crf", "18",
                "-c:a", "aac", "-b:a", "128k",
                "-pix_fmt", "yuv420p",
                "-shortest", "-r", str(fps),
                clip,
            ]
            r = subprocess.run(cmd, capture_output=True, text=True)
            if r.returncode != 0:
                raise RuntimeError(f"Clip {i} failed: {r.stderr[-500:]}")
            clips.append(clip)
            print(f"      Clip {i} encoded.")

        # Step 2: concat all clips via list file
        list_file = str(tmp / "clips.txt")
        with open(list_file, "w") as lf:
            for c in clips:
                lf.write(f"file '{c}'\n")

        print(f"[FFmpeg] Concat {len(clips)} clips → {output_path}")
        cmd = [
            "ffmpeg", "-y",
            "-f", "concat", "-safe", "0", "-i", list_file,
            "-c:v", "libx264", "-preset", "fast", "-crf", "18",
            "-c:a", "aac", "-b:a", "192k",
            "-pix_fmt", "yuv420p",
            output_path,
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            print("STDERR:", result.stderr[-2000:])
            raise RuntimeError(f"FFmpeg concat failed: {result.returncode}")

    print(f"[Done] → {output_path}")
    return output_path
