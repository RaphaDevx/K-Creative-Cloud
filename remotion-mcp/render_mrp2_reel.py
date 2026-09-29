"""
MRP II reel — Manufacturing Resource Planning, 5 steps, exam traps.
Run: /storage/projekte/ki_pipeline_env_312/bin/python3 render_mrp2_reel.py
"""
import json, sys, time, uuid, subprocess
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "video-shorts-mcp"))
from tts_kokoro import synthesize

REMOTION_DIR = Path(__file__).parent
OUTPUT_DIR = Path("/home/raphael/Sara_Home/HSG/Bachelor/FS 26/OM/Reels")
FPS = 30

SCRIPT = {
    "title": "MRP II — 5 Steps, 3 Traps | OM Exam",
    "scenes": [
        {
            "id": 0,
            "type": "hook",
            "headline": "MRP II ≠ MRP I",
            "subtext": "Most students confuse them — here is the difference",
            "emoji": "🏭",
            "spoken": "Most students think MRP Two is just a bigger version of MRP One. It is not. MRP Two plans your entire factory — materials, machines, people, and money. Here are the five steps and the three exam traps.",
            "accent_hex": "#FF4444",
        },
        {
            "id": 1,
            "type": "explanation",
            "headline": "MRP II = WHOLE FACTORY",
            "subtext": "Materials + Machines + Workforce + Finance — all integrated",
            "emoji": "🔗",
            "spoken": "MRP One only handles material quantities. MRP Two integrates everything: material requirements from MRP One, plus machine capacity, workforce planning, and financial projections. It is a closed-loop system — actual results feed back into the plan.",
            "accent_hex": "#4FC3F7",
        },
        {
            "id": 2,
            "type": "fact",
            "headline": "5 STEPS — TOP TO BOTTOM",
            "subtext": "Business Plan → S&OP → MPS → MRP → Shop Floor",
            "emoji": "📋",
            "spoken": "MRP Two has exactly five steps, not six — this is a direct exam question. Step One: Business Planning, done annually. Step Two: Sales and Operations Planning, done monthly. Step Three: Master Production Scheduling, done weekly. Step Four: Material Requirements Planning, also weekly. Step Five: Production Activity Control, done daily.",
            "accent_hex": "#FFD700",
        },
        {
            "id": 3,
            "type": "warning",
            "headline": "TRAP 1: MRP = STEP 4, WEEKLY",
            "subtext": "NOT annually. NOT step 3. This is tested every semester.",
            "emoji": "🪤",
            "spoken": "Exam trap number one. MRP — that is Material Requirements Planning — is Step FOUR, not step three. And it runs weekly, not annually. The annual step is Business Planning at the top. If you see answer options mixing up the step number or the frequency, this is the trap.",
            "accent_hex": "#FF7043",
        },
        {
            "id": 4,
            "type": "warning",
            "headline": "TRAP 2: S&OP IS AGGREGATED",
            "subtext": "Product families, not individual SKUs — machines AND workers",
            "emoji": "🪤",
            "spoken": "Exam trap number two. Step Two, Sales and Operations Planning, works with aggregated product families — not individual products or SKUs. It plans both machines and workforce together. If an answer says S&OP plans individual products, it is wrong.",
            "accent_hex": "#FF7043",
        },
        {
            "id": 5,
            "type": "warning",
            "headline": "TRAP 3: CLOSED LOOP = FEEDBACK",
            "subtext": "Actual results go BACK UP to Business Planning — MRP I has no feedback",
            "emoji": "🔄",
            "spoken": "Exam trap number three. MRP Two is a closed-loop system. Actual production results flow back up to the Business Planning level. This feedback loop is what distinguishes MRP Two from MRP One — MRP One has no feedback. If an answer says MRP Two has no feedback loop, it is wrong.",
            "accent_hex": "#FF7043",
        },
        {
            "id": 6,
            "type": "takeaway",
            "headline": "THE 3 NUMBERS: 5, 4, WEEKLY",
            "subtext": "5 steps total. MRP = step 4. Frequency = weekly.",
            "emoji": "✅",
            "spoken": "Three numbers win you the MRP Two questions. Five — that is the total number of steps. Four — that is the step where MRP sits. Weekly — that is the frequency of both MPS and MRP. Remember five, four, weekly, and you will not lose a single point on MRP Two.",
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

    output_path = str(OUTPUT_DIR / "om_mrp2_vollstaendig.mp4")
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
