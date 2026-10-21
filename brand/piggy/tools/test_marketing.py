#!/usr/bin/env python3
"""
Test der Marketing-Clips (brand/piggy/3d/marketing.py) mit Blender headless in sehr niedriger Qualität.
  python3 brand/piggy/tools/test_marketing.py        # Exit 0 = ok (braucht piggy.blend: bash brand/piggy/build.sh)

Prüft je Aktion: Frames + meta.json entstehen, Bildgrösse passt zum Format, Start- und Mittelframe unterscheiden
sich (Animation bewegt sich wirklich); ausserdem --list, Icon 1024x1024 ohne Alpha mit exakter Token-Farbe und
freiem Rand, --alpha, 30 fps, --visemes, Fehlerfälle. Schreibt nur in ein temporäres Verzeichnis.
Pillow wird für den Bildvergleich gebraucht (Standard auf dem Server).
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time

from PIL import Image, ImageChops

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, ".."))
BLEND = os.path.join(ROOT, "dist", "3d", "piggy.blend")
SCRIPT = os.path.join(ROOT, "3d", "marketing.py")
TOKENS = os.path.join(ROOT, "dist", "tokens", "piggy.resolved.json")
VISEMES = os.path.join(ROOT, "3d", "examples", "visemes.example.json")
SIZE, SAMPLES = 256, 32

fails = []
passed = 0


def check(name, cond, detail=""):
    global passed
    if cond:
        passed += 1
        print("  ok   ", name)
    else:
        fails.append(name)
        print("  FEHLER", name, detail)


def blender(args, timeout=600):
    cmd = ["blender", "-b", BLEND, "--python-exit-code", "1", "-P", SCRIPT, "--"] + args
    return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)


def hex_rgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def expected_size(fmt, w):
    h = {"9x16": w * 16 / 9, "1x1": w, "16x9": w * 9 / 16}[fmt]
    return w, int(round(h / 2.0)) * 2


def main():
    for p in (BLEND, TOKENS):
        if not os.path.exists(p):
            print("fehlt:", p, "- zuerst bash brand/piggy/build.sh")
            return 2
    tokens = json.load(open(TOKENS))
    brand_bg = hex_rgb(tokens["semantic"]["color"]["bg"]["brand"])
    tmp = tempfile.mkdtemp(prefix="piggy-mk-test-")
    t0 = time.time()
    try:
        # --- --list
        r = blender(["--list"])
        rows = [json.loads(l.split("MK_LIST_JSON ", 1)[1]) for l in blender(["--list", "--json"]).stdout.splitlines() if l.startswith("MK_LIST_JSON ")]
        check("--list Exit 0", r.returncode == 0, r.stderr[-300:])
        names = [x["name"] for x in rows[0]] if rows else []
        need = ["hop", "wave", "cheer_jump", "coin_drop", "turntable", "talk_loop"]
        check("--list nennt alle Aktionen", all(n in r.stdout for n in need) and all(n in names for n in need), r.stdout[-400:])
        info = {x["name"]: x for x in rows[0]} if rows else {}

        # --- jede Aktion: 2 Frames (Start, Mitte), abwechselnd Formate
        fmts = {"hop": "9x16", "wave": "1x1", "cheer_jump": "16x9", "coin_drop": "9x16", "turntable": "1x1",
                "talk_loop": "16x9", "idle": "9x16"}
        for act in need + ["idle"]:
            n = info[act]["frames"]
            mid = n // 2
            fmt = fmts[act]
            out = os.path.join(tmp, "clips")
            r = blender(["--action", act, "--format", fmt, "--size", str(SIZE), "--samples", str(SAMPLES),
                         "--frames", "1,%d" % mid, "--out", out])
            d = os.path.join(out, act)
            f1, f2 = os.path.join(d, "frame_0001.png"), os.path.join(d, "frame_%04d.png" % mid)
            ok = r.returncode == 0 and os.path.exists(f1) and os.path.exists(f2) and os.path.exists(os.path.join(d, "meta.json"))
            check("%s: Frames + meta.json" % act, ok, (r.stdout + r.stderr)[-500:])
            if not ok:
                continue
            meta = json.load(open(os.path.join(d, "meta.json")))
            a, b = Image.open(f1), Image.open(f2)
            check("%s: Bildgrösse passt zu %s" % (act, fmt), a.size == expected_size(fmt, SIZE) == b.size, str(a.size))
            check("%s: meta (fps, frames, size, format, engine, samples, Renderzeit)" % act,
                  all(k in meta for k in ("fps", "frames", "size", "format", "engine", "samples", "render_seconds_per_frame"))
                  and meta["engine"] == "CYCLES" and meta["samples"] == SAMPLES and len(meta["render_seconds_per_frame"]) == 2
                  and meta["frames"] == n and meta["size"] == list(a.size) and meta["format"] == fmt, str(meta))
            diff = ImageChops.difference(a.convert("RGB"), b.convert("RGB")).convert("L")
            moved = sum(1 for v in diff.getdata() if v > 24)  # Pixel mit deutlicher Abweichung (Rauschen bleibt darunter)
            check("%s: Start und Mitte unterscheiden sich (%d Pixel)" % (act, moved), moved > 0.002 * a.size[0] * a.size[1])
            # Hintergrund = Brand-Token an den Ecken (kein Alpha)
            check("%s: Hintergrund = Token brand, kein Alpha" % act, a.mode == "RGB" and a.getpixel((0, 0)) == brand_bg, "%s %s" % (a.mode, a.getpixel((0, 0))))

        # --- Icon
        out = os.path.join(tmp, "icon")
        r = blender(["--format", "icon", "--still", "--samples", str(SAMPLES), "--out", out])
        p = os.path.join(out, "icon-1024.png")
        check("icon: Datei entsteht", r.returncode == 0 and os.path.exists(p), (r.stdout + r.stderr)[-500:])
        if os.path.exists(p):
            im = Image.open(p)
            check("icon: 1024x1024", im.size == (1024, 1024), str(im.size))
            check("icon: ohne Alpha", im.mode == "RGB", im.mode)
            bg = hex_rgb(tokens["component"]["appIcon"]["bgFrom"])
            check("icon: Fläche = Token appIcon.bgFrom", im.getpixel((0, 0)) == bg and im.getpixel((1023, 1023)) == bg, str(im.getpixel((0, 0))))
            edge = [im.getpixel((i, j)) for i in range(0, 1024, 8) for j in (0, 1023)] + [im.getpixel((j, i)) for i in range(0, 1024, 8) for j in (0, 1023)]
            check("icon: Rand frei (nichts abgeschnitten)", all(e == bg for e in edge))
            diffbox = ImageChops.difference(im, Image.new("RGB", im.size, bg)).convert("L").point(lambda v: 255 if v > 12 else 0).getbbox()
            fill = max(diffbox[2] - diffbox[0], diffbox[3] - diffbox[1]) / 1024.0 if diffbox else 0
            check("icon: Figur ~70%% (%.2f)" % fill, 0.62 <= fill <= 0.78)

        # --- Alpha, 30 fps, Visemes, Fehlerfälle
        out = os.path.join(tmp, "alpha")
        r = blender(["--action", "hop", "--alpha", "--fps", "30", "--format", "1x1", "--size", "128", "--samples", "8", "--frames", "3-4", "--out", out])
        p = os.path.join(out, "hop", "frame_0003.png")
        m = json.load(open(os.path.join(out, "hop", "meta.json"))) if os.path.exists(os.path.join(out, "hop", "meta.json")) else {}
        check("--alpha: RGBA mit transparenter Ecke", os.path.exists(p) and Image.open(p).mode == "RGBA" and Image.open(p).getpixel((0, 0))[3] == 0, (r.stdout + r.stderr)[-300:])
        check("--fps 30: 24 -> 30 Frames, Teilbereich", m.get("frames") == 30 and m.get("rendered") == [3, 4] and m.get("fps") == 30, str(m))

        out = os.path.join(tmp, "vis")
        r = blender(["--action", "talk_loop", "--visemes", VISEMES, "--format", "1x1", "--size", "128", "--samples", "8",
                     "--frames", "1,6,12", "--bg", "#102030", "--out", out])
        d = os.path.join(out, "talk_loop")
        m = json.load(open(os.path.join(d, "meta.json"))) if os.path.exists(os.path.join(d, "meta.json")) else {}
        check("--visemes: Lauf ok, Clip auf Visem-Länge verlängert", r.returncode == 0 and m.get("visemes") is True and m.get("frames", 0) >= 48, (r.stdout + r.stderr)[-300:])
        if r.returncode == 0:
            a_, b_ = Image.open(os.path.join(d, "frame_0001.png")), Image.open(os.path.join(d, "frame_0006.png"))
            check("--bg #hex: CLI-Farbe", a_.getpixel((0, 0)) == (0x10, 0x20, 0x30), str(a_.getpixel((0, 0))))
            mouth_diff = ImageChops.difference(a_, b_).getbbox()
            check("--visemes: Mund verändert das Bild", mouth_diff is not None)

        bad = tempfile.NamedTemporaryFile("w", suffix=".json", delete=False)
        bad.write('[{"t_start":0,"t_end":1,"viseme":"zzz"}]')
        bad.close()
        r = blender(["--action", "hop", "--visemes", bad.name, "--out", os.path.join(tmp, "bad"), "--samples", "4", "--size", "64"])
        os.unlink(bad.name)
        check("--visemes mit unbekanntem Visem schlägt fehl", r.returncode != 0)
        r = blender(["--action", "gibtsnicht", "--out", os.path.join(tmp, "bad")])
        check("unbekannte Aktion schlägt fehl", r.returncode != 0)
        r = blender(["--action", "hop", "--bg", "nope.token", "--out", os.path.join(tmp, "bad")])
        check("unbekannter --bg-Token schlägt fehl", r.returncode != 0)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    print("\n%d ok, %d Fehler (%.0f s)" % (passed, len(fails), time.time() - t0))
    for f in fails:
        print("  -", f)
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
