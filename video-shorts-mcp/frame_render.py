"""
Frame generator: produces one PNG per scene using Pillow.
Style: viral learning short — dark bg, huge bold text, accent color, emoji.
Resolution: 1080x1920 (portrait) or 1920x1080 (landscape)
"""
from PIL import Image, ImageDraw, ImageFont
import os

FONT_BOLD = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
FONT_REG  = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"

# Portrait (Shorts)
W_P, H_P = 1080, 1920
# Landscape (YouTube)
W_L, H_L = 1920, 1080


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
        draw.text((x + 3, y + 3), text, font=font, fill=(0, 0, 0, 180))
    draw.text((x, y), text, font=font, fill=color)
    return bbox[3] - bbox[1]  # return text height


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


def render_scene_frame(
    scene: dict,
    out_path: str,
    scene_idx: int,
    total_scenes: int,
    format: str = "portrait",
) -> str:
    """
    Render one scene as a PNG frame.
    scene keys: headline, subtext, emoji, accent_hex
    Returns out_path.
    """
    W, H = (W_P, H_P) if format == "portrait" else (W_L, H_L)

    # Background: near-black with subtle tint from accent
    accent = _hex_to_rgb(scene.get("accent_hex", "#4FC3F7"))
    bg_color = (
        max(0, min(10 + accent[0] // 15, 25)),
        max(0, min(10 + accent[1] // 15, 25)),
        max(0, min(10 + accent[2] // 15, 35)),
    )
    img = Image.new("RGBA", (W, H), bg_color + (255,))
    draw = ImageDraw.Draw(img)

    # Subtle radial-ish gradient: lighter in center
    overlay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ov_draw = ImageDraw.Draw(overlay)
    cx, cy = W // 2, H // 2
    for r in range(min(W, H) // 2, 0, -20):
        alpha = int(40 * (1 - r / (min(W, H) / 2)))
        color = accent + (alpha,)
        ov_draw.ellipse([cx - r, cy - r, cx + r, cy + r], fill=color)
    img = Image.alpha_composite(img, overlay)
    draw = ImageDraw.Draw(img)

    margin = int(W * 0.07)
    content_w = W - 2 * margin

    if format == "portrait":
        emoji_size = 120
        headline_size = 88
        sub_size = 44
        emoji_y = int(H * 0.22)
        headline_y = int(H * 0.42)
        sub_y = int(H * 0.60)
    else:
        emoji_size = 90
        headline_size = 72
        sub_size = 36
        emoji_y = int(H * 0.28)
        headline_y = int(H * 0.47)
        sub_y = int(H * 0.67)

    # Accent line at top
    line_h = 8
    draw.rectangle([0, 0, W, line_h], fill=accent + (255,))

    # Scene number dots
    dot_r = 10
    dot_gap = 28
    total_w = total_scenes * dot_gap
    dot_x = (W - total_w) // 2
    dot_y = 40
    for i in range(total_scenes):
        color = accent if i == scene_idx else (80, 80, 80)
        draw.ellipse([dot_x + i * dot_gap, dot_y, dot_x + i * dot_gap + dot_r * 2, dot_y + dot_r * 2], fill=color)

    # Emoji
    try:
        emoji_font = ImageFont.truetype(FONT_BOLD, emoji_size)
        _draw_text_centered(draw, scene.get("emoji", "💡"), emoji_font, emoji_y, W, (255, 255, 255), shadow=False)
    except Exception:
        pass

    # Headline (ALL CAPS, bold, accent color)
    try:
        headline_font = ImageFont.truetype(FONT_BOLD, headline_size)
        headline_text = scene.get("headline", "").upper()
        lines = _wrap_text(headline_text, headline_font, content_w, draw)
        line_h_px = headline_size + 10
        start_y = headline_y - (len(lines) * line_h_px) // 2
        for i, line in enumerate(lines):
            _draw_text_centered(draw, line, headline_font, start_y + i * line_h_px, W, accent + (255,))
    except Exception:
        pass

    # Subtext (white, regular)
    try:
        sub_font = ImageFont.truetype(FONT_REG, sub_size)
        subtext = scene.get("subtext", "")
        sub_lines = _wrap_text(subtext, sub_font, content_w, draw)
        sub_line_h = sub_size + 8
        sub_start = sub_y
        for i, line in enumerate(sub_lines):
            _draw_text_centered(draw, line, sub_font, sub_start + i * sub_line_h, W, (220, 220, 220, 255))
    except Exception:
        pass

    # Progress bar at bottom
    bar_h = 6
    bar_y = H - 40
    draw.rectangle([0, bar_y, W, bar_y + bar_h], fill=(40, 40, 40, 255))
    progress = int(W * (scene_idx + 1) / total_scenes)
    draw.rectangle([0, bar_y, progress, bar_y + bar_h], fill=accent + (255,))

    # Accent bottom line
    draw.rectangle([0, H - line_h, W, H], fill=accent + (255,))

    img = img.convert("RGB")
    img.save(out_path, "PNG")
    return out_path
