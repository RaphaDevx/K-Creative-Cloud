"""
cell_mapper.py — Maps Excel cell references to pixel coordinates in a LibreOffice screenshot.

Two modes:
  1. COLOR detection:  auto-find green (input) / yellow (answer) cells by fill color
  2. COORDINATE mode: calculate pixel rect from openpyxl column widths + row heights
"""
from __future__ import annotations
import io
from pathlib import Path
from dataclasses import dataclass
from typing import Optional

import numpy as np
from PIL import Image
import openpyxl
from openpyxl.utils import column_index_from_string, get_column_letter


# ── Calibration constants (empirically measured at 150 DPI) ──────────────────
DEFAULT_DPI         = 150
PX_PER_CHAR_96DPI   = 7.8    # 1 Excel char-width unit ≈ 7.8 px at 96 DPI
PX_PER_PT_96DPI     = 1.333  # 1 Excel row-height pt ≈ 1.333 px at 96 DPI
DEFAULT_ROW_HEIGHT  = 15.0   # Excel default row height in pts
DEFAULT_COL_WIDTH   = 8.43   # Excel default column width in char units


@dataclass
class CellRect:
    x1: int; y1: int; x2: int; y2: int

    @property
    def center(self):
        return ((self.x1 + self.x2) // 2, (self.y1 + self.y2) // 2)

    def pad(self, px: int) -> "CellRect":
        return CellRect(self.x1-px, self.y1-px, self.x2+px, self.y2+px)


class CellMapper:
    """
    Maps openpyxl worksheet cell refs → pixel coords in a LibreOffice screenshot.

    Usage:
        mapper = CellMapper(ws, img, dpi=150)
        rect = mapper.get_cell("D12")
        rect = mapper.get_range("D10:D15")
    """

    def __init__(
        self,
        ws: openpyxl.worksheet.worksheet.Worksheet,
        img: Image.Image,
        dpi: int = DEFAULT_DPI,
        margin_left: Optional[int] = None,
        margin_top: Optional[int] = None,
    ):
        self.ws = ws
        self.img = img
        self.dpi = dpi
        self._scale = dpi / 96.0
        self._px_char = PX_PER_CHAR_96DPI * self._scale
        self._px_pt   = PX_PER_PT_96DPI   * self._scale

        # Auto-detect margins if not given
        arr = np.array(img)
        if margin_left is None:
            margin_left = self._detect_content_start_x(arr)
        if margin_top is None:
            margin_top = self._detect_content_start_y(arr)

        self.margin_left = margin_left
        self.margin_top  = margin_top

        # Pre-compute cumulative column x-positions (1-indexed, col 1 = A)
        self._col_x = self._build_col_positions()
        self._row_y = self._build_row_positions()

    # ── Auto-detect content boundaries ───────────────────────────────────────
    def _detect_content_start_x(self, arr: np.ndarray) -> int:
        # Find first column with a consistent non-white strip (the left border)
        non_white = (arr[:,:,0] < 200) | (arr[:,:,1] < 200) | (arr[:,:,2] < 200)
        col_hits = np.sum(non_white, axis=0)
        for x in range(arr.shape[1]):
            if col_hits[x] > 5:
                return x + 2
        return 80  # fallback

    def _detect_content_start_y(self, arr: np.ndarray) -> int:
        non_white = (arr[:,:,0] < 200) | (arr[:,:,1] < 200) | (arr[:,:,2] < 200)
        row_hits = np.sum(non_white, axis=1)
        for y in range(arr.shape[0]):
            if row_hits[y] > 5:
                return y + 2
        return 80

    # ── Build position lookup tables ─────────────────────────────────────────
    def _build_col_positions(self) -> list[int]:
        """Returns list where index i = x-pixel start of column (i+1), col 1=A."""
        max_col = self.ws.max_column or 20
        positions = [self.margin_left]
        for col_idx in range(1, max_col + 1):
            letter = get_column_letter(col_idx)
            dim = self.ws.column_dimensions.get(letter)
            w = (dim.width if dim and dim.width else DEFAULT_COL_WIDTH)
            positions.append(positions[-1] + int(w * self._px_char))
        return positions

    def _build_row_positions(self) -> list[int]:
        """Returns list where index i = y-pixel start of row (i+1), row 1=top."""
        max_row = self.ws.max_row or 50
        positions = [self.margin_top]
        for row_idx in range(1, max_row + 1):
            dim = self.ws.row_dimensions.get(row_idx)
            h = (dim.height if dim and dim.height else DEFAULT_ROW_HEIGHT)
            positions.append(positions[-1] + int(h * self._px_pt))
        return positions

    # ── Public API ────────────────────────────────────────────────────────────
    def get_cell(self, cell_ref: str) -> CellRect:
        """Get pixel rect for a single cell, e.g. 'D12'."""
        col_letter = ""
        row_num = ""
        for ch in cell_ref:
            if ch.isalpha():
                col_letter += ch
            else:
                row_num += ch
        col_idx = column_index_from_string(col_letter)
        row_idx = int(row_num)
        return CellRect(
            x1=self._col_x[col_idx - 1],
            y1=self._row_y[row_idx - 1],
            x2=self._col_x[col_idx],
            y2=self._row_y[row_idx],
        )

    def get_range(self, cell_range: str) -> CellRect:
        """Get merged pixel rect for a range, e.g. 'D10:D15'."""
        parts = cell_range.split(":")
        if len(parts) == 1:
            return self.get_cell(parts[0])
        r1 = self.get_cell(parts[0])
        r2 = self.get_cell(parts[1])
        return CellRect(
            x1=min(r1.x1, r2.x1), y1=min(r1.y1, r2.y1),
            x2=max(r1.x2, r2.x2), y2=max(r1.y2, r2.y2),
        )


# ── Color-based cell finder ───────────────────────────────────────────────────

def find_colored_cells(
    img: Image.Image,
    color: str = "green",   # "green", "yellow", "blue", "orange"
    min_area: int = 200,
) -> list[CellRect]:
    """
    Find cells filled with a specific highlight color.
    Returns list of CellRect sorted top-to-bottom, left-to-right.

    LibreOffice renders Excel fills as antialiased colors:
      green  ≈ RGB(226, 240, 217)  — Excel light green fill
      yellow ≈ RGB(255, 255, 153)  — Excel yellow fill
    """
    arr = np.array(img).astype(int)
    R, G, B = arr[:,:,0], arr[:,:,1], arr[:,:,2]

    if color == "green":
        # G significantly > R and G significantly > B, but not too dark
        mask = (G - R > 8) & (G - B > 8) & (G > 150) & (G < 255)
    elif color == "yellow":
        mask = (R > 200) & (G > 200) & (B < 140) & (R > B + 80)
    elif color == "blue":
        mask = (B > 150) & (B > R + 30) & (B > G + 10)
    elif color == "orange":
        mask = (R > 200) & (G > 100) & (G < 180) & (B < 80)
    else:
        raise ValueError(f"Unknown color: {color}")

    return _extract_rects(mask, min_area)


def _extract_rects(mask: np.ndarray, min_area: int) -> list[CellRect]:
    """Extract non-overlapping bounding boxes from a binary mask using scanlines."""
    rects = []
    visited = np.zeros_like(mask, dtype=bool)
    ys, xs = np.where(mask)

    for y0, x0 in zip(ys, xs):
        if visited[y0, x0]:
            continue
        # Simple BFS flood fill
        queue = [(y0, x0)]
        pixels = []
        while queue:
            y, x = queue.pop()
            if y < 0 or y >= mask.shape[0] or x < 0 or x >= mask.shape[1]:
                continue
            if visited[y, x] or not mask[y, x]:
                continue
            visited[y, x] = True
            pixels.append((y, x))
            queue += [(y+1,x),(y-1,x),(y,x+1),(y,x-1)]

        if len(pixels) < min_area:
            continue
        py = [p[0] for p in pixels]
        px = [p[1] for p in pixels]
        rects.append(CellRect(min(px), min(py), max(px), max(py)))

    return sorted(rects, key=lambda r: (r.y1, r.x1))


# ── Quick test ────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import sys
    img = Image.open("/tmp/lo_sheet12.png")

    print("=== Color detection ===")
    for color in ("green", "yellow"):
        cells = find_colored_cells(img, color=color)
        print(f"{color}: {len(cells)} region(s)")
        for r in cells:
            print(f"  {r}")

    print("\n=== Coordinate mapping ===")
    import msoffcrypto, io as _io

    with open("/home/raphael/Sara_Home/HSG/Bachelor/FS 26/OM/Pruefungen/Original/OM_23HS_Exam.xlsx", "rb") as f:
        office = msoffcrypto.OfficeFile(f)
        office.load_key(password="OMROCKS23")
        dec = _io.BytesIO(); office.decrypt(dec)

    wb = openpyxl.load_workbook(dec)
    ws = wb["12"]
    mapper = CellMapper(ws, img, dpi=150)
    print(f"Margin left={mapper.margin_left}, top={mapper.margin_top}")
    for ref in ["C3", "D7", "D12", "D15"]:
        r = mapper.get_cell(ref)
        print(f"  {ref}: {r}")
