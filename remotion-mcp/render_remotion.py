"""
Remotion render orchestrator.
Bridges Python (script gen + TTS) with Node.js Remotion renderer.

Flow:
  topic -> Claude Haiku script -> Kokoro TTS per scene
       -> [2D only] Rhubarb lip sync per scene
       -> scene JSON with durationFrames -> npx remotion render -> MP4
"""
import json
import os
import shutil
import subprocess
import sys
import time
import uuid
from pathlib import Path

SHORTS_DIR = Path(__file__).parent.parent / "video-shorts-mcp"
sys.path.insert(0, str(SHORTS_DIR))

from script_gen import generate_script
from tts_kokoro import synthesize

REMOTION_DIR = Path(__file__).parent
OUTPUT_DIR = Path.home() / "renders" / "shorts"
FPS = 30
RHUBARB_BIN = shutil.which("rhubarb") or "/usr/local/bin/rhubarb"


def run_rhubarb(audio_path: str) -> list:
    """Run Rhubarb on a WAV file. Returns list of {start, phoneme} dicts."""
    if not Path(RHUBARB_BIN).exists():
        print(f"      [rhubarb] binary not found at {RHUBARB_BIN}, skipping lip sync")
        return []
    try:
        result = subprocess.run(
            [RHUBARB_BIN, "-f", "tsv", "-r", "phonetic", "--extendedShapes", "none", audio_path],
            capture_output=True, text=True, timeout=30,
        )
        cues = []
        for line in result.stdout.strip().splitlines():
            parts = line.strip().split("\t")
            if len(parts) >= 2:
                try:
                    cues.append({"start": float(parts[0]), "phoneme": parts[1]})
                except ValueError:
                    pass
        return cues
    except Exception as e:
        print(f"      [rhubarb] error: {e}")
        return []


def create_remotion_short(
    topic: str,
    voice: str = "am_adam",
    format: str = "portrait",
    output_name: str = "",
    extra_instructions: str = "",
    style: str = "minimal",
    character_id: str = "default",
) -> dict:
    """Full Remotion pipeline: topic -> animated MP4."""
    t_start = time.time()
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    render_id = uuid.uuid4().hex[:8]
    PUBLIC_AUDIO = REMOTION_DIR / "public" / "audio" / render_id
    PUBLIC_AUDIO.mkdir(parents=True, exist_ok=True)

    use_lipsync = (style == "2D")

    print(f"[1/4] Generating script: {topic} (style={style})")
    script = generate_script(topic, extra_instructions)
    scenes = script["scenes"]
    title = script.get("title", topic)
    tokens = script.get("_tokens", {})
    print(f"      {len(scenes)} scenes | {tokens.get('total', '?')} tokens")

    print(f"[2/4] TTS ({voice})...")
    total_frames = 0
    for i, scene in enumerate(scenes):
        audio_filename = f"{render_id}/scene_{i:03d}.wav"
        audio_path = str(PUBLIC_AUDIO / f"scene_{i:03d}.wav")
        duration = synthesize(scene["spoken"], audio_path, voice=voice, speed=1.2, lang="auto")
        duration_frames = int(duration * FPS) + 6
        scene["audioFile"] = audio_filename
        scene["durationFrames"] = duration_frames
        total_frames += duration_frames

        if use_lipsync:
            print(f"      Scene {i}: TTS done, running Rhubarb...")
            scene["lipSync"] = run_rhubarb(audio_path)
            print(f"      Scene {i}: {len(scene['lipSync'])} lip-sync cues")
        else:
            print(f"      Scene {i}: {duration:.1f}s — {scene['headline'][:40]}")

    print(f"      Total: {total_frames} frames = {total_frames/FPS:.1f}s")

    video_props = {
        "scenes": scenes,
        "title": title,
        "totalDurationFrames": total_frames,
        "style": style,
        "characterId": character_id,
    }
    props_path = REMOTION_DIR / "public" / "video-props.json"
    props_path.write_text(json.dumps(video_props, indent=2))

    if not output_name:
        safe = "".join(c if c.isalnum() or c in "-_" else "_" for c in topic[:40])
        output_name = f"{safe}_{style}_remotion.mp4"
    output_path = str(OUTPUT_DIR / output_name)

    print(f"[3/4] Remotion render → {output_path}")
    cmd = [
        "npx", "remotion", "render",
        "src/index.ts", "VideoShort", output_path,
        "--props", json.dumps(video_props),
        "--duration-in-frames", str(total_frames),
        "--fps", str(FPS),
        "--width", "1080",
        "--height", "1920" if format == "portrait" else "1080",
        "--log", "verbose",
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, cwd=str(REMOTION_DIR))
    if result.returncode != 0:
        raise RuntimeError(f"Remotion render failed (exit {result.returncode}):\n{result.stderr[-1000:]}")

    print("[4/4] Done!")
    elapsed = time.time() - t_start
    return {
        "output": output_path,
        "title": title,
        "style": style,
        "scenes": len(scenes),
        "total_duration_s": round(total_frames / FPS, 1),
        "total_frames": total_frames,
        "tokens": tokens,
        "render_time_s": round(elapsed, 1),
        "engine": "remotion",
        "lip_sync": use_lipsync,
    }


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("topic", nargs="*", default=["Was ist empirische Sozialforschung?"])
    parser.add_argument("--style", default="minimal")
    parser.add_argument("--voice", default="am_adam")
    args = parser.parse_args()
    result = create_remotion_short(" ".join(args.topic), voice=args.voice, style=args.style)
    print(json.dumps(result, indent=2))
