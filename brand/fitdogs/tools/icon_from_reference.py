#!/usr/bin/env python3
"""App-Icons 1:1 aus dem Referenzbild (reference/muscle-dogs-reference.jpg): Figur freistellen, auf Skin-Hintergrund setzen.
Aufruf: python3 brand/fitdogs/tools/icon_from_reference.py [--size 1024] [--margin 0.06]
Schreibt dist/icons/<skin>-1024.png (RGB) + dist/ref/<skin>-cutout.png (RGBA, Freisteller)."""
import argparse, json
from pathlib import Path
import cv2
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
REF = ROOT / "reference" / "muscle-dogs-reference.jpg"


def hexrgb(h):
    h = h.lstrip("#")
    return np.array([int(h[i:i + 2], 16) for i in (0, 2, 4)], np.float32)


def cutout(panel, white_bg):
    """Figur + Outline/Aura vom Hintergrund trennen: Farbabstand zum (Verlaufs-)Hintergrund, grösste Fläche, Löcher innen füllen."""
    h, w = panel.shape[:2]
    p = cv2.GaussianBlur(panel, (0, 0), 1.0).astype(np.float32)
    if white_bg:
        bg = np.full_like(p, 255.0)
        thr = 22
    else:
        edge = np.concatenate([p[:, 12:30], p[:, -30:-12]], axis=1)  # Hintergrund je Zeile aus den Rändern schätzen
        row = np.median(edge, axis=1)
        bg = np.repeat(row[:, None, :], w, axis=1)
        thr = 38
    fg = (np.sqrt(((p - bg) ** 2).sum(axis=2)) > thr).astype(np.uint8) * 255
    fg = cv2.morphologyEx(fg, cv2.MORPH_CLOSE, np.ones((5, 5), np.uint8))
    n, lab, stats, _ = cv2.connectedComponentsWithStats(fg)
    big = [i for i in range(1, n) if stats[i, cv2.CC_STAT_AREA] > 0.004 * h * w]  # alle grossen Teile (Kopf, Körper), Rauschen weg
    fg = (np.isin(lab, big) * 255).astype(np.uint8)
    # Löcher füllen, die nicht mit dem Rand verbunden sind (kleine Lücken; grosse Zwischenräume zwischen Arm und Körper bleiben offen)
    inv = 255 - fg
    n, lab, stats, _ = cv2.connectedComponentsWithStats(inv)
    for i in range(1, n):
        x, y, bw, bh, area = stats[i]
        touches = x == 0 or y == 0 or x + bw == w or y + bh == h
        if not touches and area < 6000:
            fg[lab == i] = 255
    return cv2.GaussianBlur(fg, (0, 0), 0.8)


def background(size, bg):
    top, bot = hexrgb(bg["top"]), hexrgb(bg["bottom"])
    t = np.linspace(0, 1, size, dtype=np.float32)[:, None, None]
    img = top * (1 - t) + bot * t
    img = np.repeat(img, size, axis=1)
    gs = float(bg.get("glow_strength", 0))
    if gs > 0:
        cx, cy = bg.get("glow_center", [0.5, 0.5])
        yy, xx = np.mgrid[0:size, 0:size].astype(np.float32) / size
        d = np.sqrt((xx - cx) ** 2 + (yy - cy) ** 2)
        k = np.clip(1 - d / 0.6, 0, 1)[..., None] ** 2 * gs
        img = img * (1 - k) + hexrgb(bg["glow"]) * k
    return img


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--size", type=int, default=1024)
    ap.add_argument("--margin", type=float, default=0.06)
    a = ap.parse_args()
    ref = cv2.imread(str(REF))
    H, W = ref.shape[:2]
    panels = {"shiba": (ref[:, : W // 2], True), "dobermann": (ref[:, W // 2 + 6:], False)}
    (ROOT / "dist" / "icons").mkdir(parents=True, exist_ok=True)
    (ROOT / "dist" / "ref").mkdir(parents=True, exist_ok=True)
    for skin, (panel, white) in panels.items():
        alpha = cutout(panel, white)
        ys, xs = np.where(alpha > 20)
        y0, y1, x0, x1 = ys.min(), ys.max() + 1, xs.min(), xs.max() + 1
        rgba = np.dstack([panel, alpha])[y0:y1, x0:x1]
        cv2.imwrite(str(ROOT / "dist" / "ref" / f"{skin}-cutout.png"), rgba)
        bg = json.loads((ROOT / "skins" / f"{skin}.json").read_text())["background"]
        S = a.size
        box = S * (1 - 2 * a.margin)
        sc = box / max(rgba.shape[:2])
        fig = cv2.resize(rgba, (round(rgba.shape[1] * sc), round(rgba.shape[0] * sc)), interpolation=cv2.INTER_AREA)
        img = background(S, bg)
        oy, ox = (S - fig.shape[0]) // 2, (S - fig.shape[1]) // 2
        al = fig[..., 3:4].astype(np.float32) / 255
        roi = img[oy:oy + fig.shape[0], ox:ox + fig.shape[1]]
        roi[:] = roi * (1 - al) + fig[..., 2::-1].astype(np.float32) * al
        out = ROOT / "dist" / "icons" / f"{skin}-1024.png"
        if out.exists() and not (ROOT / "dist" / "icons" / f"{skin}-3d.png").exists():
            out.rename(out.with_name(f"{skin}-3d.png"))  # alte Blender-Variante behalten
        cv2.imwrite(str(out), np.clip(img, 0, 255).astype(np.uint8)[..., ::-1])
        print(skin, out, "Figur", fig.shape[1], "x", fig.shape[0])


if __name__ == "__main__":
    main()
