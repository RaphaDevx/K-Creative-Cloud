"""
Generic OM reel renderer — call with a hand-crafted SCRIPT dict.
Output goes directly to ~/Sara_Home/HSG/Bachelor/FS 26/OM/Reels/

Usage: /storage/projekte/ki_pipeline_env_312/bin/python3 render_om_reel.py
"""
import json
import sys
import time
import uuid
import subprocess
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "video-shorts-mcp"))
from tts_kokoro import synthesize

REMOTION_DIR = Path(__file__).parent
OM_REELS_DIR = Path.home() / "Sara_Home" / "HSG" / "Bachelor" / "FS 26" / "OM" / "Reels"
FPS = 30


def render_om_reel(script: dict, output_name: str, voice: str = "bm_george") -> str:
    """Render one OM reel. Returns output path."""
    OM_REELS_DIR.mkdir(parents=True, exist_ok=True)
    render_id = uuid.uuid4().hex[:8]
    PUBLIC_AUDIO = REMOTION_DIR / "public" / "audio" / render_id
    PUBLIC_AUDIO.mkdir(parents=True, exist_ok=True)

    scenes = script["scenes"]
    title = script["title"]
    print(f"[1/4] Script: {len(scenes)} scenes — '{title}'")

    print(f"[2/4] TTS ({voice})...")
    total_frames = 0
    for i, scene in enumerate(scenes):
        audio_path = str(PUBLIC_AUDIO / f"scene_{i:03d}.wav")
        duration = synthesize(scene["spoken"], audio_path, voice=voice, speed=1.2, lang="auto")
        duration_frames = int(duration * FPS) + 6
        scene["audioFile"] = f"{render_id}/scene_{i:03d}.wav"
        scene["durationFrames"] = duration_frames
        total_frames += duration_frames
        print(f"      Scene {i}: {duration:.1f}s — {scene['headline']}")

    print(f"      Total: {total_frames} frames = {total_frames/FPS:.1f}s")

    video_props = {
        "scenes": scenes,
        "title": title,
        "totalDurationFrames": total_frames,
        "style": "minimal",
        "characterId": "default",
    }
    (REMOTION_DIR / "public" / "video-props.json").write_text(json.dumps(video_props, indent=2))

    output_path = str(OM_REELS_DIR / output_name)
    print(f"[3/4] Remotion render → {output_path}")
    t = time.time()
    cmd = [
        "npx", "remotion", "render",
        "src/index.ts", "VideoShort", output_path,
        "--props", json.dumps(video_props),
        "--duration-in-frames", str(total_frames),
        "--fps", str(FPS),
        "--width", "1080",
        "--height", "1920",
        "--log", "verbose",
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, cwd=str(REMOTION_DIR))
    if result.returncode != 0:
        print("STDERR:", result.stderr[-2000:])
        raise RuntimeError(f"Remotion render failed (exit {result.returncode})")

    print(f"[4/4] Done in {time.time()-t:.0f}s → {output_path}")
    return output_path
