#!/usr/bin/env python3
"""Compositing für Piggy-Marketing-Videos (rein lokal: ffmpeg + Pillow).

Setzt aus einem Briefing (YAML/JSON) Szenen zusammen:
  kind: piggy  Piggy-PNG-Sequenz (Alpha, aus marketing.py) auf Brand-Hintergrund
  kind: app    Simulator-Aufnahme im Geräterahmen, optional mit kleinem Piggy-Overlay
Stimme kommt aus voice.synthesize (Persona) oder aus einer vorhandenen WAV (`audio:`).
Untertitel werden gebrannt (ASS) und als SRT ausgegeben; Musik optional mit Ducking.

Aufruf:  python3 brand/piggy/3d/compose.py briefing.yaml --out <dir> [--music f.mp3] [--no-synth]
Briefing-Felder: name, format (9x16|1x1|16x9), persona|channel, bg (#hex), fps, scenes[].
Szene: kind, say, audio, seconds (nur ohne Stimme), pad (Sekunden Nachlauf, Standard 0.4),
       piggy: Ordner mit frame_####.png (kind piggy: Pflicht, kind app: Overlay optional),
       video: Simulator-Aufnahme (kind app).
Untertitel-Zeiten sind proportional zur Zeichenzahl verteilt, nicht per Spracherkennung ausgerichtet.
"""
import argparse
import json
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from PIL import Image, ImageDraw

REPO = Path(__file__).resolve().parents[3]
FORMATS = {"9x16": (1080, 1920), "1x1": (1080, 1080), "16x9": (1920, 1080)}
DEFAULT_BG = "#FFF0F4"
WORDS_PER_CUE = 4


def run(cmd):
    r = subprocess.run([str(c) for c in cmd], capture_output=True, text=True)
    if r.returncode:
        sys.exit(f"ffmpeg/ffprobe fehlgeschlagen: {' '.join(map(str, cmd))[:200]}\n{r.stderr[-1500:]}")
    return r.stdout


def probe_duration(path):
    return float(run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", path]).strip())


def load_briefing(p):
    txt = Path(p).read_text(encoding="utf-8")
    if str(p).endswith(".json"):
        return json.loads(txt)
    import yaml
    return yaml.safe_load(txt)


def make_bezel(path, sw, sh, border=22, radius=70):
    """Geräterahmen als PNG mit transparentem Bildschirm-Ausschnitt (abgerundet) und Dynamic Island."""
    W, H = sw + 2 * border, sh + 2 * border
    k = 2  # Supersampling für glatte Kanten
    big = Image.new("RGBA", (W * k, H * k), (0, 0, 0, 0))
    d = ImageDraw.Draw(big)
    d.rounded_rectangle([0, 0, W * k - 1, H * k - 1], radius=(radius + border) * k, fill=(24, 24, 28, 255))
    hole = Image.new("L", big.size, 0)
    ImageDraw.Draw(hole).rounded_rectangle([border * k, border * k, (border + sw) * k - 1, (border + sh) * k - 1],
                                           radius=radius * k, fill=255)
    alpha = big.getchannel("A")
    alpha = Image.composite(Image.new("L", big.size, 0), alpha, hole)
    big.putalpha(alpha)
    d = ImageDraw.Draw(big)
    iw, ih = int(sw * 0.28), int(sw * 0.075)
    cx, top = W * k // 2, (border + int(sw * 0.025)) * k
    d.rounded_rectangle([cx - iw * k // 2, top, cx + iw * k // 2, top + ih * k], radius=ih * k // 2, fill=(0, 0, 0, 255))
    big.resize((W, H), Image.LANCZOS).save(path)
    return W, H


def cues(text, dur):
    words = re.sub(r"\{en:([^}]*)\}", r"\1", text).split()
    chunks = [words[i:i + WORDS_PER_CUE] for i in range(0, len(words), WORDS_PER_CUE)]
    total = sum(len(" ".join(c)) for c in chunks) or 1
    out, t = [], 0.0
    for c in chunks:
        share = dur * len(" ".join(c)) / total
        out.append((t, t + share, " ".join(c)))
        t += share
    return out


def ts_ass(t):
    return f"{int(t // 3600)}:{int(t % 3600 // 60):02d}:{t % 60:05.2f}"


def ts_srt(t):
    return f"{int(t // 3600):02d}:{int(t % 3600 // 60):02d}:{int(t % 60):02d},{int(t * 1000) % 1000:03d}"


def write_ass(path, items, w, h):
    size, margin = int(h * 0.035) if h > w else int(h * 0.05), int(h * 0.12)
    lines = ["[Script Info]", "ScriptType: v4.00+", f"PlayResX: {w}", f"PlayResY: {h}", "",
             "[V4+ Styles]",
             "Format: Name,Fontname,Fontsize,PrimaryColour,OutlineColour,BackColour,Bold,BorderStyle,Outline,Shadow,Alignment,MarginL,MarginR,MarginV",
             f"Style: Default,DejaVu Sans,{size},&H00FFFFFF,&H00502A3A,&H00000000,1,1,6,0,2,60,60,{margin}", "",
             "[Events]", "Format: Layer,Start,End,Style,Text"]
    for a, b, t in items:
        lines.append(f"Dialogue: 0,{ts_ass(a)},{ts_ass(b)},Default,{t}")
    Path(path).write_text("\n".join(lines) + "\n", encoding="utf-8")


def synth(text, out, brief):
    sys.path.insert(0, str(REPO / "video-shorts-mcp"))
    from voice import synthesize
    return synthesize(text, str(out), channel=brief.get("channel"), persona=brief.get("persona"))


def build_scene(i, sc, brief, tmp, W, H, fps, bg, no_synth):
    pad = float(sc.get("pad", 0.4))
    audio = None
    if sc.get("audio"):
        audio = Path(sc["audio"])
    elif sc.get("say") and not no_synth:
        audio = tmp / f"voice_{i}.wav"
        synth(sc["say"], audio, brief)
    elif sc.get("say"):
        sys.exit(f"Szene {i}: 'say' ohne Stimme (--no-synth) braucht 'audio:'")
    voice_dur = probe_duration(audio) if audio else 0.0
    kind = sc["kind"]
    video = Path(sc["video"]) if kind == "app" else None
    if kind == "app" and not video.exists():
        sys.exit(f"Szene {i}: Aufnahme fehlt: {video}")
    dur = (voice_dur + pad) if audio else float(sc.get("seconds", 2.0))
    if video:
        dur = max(dur, probe_duration(video))
    seq = Path(sc["piggy"]) if sc.get("piggy") else None
    if seq and not list(seq.glob("frame_*.png")):
        sys.exit(f"Szene {i}: keine frame_####.png in {seq}")
    if kind == "piggy" and not seq:
        sys.exit(f"Szene {i}: kind piggy braucht 'piggy:'")

    ins = ["-f", "lavfi", "-t", f"{dur:.3f}", "-i", f"color=c={bg}:s={W}x{H}:r={fps}"]
    fc, last, n = [], "[0:v]", 1
    if video:
        sh = int(H * 0.72) if H >= W else int(H * 0.78)
        probe = json.loads(run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
                                "stream=width,height", "-of", "json", video]))["streams"][0]
        sw = int(sh * probe["width"] / probe["height"]) // 2 * 2
        bz = tmp / "bezel.png"
        bw, bh = make_bezel(bz, sw, sh)
        ins += ["-i", video, "-loop", "1", "-framerate", str(fps), "-i", bz]
        fc += [f"[{n}:v]fps={fps},scale={sw}:{sh},tpad=stop_mode=clone:stop_duration={dur:.3f},setsar=1[scr]",
               f"{last}[scr]overlay=(W-w)/2:(H-h)/2-{int(H*0.07)}[a]",
               f"[a][{n+1}:v]overlay=(W-w)/2:(H-h)/2-{int(H*0.07)}:shortest=0[b]"]
        last, n = "[b]", n + 2
    if seq:
        small = kind == "app"
        pw = int(W * (0.30 if small else 0.95)) if H >= W else int(H * (0.40 if small else 0.9))
        ins += ["-stream_loop", "-1", "-framerate", str(fps), "-i", seq / "frame_%04d.png"]
        x = "W-w-20" if small else "(W-w)/2"
        y = "H-h-20" if small else "H-h-" + str(int(H * 0.16))
        fc += [f"[{n}:v]scale={pw}:-1,format=rgba[pg]", f"{last}[pg]overlay={x}:{y}:shortest=0[c]"]
        last, n = "[c]", n + 1
    cl = sc.get("say")
    items = cues(cl, voice_dur or dur) if cl else []
    if items:
        ass = tmp / f"sub_{i}.ass"
        write_ass(ass, items, W, H)
        fc.append(f"{last}ass={ass}[v]")
    else:
        fc.append(f"{last}null[v]")
    if audio:
        ins += ["-i", audio]
        afil = f"[{n}:a]aresample=48000,apad,atrim=0:{dur:.3f}[a]"
    else:
        ins += ["-f", "lavfi", "-t", f"{dur:.3f}", "-i", "anullsrc=r=48000:cl=mono"]
        afil = f"[{n}:a]anull[a]"
    out = tmp / f"scene_{i}.mp4"
    run(["ffmpeg", "-y", "-v", "error", *ins, "-filter_complex", ";".join(fc + [afil]), "-map", "[v]", "-map", "[a]",
         "-t", f"{dur:.3f}", "-r", fps, "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "18",
         "-c:a", "aac", "-ar", "48000", "-ac", "1", "-shortest", out])
    return out, dur, items


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("briefing")
    ap.add_argument("--out", required=True)
    ap.add_argument("--music")
    ap.add_argument("--no-synth", action="store_true", help="keine Stimme erzeugen, Szenen brauchen 'audio:'")
    ap.add_argument("--keep-tmp", action="store_true")
    a = ap.parse_args()

    brief = load_briefing(a.briefing)
    fmt = brief.get("format", "9x16")
    if fmt not in FORMATS:
        sys.exit(f"Unbekanntes Format {fmt}; erlaubt: {', '.join(FORMATS)}")
    W, H = FORMATS[fmt]
    fps = int(brief.get("fps", 24))
    bg = "0x" + brief.get("bg", DEFAULT_BG).lstrip("#")
    name = re.sub(r"[^\w-]", "_", brief.get("name", "piggy-video"))
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    tmp = Path(tempfile.mkdtemp(prefix="compose_"))
    try:
        scenes, t0, srt = [], 0.0, []
        for i, sc in enumerate(brief["scenes"]):
            f, d, items = build_scene(i, sc, brief, tmp, W, H, fps, bg, a.no_synth)
            scenes.append(f)
            srt += [(t0 + s, t0 + e, tx) for s, e, tx in items]
            t0 += d
        lst = tmp / "list.txt"
        lst.write_text("".join(f"file '{p}'\n" for p in scenes))
        joined = tmp / "joined.mp4"
        run(["ffmpeg", "-y", "-v", "error", "-f", "concat", "-safe", "0", "-i", lst, "-c", "copy", joined])
        final = out / f"{name}.mp4"
        if a.music:
            af = ("[1:a]volume=0.5,aloop=-1:2e9[m];[0:a]asplit[v1][v2];[m][v2]sidechaincompress=threshold=0.03:ratio=8[d];"
                  "[v1][d]amix=inputs=2:normalize=0:duration=first,loudnorm=I=-14:TP=-1.5:LRA=11[a]")
            run(["ffmpeg", "-y", "-v", "error", "-i", joined, "-i", a.music, "-filter_complex", af, "-map", "0:v",
                 "-map", "[a]", "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-shortest", final])
        else:
            run(["ffmpeg", "-y", "-v", "error", "-i", joined, "-af", "loudnorm=I=-14:TP=-1.5:LRA=11",
                 "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", final])
        (out / f"{name}.srt").write_text("".join(
            f"{k}\n{ts_srt(s)} --> {ts_srt(e)}\n{t}\n\n" for k, (s, e, t) in enumerate(srt, 1)), encoding="utf-8")
        run(["ffmpeg", "-y", "-v", "error", "-ss", f"{min(1.0, t0 / 2):.2f}", "-i", final, "-frames:v", "1", out / f"{name}.jpg"])
        meta = {"name": name, "format": fmt, "size": [W, H], "fps": fps, "duration": probe_duration(final),
                "scenes": len(scenes), "music": bool(a.music), "persona": brief.get("persona"),
                "channel": brief.get("channel"), "subtitle_timing": "proportional (nicht per ASR ausgerichtet)"}
        (out / f"{name}.compose.json").write_text(json.dumps(meta, indent=2, ensure_ascii=False))
        print(json.dumps(meta, ensure_ascii=False))
    finally:
        if not a.keep_tmp:
            shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    main()
