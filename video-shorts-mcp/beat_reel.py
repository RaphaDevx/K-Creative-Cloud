"""
beat_reel.py — Erklaer-Reels mit Formeln, Tabellen und Plots (Hochformat 1080x1920).

Warum es das gibt: frame_render.py kennt nur Headline + Untertitel (+ stat_viz). Fuer
Pruefungsstoff mit Rechenbeispielen braucht es Formeln (Mathtext), Tabellen und
schrittweises Aufbauen, das exakt zur Sprache passt.

Modell: Ein Reel besteht aus "Beats". Jeder Beat = ein gesprochener Satz (`say`) plus
Elemente, die ab diesem Beat sichtbar werden (`show`). Elemente mit gleicher `id`
ersetzen frueher gezeigte (z.B. Tabelle mit weiterer Zeile). `clear=True` leert die Buehne.
Dauer eines Beats = TTS-Dauer + Pause, damit Bild und Ton immer synchron sind.

Nutzung (Python-Datei pro Reel, siehe reels/om/*.py):

    from beat_reel import *
    reel = Reel(slug="...", kicker="OPERATIONS MANAGEMENT", accent="#f97316", beats=[
        Beat("Hallo.", [title("Titel"), math(r"x=\\frac{a}{b}")]),
        ...
    ])
    build(reel, out_dir)          # -> mp4, srt, png-Thumbnail

TTS: tts_kokoro.synthesize (Deutsch -> Edge TTS, braucht Internet + edge-tts >= 7.3).
Interpreter: /storage/projekte/ki_pipeline_env_312/bin/python3
"""
from __future__ import annotations

import hashlib
import io
import json
import os
import subprocess
import sys
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from PIL import Image, ImageDraw, ImageFont  # noqa: E402

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

W, H = 1080, 1920
CONTENT_W = 940
TOP = 250          # unterhalb Kopfzeile / Plattform-UI
BOTTOM = 1640      # oberhalb Fortschrittsbalken / Plattform-UI
GAP = 34
PAUSE = 0.35       # Sekunden Stille nach jedem Beat
FPS = 30

FONT_DIR = "/usr/share/fonts/truetype/roboto/unhinted/RobotoTTF/"
F_BLACK = FONT_DIR + "Roboto-Black.ttf"
F_BOLD = FONT_DIR + "Roboto-Bold.ttf"
F_REG = FONT_DIR + "Roboto-Regular.ttf"
if not os.path.exists(F_BLACK):  # Fallback
    F_BLACK = F_BOLD = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
    F_REG = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"

BG = (13, 15, 22)
WHITE = "#f1f1f4"
GRAY = "#9aa0ad"
ORANGE = "#f97316"
GREEN = "#22c55e"
RED = "#ef4444"
BLUE = "#38bdf8"
YELLOW = "#fbbf24"
PANEL = (28, 32, 44)


def _rgb(h: str) -> tuple:
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def _font(path: str, size: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(path, size)


# --------------------------------------------------------------------------- Elemente
@dataclass
class El:
    kind: str
    id: str | None = None
    args: dict = field(default_factory=dict)


def title(text: str, color: str = WHITE, size: int = 110, id: str | None = None) -> El:
    return El("text", id, dict(text=text, color=color, size=size, font=F_BLACK, align="center"))


def text(text: str, color: str = WHITE, size: int = 56, bold: bool = False, align: str = "center",
         id: str | None = None) -> El:
    return El("text", id, dict(text=text, color=color, size=size, font=F_BOLD if bold else F_REG, align=align))


def kicker(text: str, color: str = ORANGE, id: str | None = None) -> El:
    return El("text", id, dict(text=text.upper(), color=color, size=40, font=F_BOLD, align="center", spacing=4))


def math(latex: str, color: str = WHITE, size: int = 88, id: str | None = None) -> El:
    return El("math", id, dict(latex=latex, color=color, size=size))


def table(headers: list[str], rows: list[list], accent: str = ORANGE, hl: dict | None = None,
          row_hl: dict | None = None, size: int = 58, first_col_w: int | None = None, id: str | None = None) -> El:
    """hl: {(row, col): color}; row_hl: {row: color}. Zeilenindex 0 = erste Datenzeile."""
    return El("table", id, dict(headers=headers, rows=rows, accent=accent, hl=hl or {}, row_hl=row_hl or {},
                                size=size, first_col_w=first_col_w))


def callout(text: str, color: str = RED, label: str | None = None, size: int = 52, id: str | None = None) -> El:
    return El("callout", id, dict(text=text, color=color, label=label, size=size))


def plot(draw: Callable, height: int = 620, id: str | None = None) -> El:
    """draw(ax) zeichnet in ein dunkel gestyltes Matplotlib-Axes."""
    return El("plot", id, dict(draw=draw, height=height))


def spacer(h: int = 30) -> El:
    return El("spacer", None, dict(h=h))


@dataclass
class Beat:
    say: str
    show: list = field(default_factory=list)
    clear: bool = False


@dataclass
class Reel:
    slug: str
    beats: list
    kicker: str = "OPERATIONS MANAGEMENT"
    accent: str = ORANGE
    brand: str = "K-Learning  ·  HSG"


# --------------------------------------------------------------------------- Rendering der Elemente
def _wrap(draw, txt, font, max_w, spacing=0):
    out = []
    for para in txt.split("\n"):
        cur = []
        for word in para.split():
            test = " ".join(cur + [word])
            if draw.textlength(test, font=font) > max_w and cur:
                out.append(" ".join(cur))
                cur = [word]
            else:
                cur.append(word)
        out.append(" ".join(cur))
    return out


def _render_text(a, width):
    size = a["size"]
    font = _font(a["font"], size)
    dummy = ImageDraw.Draw(Image.new("RGB", (4, 4)))
    lines = _wrap(dummy, a["text"], font, width)
    lh = int(size * 1.22)
    img = Image.new("RGBA", (width, lh * len(lines) + 8), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    for i, line in enumerate(lines):
        tw = d.textlength(line, font=font)
        x = (width - tw) / 2 if a["align"] == "center" else 0
        d.text((x, i * lh), line, font=font, fill=_rgb(a["color"]) + (255,))
    return img


_math_cache: dict = {}


def _render_math(a, width):
    key = (a["latex"], a["color"], a["size"])
    if key in _math_cache:
        img = _math_cache[key]
    else:
        fig = plt.figure(figsize=(1, 1), dpi=200)
        fig.patch.set_alpha(0)
        fig.text(0, 0, f"${a['latex']}$", fontsize=a["size"] * 72 / 200,
                 color=a["color"])
        buf = io.BytesIO()
        fig.savefig(buf, format="png", dpi=200, transparent=True, bbox_inches="tight", pad_inches=0.04)
        plt.close(fig)
        buf.seek(0)
        img = Image.open(buf).convert("RGBA")
        _math_cache[key] = img
    if img.width > width:
        img = img.resize((width, int(img.height * width / img.width)), Image.LANCZOS)
    return img


def _render_table(a, width):
    size = a["size"]
    headers, rows = a["headers"], a["rows"]
    ncol = len(headers)
    dummy = ImageDraw.Draw(Image.new("RGB", (4, 4)))
    while True:
        fh, fb = _font(F_BOLD, size), _font(F_REG, size)
        pad = int(size * 0.5)
        colw = []
        for c in range(ncol):
            cells = [str(headers[c])] + [str(r[c]) for r in rows]
            w = max(dummy.textlength(t, font=fh if i == 0 else fb) for i, t in enumerate(cells))
            colw.append(int(w) + 2 * pad)
        if a["first_col_w"]:
            colw[0] = max(colw[0], a["first_col_w"])
        if sum(colw) <= width or size <= 24:
            break
        size -= 2
    total = sum(colw)
    rh = int(size * 1.9)
    img = Image.new("RGBA", (total, rh * (len(rows) + 1)), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    acc = _rgb(a["accent"])
    d.rounded_rectangle([0, 0, total - 1, rh * (len(rows) + 1) - 1], radius=18, fill=PANEL + (255,))
    d.rounded_rectangle([0, 0, total - 1, rh], radius=18, fill=acc + (255,))
    d.rectangle([0, rh // 2, total - 1, rh], fill=acc + (255,))
    for r in range(len(rows)):
        y = rh * (r + 1)
        if r in a["row_hl"]:
            d.rectangle([0, y, total - 1, y + rh], fill=_rgb(a["row_hl"][r]) + (70,))
        d.line([(0, y), (total, y)], fill=(60, 66, 84, 255), width=2)
    x = 0
    for c in range(ncol):
        tw = d.textlength(str(headers[c]), font=fh)
        d.text((x + (colw[c] - tw) / 2, (rh - size * 1.2) / 2), str(headers[c]), font=fh, fill=(15, 15, 20, 255))
        for r, row in enumerate(rows):
            y = rh * (r + 1)
            cell = str(row[c])
            if (r, c) in a["hl"]:
                d.rounded_rectangle([x + 6, y + 8, x + colw[c] - 6, y + rh - 8], radius=12,
                                    fill=_rgb(a["hl"][(r, c)]) + (255,))
                col = (15, 15, 20, 255)
                f = fh
            else:
                col = _rgb(WHITE) + (255,)
                f = fb
            tw = d.textlength(cell, font=f)
            d.text((x + (colw[c] - tw) / 2, y + (rh - size * 1.2) / 2), cell, font=f, fill=col)
        x += colw[c]
    return img


def _render_callout(a, width):
    size = a["size"]
    font = _font(F_BOLD, size)
    lab_font = _font(F_BLACK, int(size * 0.8))
    dummy = ImageDraw.Draw(Image.new("RGB", (4, 4)))
    pad = 30
    lines = _wrap(dummy, a["text"], font, width - 2 * pad - 14)
    lh = int(size * 1.25)
    lab_h = int(size * 1.15) if a["label"] else 0
    h = pad * 2 + lab_h + lh * len(lines)
    img = Image.new("RGBA", (width, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    col = _rgb(a["color"])
    d.rounded_rectangle([0, 0, width - 1, h - 1], radius=20, fill=col + (40,), outline=col + (255,), width=3)
    d.rounded_rectangle([0, 0, 14, h - 1], radius=7, fill=col + (255,))
    y = pad
    if a["label"]:
        d.text((pad + 14, y), a["label"].upper(), font=lab_font, fill=col + (255,))
        y += lab_h
    for line in lines:
        d.text((pad + 14, y), line, font=font, fill=_rgb(WHITE) + (255,))
        y += lh
    return img


def _render_plot(a, width):
    h = a["height"]
    dpi = 200
    fig, ax = plt.subplots(figsize=(width / dpi, h / dpi), dpi=dpi)
    fig.patch.set_facecolor("#1c202c")
    ax.set_facecolor("#1c202c")
    for s in ax.spines.values():
        s.set_color("#4a5066")
    ax.tick_params(colors="#c9ccd6", labelsize=9)
    ax.xaxis.label.set_color("#c9ccd6")
    ax.yaxis.label.set_color("#c9ccd6")
    ax.grid(color="#2c3242", linewidth=0.6)
    a["draw"](ax)
    fig.tight_layout(pad=0.6)
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=dpi, facecolor=fig.get_facecolor())
    plt.close(fig)
    buf.seek(0)
    img = Image.open(buf).convert("RGBA")
    # abgerundete Ecken
    mask = Image.new("L", img.size, 0)
    ImageDraw.Draw(mask).rounded_rectangle([0, 0, img.width - 1, img.height - 1], radius=22, fill=255)
    img.putalpha(mask)
    return img


def render_element(el: El, width: int = CONTENT_W) -> Image.Image:
    if el.kind == "text":
        return _render_text(el.args, width)
    if el.kind == "math":
        return _render_math(el.args, width)
    if el.kind == "table":
        return _render_table(el.args, width)
    if el.kind == "callout":
        return _render_callout(el.args, width)
    if el.kind == "plot":
        return _render_plot(el.args, width)
    if el.kind == "spacer":
        return Image.new("RGBA", (width, el.args["h"]), (0, 0, 0, 0))
    raise ValueError(el.kind)


# --------------------------------------------------------------------------- Frame
def render_frame(stage: list, reel: Reel, idx: int, total: int, path: str) -> None:
    acc = _rgb(reel.accent)
    img = Image.new("RGBA", (W, H), BG + (255,))
    glow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    gd = ImageDraw.Draw(glow)
    for r in range(520, 0, -20):
        gd.ellipse([W // 2 - r * 2, -r, W // 2 + r * 2, r], fill=acc + (int(18 * (1 - r / 520)),))
    img.alpha_composite(glow)
    d = ImageDraw.Draw(img)
    d.rectangle([0, 0, W, 8], fill=acc + (255,))
    kf = _font(F_BOLD, 34)
    kw = d.textlength(reel.kicker, font=kf)
    d.text(((W - kw) / 2, 92), reel.kicker, font=kf, fill=acc + (255,))

    imgs = [render_element(e) for e in stage]
    total_h = sum(i.height for i in imgs) + GAP * (len(imgs) - 1)
    avail = BOTTOM - TOP
    scale = min(1.0, avail / total_h) if total_h else 1.0
    if scale < 1.0:
        imgs = [i.resize((max(1, int(i.width * scale)), max(1, int(i.height * scale))), Image.LANCZOS) for i in imgs]
        total_h = int(total_h * scale)
    y = TOP + max(0, (avail - total_h) // 2)
    for i in imgs:
        img.alpha_composite(i, ((W - i.width) // 2, int(y)))
        y += i.height + GAP * scale

    # Fortschritt + Brand
    bar_y = H - 120
    d.rectangle([60, bar_y, W - 60, bar_y + 8], fill=(40, 44, 58, 255))
    d.rectangle([60, bar_y, 60 + int((W - 120) * (idx + 1) / total), bar_y + 8], fill=acc + (255,))
    bf = _font(F_REG, 30)
    bw = d.textlength(reel.brand, font=bf)
    d.text(((W - bw) / 2, bar_y + 28), reel.brand, font=bf, fill=_rgb(GRAY) + (255,))
    img.convert("RGB").save(path, "PNG")


# --------------------------------------------------------------------------- Build
def _tts(text_: str, cache_dir: Path) -> tuple[str, float]:
    from tts_kokoro import synthesize  # lazy: braucht Kokoro/edge-tts nur beim Bauen
    key = hashlib.sha1(("de|" + text_).encode()).hexdigest()[:16]
    wav = cache_dir / f"{key}.wav"
    meta = cache_dir / f"{key}.json"
    if wav.exists() and meta.exists():
        return str(wav), json.loads(meta.read_text())["dur"]
    dur = synthesize(text_, str(wav), lang="de")
    meta.write_text(json.dumps({"dur": dur}))
    return str(wav), dur


def _run(cmd):
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(f"{' '.join(cmd[:3])} failed:\n{r.stderr[-1500:]}")


def _fmt_srt(t: float) -> str:
    ms = int(round(t * 1000))
    return f"{ms // 3600000:02d}:{ms // 60000 % 60:02d}:{ms // 1000 % 60:02d},{ms % 1000:03d}"


def build(reel: Reel, out_dir: str | Path, cache_dir: str | Path | None = None, keep_frames: bool = False) -> dict:
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    cache_dir = Path(cache_dir or out_dir / ".tts_cache")
    cache_dir.mkdir(parents=True, exist_ok=True)
    work = Path(tempfile.mkdtemp(prefix="beatreel_"))

    stage: list[El] = []
    clips, srt, t = [], [], 0.0
    last_frame = None
    n = len(reel.beats)
    for i, b in enumerate(reel.beats):
        if b.clear:
            stage = []
        for el in b.show:
            if el.id is not None:
                stage = [e if e.id != el.id else el for e in stage]
                if not any(e.id == el.id for e in stage):
                    stage.append(el)
            else:
                stage.append(el)
        wav, dur = _tts(b.say, cache_dir)
        frame = work / f"f{i:03d}.png"
        render_frame(stage, reel, i, n, str(frame))
        last_frame = frame
        clip = work / f"c{i:03d}.mp4"
        total = dur + PAUSE
        _run(["ffmpeg", "-y", "-loop", "1", "-framerate", str(FPS), "-i", str(frame), "-i", wav,
              "-af", f"apad=pad_dur={PAUSE},aresample=44100", "-ac", "2",
              "-t", f"{total:.3f}", "-c:v", "libx264", "-tune", "stillimage", "-pix_fmt", "yuv420p",
              "-r", str(FPS), "-c:a", "aac", "-b:a", "160k", str(clip)])
        clips.append(clip)
        srt.append((t, t + dur, b.say))
        t += total

    lst = work / "list.txt"
    lst.write_text("".join(f"file '{c}'\n" for c in clips))
    mp4 = out_dir / f"{reel.slug}.mp4"
    _run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(lst), "-c:v", "libx264", "-crf", "20",
          "-preset", "medium", "-pix_fmt", "yuv420p", "-af", "loudnorm=I=-16:TP=-1.5:LRA=11", "-ar", "44100", "-c:a", "aac", "-b:a", "160k", "-movflags", "+faststart",
          str(mp4)])
    (out_dir / f"{reel.slug}.srt").write_text(
        "".join(f"{k + 1}\n{_fmt_srt(a)} --> {_fmt_srt(b_)}\n{txt}\n\n" for k, (a, b_, txt) in enumerate(srt)))
    thumb = out_dir / f"{reel.slug}.png"
    Image.open(last_frame).save(thumb)
    if keep_frames:
        fr = out_dir / f"{reel.slug}_frames"
        fr.mkdir(exist_ok=True)
        for f in work.glob("f*.png"):
            f.replace(fr / f.name)
    return dict(mp4=str(mp4), srt=str(out_dir / f"{reel.slug}.srt"), thumb=str(thumb), duration_s=round(t, 1),
                beats=n, words=sum(len(b.say.split()) for b in reel.beats))
