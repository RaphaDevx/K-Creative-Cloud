#!/usr/bin/env python3
"""Test des 2,5D-Rigs (brand/fitdogs/2d): Teile, Rigs, gemeinsame Animationen, Render, Loop, Ruhepose, compose.py.
  python3 brand/fitdogs/tools/test_fitdogs2d.py        # Exit 0 = ok, gibt "N ok" aus
Arbeitet in einem temporären Verzeichnis (Teile + Frames in kleiner Auflösung), braucht cv2, numpy und ffmpeg."""
import importlib.util
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
REPO = ROOT.parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import split_parts  # noqa: E402

spec = importlib.util.spec_from_file_location("render_2d", ROOT / "2d" / "render_2d.py")
r2d = importlib.util.module_from_spec(spec)
spec.loader.exec_module(r2d)

SKINS = ("shiba", "dobermann")
SIZE = 360
passed = 0


def ok(cond, msg):
    global passed
    if not cond:
        print(f"FAIL: {msg}")
        sys.exit(1)
    passed += 1


def over_white(premul):
    a = premul[..., 3:4]
    return np.clip(premul[..., :3] + (1 - a), 0, 1) * 255


tmp = Path(tempfile.mkdtemp(prefix="fitdogs2d_"))
anims = json.loads((ROOT / "2d" / "anims.json").read_text())
rigs = {s: json.loads((ROOT / "2d" / "rigs" / f"{s}.json").read_text()) for s in SKINS}

# Rigs: gleiche Teile, Eltern, Reihenfolge; gemeinsame Animationen
names = {s: [p["name"] for p in rigs[s]["parts"]] for s in SKINS}
ok(names["shiba"] == names["dobermann"], "Teilenamen/Reihenfolge verschieden")
ok([p["parent"] for p in rigs["shiba"]["parts"]] == [p["parent"] for p in rigs["dobermann"]["parts"]], "Eltern verschieden")
ok({"head", "torso", "upper_arm_l", "upper_arm_r", "forearm_l", "forearm_r"} <= set(names["shiba"]), "Pflichtteile fehlen")
ok(all(rigs[s]["skeleton"] == anims["skeleton"] for s in SKINS), "Skeleton-Kennung weicht von anims.json ab")
valid = set(names["shiba"]) | {"root"}
for act in anims["actions"].values():
    ok(set(act["tracks"]) <= valid, "Animation referenziert unbekanntes Teil")
for pose in anims["poses"].values():
    ok(set(pose) <= valid, "Pose referenziert unbekanntes Teil")
ok({"idle", "flex", "wave", "hop", "talk"} <= set(anims["actions"]) and {"pose_idle", "pose_flex", "pose_wave"} <= set(anims["poses"]),
   "Aktionen/Posen unvollständig")
ok(anims["fps"] == 24, "fps nicht 24")

# Teile schneiden
loaded = {}
for s in SKINS:
    split_parts.split(s, tmp / "parts")
    meta = json.loads((tmp / "parts" / s / "parts.json").read_text())
    ok([p["name"] for p in meta["parts"]] == names[s], f"{s}: parts.json Reihenfolge")
    for p in meta["parts"]:
        img = cv2.imread(str(tmp / "parts" / s / p["file"]), cv2.IMREAD_UNCHANGED)
        ok(img is not None and img.shape[2] == 4, f"{s}/{p['name']}: kein RGBA")
        ok((img[..., 3] > 128).sum() > 2000, f"{s}/{p['name']}: Teil leer")
    loaded[s] = r2d.Rig(s, tmp / "parts")
    ok(len(loaded[s].parts) == 6, f"{s}: Rig lädt nicht")

# Render: RGBA, nicht leer, Figur komplett im Bild; Frames je Aktion
for s in SKINS:
    rig = loaded[s]
    fr = r2d.framing(rig, anims, 24, SIZE)
    for action, act in anims["actions"].items():
        n = round(act["duration"] * 24)
        worst = 1e9
        for i in range(0, n, 2):
            png = r2d.to_png(r2d.render_pose(rig, r2d.pose_at(anims, action, i / 24), fr, SIZE))
            ok(png.shape == (SIZE, SIZE, 4) and png.dtype == np.uint8, f"{s}/{action}: kein RGBA-Frame")
            al = png[..., 3]
            ys, xs = np.where(al > 8)
            ok(len(xs) > 0.1 * SIZE * SIZE * 0.3, f"{s}/{action}/{i}: Frame fast leer")
            worst = min(worst, xs.min(), ys.min(), SIZE - 1 - xs.max(), SIZE - 1 - ys.max())
        ok(worst >= 4, f"{s}/{action}: Figur angeschnitten (Rand {worst}px)")
    # Loop: Frame 1 == Frame (n+1) der Idle-Animation
    idle = anims["actions"]["idle"]
    f0 = r2d.render_pose(rig, r2d.pose_at(anims, "idle", 0), fr, SIZE)
    fn = r2d.render_pose(rig, r2d.pose_at(anims, "idle", idle["duration"]), fr, SIZE)
    fl = r2d.render_pose(rig, r2d.pose_at(anims, "idle", (round(idle["duration"] * 24) - 1) / 24), fr, SIZE)
    d_loop = np.abs(over_white(f0) - over_white(fn)).mean()
    d_step = np.abs(over_white(f0) - over_white(r2d.render_pose(rig, r2d.pose_at(anims, "idle", 1 / 24), fr, SIZE))).mean()
    ok(d_loop < 0.3, f"{s}: idle ist kein Loop (Abweichung {d_loop:.2f})")
    ok(np.abs(over_white(fl) - over_white(f0)).mean() < 2 * max(d_step, 0.2) + 0.5, f"{s}: idle Sprung am Loop-Ende")
    # Ruhepose ähnelt dem Freisteller (gleiche Kamera)
    pose0 = r2d.static_pose(anims, "pose_idle")
    mine = over_white(r2d.render_pose(rig, pose0, fr, SIZE))
    cut = rig.cutout.astype(np.float32) / 255
    k = fr["scale"]
    cam = np.array([[k, 0, fr["ox"]], [0, k, fr["oy"]]], np.float64)
    prem = np.dstack([cut[..., :3] * cut[..., 3:4], cut[..., 3:4]])
    ref = over_white(cv2.warpAffine(prem, cam, (SIZE, SIZE), flags=cv2.INTER_AREA))
    diff = np.abs(mine - ref).mean()
    ok(diff < 2.0, f"{s}: Ruhepose weicht vom Freisteller ab (mittlere Abweichung {diff:.2f}/255)")
    print(f"  {s}: Ruhepose-Abweichung {diff:.3f}/255, Loop-Abweichung {d_loop:.4f}")

# compose.py: Mini-Briefing mit zwei Szenen (je Hund eine)
frames = {}
for s in SKINS:
    subprocess.run([sys.executable, str(ROOT / "2d" / "render_2d.py"), "--skin", s, "--action", "idle", "--size", str(SIZE),
                    "--out", str(tmp / "frames"), "--parts", str(tmp / "parts")], check=True, capture_output=True)
    d = tmp / "frames" / s / "idle"
    ok(len(list(d.glob("frame_*.png"))) == 48 and (d / "meta.json").exists(), f"{s}: idle-Sequenz unvollständig")
    ok(cv2.imread(str(d / "frame_0001.png"), cv2.IMREAD_UNCHANGED).shape[2] == 4, f"{s}: Frame ohne Alpha")
    frames[s] = d
brief = {"name": "fitdogs2d_test", "format": "1x1", "fps": 24, "bg": "#FFFFFF",
         "scenes": [{"kind": "piggy", "seconds": 1.5, "piggy": str(frames["shiba"])},
                    {"kind": "piggy", "seconds": 1.5, "piggy": str(frames["dobermann"])}]}
(tmp / "brief.json").write_text(json.dumps(brief))
res = subprocess.run([sys.executable, str(REPO / "brand" / "piggy" / "3d" / "compose.py"), str(tmp / "brief.json"),
                      "--out", str(tmp / "video"), "--no-synth"], capture_output=True, text=True)
ok(res.returncode == 0, f"compose.py fehlgeschlagen: {res.stderr[-300:] or res.stdout[-300:]}")
mp4 = tmp / "video" / "fitdogs2d_test.mp4"
ok(mp4.exists() and mp4.stat().st_size > 5000, "compose-Video fehlt")

shutil.rmtree(tmp, ignore_errors=True)
print(f"{passed} ok")
