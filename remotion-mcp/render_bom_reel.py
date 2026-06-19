"""
Direct BOM reel render — bypasses API call, uses hand-crafted script.
Run with: /storage/projekte/ki_pipeline_env_312/bin/python3 render_bom_reel.py
"""
import json
import os
import sys
import time
import uuid
import subprocess
from pathlib import Path

# Patch sys.path
sys.path.insert(0, str(Path(__file__).parent.parent / "video-shorts-mcp"))

from tts_kokoro import synthesize

REMOTION_DIR = Path(__file__).parent
OUTPUT_DIR = Path.home() / "Sara_Home" / "HSG" / "Bachelor" / "FS 26" / "OM" / "Reels"
FPS = 30

# ── Hand-crafted BOM storyboard ───────────────────────────────────────────────
SCRIPT = {
    "title": "BOM — Bill of Materials | OM Exam",
    "scenes": [
        {
            "id": 0,
            "type": "hook",
            "headline": "ONE WRONG LEVEL = FAIL",
            "subtext": "BOM calculation: the 4-point trap in every OM exam",
            "emoji": "⚠️",
            "spoken": "One wrong level in your BOM and you lose four points — instantly. Here is exactly how to nail it every single time.",
            "accent_hex": "#FF4444",
        },
        {
            "id": 1,
            "type": "explanation",
            "headline": "WHAT IS A BOM?",
            "subtext": "Bill of Materials = hierarchical parts list for a product",
            "emoji": "🌳",
            "spoken": "A Bill of Materials is a tree. Level zero is your finished product — the Battery Tester in the HS23 exam. Level one holds sub-assemblies. Level two holds raw components. Every node has a quantity, a unit cost, and a manufacturing cost.",
            "accent_hex": "#4FC3F7",
        },
        {
            "id": 2,
            "type": "fact",
            "headline": "COSTS FLOW BOTTOM-UP",
            "subtext": "Start lowest level → roll up → never top-down",
            "emoji": "⬆️",
            "spoken": "The golden rule: always start at the lowest level and work upward. At every level the formula is the same — quantity times unit cost, plus manufacturing cost at that level. Never start from the top.",
            "accent_hex": "#FFD700",
        },
        {
            "id": 3,
            "type": "explanation",
            "headline": "EXCEL: 3-STEP FORMULA",
            "subtext": "Column setup: Qty | Unit Cost | Manuf. Cost | Total",
            "emoji": "📊",
            "spoken": "In Excel, set up four columns: Quantity, Unit Cost, Manufacturing Cost, and Total. For every bottom-level component: Total equals Quantity times Unit Cost. For every parent node: Total equals the sum of all child totals plus its own manufacturing cost. Then reference the Level Zero cell — that is your answer.",
            "accent_hex": "#4FC3F7",
        },
        {
            "id": 4,
            "type": "fact",
            "headline": "HS23 EXAM: 2750 CHF",
            "subtext": "Q19 — multi-level BOM, Battery Tester, worksheet 19",
            "emoji": "🎯",
            "spoken": "In the HS23 exam, Question 19, you are given a multi-level BOM for a Battery Tester. Open worksheet 19, build the tree bottom-up with the formula, and the total cost is two thousand seven hundred and fifty Swiss francs. Answer A.",
            "accent_hex": "#FFD700",
        },
        {
            "id": 5,
            "type": "warning",
            "headline": "MRP II TRAP: STEP 4",
            "subtext": "BOM is used in MRP = Step 4, short-term, NOT annually",
            "emoji": "🪤",
            "spoken": "Exam trap: BOM feeds into Material Requirements Planning — that is Step FOUR of MRP Two, not step three. It is done short-term, not annually. And MRP Two has exactly FIVE steps, not six. These three facts come up every semester.",
            "accent_hex": "#FF7043",
        },
        {
            "id": 6,
            "type": "takeaway",
            "headline": "BOTTOM-UP. ALWAYS.",
            "subtext": "Qty × Unit Cost + Manuf. Cost — repeat up every level",
            "emoji": "✅",
            "spoken": "Remember: lowest level first, roll up with the same formula at every node, and watch for components that appear under multiple parents — multiply by quantity each time. BOM is free points if you know the direction.",
            "accent_hex": "#CE93D8",
        },
    ],
}


def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    render_id = uuid.uuid4().hex[:8]
    PUBLIC_AUDIO = REMOTION_DIR / "public" / "audio" / render_id
    PUBLIC_AUDIO.mkdir(parents=True, exist_ok=True)

    scenes = SCRIPT["scenes"]
    title = SCRIPT["title"]
    voice = "bm_george"

    print(f"[1/4] Script ready: {len(scenes)} scenes — '{title}'")

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
    props_path = REMOTION_DIR / "public" / "video-props.json"
    props_path.write_text(json.dumps(video_props, indent=2))

    output_name = "om_bom_bill_of_materials_remotion.mp4"
    output_path = str(OUTPUT_DIR / output_name)

    print(f"[3/4] Remotion render → {output_path}")
    t_render = time.time()
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

    elapsed = time.time() - t_render
    print(f"[4/4] Done in {elapsed:.0f}s → {output_path}")
    return output_path


if __name__ == "__main__":
    main()
