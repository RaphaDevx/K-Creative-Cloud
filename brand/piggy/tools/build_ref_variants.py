#!/usr/bin/env python3
"""Piggy-Icon-Varianten im Referenzstil -> brand/piggy/dist/variants/ref-<name>/ (Basis bleibt unverändert).
Aufruf: python3 brand/piggy/tools/build_ref_variants.py   (braucht inkscape + Pillow)
Je Variante: App-Icon 1024 (RGB, ohne Alpha, eckig), Android-Adaptive-Vordergrund 1024 (transparent, Figur im inneren 66 %),
Splash 1024 (transparent, Figur + Wortmarke aus base), Favicon 48, SVGs, Vorschau 1024/180/60."""
import json, subprocess, tempfile, sys
from pathlib import Path
from PIL import Image

sys.path.insert(0, str(Path(__file__).parent))
import ref_style as R

ROOT = Path(__file__).resolve().parents[1]
VAR = ROOT / "dist" / "variants"
BASE_SPLASH = (VAR / "base" / "piggy-splash-base.svg").read_text()
GOLD_TOP, GOLD_MID, GOLD_BOT = "#FFE4A8", "#FFC247", "#FF9F0A"
ADAPTIVE_BG = "#FFC247"

BG_DEFS = f'''<radialGradient id="gBg" cx="0.5" cy="0.42" r="0.78"><stop offset="0" stop-color="{GOLD_TOP}"/><stop offset="0.7" stop-color="{GOLD_MID}"/><stop offset="1" stop-color="{GOLD_BOT}"/></radialGradient>'''


def render(svg, out, w, transparent=True):
    with tempfile.NamedTemporaryFile("w", suffix=".svg", delete=False) as f:
        f.write(svg)
    cmd = ["inkscape", f.name, "-o", str(out), "-w", str(w), "-h", str(w)]
    subprocess.run(cmd, capture_output=True, check=True)
    Path(f.name).unlink()


def wrap(inner, size=1024, bg=None, extra_defs=""):
    bgrect = f'<rect width="{size}" height="{size}" fill="{bg}"/>' if bg else ""
    return f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {size} {size}"><defs>{BG_DEFS}{extra_defs}</defs>{R.DEFS}{bgrect}{inner}</svg>'


_bbox_cache = {}


def bbox_of(key, inner):
    if key not in _bbox_cache:
        tmp = Path(tempfile.mkdtemp()) / "b.png"
        render(wrap(inner), tmp, 1024)
        _bbox_cache[key] = Image.open(tmp).getchannel("A").point(lambda a: 255 if a > 8 else 0).getbbox()
    return _bbox_cache[key]


def fit(inner, key, box, cx=512, cy=512):
    """Skaliert/zentriert die Zeichnung (Bounding-Box aus Testrender) in ein Quadrat der Kantenlänge `box`."""
    x0, y0, x1, y1 = bbox_of(key, inner)
    s = box / max(x1 - x0, y1 - y0)
    tx = cx - s * (x0 + x1) / 2
    ty = cy - s * (y0 + y1) / 2
    return f'<g transform="translate({tx:.2f} {ty:.2f}) scale({s:.4f})">{inner}</g>'


VARIANTS = {
    "kopf":   dict(title="Kopf nah", inner=lambda: R.pig(head_only=True), key="head", shadow=False, box=700),
    "figur":  dict(title="Figur ganz", inner=lambda: R.pig(), key="full", shadow=True, box=800),
    "muenze": dict(title="Figur mit Münze", inner=lambda: R.pig(coin=True), key="coin", shadow=True, box=800),
}


def wordmark():
    i = BASE_SPLASH.index('<g transform="translate(13.279999999999973 540)')
    wm = BASE_SPLASH[i:BASE_SPLASH.rindex("</g></g></svg>") + len("</g>")]
    return wm, BASE_SPLASH[BASE_SPLASH.index("<defs>") + 6:BASE_SPLASH.index("</defs>")]


def build(name, v):
    global WM_DEFS
    out = VAR / f"ref-{name}"
    out.mkdir(parents=True, exist_ok=True)
    inner = v["inner"]()
    sh = R.shadow(cx=520, cy=905, rx=340, ry=34) if v["shadow"] else ""
    # 1) App-Icon: Gold-Verlauf, Figur gross, eckig
    key = v["key"]
    fig_inner = (sh + inner)
    icon_svg = wrap(fit(fig_inner, key + "s" if v["shadow"] else key, v["box"], 512, 520), bg="url(#gBg)")
    (out / f"piggy-appicon-ref-{name}.svg").write_text(icon_svg)
    tmp_png = out / "_icon.png"
    render(icon_svg, tmp_png, 1024)
    Image.open(tmp_png).convert("RGBA").convert("RGB").save(out / f"piggy-appicon-ref-{name}-1024.png")
    tmp_png.unlink()
    # 2) Adaptive Vordergrund: transparent, innerer Sicherheitsbereich 66 % (= 676 px)
    ad_svg = wrap(fit(inner, key + "n", 640, 512, 512))
    (out / f"piggy-adaptive-ref-{name}.svg").write_text(ad_svg)
    render(ad_svg, out / f"piggy-adaptive-ref-{name}-1024.png", 1024)
    # 3) Splash: Figur oben, Wortmarke unten, transparent
    wm, wm_defs = wordmark()
    x0, y0, x1, y1 = bbox_of("wordmark", wm)
    wm = f'<g transform="translate({512 - (x0 + x1) / 2:.1f} {905 - y1:.1f})">{wm}</g>'
    sp = fit(inner, key + "n", 470, 512, 330) + wm
    sp_svg = wrap(sp, extra_defs=wm_defs)
    (out / f"piggy-splash-ref-{name}.svg").write_text(sp_svg)
    render(sp_svg, out / f"piggy-splash-ref-{name}-1024.png", 1024)
    # 4) Favicon 48 (Kopf nah liest sich am besten; Icon ohne Schatten herunterskaliert)
    icon = Image.open(out / f"piggy-appicon-ref-{name}-1024.png")
    icon.resize((48, 48), Image.LANCZOS).save(out / f"favicon-ref-{name}-48.png")
    # 5) Vorschau 1024/180/60 nebeneinander auf hellem und dunklem Grund
    sheet = Image.new("RGB", (1024 + 180 + 60 + 120, 1024), (250, 250, 249))
    sheet.paste(icon, (0, 0))
    sheet.paste(icon.resize((180, 180), Image.LANCZOS), (1044, 40))
    sheet.paste(icon.resize((60, 60), Image.LANCZOS), (1044 + 200, 40))
    sheet.paste(icon.resize((60, 60), Image.LANCZOS), (1044, 260))
    sheet.save(out / f"preview-ref-{name}.png")
    meta = {"id": f"ref-{name}", "title": v["title"], "kind": "ref-style", "background": [GOLD_MID, GOLD_BOT],
            "adaptiveBg": ADAPTIVE_BG, "splashBg": "#FAFAF9", "note": "Eigene Zeichnung im Stil der Referenzen (nicht abgepaust); Referenzen KI-generiert, kommerzielle Nutzung ungeprüft"}
    (out / "meta.json").write_text(json.dumps(meta, indent=2, ensure_ascii=False))
    return out


if __name__ == "__main__":
    for n, v in VARIANTS.items():
        print(build(n, v))
