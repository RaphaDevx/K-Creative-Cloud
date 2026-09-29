"""
Frame generator: produces one PNG per scene using Pillow.
Style: viral learning short — dark bg, accent glow, Roboto-Black type, NotoColorEmoji.
Resolution: 1080x1920 (portrait) or 1920x1080 (landscape)
"""
from PIL import Image, ImageDraw, ImageFont
import os

try:
    from stat_viz import render_viz as _render_viz
    _STAT_VIZ_AVAILABLE = True
except ImportError:
    _STAT_VIZ_AVAILABLE = False

FONT_BLACK = "/usr/share/fonts/truetype/roboto/unhinted/RobotoTTF/Roboto-Black.ttf"
FONT_BOLD  = "/usr/share/fonts/truetype/roboto/unhinted/RobotoTTF/Roboto-Bold.ttf"
FONT_REG   = "/usr/share/fonts/truetype/roboto/unhinted/RobotoTTF/Roboto-Regular.ttf"
FONT_EMOJI = "/usr/share/fonts/truetype/noto/NotoColorEmoji.ttf"

# Fallback to DejaVu if Roboto missing
if not os.path.exists(FONT_BLACK):
    FONT_BLACK = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
    FONT_BOLD  = FONT_BLACK
    FONT_REG   = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"

W_P, H_P = 1080, 1920
W_L, H_L = 1920, 1080

TYPE_LABELS = {
    "hook":        ("EINSTIEG",  "#FF4444"),
    "fact":        ("FAKT",      "#FFD700"),
    "explanation": ("ERKLÄRT",   "#4FC3F7"),
    "warning":     ("ACHTUNG",   "#FF7043"),
    "tip":         ("TIPP",      "#66BB6A"),
    "takeaway":    ("FAZIT",     "#CE93D8"),
}


def _hex_to_rgb(hex_color: str) -> tuple:
    h = hex_color.lstrip("#")
    return tuple(int(h[i:i+2], 16) for i in (0, 2, 4))


def _draw_text_centered(draw, text, font, y_center, width, color, shadow=True):
    """Draw text centered horizontally with optional drop shadow."""
    bbox = draw.textbbox((0, 0), text, font=font)
    tw = bbox[2] - bbox[0]
    x = (width - tw) // 2
    y = y_center - (bbox[3] - bbox[1]) // 2
    if shadow:
        draw.text((x + 3, y + 3), text, font=font, fill=(0, 0, 0, 160))
    draw.text((x, y), text, font=font, fill=color)
    return bbox[3] - bbox[1]


def _wrap_text(text: str, font, max_width: int, draw: ImageDraw) -> list[str]:
    """Wrap text to fit within max_width."""
    words = text.split()
    lines = []
    current = []
    for word in words:
        test = " ".join(current + [word])
        bbox = draw.textbbox((0, 0), test, font=font)
        if bbox[2] - bbox[0] > max_width and current:
            lines.append(" ".join(current))
            current = [word]
        else:
            current.append(word)
    if current:
        lines.append(" ".join(current))
    return lines


def _draw_type_badge(draw, img, scene_type, accent_hex, W, y_top=88):
    """Draw a rounded pill badge with the scene type label."""
    label, badge_color = TYPE_LABELS.get(scene_type, ("●", accent_hex))
    try:
        font = ImageFont.truetype(FONT_BOLD, 36)
    except Exception:
        return y_top + 60
    bbox = draw.textbbox((0, 0), label, font=font)
    tw = bbox[2] - bbox[0]
    th = bbox[3] - bbox[1]
    pad_x, pad_y = 32, 14
    rect_w = tw + 2 * pad_x
    rect_h = th + 2 * pad_y
    x0 = (W - rect_w) // 2
    y0 = y_top
    rgb = _hex_to_rgb(badge_color)
    # Background fill (semi-transparent)
    badge_layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
    bd = ImageDraw.Draw(badge_layer)
    bd.rounded_rectangle([x0, y0, x0 + rect_w, y0 + rect_h],
                          radius=rect_h // 2,
                          fill=rgb + (45,),
                          outline=rgb + (210,),
                          width=3)
    img.alpha_composite(badge_layer)
    # Redraw on main draw context for text
    draw = ImageDraw.Draw(img)
    draw.text((x0 + pad_x, y0 + pad_y), label, font=font, fill=rgb + (255,))
    return y0 + rect_h + 8, draw


def _draw_accent_icon(img, scene_type, accent, W, y_center):
    """Draw a large decorative accent glyph/shape to fill the visual space."""
    layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    r = 140
    cx = W // 2
    # Outer ring
    d.ellipse([cx - r, y_center - r, cx + r, y_center + r],
              outline=accent + (60,), width=4)
    # Inner glow
    d.ellipse([cx - r + 20, y_center - r + 20, cx + r - 20, y_center + r - 20],
              fill=accent + (18,))
    # Type-specific inner symbol drawn with lines
    symbols = {
        "hook":        lambda: d.polygon([(cx, y_center - 55), (cx + 48, y_center + 32), (cx - 48, y_center + 32)], fill=accent + (100,)),
        "fact":        lambda: [d.ellipse([cx - 14, y_center - 52, cx + 14, y_center - 22], fill=accent + (120,)),
                                d.rectangle([cx - 10, y_center - 10, cx + 10, y_center + 42], fill=accent + (120,))],
        "explanation": lambda: [d.ellipse([cx - 40, y_center - 50, cx + 40, y_center + 20], fill=accent + (80,)),
                                d.rectangle([cx - 8, y_center + 28, cx + 8, y_center + 46], fill=accent + (80,))],
        "warning":     lambda: d.polygon([(cx, y_center - 58), (cx + 52, y_center + 38), (cx - 52, y_center + 38)], outline=accent + (130,), width=8),
        "tip":         lambda: [d.line([(cx - 40, y_center), (cx - 10, y_center + 30), (cx + 45, y_center - 35)], fill=accent + (150,), width=10)],
        "takeaway":    lambda: [d.ellipse([cx - 38, y_center - 38, cx + 38, y_center + 38], fill=accent + (80,)),
                                d.polygon([(cx, y_center - 20), (cx + 20, y_center + 14), (cx - 20, y_center + 14)], fill=(0, 0, 0, 160))],
    }
    fn = symbols.get(scene_type)
    if fn:
        result = fn()
        if isinstance(result, list):
            pass  # side effects already applied
    img.alpha_composite(layer)


def _draw_background(img, W, H, accent):
    """Fill with dark bg + subtle accent glow at top-center."""
    draw = ImageDraw.Draw(img)
    # Base fill (already set on image creation)
    # Top accent glow
    glow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    gd = ImageDraw.Draw(glow)
    # Large soft ellipse at top-center
    cx = W // 2
    for r in range(420, 0, -15):
        alpha = int(22 * (1 - r / 420))
        gd.ellipse([cx - r * 2, -r // 2, cx + r * 2, r + r // 2], fill=accent + (alpha,))
    img.alpha_composite(glow)
    return ImageDraw.Draw(img)


def render_scene_frame(
    scene: dict,
    out_path: str,
    scene_idx: int,
    total_scenes: int,
    format: str = "portrait",
) -> str:
    W, H = (W_P, H_P) if format == "portrait" else (W_L, H_L)

    accent = _hex_to_rgb(scene.get("accent_hex", "#4FC3F7"))
    # Very dark background with slight accent tint
    bg = (
        max(8, min(accent[0] // 18, 18)),
        max(8, min(accent[1] // 18, 18)),
        max(12, min(accent[2] // 14, 22)),
    )
    img = Image.new("RGBA", (W, H), bg + (255,))

    draw = _draw_background(img, W, H, accent)

    margin = int(W * 0.07)
    content_w = W - 2 * margin

    has_viz = bool(scene.get("viz"))
    scene_type = scene.get("type", "explanation")

    if format == "portrait":
        if has_viz:
            headline_size = 72
            sub_size = 36
            headline_y = int(H * 0.17)
            sub_y = int(H * 0.29)
            viz_y_override = int(H * 0.38)
        else:
            icon_y = int(H * 0.36)
            headline_size = 92
            sub_size = 46
            headline_y = int(H * 0.57)
            sub_y = int(H * 0.74)
            viz_y_override = int(H * 0.52)
    else:
        has_viz = False
        icon_y = int(H * 0.28)
        headline_size = 72
        sub_size = 36
        headline_y = int(H * 0.47)
        sub_y = int(H * 0.67)
        viz_y_override = int(H * 0.52)

    # Top accent bar
    draw.rectangle([0, 0, W, 8], fill=accent + (255,))

    # Progress dots
    dot_r = 11
    dot_gap = 30
    total_w_dots = total_scenes * dot_gap
    dot_x = (W - total_w_dots) // 2
    dot_y = 28
    for i in range(total_scenes):
        color = accent + (255,) if i == scene_idx else (70, 70, 70, 255)
        draw.ellipse([dot_x + i * dot_gap, dot_y,
                      dot_x + i * dot_gap + dot_r * 2, dot_y + dot_r * 2], fill=color)

    # Type badge (all modes)
    badge_bottom, draw = _draw_type_badge(draw, img, scene_type, scene.get("accent_hex", "#4FC3F7"), W, y_top=70)

    # Decorative accent icon (non-viz only)
    if not has_viz and format == "portrait":
        _draw_accent_icon(img, scene_type, accent, W, icon_y)
        draw = ImageDraw.Draw(img)

    # Headline
    try:
        hl_font = ImageFont.truetype(FONT_BLACK, headline_size)
        headline_text = scene.get("headline", "").upper()
        lines = _wrap_text(headline_text, hl_font, content_w, draw)
        line_h_px = headline_size + 12
        start_y = headline_y - (len(lines) * line_h_px) // 2
        for i, line in enumerate(lines):
            _draw_text_centered(draw, line, hl_font, start_y + i * line_h_px, W, accent + (255,))
    except Exception:
        pass

    # Subtext
    try:
        sub_font = ImageFont.truetype(FONT_REG, sub_size)
        subtext = scene.get("subtext", "")
        sub_lines = _wrap_text(subtext, sub_font, content_w, draw)
        sub_line_h = sub_size + 10
        for i, line in enumerate(sub_lines):
            _draw_text_centered(draw, line, sub_font, sub_y + i * sub_line_h, W, (215, 215, 215, 255))
    except Exception:
        pass

    # Progress bar at bottom
    bar_h = 7
    bar_y = H - 45
    draw.rectangle([0, bar_y, W, bar_y + bar_h], fill=(35, 35, 35, 255))
    progress = int(W * (scene_idx + 1) / total_scenes)
    draw.rectangle([0, bar_y, progress, bar_y + bar_h], fill=accent + (255,))

    # Bottom accent line
    draw.rectangle([0, H - 8, W, H], fill=accent + (255,))

    # Viz overlay
    viz = scene.get("viz")
    if viz and _STAT_VIZ_AVAILABLE:
        try:
            viz_img = _render_viz(viz, width_px=int(W * 0.88), height_px=int(H * 0.42))
            if viz_img:
                viz_x = (W - viz_img.width) // 2
                img = img.convert("RGBA")
                img.alpha_composite(viz_img, (viz_x, viz_y_override))
        except Exception as e:
            print(f"[frame_render] viz render failed: {e}")

    img = img.convert("RGB")
    img.save(out_path, "PNG")
    return out_path
