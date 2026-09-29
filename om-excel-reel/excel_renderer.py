"""
Excel Sheet → Annotated PNG Renderer
Reads openpyxl sheet data and renders it as a styled image using PIL.
Supports per-step highlighting for tutorial video frames.
"""
from __future__ import annotations
from PIL import Image, ImageDraw, ImageFont
from pathlib import Path
import math

# ── Constants ─────────────────────────────────────────────────────────────────
BG_DARK   = (18, 18, 28)
BG_HEADER = (35, 35, 55)
BG_ROW_A  = (25, 25, 40)
BG_ROW_B  = (30, 30, 48)
TEXT_PRI  = (240, 240, 250)
TEXT_SEC  = (180, 180, 200)
TEXT_DIM  = (110, 110, 140)
BORDER    = (60, 60, 90)

LEVEL_COLORS = {
    1: "#4FC3F7",  # blue
    2: "#FFD700",  # gold
    3: "#FF7043",  # orange
}
LEVEL_BG = {
    1: (30, 60, 90),
    2: (70, 60, 20),
    3: (80, 40, 20),
}
HIGHLIGHT_FILL  = (255, 80,  80,  80)   # RGBA red highlight
HIGHLIGHT_DONE  = (80,  200, 80,  70)   # RGBA green (completed)
STEP_ACCENT     = "#FF4444"

CELL_H   = 48
PADDING  = 40
FONT_DIR = Path("/usr/share/fonts/truetype/dejavu")


def _font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    name = "DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf"
    path = FONT_DIR / name
    if path.exists():
        return ImageFont.truetype(str(path), size)
    return ImageFont.load_default()


def _hex_to_rgb(h: str) -> tuple[int, int, int]:
    h = h.lstrip("#")
    return tuple(int(h[i:i+2], 16) for i in (0, 2, 4))


class BOMTable:
    """Renders a multi-level BOM as an annotated PIL image."""

    def __init__(self, rows: list[dict], col_widths: list[int] | None = None):
        """
        rows: list of dicts with keys:
          level (int 1-3), part (str), level_qty (int),
          total_qty (int|None), price (float),
          cost (float|None), is_header (bool)
        col_widths: pixel widths for columns [Level, Part, L.Qty, T.Qty, Price/Unit, Cost]
        """
        self.rows = rows
        self.col_widths = col_widths or [120, 200, 120, 140, 160, 180]
        self.col_labels = ["Level", "Part", "Level Qty", "Total Qty", "Price/Unit", "Cost"]
        self.total_w = sum(self.col_widths) + PADDING * 2
        self.total_h = CELL_H * (len(rows) + 2) + PADDING * 2  # +2 for header rows

    def render(
        self,
        highlight_rows: list[int] | None = None,
        done_rows: list[int] | None = None,
        step_label: str | None = None,
        formula_hint: str | None = None,
        width: int = 1920,
        height: int = 1080,
    ) -> Image.Image:
        """Render full 1920×1080 frame with the BOM table centered."""
        canvas = Image.new("RGB", (width, height), BG_DARK)
        draw = ImageDraw.Draw(canvas, "RGBA")

        # Title bar
        draw.rectangle([0, 0, width, 70], fill=(20, 20, 35))
        draw.text((width // 2, 35), "Q19 — Multi-Level Bill of Materials | Battery Tester",
                  font=_font(28, bold=True), fill=TEXT_PRI, anchor="mm")

        # Step label (top right)
        if step_label:
            draw.text((width - PADDING, 35), step_label,
                      font=_font(22, bold=True), fill=_hex_to_rgb(STEP_ACCENT), anchor="rm")

        # Center the table
        tbl_x = (width - self.total_w) // 2
        tbl_y = 90

        self._draw_table(draw, tbl_x, tbl_y,
                         highlight_rows=highlight_rows or [],
                         done_rows=done_rows or [])

        # Formula hint (bottom bar)
        if formula_hint:
            bar_y = height - 80
            draw.rectangle([0, bar_y, width, height], fill=(20, 20, 35))
            draw.text((width // 2, bar_y + 40), formula_hint,
                      font=_font(26), fill=_hex_to_rgb("#FFD700"), anchor="mm")

        return canvas

    def _draw_table(self, draw: ImageDraw.ImageDraw,
                    x: int, y: int,
                    highlight_rows: list[int],
                    done_rows: list[int]):
        # Column header background
        draw.rectangle([x, y, x + self.total_w - PADDING * 2, y + CELL_H],
                       fill=BG_HEADER)
        cx = x
        for label, w in zip(self.col_labels, self.col_widths):
            draw.text((cx + w // 2, y + CELL_H // 2), label,
                      font=_font(20, bold=True), fill=TEXT_PRI, anchor="mm")
            cx += w

        y += CELL_H

        for i, row in enumerate(self.rows):
            row_y = y + i * CELL_H
            row_h  = CELL_H
            row_w  = self.total_w - PADDING * 2
            level  = row.get("level", 0)

            # Row background (alternating)
            bg = LEVEL_BG.get(level, BG_ROW_A if i % 2 == 0 else BG_ROW_B)
            draw.rectangle([x, row_y, x + row_w, row_y + row_h - 1], fill=bg)

            # Highlight overlays
            if i in highlight_rows:
                draw.rectangle([x, row_y, x + row_w, row_y + row_h - 1],
                                fill=HIGHLIGHT_FILL)
            elif i in done_rows:
                draw.rectangle([x, row_y, x + row_w, row_y + row_h - 1],
                                fill=HIGHLIGHT_DONE)

            # Level indent indicator
            if level:
                color = _hex_to_rgb(LEVEL_COLORS.get(level, "#FFFFFF"))
                indent = (level - 1) * 18
                draw.rectangle([x, row_y, x + 6, row_y + row_h - 1], fill=color)
                draw.text((x + 14 + indent, row_y + row_h // 2),
                          f"L{level}", font=_font(16, bold=True),
                          fill=color, anchor="lm")

            # Cell values
            vals = [
                str(level) if level else "",
                row.get("part", ""),
                str(row.get("level_qty", "")) if row.get("level_qty") else "",
                str(row.get("total_qty", "")) if row.get("total_qty") is not None else "?",
                f"{row.get('price', 0):.2f}" if row.get("price") else "",
                f"{row.get('cost', 0):.2f}" if row.get("cost") is not None else ("?" if level else ""),
            ]

            cx = x
            for j, (val, w) in enumerate(zip(vals, self.col_widths)):
                color = TEXT_PRI
                if val == "?":
                    color = _hex_to_rgb("#FF7043")
                elif j == 5 and row.get("cost") is not None:
                    color = _hex_to_rgb("#66BB6A")
                draw.text((cx + w // 2, row_y + row_h // 2), val,
                          font=_font(18), fill=color, anchor="mm")
                cx += w

            # Bottom border
            draw.line([x, row_y + row_h - 1, x + row_w, row_y + row_h - 1],
                      fill=BORDER, width=1)

        # Total row
        total_y = y + len(self.rows) * CELL_H + 10
        draw.rectangle([x, total_y, x + self.total_w - PADDING * 2, total_y + CELL_H],
                       fill=(40, 50, 40))
        draw.text((x + sum(self.col_widths[:5]) + self.col_widths[5] // 2, total_y + CELL_H // 2),
                  "= TOTAL", font=_font(20, bold=True), fill=TEXT_PRI, anchor="mm")
