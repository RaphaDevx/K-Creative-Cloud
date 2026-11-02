#!/usr/bin/env python3
"""Test des Tracing-3D (brand/fitdogs/3d/build_traced.py): beide Skins bauen, Meshes, Bones/Actions, Front gegen Freisteller,
Idle-Animation, glb.
  python3 brand/fitdogs/tools/test_fitdogs_traced.py        # Exit 0 = ok, gibt "N ok" aus (ca. 1 min)
Braucht Blender 4.x (blender im PATH), cv2, numpy und die Teile aus split_parts.py (werden bei Bedarf erzeugt)."""
import json
import shutil
import struct
import subprocess
import sys
import tempfile
from pathlib import Path

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
SKINS = ("shiba", "dobermann")
SIZE = 360
FRONT_MAX_ERR = 6.0  # mittlerer Pixelfehler im Figurbereich (0..255)
passed = 0
BLENDER = shutil.which("blender")


def ok(cond, msg):
    global passed
    if not cond:
        print(f"FAIL: {msg}")
        sys.exit(1)
    passed += 1


def blender(*args, blend=None):
    cmd = [BLENDER, "-b"] + ([str(blend)] if blend else []) + ["-P", str(ROOT / "3d" / "build_traced.py"), "--"] + [str(a) for a in args]
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=900)
    if r.returncode != 0 or "Traceback" in r.stdout + r.stderr:
        print(r.stdout[-3000:], r.stderr[-2000:])
        ok(False, "blender-Lauf fehlgeschlagen")
    return r.stdout


def glb_json(path):
    b = Path(path).read_bytes()
    magic, ver, _ = struct.unpack("<4sII", b[:12])
    n, typ = struct.unpack("<I4s", b[12:20])
    return magic, json.loads(b[20:20 + n])


def over_white(img):
    a = img[..., 3:4].astype(np.float32) / 255
    return (img[..., :3] * a + 255 * (1 - a)).astype(np.float32)


ok(BLENDER is not None, "blender nicht gefunden")
for s in SKINS:  # Teile vorhanden?
    if not (ROOT / "dist" / "2d" / s / "parts.json").exists():
        import split_parts
        split_parts.split(s, ROOT / "dist" / "2d")

tmp = Path(tempfile.mkdtemp(prefix="fitdogs_traced_"))
try:
    blender("--skin", "all", "--out", tmp, "--render", "preview", "--cam", "front", "--action", "idle", "--action-stride", 12,
            "--size", SIZE, "--samples", 8)
    man = {s: json.loads((tmp / f"{s}.manifest.json").read_text()) for s in SKINS}
    anims = json.loads((ROOT / "2d" / "anims.json").read_text())

    # --- Dateien, glb
    for s in SKINS:
        ok((tmp / f"{s}.glb").stat().st_size > 100_000, f"{s}.glb fehlt/zu klein")
        ok((tmp / f"{s}.blend").exists(), f"{s}.blend fehlt")
        magic, g = glb_json(tmp / f"{s}.glb")
        ok(magic == b"glTF", f"{s}.glb ist kein glTF")
        ok(len(g.get("images", [])) >= 12 and len(g.get("skins", [])) == 1, f"{s}.glb: Texturen/Skin fehlen")
        ok(all(m["pbrMetallicRoughness"].get("roughnessFactor", 1) == 1 for m in g["materials"]), f"{s}.glb: roughness != 1")
        ok(all("baseColorTexture" in m["pbrMetallicRoughness"] for m in g["materials"]), f"{s}.glb: Basecolor-Textur fehlt")
        ok({a["name"] for a in g.get("animations", [])} == set(anims["actions"]), f"{s}.glb: Animationen {[a['name'] for a in g.get('animations', [])]}")
    ga, gb = (glb_json(tmp / f"{s}.glb")[1] for s in SKINS)
    jn = lambda g: [g["nodes"][j]["name"] for j in g["skins"][0]["joints"]]
    ok(sorted(jn(ga)) == sorted(jn(gb)), "glb-Joints verschieden")

    # --- gleiche Bones/Actions
    ok(man["shiba"]["bones"] and [(b["name"], b["parent"]) for b in man["shiba"]["bones"]] ==
       [(b["name"], b["parent"]) for b in man["dobermann"]["bones"]], "Bones/Hierarchie verschieden")
    names = {b["name"] for b in man["shiba"]["bones"]}
    ok({"root", "torso", "head", "upper_arm_l", "upper_arm_r", "forearm_l", "forearm_r"} <= names, "Pflicht-Bones fehlen")
    ok(man["shiba"]["actions"] == man["dobermann"]["actions"], "Actions verschieden")
    ok(set(man["shiba"]["actions"]) == set(anims["actions"]), "Actions != anims.json")
    ok(all(a["frames"][1] - a["frames"][0] == round(anims["actions"][n]["duration"] * 24) for n, a in man["shiba"]["actions"].items()),
       "Action-Laengen weichen von anims.json ab")
    ok(any(b["head"] != c["head"] for b, c in zip(man["shiba"]["bones"], man["dobermann"]["bones"])), "Pivots sind gleich (sollten aus den Rigs kommen)")

    # --- Meshes unabhaengig aus der .blend nachgemessen
    for s in SKINS:
        out = blender("--check", blend=tmp / f"{s}.blend")
        chk = json.loads(next(l for l in out.splitlines() if l.startswith("TRACED_CHECK ")).split(" ", 1)[1])
        ok(len(chk["meshes"]) == 6, f"{s}: {len(chk['meshes'])} Meshes")
        worst = 0.0
        for n, m in chk["meshes"].items():
            ok(m["faces"] > 3000, f"{s}/{n}: zu wenige Flaechen")
            frac = (m["boundary_edges"] + m["nonmanifold_edges"]) / m["edges"]
            worst = max(worst, frac)
            ok(m["boundary_edges"] <= 8 and frac < 0.002, f"{s}/{n}: Mesh nicht geschlossen ({m})")
        ok(chk["bones"] == [tuple(b) for b in [(x["name"], x["parent"]) for x in man[s]["bones"]]] or
           [list(b) for b in chk["bones"]] == [[x["name"], x["parent"]] for x in man[s]["bones"]], f"{s}: Bones in .blend weichen ab")
        ok(sorted(chk["actions"]) == sorted(anims["actions"]), f"{s}: Actions in .blend")
        ok(all(a["fcurves"] for a in chk["actions"].values()), f"{s}: Action ohne F-Curves")
    ok(chk["actions"]["idle"]["fcurves"] and True, "idle")
    fc = {s: None for s in SKINS}
    # --- F-Curves identisch (zweiter Lauf nur fuer die Pfade)
    paths = {}
    for s in SKINS:
        out = blender("--check", blend=tmp / f"{s}.blend")
        paths[s] = json.loads(next(l for l in out.splitlines() if l.startswith("TRACED_CHECK ")).split(" ", 1)[1])["actions"]
    ok(paths["shiba"] == paths["dobermann"], "F-Curve-Pfade/Frames verschieden")

    # --- Front gegen Freisteller
    for s in SKINS:
        r = cv2.imread(str(tmp / s / "front" / "frame_0001.png"), cv2.IMREAD_UNCHANGED)
        ok(r is not None and r.shape[2] == 4, f"{s}: Front-Render fehlt/kein RGBA")
        cut = cv2.imread(str(ROOT / "dist" / "2d" / s / "cutout.png"), cv2.IMREAD_UNCHANGED)
        ok(abs(r.shape[1] / r.shape[0] - cut.shape[1] / cut.shape[0]) < 0.01, f"{s}: Seitenverhaeltnis")
        c = cv2.resize(cut, (r.shape[1], r.shape[0]), interpolation=cv2.INTER_AREA)
        fig = (np.maximum(r[..., 3], c[..., 3]) > 127)
        err = np.abs(over_white(r) - over_white(c)).mean(axis=2)[fig].mean()
        aerr = np.abs(r[..., 3].astype(float) - c[..., 3].astype(float)).mean()
        print(f"  Front {s}: mittlerer Pixelfehler im Figurbereich {err:.2f}/255 (Schwelle {FRONT_MAX_ERR}), Alpha-Fehler {aerr:.2f}")
        ok(err < FRONT_MAX_ERR, f"{s}: Frontfehler {err:.2f} >= {FRONT_MAX_ERR}")
        ok(aerr < 3.0, f"{s}: Alpha-Fehler {aerr:.2f}")

    # --- Idle animiert wirklich
    for s in SKINS:
        fr = sorted((tmp / s / "idle_front").glob("frame_*.png"))
        ok(len(fr) >= 4, f"{s}: zu wenige Idle-Frames")
        imgs = [cv2.imread(str(f), cv2.IMREAD_UNCHANGED).astype(np.float32) for f in fr]
        d = max(np.abs(imgs[0] - i).mean() for i in imgs[1:])
        ok(d > 0.05, f"{s}: Idle-Frames unterscheiden sich nicht ({d:.3f})")
        ok(all(i.shape[2] == 4 for i in imgs), f"{s}: Idle nicht RGBA")
        print(f"  Idle {s}: max. mittlere Frame-Differenz {d:.2f}")
finally:
    shutil.rmtree(tmp, ignore_errors=True)
print(f"{passed} ok")
