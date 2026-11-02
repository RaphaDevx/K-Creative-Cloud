#!/usr/bin/env python3
"""
Test der FitDogs-Pipeline (brand/fitdogs/3d/build_dogs.py) mit Blender headless in sehr niedriger Qualitaet.
  python3 brand/fitdogs/tools/test_fitdogs.py        # Exit 0 = ok, gibt "N ok" aus

Baut beide Skins in ein temporaeres Verzeichnis (Sprites 192 px, 4 Samples, Icon 256 px) und prueft:
Dateien, identisches Skelett (Bones, Hierarchie, Ruhepositionen, glTF-Joints), identische Actions und F-Curve-Pfade,
identische Gesichts-Shape-Keys, echte Skin-Unterschiede (Materialfarben, Ohrenhoehe), Sprites mit Alpha, Icon ohne
Alpha und ohne angeschnittene Figur, Character-Dateien. Braucht blender im PATH und Pillow.
"""
import json
import os
import shutil
import struct
import subprocess
import sys
import tempfile

from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, ".."))
REPO = os.path.abspath(os.path.join(ROOT, "..", ".."))
SCRIPT = os.path.join(ROOT, "3d", "build_dogs.py")
SKINS = ("shiba", "dobermann")
ACTIONS = {"idle", "flex", "wave", "hop", "talk"}
EXPR = ["neutral", "happy", "angry", "surprised"]
ICON = 256

passed = 0
fails = []


def check(name, cond, detail=""):
    global passed
    if cond:
        passed += 1
        print("  ok   ", name)
    else:
        fails.append(name)
        print("  FEHLER", name, detail)


def read_glb(path):
    with open(path, "rb") as f:
        magic, ver, _ = struct.unpack("<4sII", f.read(12))
        ln, kind = struct.unpack("<I4s", f.read(8))
        assert magic == b"glTF" and kind == b"JSON"
        return json.loads(f.read(ln))


def glb_summary(g):
    names = [n["name"] for n in g["nodes"]]
    skin = g["skins"][0]
    joints = [names[j] for j in skin["joints"]]
    parent = {}
    for i, n in enumerate(g["nodes"]):
        for c in n.get("children", []):
            parent[names[c]] = names[i]
    hierarchy = {j: parent.get(j) for j in joints}
    anims = {}
    for a in g["animations"]:
        anims[a["name"]] = sorted((names[c["target"]["node"]], c["target"]["path"]) for c in a["channels"])
    return joints, hierarchy, anims


def mesh_height(g, node_name):
    for n in g["nodes"]:
        if n["name"] == node_name and "mesh" in n:
            for prim in g["meshes"][n["mesh"]]["primitives"]:
                acc = g["accessors"][prim["attributes"]["POSITION"]]
                return acc["max"][1] - acc["min"][1]
    return None


def main():
    tmp = tempfile.mkdtemp(prefix="fitdogs_test_")
    try:
        out = os.path.join(tmp, "3d")
        r = subprocess.run(["blender", "-b", "-P", SCRIPT, "--", "--skin", "all", "--out", out, "--render", "all",
                            "--size", "192", "--samples", "4", "--icon-size", str(ICON)],
                           capture_output=True, text=True, timeout=900)
        check("blender-Build laeuft durch", r.returncode == 0 and "[fitdogs] done" in r.stdout, r.stdout[-800:] + r.stderr[-800:])

        man, glb = {}, {}
        for s in SKINS:
            for rel in (s + ".blend", s + ".glb", s + ".manifest.json", s + "-overview.png",
                        "sprites/%s-mascot-idle-neutral.png" % s, "sprites/%s-mascot-flex-happy.png" % s,
                        "sprites/%s-mascot-talk-neutral.png" % s):
                check("%s: %s vorhanden" % (s, rel), os.path.getsize(os.path.join(out, rel)) > 1000 if os.path.exists(os.path.join(out, rel)) else False)
            man[s] = json.load(open(os.path.join(out, s + ".manifest.json")))
            glb[s] = read_glb(os.path.join(out, s + ".glb"))
        a, b = SKINS

        # Skelett
        check("Bone-Namen identisch", list(man[a]["bones"]) == list(man[b]["bones"]))
        check("Hierarchie identisch", {k: v["parent"] for k, v in man[a]["bones"].items()} == {k: v["parent"] for k, v in man[b]["bones"].items()})
        check("Ruhepositionen identisch", man[a]["bones"] == man[b]["bones"])
        check("Skelett-Kennung", man[a]["skeleton"] == man[b]["skeleton"] == "fitdogs-v1")
        ja, ha, aa = glb_summary(glb[a])
        jb, hb, ab = glb_summary(glb[b])
        check("glTF: Joints und Hierarchie identisch", sorted(ja) == sorted(jb) and ha == hb and len(ja) == len(man[a]["bones"]))

        # Actions
        check("Action-Namen (.blend-Manifest)", set(man[a]["actions"]) == set(man[b]["actions"]) == ACTIONS)
        check("F-Curve-Datenpfade identisch", all(man[a]["actions"][k]["fcurves"] == man[b]["actions"][k]["fcurves"] and man[a]["actions"][k]["fcurves"] for k in ACTIONS))
        check("Action-Laengen identisch", all(man[a]["actions"][k]["frames"] == man[b]["actions"][k]["frames"] for k in ACTIONS))
        check("glTF: Animationsnamen", set(aa) == set(ab) == ACTIONS, "%s %s" % (set(aa), set(ab)))
        check("glTF: Kanaele je Animation identisch", aa == ab)
        check("jaw-Bone wird von talk bewegt", any('"jaw"' in p for p in man[a]["actions"]["talk"]["fcurves"]))

        # Shape Keys
        check("Gesichts-Shape-Keys identisch", man[a]["shape_keys"] == man[b]["shape_keys"] and bool(man[a]["shape_keys"]))
        check("Shape-Key-Namen = neutral/happy/angry/surprised", all(v == EXPR for v in man[a]["shape_keys"].values()))
        check("Shape-Key-Objekte: Augen, Brauen, Mund", set(man[a]["shape_keys"]) == {"eye.L", "eye.R", "brow.L", "brow.R", "mouth"})
        for s in SKINS:
            morph = [m for m in glb[s]["meshes"] if m["primitives"][0].get("targets")]
            check("%s: glTF enthaelt Morph Targets" % s, len(morph) >= 5)

        # Skin-Unterschiede
        ca, cb = set(man[a]["material_colors"].values()), set(man[b]["material_colors"].values())
        check("Materialfarben unterscheiden sich", ca != cb and len(ca - cb) >= 4, "%s | %s" % (ca - cb, cb - ca))
        def base_colors(g):
            return {tuple(round(c, 3) for c in m["pbrMetallicRoughness"].get("baseColorFactor", [1, 1, 1, 1])) for m in g["materials"]}
        check("glTF-Materialfarben unterscheiden sich", base_colors(glb[a]) != base_colors(glb[b]))
        fur = lambda s: json.load(open(os.path.join(ROOT, "skins", s + ".json")))["palette"]["fur"]
        check("Fellfarben in den Skin-Dateien verschieden", fur(a) != fur(b))
        ha_, hb_ = mesh_height(glb[a], "ear.L"), mesh_height(glb[b], "ear.L")
        check("Ohrenform unterscheidet sich (Mesh-Hoehe)", ha_ and hb_ and abs(ha_ - hb_) > 0.1, "%s %s" % (ha_, hb_))
        check("Goldkette nur beim Dobermann", "chain" in man["dobermann"]["objects"] and "chain" not in man["shiba"]["objects"])
        check("Outline nicht im glTF", not any(n["name"].endswith(".ol") for g in glb.values() for n in g["nodes"]))

        # Sprites
        for s in SKINS:
            sd = os.path.join(out, "sprites")
            files = sorted(f for f in os.listdir(sd) if f.startswith(s + "-mascot-"))
            check("%s: 8 Sprites" % s, len(files) == 8, str(files))
            ok_alpha = True
            for f in files:
                im = Image.open(os.path.join(sd, f))
                al = im.getchannel("A") if im.mode == "RGBA" else None
                w, h = im.size
                if al is None or al.getpixel((2, 2)) != 0 or al.getpixel((w - 3, h - 3)) != 0 or al.getextrema()[1] != 255:
                    ok_alpha = False
            check("%s: Sprites haben Alpha (Rand transparent, Figur deckend)" % s, ok_alpha)
            a0 = Image.open(os.path.join(sd, "%s-mascot-idle-neutral.png" % s)).convert("RGBA")
            a1 = Image.open(os.path.join(sd, "%s-mascot-flex-happy.png" % s)).convert("RGBA")
            check("%s: Posen sehen verschieden aus" % s, a0.tobytes() != a1.tobytes())
            ov = Image.open(os.path.join(out, s + "-overview.png"))
            check("%s: Overview RGB, 5 Spalten" % s, ov.mode == "RGB" and ov.size[0] == 5 * 192)

        # Icons
        for s in SKINS:
            p = os.path.join(tmp, "icons", "%s-%d.png" % (s, ICON))
            check("%s: Icon vorhanden + Meta" % s, os.path.exists(p) and os.path.exists(p[:-4] + ".meta.json"))
            im = Image.open(p)
            check("%s: Icon %dx%d ohne Alpha" % (s, ICON, ICON), im.size == (ICON, ICON) and im.mode == "RGB", im.mode)
            px = im.load()
            band = max(3, ICON // 50)
            worst = 0
            for i in range(ICON):
                for k in range(band):
                    for (x, y, x2, y2) in ((i, k, i, k + 1), (i, ICON - 1 - k, i, ICON - 2 - k), (k, i, k + 1, i), (ICON - 1 - k, i, ICON - 2 - k, i)):
                        worst = max(worst, max(abs(px[x, y][c] - px[x2, y2][c]) for c in range(3)))
            check("%s: Figur nicht angeschnitten (Randband ist glatter Hintergrund)" % s, worst <= 4, "max Sprung %d" % worst)
            small = im.resize((60, 60), Image.LANCZOS).convert("L")
            bgc = small.getpixel((1, 1))
            diff = sum(1 for v in small.getdata() if abs(v - bgc) > 40)
            check("%s: bei 60 px hebt sich die Figur vom Hintergrund ab" % s, diff > 60 * 60 * 0.25, "%d px" % diff)
        bgs = {s: json.load(open(os.path.join(ROOT, "skins", s + ".json")))["background"] for s in SKINS}
        lum = lambda h: sum(int(h[i:i + 2], 16) for i in (1, 3, 5)) / 3
        check("Shiba-Hintergrund hell, Dobermann-Hintergrund dunkel", lum(bgs["shiba"]["top"]) > 220 and lum(bgs["dobermann"]["top"]) < 70)

        # Character-Dateien
        for s in SKINS:
            c1 = json.load(open(os.path.join(ROOT, "characters", s + ".json")))
            c2 = json.load(open(os.path.join(REPO, "voice-data", "characters", s + ".json")))
            keys = {"id", "name", "description", "persona", "actions", "expressions", "assets", "skeleton", "palette", "icon", "background"}
            check("%s: Character-Schema + Kopie in voice-data" % s, c1 == c2 and keys <= set(c1) and c1["id"] == s and c1["skeleton"] == "fitdogs-v1")
            check("%s: Character-Actions/Ausdruecke = Rig" % s, set(c1["actions"]) == ACTIONS and c1["expressions"] == EXPR)
            check("%s: Platzhalter-Name markiert, ohne Persona" % s, c1.get("placeholder_name") is True and c1["persona"] is None)
            sk = json.load(open(os.path.join(ROOT, "skins", s + ".json")))
            check("%s: Palette stimmt mit Skin-Datei" % s, all(sk["palette"].get(k, c1["palette"][k]) == c1["palette"][k] for k in c1["palette"]) and c1["background"] == sk["background"])
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    if fails:
        print("\n%d ok, %d FEHLER: %s" % (passed, len(fails), ", ".join(fails)))
        sys.exit(1)
    print("\n%d ok" % passed)


if __name__ == "__main__":
    main()
