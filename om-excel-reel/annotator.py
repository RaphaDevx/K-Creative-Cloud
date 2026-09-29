"""
annotator.py — Draws step-by-step annotations on LibreOffice sheet screenshots.
"""
from __future__ import annotations
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageFilter
from cell_mapper import CellRect

FONT_DIR = Path("/usr/share/fonts/truetype/dejavu")

# ── Color palette ─────────────────────────────────────────────────────────────
HIGHLIGHT = {
    "yellow":  (255, 230, 0,   140),
    "green":   (80,  220, 80,  130),
    "red":     (255, 60,  60,  120),
    "blue":    (60,  140, 255, 120),
    "orange":  (255, 160, 0,   130),
    "purple":  (180, 80,  255, 110),
}
BORDER = {
    "yellow":  (200, 160, 0),
    "green":   (0,   160, 60),
    "red":     (200, 0,   0),
    "blue":    (0,   80,  200),
    "orange":  (200, 100, 0),
    "purple":  (130, 0,   200),
}
DARK_BG   = (15,  15,  25)
TEXT_PRI  = (240, 240, 255)
TEXT_DIM  = (160, 160, 190)
GOLD      = (255, 215, 0)
ACCENT    = (255, 68,  68)


def _font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    name = "DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf"
    p = FONT_DIR / name
    return ImageFont.truetype(str(p), size) if p.exists() else ImageFont.load_default()


class SheetAnnotator:
    """
    Wraps a LibreOffice sheet screenshot and provides annotation methods.
    All methods return `self` for chaining.

    Example:
        ann = SheetAnnotator(img)
        ann.highlight(rect1, "green") \
           .highlight(rect2, "yellow") \
           .formula_bar("=SQRT(2*D7*D8/D9)") \
           .step_badge(2, "EOQ berechnen") \
           .arrow(rect1, "Enter formula here")
        final = ann.render(target_width=1920)
    """

    def __init__(self, sheet_img: Image.Image):
        self._sheet = sheet_img.convert("RGBA")
        self._overlay = Image.new("RGBA", sheet_img.size, (0, 0, 0, 0))
        self._draw = ImageDraw.Draw(self._overlay)
        self._annotations: list[dict] = []
        self._formula_text: str | None = None
        self._step_text: str | None = None
        self._step_num: int | None = None

    # ── Highlight a cell or range ─────────────────────────────────────────────
    def highlight(
        self,
        rect: CellRect,
        color: str = "yellow",
        border_width: int = 4,
        padding: int = 3,
    ) -> "SheetAnnotator":
        r = rect.pad(padding)
        fill = HIGHLIGHT.get(color, HIGHLIGHT["yellow"])
        border = BORDER.get(color, BORDER["yellow"])
        # Fill
        self._draw.rectangle([r.x1, r.y1, r.x2, r.y2], fill=fill)
        # Border
        for i in range(border_width):
            self._draw.rectangle(
                [r.x1-i, r.y1-i, r.x2+i, r.y2+i],
                outline=border + (255,),
            )
        return self

    def highlight_many(self, rects: list[CellRect], color: str = "yellow") -> "SheetAnnotator":
        for r in rects:
            self.highlight(r, color)
        return self

    # ── Arrow pointing to a cell with label ──────────────────────────────────
    def arrow(
        self,
        rect: CellRect,
        label: str,
        color: str = "orange",
        side: str = "right",  # "right", "left", "top", "bottom"
    ) -> "SheetAnnotator":
        cx, cy = rect.center
        rgb = BORDER.get(color, (255, 160, 0))
        rgba = rgb + (220,)

        offset = 130
        if side == "right":
            lx, ly = rect.x2 + offset, cy
            ax, ay = rect.x2 + 8, cy
        elif side == "left":
            lx, ly = rect.x1 - offset, cy
            ax, ay = rect.x1 - 8, cy
        elif side == "bottom":
            lx, ly = cx, rect.y2 + 50
            ax, ay = cx, rect.y2 + 8
        else:
            lx, ly = cx, rect.y1 - 50
            ax, ay = cx, rect.y1 - 8

        # Arrow line
        self._draw.line([(lx, ly), (ax, ay)], fill=rgba, width=3)
        # Arrowhead
        self._draw.polygon([
            (ax, ay), (ax-8, ay-8), (ax+8, ay-8)
            if side in ("top", "bottom") else
            (ax, ay), (ax-8, ay-8), (ax-8, ay+8)
        ], fill=rgba)
        # Label box
        tw = len(label) * 9 + 16
        th = 32
        self._draw.rounded_rectangle(
            [lx - tw//2, ly - th//2, lx + tw//2, ly + th//2],
            radius=6, fill=rgb + (200,),
        )
        self._draw.text(
            (lx, ly), label, font=_font(18, True),
            fill=(255, 255, 255, 255), anchor="mm",
        )
        return self

    # ── Formula bar at bottom ─────────────────────────────────────────────────
    def formula_bar(self, formula: str, label: str = "Excel-Formel:") -> "SheetAnnotator":
        self._formula_text = formula
        self._formula_label = label
        return self

    # ── Step badge (top right) ────────────────────────────────────────────────
    def step_badge(self, num: int, title: str) -> "SheetAnnotator":
        self._step_num = num
        self._step_text = title
        return self

    # ── Dim everything EXCEPT highlighted regions ─────────────────────────────
    def dim_rest(self, alpha: int = 140) -> "SheetAnnotator":
        dim = Image.new("RGBA", self._sheet.size, (0, 0, 0, alpha))
        # We'll apply this before the overlay in render()
        self._dim = dim
        return self

    # ── Render to final 1920×1080 frame ──────────────────────────────────────
    def render(
        self,
        target_width: int = 1920,
        target_height: int = 1080,
        bg_color: tuple = DARK_BG,
    ) -> Image.Image:
        # Composite sheet + overlay
        composed = Image.alpha_composite(self._sheet, self._overlay).convert("RGB")

        # Fit sheet into left ~65% of frame (leave right side for info panel)
        sheet_area_w = int(target_width * 0.64)
        sheet_area_h = target_height

        scale = min(sheet_area_w / composed.width, sheet_area_h / composed.height)
        new_w = int(composed.width  * scale)
        new_h = int(composed.height * scale)
        sheet_resized = composed.resize((new_w, new_h), Image.LANCZOS)

        # Canvas
        canvas = Image.new("RGB", (target_width, target_height), bg_color)
        # Center sheet vertically on left side
        sheet_x = (sheet_area_w - new_w) // 2
        sheet_y = (sheet_area_h - new_h) // 2
        canvas.paste(sheet_resized, (sheet_x, sheet_y))

        draw = ImageDraw.Draw(canvas)

        # Separator line
        sep_x = sheet_area_w + 8
        draw.line([(sep_x, 40), (sep_x, target_height - 40)], fill=(60, 60, 90), width=2)

        # ── Right info panel ─────────────────────────────────────────────────
        px = sep_x + 30
        py = 60

        # Step badge
        if self._step_num is not None:
            draw.rounded_rectangle([px, py, px + 60, py + 60], radius=10, fill=ACCENT)
            draw.text((px + 30, py + 30), str(self._step_num),
                      font=_font(32, True), fill=(255, 255, 255), anchor="mm")
            draw.text((px + 75, py + 30), self._step_text or "",
                      font=_font(24, True), fill=GOLD, anchor="lm")
            py += 80

        # Formula bar
        if self._formula_text:
            label = getattr(self, "_formula_label", "Excel-Formel:")
            draw.text((px, py), label, font=_font(18), fill=TEXT_DIM)
            py += 26
            # Formula box
            fw = target_width - px - 30
            fh = 52
            draw.rounded_rectangle([px, py, px + fw, py + fh], radius=8,
                                   fill=(25, 35, 55))
            draw.rounded_rectangle([px, py, px + fw, py + fh], radius=8,
                                   outline=GOLD + (0,), width=0)
            draw.rectangle([px, py, px + 4, py + fh], fill=GOLD)
            draw.text((px + 16, py + fh//2), self._formula_text,
                      font=_font(22, True), fill=GOLD, anchor="lm")
            py += fh + 20

        return canvas


def annotate_sheet(
    sheet_img: Image.Image,
    highlights: list[tuple[CellRect, str]] | None = None,
    formula: str | None = None,
    step_num: int | None = None,
    step_title: str | None = None,
    arrows: list[tuple[CellRect, str]] | None = None,
    **kwargs,
) -> Image.Image:
    """Convenience one-shot function."""
    ann = SheetAnnotator(sheet_img)
    for rect, color in (highlights or []):
        ann.highlight(rect, color)
    for rect, label in (arrows or []):
        ann.arrow(rect, label)
    if formula:
        ann.formula_bar(formula)
    if step_num is not None:
        ann.step_badge(step_num, step_title or "")
    return ann.render(**kwargs)


# ── Quick visual test ─────────────────────────────────────────────────────────
if __name__ == "__main__":
    from cell_mapper import find_colored_cells, CellMapper
    import msoffcrypto, openpyxl, io as _io

    img = Image.open("/tmp/lo_sheet12.png")

    # Detect green + yellow cells
    green  = find_colored_cells(img, "green")
    yellow = find_colored_cells(img, "yellow")

    with open("/home/raphael/Sara_Home/HSG/Bachelor/FS 26/OM/Pruefungen/Original/OM_23HS_Exam.xlsx", "rb") as f:
        office = msoffcrypto.OfficeFile(f)
        office.load_key(password="OMROCKS23")
        dec = _io.BytesIO(); office.decrypt(dec)
    wb = openpyxl.load_workbook(dec)
    mapper = CellMapper(wb["12"], img, dpi=150)

    # Build annotated frame
    ann = SheetAnnotator(img)
    for r in green:
        ann.highlight(r, "green")
    for r in yellow:
        ann.highlight(r, "yellow")
    ann.formula_bar("=SQRT(2*D7*D8/D9)", "Step 2 — EOQ berechnen:")
    ann.step_badge(2, "EOQ berechnen")

    frame = ann.render()
    frame.save("/tmp/annotator_test.png")
    print(f"Saved {frame.width}×{frame.height} → /tmp/annotator_test.png")
