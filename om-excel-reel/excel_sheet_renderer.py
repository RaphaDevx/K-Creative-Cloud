"""
Pixel-perfect recreation of the OM_23HS_Exam.xlsx Sheet 19 layout.
Matches Bild 2 exactly: white bg, green input columns, yellow total row,
indented level structure, black grid borders.

Produces annotated 1920×1080 frames for tutorial video.
"""
from __future__ import annotations
from PIL import Image, ImageDraw, ImageFont
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional

# ── Colours matching the real Excel template (Bild 2) ─────────────────────────
WHITE        = (255, 255, 255)
LIGHT_GREY   = (242, 242, 242)   # alternating row bg
GREEN_FILL   = (198, 224, 180)   # Excel "light green" input cells
YELLOW_FILL  = (255, 255, 153)   # Total costs yellow
HEADER_FILL  = (217, 217, 217)   # grey header row
BORDER_CLR   = (166, 166, 166)   # Excel grid line colour
TITLE_BG     = (255, 255, 255)
BLACK        = (0, 0, 0)
DARK_GREY    = (64, 64, 64)
RED_TEXT     = (192, 0, 0)       # level numbers in red like real Excel

# Highlight overlays (RGBA)
HL_ACTIVE    = (255, 200, 0,  110)   # yellow — active cell being edited
HL_DONE      = (92,  184, 92, 100)   # green  — formula filled in
HL_FOCUS_COL = (173, 216, 230, 80)   # blue   — whole column highlight

FONT_DIR = Path("/usr/share/fonts/truetype/dejavu")

def _font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    name = "DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf"
    p = FONT_DIR / name
    return ImageFont.truetype(str(p), size) if p.exists() else ImageFont.load_default()


# ── Layout constants ───────────────────────────────────────────────────────────
# Real column widths from openpyxl (converted to pixels at ~8px per char-unit)
# C(7.46) D(8.0) E(9.33) F(18.53) G(42.33) H(34.53) I(30.73) J(32.66)
COL_SCALE = 7.0   # px per character unit

COLS = [
    ("C",  7.46,  "Level 1"),
    ("D",  8.00,  "Level 2"),
    ("E",  9.33,  "Level 3"),
    ("F", 18.53,  "Part"),
    ("G", 18.00,  "Level\nquantity"),
    ("H", 18.00,  "Total\nquantity"),   # GREEN
    ("I", 18.00,  "Price\nper unit"),
    ("J", 18.00,  "Costs for\ntotal quantity"),  # GREEN
]

# Pixel widths (calculated, then manually adjusted for readability)
COL_WIDTHS_PX = [52, 56, 65, 130, 130, 130, 130, 175]

ROW_H        = 34    # data row height px
HEADER_H     = 50    # header row height
TITLE_H      = 36    # title row height
TOTAL_H      = 36    # total costs row
TABLE_X      = 60    # left margin
TABLE_Y      = 100   # top margin (inside the frame panel)

GREEN_COLS   = {5, 7}   # column indices (0-based) that get green fill: H and J
LEVEL_COL_IX = {0, 1, 2}  # C, D, E are level columns

# ── Data rows ─────────────────────────────────────────────────────────────────
@dataclass
class BOMRow:
    level_col: int          # 0=C, 1=D, 2=E  (which col the level number is in)
    part: str
    level_qty: int
    price: float
    total_qty: Optional[int] = None    # None = blank (to be filled)
    cost: Optional[float]   = None    # None = blank (to be filled)

EXAM_ROWS: list[BOMRow] = [
    BOMRow(0, "NKW-231", 3,  10.32),
    BOMRow(1, "LFS-121", 10,  8.56),
    BOMRow(2, "KWG-294", 3,   1.34),
    BOMRow(2, "SGQ-201", 4,   4.67),
    BOMRow(1, "FBS-892", 2,  17.44),
    BOMRow(1, "ZHK-137", 5,   8.93),
    BOMRow(0, "GWL-120", 2,   7.23),
    BOMRow(0, "SBN-832", 6,   2.75),
    BOMRow(1, "QLI-200", 10,  4.68),
    BOMRow(2, "SGF-210", 3,   6.84),
]

# Solved values
SOLVED_TOTAL_QTY   = [3, 30, 90, 120, 6, 15, 2, 6, 60, 180]
SOLVED_COSTS       = [30.96, 256.80, 120.60, 560.40, 104.64, 133.95, 14.46, 16.50, 280.80, 1231.20]
SOLVED_TOTAL_COSTS = 2750.31

# Excel formulas (real column letters from the actual file)
FORMULAS_TOTAL_QTY = [
    "=G5",         # NKW-231 L1
    "=G6*H5",      # LFS-121 L2
    "=G7*H6",      # KWG-294 L3
    "=G8*H6",      # SGQ-201 L3
    "=G9*H5",      # FBS-892 L2 → parent NKW-231
    "=G10*H5",     # ZHK-137 L2 → parent NKW-231
    "=G11",        # GWL-120 L1
    "=G12",        # SBN-832 L1
    "=G13*H12",    # QLI-200 L2 → parent SBN-832
    "=G14*H13",    # SGF-210 L3 → parent QLI-200
]
FORMULAS_COSTS = [f"=H{5+i}*I{5+i}" for i in range(10)]
FORMULA_TOTAL  = "=SUM(J5:J14)"


class ExcelSheetRenderer:
    """
    Renders the BOM sheet as pixel-perfect Excel-lookalike frames.
    Supports per-cell highlighting for step-by-step tutorial.
    """

    def __init__(self, rows: list[BOMRow] = None):
        self.rows = rows or EXAM_ROWS
        self._compute_layout()

    def _compute_layout(self):
        """Compute pixel coordinates for each column and row."""
        self.col_x = []   # left x of each column
        x = TABLE_X
        for w in COL_WIDTHS_PX:
            self.col_x.append(x)
            x += w
        self.table_right = x

        # Row y positions: title + header + data rows + total
        self.title_y  = TABLE_Y
        self.header_y = TABLE_Y + TITLE_H
        self.row_y    = [self.header_y + HEADER_H + i * ROW_H for i in range(len(self.rows))]
        self.total_y  = self.row_y[-1] + ROW_H + 4

    def table_height(self) -> int:
        return self.total_y + TOTAL_H - TABLE_Y + 10

    def render_frame(
        self,
        # Per-row state: index → ('blank'|'active'|'formula'|'done')
        total_qty_state: dict[int, str] | None = None,
        cost_state:      dict[int, str] | None = None,
        total_state:     str = 'blank',     # state of Total Costs cell
        # Annotation
        formula_bar:     str | None = None,  # shown in "formula bar" at top
        step_label:      str | None = None,
        tip_text:        str | None = None,
        # Canvas
        canvas_w: int = 1920,
        canvas_h: int = 1080,
    ) -> Image.Image:

        tq = total_qty_state or {}
        cs = cost_state or {}

        canvas = Image.new("RGB", (canvas_w, canvas_h), (245, 245, 245))
        draw   = ImageDraw.Draw(canvas, "RGBA")

        # ── Top bar (formula bar simulation) ──────────────────────────────────
        draw.rectangle([0, 0, canvas_w, 56], fill=(240, 240, 240))
        draw.line([0, 56, canvas_w, 56], fill=(180, 180, 180), width=1)

        # Excel-style name box
        draw.rectangle([8, 12, 90, 44], fill=WHITE, outline=(150, 150, 150))
        if formula_bar:
            # Extract cell ref from formula bar text
            parts = formula_bar.split("  ", 1)
            cell_ref = parts[0] if len(parts) > 1 else ""
            formula  = parts[1] if len(parts) > 1 else formula_bar
            draw.text((49, 28), cell_ref, font=_font(14, bold=True),
                      fill=DARK_GREY, anchor="mm")
            # Formula bar box
            draw.rectangle([100, 12, canvas_w - 400, 44],
                           fill=WHITE, outline=(150, 150, 150))
            draw.text((110, 28), formula, font=_font(15),
                      fill=(0, 0, 200), anchor="lm")

        # fx label
        draw.text((94, 28), "fx", font=_font(14), fill=(80, 80, 80), anchor="lm")

        # Step label (top right)
        if step_label:
            draw.rectangle([canvas_w - 380, 8, canvas_w - 8, 48],
                           fill=(30, 30, 50), outline=(80, 80, 120))
            draw.text((canvas_w - 194, 28), step_label,
                      font=_font(15, bold=True), fill=(255, 200, 0), anchor="mm")

        # ── White sheet panel (the "Excel window") ────────────────────────────
        panel_y = 66
        draw.rectangle([0, panel_y, canvas_w, canvas_h], fill=WHITE)

        # Column header letters (A, B, C… like Excel)
        col_header_y = panel_y + 2
        col_header_h = 22
        for i, (x, w) in enumerate(zip(self.col_x, COL_WIDTHS_PX)):
            letter = chr(ord('C') + i)
            draw.rectangle([x, col_header_y, x+w-1, col_header_y+col_header_h],
                           fill=(218, 218, 218), outline=(166, 166, 166))
            draw.text((x + w//2, col_header_y + col_header_h//2), letter,
                      font=_font(11), fill=DARK_GREY, anchor="mm")

        # Row numbers (like Excel's row numbers on left)
        row_num_x = TABLE_X - 38
        for i, ry in enumerate(self.row_y):
            row_num = 5 + i
            draw.rectangle([row_num_x - 2, ry, TABLE_X - 2, ry + ROW_H - 1],
                           fill=(218, 218, 218), outline=(166, 166, 166))
            draw.text((row_num_x + 17, ry + ROW_H//2), str(row_num),
                      font=_font(11), fill=DARK_GREY, anchor="mm")

        # ── Render table ──────────────────────────────────────────────────────
        actual_y = panel_y + col_header_h + 4

        self._draw_title_row(draw, actual_y)
        self._draw_header_row(draw, actual_y + TITLE_H)
        self._draw_data_rows(draw, actual_y + TITLE_H + HEADER_H,
                             tq, cs)
        self._draw_total_row(draw, actual_y + TITLE_H + HEADER_H + len(self.rows) * ROW_H + 8,
                             total_state)

        # ── Right panel: Step explanation ─────────────────────────────────────
        right_x = self.table_right + 30
        if right_x < canvas_w - 20:
            draw.rectangle([right_x - 10, panel_y + 5, canvas_w - 10, canvas_h - 10],
                           fill=(15, 15, 30), outline=(60, 60, 100))
            if tip_text:
                self._draw_tip_panel(draw, right_x, panel_y + 20, canvas_w - 20, tip_text)

        # ── Highlight active/done column bands ────────────────────────────────
        # Already handled per-cell in data rows

        return canvas

    def _draw_title_row(self, draw, y):
        total_w = sum(COL_WIDTHS_PX)
        draw.rectangle([TABLE_X, y, TABLE_X + total_w, y + TITLE_H - 1],
                       fill=WHITE, outline=BORDER_CLR)
        draw.text((TABLE_X + 6, y + TITLE_H//2),
                  "Multi-level BOM list for 1 battery tester with 3 modules",
                  font=_font(13, bold=True), fill=BLACK, anchor="lm")

    def _draw_header_row(self, draw, y):
        for i, (col, w_ch, label) in enumerate(COLS):
            x = self.col_x[i]
            w = COL_WIDTHS_PX[i]
            fill = HEADER_FILL
            draw.rectangle([x, y, x+w-1, y+HEADER_H-1], fill=fill, outline=BORDER_CLR)
            lines = label.split('\n')
            if len(lines) == 2:
                draw.text((x+w//2, y+HEADER_H//2-9), lines[0],
                          font=_font(11, bold=True), fill=BLACK, anchor="mm")
                draw.text((x+w//2, y+HEADER_H//2+9), lines[1],
                          font=_font(11, bold=True), fill=BLACK, anchor="mm")
            else:
                draw.text((x+w//2, y+HEADER_H//2), label,
                          font=_font(11, bold=True), fill=BLACK, anchor="mm")

    def _draw_data_rows(self, draw, y_start, tq_state, cost_state):
        for row_i, row in enumerate(self.rows):
            ry = y_start + row_i * ROW_H
            bg = WHITE if row_i % 2 == 0 else LIGHT_GREY

            for col_i in range(len(COLS)):
                cx = self.col_x[col_i]
                cw = COL_WIDTHS_PX[col_i]

                # Column fill
                cell_bg = bg
                if col_i in GREEN_COLS:
                    cell_bg = GREEN_FILL

                draw.rectangle([cx, ry, cx+cw-1, ry+ROW_H-1],
                               fill=cell_bg, outline=BORDER_CLR)

                # Cell value / state overlays
                if col_i == row.level_col:
                    # Level number (red, indented)
                    level_num = col_i + 1
                    draw.text((cx+cw//2, ry+ROW_H//2), str(level_num),
                              font=_font(13, bold=True), fill=RED_TEXT, anchor="mm")

                elif col_i == 3:  # Part name
                    draw.text((cx+4, ry+ROW_H//2), row.part,
                              font=_font(12), fill=BLACK, anchor="lm")

                elif col_i == 4:  # Level qty
                    draw.text((cx+cw//2, ry+ROW_H//2), str(row.level_qty),
                              font=_font(12), fill=BLACK, anchor="mm")

                elif col_i == 5:  # Total qty (H) — state-driven
                    state = tq_state.get(row_i, 'blank')
                    self._draw_cell_state(draw, cx, ry, cw, ROW_H,
                                         state,
                                         value=str(SOLVED_TOTAL_QTY[row_i]),
                                         formula=FORMULAS_TOTAL_QTY[row_i])

                elif col_i == 6:  # Price per unit
                    draw.text((cx+cw//2, ry+ROW_H//2),
                              f"{row.price:.2f}".replace('.', ','),
                              font=_font(12), fill=BLACK, anchor="mm")

                elif col_i == 7:  # Costs (J) — state-driven
                    state = cost_state.get(row_i, 'blank')
                    self._draw_cell_state(draw, cx, ry, cw, ROW_H,
                                         state,
                                         value=f"{SOLVED_COSTS[row_i]:.2f}".replace('.', ','),
                                         formula=FORMULAS_COSTS[row_i])

    def _draw_cell_state(self, draw, cx, ry, cw, ch, state,
                         value: str, formula: str):
        """Draw a green-column cell based on its state."""
        if state == 'blank':
            # Empty green cell (as in original exam)
            pass  # already filled with GREEN_FILL

        elif state == 'active':
            # Blue outline = currently selected cell
            draw.rectangle([cx+1, ry+1, cx+cw-2, ry+ch-2],
                           fill=(204, 228, 247), outline=(0, 120, 215), width=2)
            # Show formula hint in grey
            draw.text((cx+cw//2, ry+ch//2), formula,
                      font=_font(10), fill=(100, 100, 200), anchor="mm")

        elif state == 'formula':
            # Cell shows formula being typed
            draw.rectangle([cx, ry, cx+cw-1, ry+ch-1],
                           fill=(255, 255, 200), outline=(0, 120, 215), width=2)
            draw.text((cx+cw//2, ry+ch//2), formula,
                      font=_font(10, bold=True), fill=(0, 0, 180), anchor="mm")

        elif state == 'done':
            # Cell shows calculated value (green tint)
            draw.rectangle([cx, ry, cx+cw-1, ry+ch-1],
                           fill=(198, 239, 206), outline=BORDER_CLR)
            draw.text((cx+cw//2, ry+ch//2), value,
                      font=_font(12, bold=True), fill=(0, 97, 0), anchor="mm")

    def _draw_total_row(self, draw, ry, state):
        total_w = sum(COL_WIDTHS_PX)
        # Label cell (spans C through I)
        label_w = sum(COL_WIDTHS_PX[:7])
        draw.rectangle([TABLE_X, ry, TABLE_X+label_w-1, ry+TOTAL_H-1],
                       fill=WHITE, outline=BORDER_CLR)
        draw.text((TABLE_X + label_w - 8, ry+TOTAL_H//2), "Total costs",
                  font=_font(13, bold=True), fill=BLACK, anchor="rm")

        # Value cell (J = index 7)
        cx = self.col_x[7]
        cw = COL_WIDTHS_PX[7]
        if state == 'blank':
            draw.rectangle([cx, ry, cx+cw-1, ry+TOTAL_H-1],
                           fill=YELLOW_FILL, outline=BORDER_CLR)
            draw.text((cx+cw//2, ry+TOTAL_H//2), "0",
                      font=_font(12), fill=DARK_GREY, anchor="mm")
        elif state == 'active':
            draw.rectangle([cx, ry, cx+cw-1, ry+TOTAL_H-1],
                           fill=YELLOW_FILL, outline=(0,120,215), width=2)
            draw.text((cx+cw//2, ry+TOTAL_H//2), FORMULA_TOTAL,
                      font=_font(10), fill=(0, 0, 180), anchor="mm")
        elif state == 'done':
            draw.rectangle([cx, ry, cx+cw-1, ry+TOTAL_H-1],
                           fill=YELLOW_FILL, outline=BORDER_CLR)
            draw.text((cx+cw//2, ry+TOTAL_H//2),
                      f"{SOLVED_TOTAL_COSTS:.2f}".replace('.', ','),
                      font=_font(13, bold=True), fill=(0, 97, 0), anchor="mm")

    def _draw_tip_panel(self, draw, x, y, x_end, text: str):
        """Right-side explanation panel."""
        w = x_end - x - 10
        lines = text.split('\n')
        ty = y + 10
        for line in lines:
            if line.startswith('##'):
                draw.text((x+10, ty), line[2:].strip(),
                          font=_font(16, bold=True), fill=(255, 200, 0), anchor="lm")
                ty += 28
            elif line.startswith('#'):
                draw.text((x+10, ty), line[1:].strip(),
                          font=_font(14, bold=True), fill=(150, 200, 255), anchor="lm")
                ty += 22
            elif line.startswith('→'):
                draw.text((x+10, ty), line,
                          font=_font(13, bold=True), fill=(92, 184, 92), anchor="lm")
                ty += 20
            elif line.startswith('⚠'):
                draw.text((x+10, ty), line,
                          font=_font(12), fill=(255, 160, 0), anchor="lm")
                ty += 20
            elif line == '---':
                draw.line([x+10, ty+5, x_end-20, ty+5], fill=(60, 60, 90), width=1)
                ty += 14
            elif line.strip() == '':
                ty += 10
            else:
                # Word-wrap if too wide
                draw.text((x+10, ty), line,
                          font=_font(12), fill=(200, 200, 220), anchor="lm")
                ty += 18
