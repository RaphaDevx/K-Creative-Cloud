#!/usr/bin/env python3
"""Rendert die FitDogs (2,5D-Rig aus der Zeichnung) als PNG-Sequenzen. Rein lokal: OpenCV + NumPy.

Aufruf:
  python3 brand/fitdogs/2d/render_2d.py --skin shiba|dobermann|all --action idle|hop|wave|flex|talk|all \
      [--size 1080] [--bg transparent|skin] [--fps 24] [--sheet] --out brand/fitdogs/dist/2d
  python3 brand/fitdogs/2d/render_2d.py --skin all --still pose_flex --out brand/fitdogs/dist/2d

Ausgabe: <out>/<skin>/<action>/frame_0001.png ... (RGBA, 2x Supersampling) + meta.json (+ sheet.png mit --sheet);
         --still: <out>/<skin>/stills/<pose>.png. Frame 1 ist die Ruhepose; bei Loops folgt nach dem letzten Frame wieder Frame 1.
Das Bild ist für alle Aktionen eines Skins gleich eingepasst (Vereinigung aller Posen + Rand), die Figur bleibt im Bild.
Teile fehlen? Dann werden sie mit tools/split_parts.py erzeugt."""
import argparse
import json
import math
import sys
from pathlib import Path

import cv2
import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT / "tools"))
SKINS = ("shiba", "dobermann")
ACTIONS = ("idle", "hop", "wave", "flex", "talk")
CH = ("rot", "tx", "ty", "sx", "sy")
DEFAULT = {"rot": 0.0, "tx": 0.0, "ty": 0.0, "sx": 1.0, "sy": 1.0}
MARGIN = 0.05


# ---------------------------------------------------------------- Animation
def ease(kind, u):
    if kind == "hold":
        return 0.0
    if kind == "in":
        return u * u
    if kind == "out":
        return 1 - (1 - u) ** 2
    if kind == "inout":
        return u * u * (3 - 2 * u)
    if kind == "out_back":
        c1 = 1.2
        c3 = c1 + 1
        return 1 + c3 * (u - 1) ** 3 + c1 * (u - 1) ** 2
    return u


def eval_track(keys, t):
    if t <= keys[0][0]:
        return keys[0][1]
    for a, b in zip(keys, keys[1:]):
        if t < b[0]:
            u = (t - a[0]) / (b[0] - a[0])
            return a[1] + (b[1] - a[1]) * ease(a[2] if len(a) > 2 else "linear", u)
    return keys[-1][1]


def pose_at(anims, action, t):
    tracks = anims["actions"][action]["tracks"]
    return {part: {c: eval_track(ch[c], t) if c in ch else DEFAULT[c] for c in CH} for part, ch in tracks.items()}


def static_pose(anims, name):
    return {part: {c: ch.get(c, DEFAULT[c]) for c in CH} for part, ch in anims["poses"][name].items()}


# ---------------------------------------------------------------- Rig
def mat_t(x, y):
    return np.array([[1, 0, x], [0, 1, y], [0, 0, 1]], np.float64)


def mat_local(pivot, st, fh):
    a = math.radians(st["rot"])
    c, s = math.cos(a), math.sin(a)
    r = np.array([[c, -s, 0], [s, c, 0], [0, 0, 1]], np.float64)
    sc = np.diag([st["sx"], st["sy"], 1.0])
    return mat_t(pivot[0] + st["tx"] * fh, pivot[1] + st["ty"] * fh) @ r @ sc @ mat_t(-pivot[0], -pivot[1])


class Rig:
    def __init__(self, skin, parts_root):
        self.skin = skin
        d = parts_root / skin
        if not (d / "parts.json").exists():
            import split_parts
            split_parts.split(skin, parts_root)
        self.meta = json.loads((d / "parts.json").read_text())
        self.fh = self.meta["figure_bbox"][3] - self.meta["figure_bbox"][1]
        self.parts = []
        for p in self.meta["parts"]:
            img = cv2.imread(str(d / p["file"]), cv2.IMREAD_UNCHANGED).astype(np.float32) / 255
            ys, xs = np.where(img[..., 3] > 0.02)
            img[..., :3] *= img[..., 3:4]  # premultiplied: keine Säume beim Drehen/Skalieren
            self.parts.append({**p, "img": img, "abox": (xs.min(), ys.min(), xs.max() + 1, ys.max() + 1)})
        self.root_pivot = self.meta["root"]["pivot"]
        self.cutout = cv2.imread(str(d / "cutout.png"), cv2.IMREAD_UNCHANGED)
        self.skin_json = json.loads((ROOT / "skins" / f"{skin}.json").read_text())

    def world(self, pose):
        w = {"root": mat_local(self.root_pivot, {**DEFAULT, **pose.get("root", {})}, self.fh)}
        for p in self.parts:  # Eltern stehen vor Kindern
            st = {**DEFAULT, **pose.get(p["name"], {})}
            w[p["name"]] = w[p["parent"]] @ mat_local(p["pivot"], st, self.fh)
        return w

    def bbox(self, pose):
        w = self.world(pose)
        pts = []
        for p in self.parts:
            ox, oy = p["offset"]
            bx0, by0, bx1, by1 = p["abox"]
            c = np.array([[ox + bx0, oy + by0, 1], [ox + bx1, oy + by0, 1],
                          [ox + bx1, oy + by1, 1], [ox + bx0, oy + by1, 1]], np.float64)
            pts.append((w[p["name"]] @ c.T)[:2].T)
        pts = np.concatenate(pts)
        return pts[:, 0].min(), pts[:, 1].min(), pts[:, 0].max(), pts[:, 1].max()


def union_bbox(rig, anims, fps):
    boxes = [rig.bbox(static_pose(anims, n)) for n in anims["poses"]]
    for name, act in anims["actions"].items():
        n = max(2, round(act["duration"] * 48))
        for i in range(n + 1):
            boxes.append(rig.bbox(pose_at(anims, name, act["duration"] * i / n)))
    b = np.array(boxes)
    return b[:, 0].min(), b[:, 1].min(), b[:, 2].max(), b[:, 3].max()


def framing(rig, anims, fps, size):
    x0, y0, x1, y1 = union_bbox(rig, anims, fps)
    s = size * (1 - 2 * MARGIN) / max(x1 - x0, y1 - y0)
    return {"scale": s, "ox": (size - (x1 - x0) * s) / 2 - x0 * s, "oy": (size - (y1 - y0) * s) / 2 - y0 * s,
            "bbox": [float(x0), float(y0), float(x1), float(y1)]}


# ---------------------------------------------------------------- Rendern
def render_pose(rig, pose, fr, size, ss=2):
    S = size * ss
    k = fr["scale"] * ss
    cam = np.array([[k, 0, fr["ox"] * ss], [0, k, fr["oy"] * ss], [0, 0, 1]], np.float64)
    w = rig.world(pose)
    canvas = np.zeros((S, S, 4), np.float32)
    for p in rig.parts:
        m = cam @ w[p["name"]] @ mat_t(*p["offset"])
        sw, sh = p["size"]
        c = (m @ np.array([[0, 0, 1], [sw, 0, 1], [sw, sh, 1], [0, sh, 1]], np.float64).T)[:2].T
        x0, y0 = max(int(math.floor(c[:, 0].min())) - 1, 0), max(int(math.floor(c[:, 1].min())) - 1, 0)
        x1, y1 = min(int(math.ceil(c[:, 0].max())) + 1, S), min(int(math.ceil(c[:, 1].max())) + 1, S)
        if x1 <= x0 or y1 <= y0:
            continue
        a = (mat_t(-x0, -y0) @ m)[:2]
        src = cv2.warpAffine(p["img"], a, (x1 - x0, y1 - y0), flags=cv2.INTER_LINEAR,
                             borderMode=cv2.BORDER_CONSTANT, borderValue=(0, 0, 0, 0))
        roi = canvas[y0:y1, x0:x1]
        roi[:] = src + roi * (1 - src[..., 3:4])
    out = cv2.resize(canvas, (size, size), interpolation=cv2.INTER_AREA) if ss > 1 else canvas
    return out  # premultiplied BGRA float


def skin_background(size, bg):
    def hexbgr(h):
        h = h.lstrip("#")
        return np.array([int(h[i:i + 2], 16) for i in (4, 2, 0)], np.float32)
    top, bot = hexbgr(bg["top"]), hexbgr(bg["bottom"])
    t = np.linspace(0, 1, size, dtype=np.float32)[:, None, None]
    img = np.repeat(top * (1 - t) + bot * t, size, axis=1)
    gs = float(bg.get("glow_strength", 0))
    if gs > 0:
        cx, cy = bg.get("glow_center", [0.5, 0.5])
        yy, xx = np.mgrid[0:size, 0:size].astype(np.float32) / size
        k = np.clip(1 - np.sqrt((xx - cx) ** 2 + (yy - cy) ** 2) / 0.6, 0, 1)[..., None] ** 2 * gs
        img = img * (1 - k) + hexbgr(bg["glow"]) * k
    return img


def to_png(premul, bg_img=None):
    a = premul[..., 3:4]
    if bg_img is not None:
        rgb = premul[..., :3] + bg_img * (1 - a)
        return np.dstack([np.clip(rgb, 0, 1) * 255, np.full(a.shape[:2], 255.0)]).round().astype(np.uint8)
    rgb = np.where(a > 1e-4, premul[..., :3] / np.maximum(a, 1e-4), 0)
    return np.dstack([np.clip(rgb, 0, 1) * 255, np.clip(a[..., 0], 0, 1) * 255]).round().astype(np.uint8)


def sheet(frames, path, bg_img, thumb=300, cols=6, count=12):
    idx = np.linspace(0, len(frames) - 1, min(count, len(frames))).round().astype(int)
    rows = math.ceil(len(idx) / cols)
    sh = np.full((rows * thumb, cols * thumb, 3), 235, np.uint8)
    yy, xx = np.mgrid[0:rows * thumb, 0:cols * thumb]
    sh[((yy // 20 + xx // 20) % 2) == 0] = 250
    for n, i in enumerate(idx):
        f = cv2.resize(frames[i], (thumb, thumb), interpolation=cv2.INTER_AREA).astype(np.float32)
        a = f[..., 3:4] / 255
        r, c = divmod(n, cols)
        roi = sh[r * thumb:(r + 1) * thumb, c * thumb:(c + 1) * thumb].astype(np.float32)
        sh[r * thumb:(r + 1) * thumb, c * thumb:(c + 1) * thumb] = (f[..., :3] * a + roi * (1 - a)).astype(np.uint8)
        cv2.putText(sh, f"{i + 1}", (c * thumb + 6, r * thumb + 18), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (60, 60, 60), 1, cv2.LINE_AA)
    cv2.imwrite(str(path), sh)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--skin", default="all")
    ap.add_argument("--action", default="all", help="idle|hop|wave|flex|talk|all")
    ap.add_argument("--still", help="Einzelpose aus anims.json (pose_idle|pose_flex|pose_wave)")
    ap.add_argument("--size", type=int, default=1080)
    ap.add_argument("--bg", choices=("transparent", "skin"), default="transparent")
    ap.add_argument("--fps", type=int, default=24)
    ap.add_argument("--sheet", action="store_true", help="Kontaktbogen sheet.png je Aktion")
    ap.add_argument("--out", default=str(ROOT / "dist" / "2d"))
    ap.add_argument("--parts", default=str(ROOT / "dist" / "2d"), help="Ordner mit den Teilen (split_parts.py)")
    a = ap.parse_args()
    anims = json.loads((HERE / "anims.json").read_text())
    out = Path(a.out)
    skins = SKINS if a.skin == "all" else (a.skin,)
    actions = ACTIONS if a.action == "all" else (a.action,)
    for skin in skins:
        rig = Rig(skin, Path(a.parts))
        fr = framing(rig, anims, a.fps, a.size)
        bg_img = skin_background(a.size, rig.skin_json["background"]) / 255 if a.bg == "skin" else None
        if a.still:
            png = to_png(render_pose(rig, static_pose(anims, a.still), fr, a.size), bg_img)
            d = out / skin / "stills"
            d.mkdir(parents=True, exist_ok=True)
            cv2.imwrite(str(d / f"{a.still}.png"), png)
            print(f"{skin}: {d / (a.still + '.png')}")
            continue
        for action in actions:
            act = anims["actions"][action]
            n = max(1, round(act["duration"] * a.fps))
            d = out / skin / action
            d.mkdir(parents=True, exist_ok=True)
            for old in d.glob("frame_*.png"):
                old.unlink()
            frames = []
            for i in range(n):
                png = to_png(render_pose(rig, pose_at(anims, action, i / a.fps), fr, a.size), bg_img)
                cv2.imwrite(str(d / f"frame_{i + 1:04d}.png"), png)
                frames.append(png)
            meta = {"skin": skin, "action": action, "skeleton": anims["skeleton"], "fps": a.fps, "frames": n,
                    "duration": n / a.fps, "loop": bool(act.get("loop")), "size": [a.size, a.size], "bg": a.bg,
                    "frame_pattern": "frame_%04d.png", "framing": fr}
            (d / "meta.json").write_text(json.dumps(meta, indent=1))
            if a.sheet:
                sheet(frames, d / "sheet.png", bg_img)
            print(f"{skin}/{action}: {n} Frames -> {d}")


if __name__ == "__main__":
    main()
