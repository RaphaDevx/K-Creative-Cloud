"""
MRP I reel — Material Requirements Planning basics for OM exam.
Run: /storage/projekte/ki_pipeline_env_312/bin/python3 render_mrp1_reel.py
"""
import json, sys, time, uuid, subprocess
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "video-shorts-mcp"))
from tts_kokoro import synthesize

REMOTION_DIR = Path(__file__).parent
OUTPUT_DIR = Path("/home/raphael/Sara_Home/HSG/Bachelor/FS 26/OM/Reels")
FPS = 30

SCRIPT = {
    "title": "MRP I — Material Requirements Planning | OM Exam",
    "scenes": [
        {
            "id": 0,
            "type": "hook",
            "headline": "WRONG ORDER DATE = ZERO POINTS",
            "subtext": "MRP I: the logic every OM exam tests",
            "emoji": "📦",
            "spoken": "Miss the order date by one week in MRP and you lose the entire question. Here is the exact logic you need — in under two minutes.",
            "accent_hex": "#FF4444",
        },
        {
            "id": 1,
            "type": "explanation",
            "headline": "MRP I = WHAT, HOW MUCH, WHEN",
            "subtext": "Material Requirements Planning — derived demand logic",
            "emoji": "🔍",
            "spoken": "MRP One answers three questions. What materials do I need? How much of each? And when do I need to order them? It works with derived demand — you do not forecast raw materials, you calculate them from the production plan.",
            "accent_hex": "#4FC3F7",
        },
        {
            "id": 2,
            "type": "fact",
            "headline": "3 INPUTS: MPS + BOM + INVENTORY",
            "subtext": "Master Schedule tells what. BOM tells how. Inventory tells what you already have.",
            "emoji": "⚙️",
            "spoken": "MRP One needs exactly three inputs. First: the Master Production Schedule — this tells you what finished product to make and when. Second: the Bill of Materials — the recipe showing which components you need for each unit. Third: Inventory Records — how much stock you already have on hand.",
            "accent_hex": "#FFD700",
        },
        {
            "id": 3,
            "type": "explanation",
            "headline": "GROSS → NET → ORDER",
            "subtext": "Net Requirements = Gross Requirements − On-Hand − Scheduled Receipts",
            "emoji": "🧮",
            "spoken": "The calculation has three steps. Step one: Gross Requirements — how much do you need in total, multiplied by BOM quantities. Step two: subtract what you already have on hand and any scheduled receipts arriving. That gives you Net Requirements. Step three: if Net Requirements is positive, you need to place a Planned Order.",
            "accent_hex": "#4FC3F7",
        },
        {
            "id": 4,
            "type": "warning",
            "headline": "LEAD TIME OFFSET — GO BACKWARDS",
            "subtext": "Need in Week 5 + 2 weeks lead time → Order Release in Week 3",
            "emoji": "⏪",
            "spoken": "This is where most students lose points. You must offset for lead time by going BACKWARDS. If you need components in Week 5 and the supplier needs 2 weeks, you place the order in Week 3. Always subtract lead time from the need date. Never add it.",
            "accent_hex": "#FF7043",
        },
        {
            "id": 5,
            "type": "fact",
            "headline": "MULTI-LEVEL BOM: TOP DOWN",
            "subtext": "Plan Level 0 first → derive Level 1 → derive Level 2",
            "emoji": "🌳",
            "spoken": "For multi-level products, always work top-down in planning. First plan the finished product at Level Zero. The Planned Order Release at Level Zero becomes the Gross Requirement for Level One components. Then repeat the same net calculation for each lower level. Do not skip levels.",
            "accent_hex": "#FFD700",
        },
        {
            "id": 6,
            "type": "takeaway",
            "headline": "MRP I IN 4 WORDS",
            "subtext": "Gross → Net → Offset → Release",
            "emoji": "✅",
            "spoken": "Four words sum it up. Gross: start with what you need. Net: subtract what you have. Offset: go backwards by lead time. Release: that is your order date. Gross, Net, Offset, Release — say it once before you open the Excel sheet.",
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

    output_path = str(OUTPUT_DIR / "om_mrp1_material_requirements.mp4")
    print(f"[3/4] Remotion render → {output_path}")
    t = time.time()
    cmd = [
        "npx", "remotion", "render",
        "src/index.ts", "VideoShort", output_path,
        "--props", json.dumps(video_props),
        "--duration-in-frames", str(total_frames),
        "--fps", str(FPS), "--width", "1080", "--height", "1920", "--log", "verbose",
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, cwd=str(REMOTION_DIR))
    if result.returncode != 0:
        print("STDERR:", result.stderr[-2000:])
        raise RuntimeError(f"Remotion render failed (exit {result.returncode})")
    print(f"[4/4] Done in {time.time()-t:.0f}s → {output_path}")
    return output_path


if __name__ == "__main__":
    main()
