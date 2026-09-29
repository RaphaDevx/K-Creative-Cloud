"""
Main pipeline: topic → script → TTS → frames → video
"""
import json
import os
import tempfile
import time
from pathlib import Path

from script_gen import generate_script
from tts_kokoro import synthesize
from frame_render import render_scene_frame
from video_assemble import assemble_video, get_audio_duration

OUTPUT_DIR = Path.home() / "renders" / "shorts"


def create_short(
    topic: str,
    voice: str = "af_heart",
    tts_speed: float = 1.2,
    format: str = "portrait",
    output_name: str = "",
    extra_instructions: str = "",
) -> dict:
    """
    Full pipeline: topic → 100-second educational short video.
    Returns dict with output path, token usage, and timing.
    """
    t_start = time.time()
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    print(f"[1/4] Generating script for: {topic}")
    script = generate_script(topic, extra_instructions)
    scenes = script["scenes"]
    title = script.get("title", topic)
    tokens = script.get("_tokens", {})
    print(f"      → {len(scenes)} scenes | {tokens.get('total', '?')} tokens")

    tmpdir = tempfile.mkdtemp(prefix="kcloud_short_")
    scene_data = []

    print(f"[2/4] Generating TTS ({voice}, {tts_speed}x speed)...")
    for i, scene in enumerate(scenes):
        audio_path = os.path.join(tmpdir, f"audio_{i:03d}.wav")
        duration = synthesize(scene["spoken"], audio_path, voice=voice, speed=tts_speed)
        scene["_audio_path"] = audio_path
        scene["_duration"] = duration
        print(f"      Scene {i}: {duration:.1f}s — {scene['headline'][:40]}")

    total_audio = sum(s["_duration"] for s in scenes)
    print(f"      Total audio: {total_audio:.1f}s")

    print(f"[3/4] Rendering frames ({format})...")
    for i, scene in enumerate(scenes):
        frame_path = os.path.join(tmpdir, f"frame_{i:03d}.png")
        render_scene_frame(scene, frame_path, i, len(scenes), format=format)
        scene["_frame_path"] = frame_path

    print(f"[4/4] Assembling video...")
    if not output_name:
        safe = "".join(c if c.isalnum() or c in "-_" else "_" for c in topic[:40])
        output_name = f"{safe}.mp4"
    output_path = str(OUTPUT_DIR / output_name)

    scene_data = [
        {"frame": s["_frame_path"], "audio": s["_audio_path"], "duration": s["_duration"]}
        for s in scenes
    ]
    assemble_video(scene_data, output_path)

    elapsed = time.time() - t_start
    result = {
        "output": output_path,
        "title": title,
        "scenes": len(scenes),
        "total_duration_s": round(total_audio, 1),
        "tokens": tokens,
        "render_time_s": round(elapsed, 1),
    }
    print(f"\nDone in {elapsed:.0f}s → {output_path}")
    print(f"Tokens used: {tokens.get('total', '?')} (input: {tokens.get('input', '?')}, output: {tokens.get('output', '?')})")
    return result


if __name__ == "__main__":
    import sys
    topic = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else "The Dunning-Kruger Effect"
    result = create_short(topic)
    print(json.dumps(result, indent=2))
