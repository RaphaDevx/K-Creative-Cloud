#!/usr/bin/env python3
"""Zerlegt den Freisteller eines FitDogs-Skins in 2D-Rig-Teile (2,5D-Rig).

Aufruf:  python3 brand/fitdogs/tools/split_parts.py [--skin shiba|dobermann|all]
Liest   2d/rigs/<skin>.json (Teile, Polygone, Pivots) und den Freisteller.
Schreibt dist/2d/<skin>/cutout.png (Freisteller, Dobermann mit Outline repariert),
         dist/2d/<skin>/parts/<part>.png (RGBA, auf Inhalt beschnitten) und dist/2d/<skin>/parts.json (Offsets).

Teile werden mit weicher, kurzer Kante (Feather) aus dem Freisteller geschnitten. Der Torso bekommt hinter Kopf und
Armen die verdeckten Bereiche per cv2.inpaint aufgefüllt (damit beim Drehen keine Lücke entsteht) und dort eine
Outline-Linie entlang der Körperkante."""
import argparse
import json
from pathlib import Path

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
REF = ROOT / "reference" / "muscle-dogs-reference.jpg"
SKINS = ("shiba", "dobermann")
PAD = 3


def hexbgr(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (4, 2, 0))


def build_cutout(skin):
    """Freisteller aus dem Referenzbild. Shiba: vorhandener Freisteller (dist/ref). Dobermann: dunkle Outline hat fast
    Hintergrundfarbe, die Schwellwert-Maske lässt sie als Loch zurück; hier wird alles, was nicht vom Rand aus
    erreichbar ist, zur Figur gezählt (Zwischenräume zwischen Arm und Körper bleiben offen, weil sie zum Rand führen)."""
    if skin == "shiba":
        return cv2.imread(str(ROOT / "dist" / "ref" / "shiba-cutout.png"), cv2.IMREAD_UNCHANGED)
    ref = cv2.imread(str(REF))
    W = ref.shape[1]
    p = ref[:, W // 2 + 6:]
    h, w = p.shape[:2]
    pb = cv2.GaussianBlur(p, (0, 0), 1.0).astype(np.float32)
    edge = np.concatenate([pb[:, 12:30], pb[:, -30:-12]], axis=1)
    bg = np.repeat(np.median(edge, axis=1)[:, None, :], w, axis=1)
    fg = (np.sqrt(((pb - bg) ** 2).sum(axis=2)) > 38).astype(np.uint8) * 255
    fg = cv2.morphologyEx(fg, cv2.MORPH_CLOSE, np.ones((5, 5), np.uint8))
    n, lab, st, _ = cv2.connectedComponentsWithStats(fg)
    fg = (np.isin(lab, [i for i in range(1, n) if st[i, cv2.CC_STAT_AREA] > 0.004 * h * w]) * 255).astype(np.uint8)
    n, lab, st, _ = cv2.connectedComponentsWithStats(255 - fg)
    outside = np.zeros_like(fg)
    for i in range(1, n):
        x, y, bw, bh, _ = st[i]
        if x == 0 or y == 0 or x + bw == w or y + bh == h:
            outside[lab == i] = 255
    alpha = cv2.GaussianBlur(255 - outside, (0, 0), 0.8)
    ys, xs = np.where(alpha > 20)
    y0, x0 = ys.min() - 1, xs.min() - 1
    return np.dstack([p, alpha])[y0:y0 + 1474, x0:x0 + 1236]


def shape_mask(shapes, size, feather):
    """Polygone/Kreise 2x supersampled rastern, dann weich machen. size = (W, H)."""
    W, H = size
    k = 2
    m = np.zeros((H * k, W * k), np.uint8)
    for s in shapes:
        if "poly" in s:
            cv2.fillPoly(m, [np.round(np.array(s["poly"], np.float32) * k).astype(np.int32)], 255)
        else:
            cx, cy, r = s["circle"]
            cv2.circle(m, (round(cx * k), round(cy * k)), round(r * k), 255, -1)
    m = cv2.resize(m, (W, H), interpolation=cv2.INTER_AREA)
    if feather > 0:
        m = cv2.GaussianBlur(m, (0, 0), feather)
    return m.astype(np.float32) / 255


def offset_edge(edge, tuck, side):
    return [[x + side * tuck, y] for x, y in edge]


def split(skin, out_root):
    rig = json.loads((ROOT / "2d" / "rigs" / f"{skin}.json").read_text())
    skin_json = json.loads((ROOT / "skins" / f"{skin}.json").read_text())
    outline = hexbgr(skin_json.get("outline", {}).get("color", "#1B1A2E"))
    cut = build_cutout(skin)
    H, W = cut.shape[:2]
    assert [W, H] == rig["size"], f"{skin}: Freisteller {W}x{H} passt nicht zum Rig {rig['size']}"
    d = out_root / skin
    (d / "parts").mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(d / "cutout.png"), cut)
    alpha = cut[..., 3].astype(np.float32) / 255
    rgb = cut[..., :3]
    feather = rig.get("feather", 1.2)
    parts = rig["parts"]
    soft = {p["name"]: shape_mask(p["shapes"], (W, H), feather) for p in parts if p["shapes"]}
    hard = {n: (m > 0.5) for n, m in soft.items()}
    others_soft = np.max(np.stack(list(soft.values())), axis=0)
    others_hard = np.any(np.stack(list(hard.values())), axis=0)

    layers = {}
    for p in parts:
        n = p["name"]
        if n in soft:
            layers[n] = (rgb, alpha * soft[n])
            continue
        # Torso: Rest der Figur + hinterfüllte verdeckte Bereiche
        # Torso behält 2 px unter den anderen Teilen (kein Spalt an der weichen Kante)
        known = alpha * (1 - cv2.erode(others_soft, np.ones((5, 5), np.uint8)))
        fill = np.zeros((H, W), np.uint8)
        for b in p["backfill"]:
            if "poly" in b:
                pts = b["poly"]
            else:
                e = b["edge"]
                pts = e + offset_edge(e, b["tuck"], b["side"])[::-1]
            cv2.fillPoly(fill, [np.round(np.array(pts, np.float32)).astype(np.int32)], 255)
        hidden = (fill > 0) & others_hard
        mask = cv2.dilate(hidden.astype(np.uint8) * 255, np.ones((3, 3), np.uint8))
        filled = cv2.inpaint(rgb, mask, 7, cv2.INPAINT_TELEA)
        hid_soft = cv2.GaussianBlur(hidden.astype(np.float32), (0, 0), 1.0)
        a = np.clip(known + hid_soft * (1 - known), 0, 1)
        col = np.where(hidden[..., None], filled, rgb)
        # Körperkante (Outline) entlang der hinterfüllten Seiten
        ov = np.zeros((H * 2, W * 2), np.uint8)
        for s in p.get("strokes", []):
            pts = np.round(np.array(offset_edge(s["edge"], s["tuck"], s["side"]), np.float32) * 2).astype(np.int32)
            cv2.polylines(ov, [pts], False, 255, s["width"] * 2, cv2.LINE_AA)
        ov = cv2.resize(ov, (W, H), interpolation=cv2.INTER_AREA).astype(np.float32) / 255
        ov *= cv2.GaussianBlur(hidden.astype(np.float32), (0, 0), 1.0)
        col = col.astype(np.float32) * (1 - ov[..., None]) + np.array(outline, np.float32) * ov[..., None]
        a = np.maximum(a, ov)
        layers[n] = (np.clip(col, 0, 255).astype(np.uint8), a)

    meta = {"skin": skin, "skeleton": rig["skeleton"], "size": [W, H], "root": rig["root"], "parts": []}
    fig_ys, fig_xs = np.where(alpha > 0.04)
    meta["figure_bbox"] = [int(fig_xs.min()), int(fig_ys.min()), int(fig_xs.max()) + 1, int(fig_ys.max()) + 1]
    for order, p in enumerate(parts):
        n = p["name"]
        c, a = layers[n]
        ys, xs = np.where(a > 0.01)
        assert len(xs) > 500, f"{skin}/{n}: Teil leer"
        x0, x1 = max(xs.min() - PAD, 0), min(xs.max() + 1 + PAD, W)
        y0, y1 = max(ys.min() - PAD, 0), min(ys.max() + 1 + PAD, H)
        img = np.dstack([c[y0:y1, x0:x1], np.round(a[y0:y1, x0:x1] * 255).astype(np.uint8)])
        cv2.imwrite(str(d / "parts" / f"{n}.png"), img)
        meta["parts"].append({"name": n, "parent": p["parent"], "pivot": p["pivot"], "order": order,
                              "file": f"parts/{n}.png", "offset": [int(x0), int(y0)], "size": [int(x1 - x0), int(y1 - y0)]})
    (d / "parts.json").write_text(json.dumps(meta, indent=1))
    print(f"{skin}: {len(parts)} Teile -> {d / 'parts'}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--skin", default="all")
    ap.add_argument("--out", default=str(ROOT / "dist" / "2d"))
    a = ap.parse_args()
    for s in (SKINS if a.skin == "all" else [a.skin]):
        split(s, Path(a.out))


if __name__ == "__main__":
    main()
