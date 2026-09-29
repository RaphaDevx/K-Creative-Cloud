"""
lo_screenshot.py — LibreOffice headless sheet → PIL Image
Exports any named sheet from any xlsx (encrypted or not) as a high-res PNG.
"""
from __future__ import annotations
import io, os, shutil, subprocess, tempfile
from pathlib import Path
from PIL import Image

try:
    import msoffcrypto
    HAS_CRYPTO = True
except ImportError:
    HAS_CRYPTO = False

import openpyxl


def capture_sheet(
    xlsx_path: str | Path,
    sheet_name: str,
    password: str | None = None,
    dpi: int = 150,
) -> Image.Image:
    """
    Export `sheet_name` from `xlsx_path` as a PIL Image using LibreOffice headless.

    Args:
        xlsx_path:  Path to the .xlsx file
        sheet_name: Exact name of the worksheet tab to export
        password:   File-level encryption password (msoffcrypto), if any
        dpi:        Export resolution (96=screen, 150=crisp, 300=print)

    Returns:
        PIL.Image.Image (RGB)
    """
    xlsx_path = Path(xlsx_path)

    with tempfile.TemporaryDirectory(prefix="lo_sheet_") as tmp:
        tmp = Path(tmp)
        work_xlsx = tmp / "sheet.xlsx"

        # ── 1. Decrypt if needed ──────────────────────────────────────────
        if password:
            if not HAS_CRYPTO:
                raise RuntimeError("msoffcrypto not installed — cannot decrypt")
            with open(xlsx_path, "rb") as f:
                office = msoffcrypto.OfficeFile(f)
                office.load_key(password=password)
                dec = io.BytesIO()
                office.decrypt(dec)
            raw_bytes = dec.getvalue()
        else:
            raw_bytes = xlsx_path.read_bytes()

        # ── 2. Set target sheet as active + hide others ───────────────────
        wb = openpyxl.load_workbook(io.BytesIO(raw_bytes))
        if sheet_name not in wb.sheetnames:
            raise ValueError(
                f"Sheet '{sheet_name}' not found. Available: {wb.sheetnames}"
            )
        # Make target sheet first and active
        target_idx = wb.sheetnames.index(sheet_name)
        wb.active = wb.worksheets[target_idx]

        # Move target sheet to position 0 so LO exports it first
        wb.move_sheet(sheet_name, offset=-target_idx)

        wb.save(str(work_xlsx))

        # ── 3. LibreOffice headless PNG export ────────────────────────────
        filter_opts = f"PixelWidth=0,PixelHeight=0,LogicalWidth=0,LogicalHeight=0"
        cmd = [
            "xvfb-run", "-a",
            "libreoffice", "--headless",
            "--convert-to", "png",
            "--outdir", str(tmp),
            str(work_xlsx),
        ]
        env = os.environ.copy()
        env["HOME"] = str(tmp)  # avoid LO locking issues with shared home

        result = subprocess.run(cmd, capture_output=True, text=True, env=env, timeout=30)
        if result.returncode != 0:
            raise RuntimeError(f"LibreOffice export failed:\n{result.stderr[-1000:]}")

        # ── 4. Load exported PNG ──────────────────────────────────────────
        png_path = tmp / "sheet.png"
        if not png_path.exists():
            raise RuntimeError(f"Export succeeded but PNG not found in {tmp}")

        img = Image.open(png_path).convert("RGB")

        # ── 5. Upscale if dpi > 96 (LO always exports at ~96 DPI) ───────
        if dpi > 96:
            scale = dpi / 96
            new_w = int(img.width * scale)
            new_h = int(img.height * scale)
            img = img.resize((new_w, new_h), Image.LANCZOS)

        return img


def capture_sheet_to_file(
    xlsx_path: str | Path,
    sheet_name: str,
    out_path: str | Path,
    password: str | None = None,
    dpi: int = 150,
) -> Path:
    """Convenience wrapper that saves PNG to disk."""
    img = capture_sheet(xlsx_path, sheet_name, password=password, dpi=dpi)
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    img.save(str(out_path))
    return out_path


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 3:
        print("Usage: lo_screenshot.py <xlsx> <sheet_name> [password] [out.png]")
        sys.exit(1)
    xlsx = sys.argv[1]
    sheet = sys.argv[2]
    pw = sys.argv[3] if len(sys.argv) > 3 else None
    out = sys.argv[4] if len(sys.argv) > 4 else "/tmp/lo_test_out.png"
    img = capture_sheet(xlsx, sheet, password=pw, dpi=150)
    img.save(out)
    print(f"Saved {img.width}×{img.height} → {out}")
