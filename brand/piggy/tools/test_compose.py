"""Test für brand/piggy/3d/compose.py mit synthetischem Material (kein Blender, keine Stimme nötig).
Aufruf: python3 brand/piggy/tools/test_compose.py   (braucht ffmpeg, Pillow, PyYAML)"""
import json, subprocess, sys, tempfile
from pathlib import Path
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
COMPOSE = ROOT / "3d" / "compose.py"
ok = 0


def check(cond, msg):
    global ok
    if not cond:
        sys.exit(f"FAIL: {msg}")
    ok += 1


def sh(*a):
    return subprocess.run([str(x) for x in a], capture_output=True, text=True)


with tempfile.TemporaryDirectory() as t:
    t = Path(t)
    (t / "seq").mkdir()
    for i in range(1, 13):
        Image.new("RGBA", (200, 200), (255, 150, 170, 255 if i % 2 else 200)).save(t / "seq" / f"frame_{i:04d}.png")
    sh("ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", "testsrc2=s=402x874:r=30:d=2", "-pix_fmt", "yuv420p", t / "sim.mp4")
    sh("ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", "sine=f=220:d=2", t / "v.wav")
    for fmt, size in (("9x16", (1080, 1920)), ("1x1", (1080, 1080)), ("16x9", (1920, 1080))):
        brief = {"name": f"t-{fmt}", "format": fmt, "scenes": [
            {"kind": "piggy", "piggy": str(t / "seq"), "say": "Hallo ich bin Piggy", "audio": str(t / "v.wav")},
            {"kind": "app", "video": str(t / "sim.mp4"), "piggy": str(t / "seq"), "say": "Tippe auf Scannen", "audio": str(t / "v.wav")},
            {"kind": "piggy", "piggy": str(t / "seq"), "seconds": 1}]}
        (t / f"{fmt}.json").write_text(json.dumps(brief))
        r = sh(sys.executable, COMPOSE, t / f"{fmt}.json", "--out", t / fmt, "--no-synth")
        check(r.returncode == 0, f"{fmt}: {r.stderr[-400:]}")
        m = json.loads(r.stdout.strip().splitlines()[-1])
        check(m["size"] == list(size) and m["scenes"] == 3, f"{fmt}: Meta {m}")
        mp4 = t / fmt / f"t-{fmt}.mp4"
        pr = json.loads(sh("ffprobe", "-v", "error", "-show_entries", "stream=codec_type,width,height", "-of", "json", mp4).stdout)
        kinds = {s["codec_type"] for s in pr["streams"]}
        check(kinds == {"video", "audio"}, f"{fmt}: Streams {kinds}")
        vs = [s for s in pr["streams"] if s["codec_type"] == "video"][0]
        check((vs["width"], vs["height"]) == size, f"{fmt}: Auflösung")
        check(5 < m["duration"] < 7, f"{fmt}: Dauer {m['duration']}")
        srt = (t / fmt / f"t-{fmt}.srt").read_text()
        check("Hallo ich bin" in srt and "Tippe auf" in srt and "-->" in srt, f"{fmt}: SRT")
        check((t / fmt / f"t-{fmt}.jpg").stat().st_size > 1000, f"{fmt}: Thumbnail")
    # Fehlerfälle
    bad = {"format": "4x3", "scenes": []}
    (t / "bad.json").write_text(json.dumps(bad))
    check(sh(sys.executable, COMPOSE, t / "bad.json", "--out", t / "x").returncode != 0, "unbekanntes Format wird abgelehnt")
    bad = {"scenes": [{"kind": "app", "video": str(t / "fehlt.mp4")}]}
    (t / "bad2.json").write_text(json.dumps(bad))
    check(sh(sys.executable, COMPOSE, t / "bad2.json", "--out", t / "x").returncode != 0, "fehlende Aufnahme wird abgelehnt")
    # Musik mit Ducking
    sh("ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", "sine=f=440:d=1", t / "m.wav")
    r = sh(sys.executable, COMPOSE, t / "9x16.json", "--out", t / "mus", "--no-synth", "--music", t / "m.wav")
    check(r.returncode == 0 and json.loads(r.stdout.strip().splitlines()[-1])["music"], f"Musik: {r.stderr[-300:]}")
print(f"{ok} ok")
