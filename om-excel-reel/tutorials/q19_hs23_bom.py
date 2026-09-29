"""
Q19 HS23 — Multi-Level Bill of Materials: Battery Tester
Excel tutorial video: step-by-step solution walkthrough.

Actual exam data from OM_23HS_Exam.xlsx, Sheet 19 (password: OMROCKS23).
Answer: A) 2'750 CHF

Run: /storage/projekte/ki_pipeline_env_312/bin/python3 tutorials/q19_hs23_bom.py
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from excel_renderer import BOMTable
from render_om_excel_reel import make_title_card, make_answer_card, render_video

# ── BOM Data (from HS23 exam sheet 19, decrypted) ─────────────────────────────
# Total quantities & costs calculated bottom-up (see solution below)
BOM_ROWS = [
    # Level 1: 3 × NKW-231 per battery tester
    {"level": 1, "part": "NKW-231", "level_qty": 3,  "total_qty": 3,   "price": 10.32, "cost":  30.96},
    # Level 2 under NKW-231: 10 × LFS-121 per NKW → total 30
    {"level": 2, "part": "LFS-121", "level_qty": 10, "total_qty": 30,  "price":  8.56, "cost": 256.80},
    # Level 3 under LFS-121: 3 × KWG-294 per LFS → total 90
    {"level": 3, "part": "KWG-294", "level_qty": 3,  "total_qty": 90,  "price":  1.34, "cost": 120.60},
    # Level 3 under LFS-121: 4 × SGQ-201 per LFS → total 120
    {"level": 3, "part": "SGQ-201", "level_qty": 4,  "total_qty": 120, "price":  4.67, "cost": 560.40},
    # Level 2 under NKW-231: 2 × FBS-892 per NKW → total 6
    {"level": 2, "part": "FBS-892", "level_qty": 2,  "total_qty": 6,   "price": 17.44, "cost": 104.64},
    # Level 2 under NKW-231: 5 × ZHK-137 per NKW → total 15
    {"level": 2, "part": "ZHK-137", "level_qty": 5,  "total_qty": 15,  "price":  8.93, "cost": 133.95},
    # Level 1: 2 × GWL-120 per battery tester
    {"level": 1, "part": "GWL-120", "level_qty": 2,  "total_qty": 2,   "price":  7.23, "cost":  14.46},
    # Level 1: 6 × SBN-832 per battery tester
    {"level": 1, "part": "SBN-832", "level_qty": 6,  "total_qty": 6,   "price":  2.75, "cost":  16.50},
    # Level 2 under SBN-832: 10 × QLI-200 per SBN → total 60
    {"level": 2, "part": "QLI-200", "level_qty": 10, "total_qty": 60,  "price":  4.68, "cost": 280.80},
    # Level 3 under QLI-200: 3 × SGF-210 per QLI → total 180
    {"level": 3, "part": "SGF-210", "level_qty": 3,  "total_qty": 180, "price":  6.84, "cost": 1231.20},
]

TOTAL_COST = sum(r["cost"] for r in BOM_ROWS)  # = 2750.31 ≈ 2750


def bom_unknown(rows, hide_total_qty=True, hide_cost=True):
    """Return rows with unknowns blanked out (as they appear in the exam)."""
    result = []
    for r in rows:
        row = dict(r)
        if hide_total_qty:
            row["total_qty"] = None
        if hide_cost:
            row["cost"] = None
        result.append(row)
    return result


def bom_partial(rows, reveal_indices: list[int]) -> list[dict]:
    """Reveal total_qty and cost for specific row indices."""
    result = []
    for i, r in enumerate(rows):
        row = dict(r)
        if i not in reveal_indices:
            row["total_qty"] = None
            row["cost"] = None
        result.append(row)
    return result


def main():
    tbl = BOMTable(BOM_ROWS, col_widths=[100, 190, 120, 130, 150, 170])

    # ── Step definitions ──────────────────────────────────────────────────────
    steps = []

    # 0: Title card
    steps.append({
        "image": make_title_card(
            title="Q19 — Multi-Level BOM",
            subtitle="Calculate total production cost for 1 Battery Tester",
            points=4,
        ),
        "spoken": (
            "Question 19, four points. You are given a multi-level Bill of Materials "
            "for a battery tester. Your job: calculate the total production cost. "
            "This is a classic bottom-up calculation — let me show you exactly how."
        ),
    })

    # 1: Show full table with all unknowns
    steps.append({
        "image": tbl.render(
            highlight_rows=list(range(10)),
            step_label="STEP 1 — Read the BOM",
            formula_hint="10 parts across 3 levels. Columns: Level Qty × ... = Total Qty × Price = Cost",
        ),
        "spoken": (
            "The exam gives you this table. You see three levels. "
            "Level one parts go directly into the battery tester. "
            "Level two parts go into level one sub-assemblies. "
            "Level three parts go into level two. "
            "The Level Quantity tells you how many units per parent. "
            "You must calculate Total Quantity — that is units per finished battery tester."
        ),
    })

    # 2: Identify Level 3 parts (start bottom-up)
    l3_indices = [2, 3, 9]
    steps.append({
        "image": tbl.render(
            highlight_rows=l3_indices,
            step_label="STEP 2 — Start at Level 3",
            formula_hint="Total Qty = Level Qty × Parent's Total Qty",
        ),
        "spoken": (
            "Always start at the lowest level — Level 3. "
            "We have three Level 3 parts: KWG-294, SGQ-201, and SGF-210. "
            "For each one, the formula is: Total Quantity equals Level Quantity "
            "times the Total Quantity of its parent. "
            "In Excel, column H equals column G times the parent row's column H."
        ),
    })

    # 3: Reveal Level 3 totals with calculation shown
    partial_l3 = bom_partial(BOM_ROWS, [2, 3, 9])
    tbl_l3 = BOMTable(partial_l3, col_widths=[100, 190, 120, 130, 150, 170])
    steps.append({
        "image": tbl_l3.render(
            done_rows=l3_indices,
            step_label="STEP 2 — Level 3 solved",
            formula_hint=(
                "KWG-294: 3 × 30 = 90  |  SGQ-201: 4 × 30 = 120  |  SGF-210: 3 × 60 = 180"
            ),
        ),
        "spoken": (
            "KWG-294: level quantity 3, parent LFS-121 needs 30 total — so 3 times 30 equals 90. "
            "SGQ-201: 4 times 30 equals 120. "
            "SGF-210: 3 times QLI-200, which needs 60 — so 3 times 60 equals 180. "
            "Now the cost for each is simply Total Quantity times Price per Unit."
        ),
    })

    # 4: Reveal all total quantities
    partial_all_qty = []
    for r in BOM_ROWS:
        row = dict(r)
        row["cost"] = None
        partial_all_qty.append(row)
    tbl_qty = BOMTable(partial_all_qty, col_widths=[100, 190, 120, 130, 150, 170])
    steps.append({
        "image": tbl_qty.render(
            done_rows=list(range(10)),
            highlight_rows=[],
            step_label="STEP 3 — All Total Quantities",
            formula_hint="NKW-231: 3 | LFS-121: 3×10=30 | FBS-892: 3×2=6 | ZHK-137: 3×5=15 | SBN-832: 6 | QLI-200: 6×10=60",
        ),
        "spoken": (
            "Now all total quantities are filled in. "
            "NKW-231: 3. LFS-121: 3 times 10 is 30. FBS-892: 3 times 2 is 6. ZHK-137: 3 times 5 is 15. "
            "GWL-120: 2. SBN-832: 6. QLI-200: 6 times 10 is 60. "
            "In Excel: put the formula equals G times the parent's H in each cell. "
            "Level 1 total quantity is just the level quantity directly."
        ),
    })

    # 5: Reveal all costs
    tbl_full = BOMTable(BOM_ROWS, col_widths=[100, 190, 120, 130, 150, 170])
    steps.append({
        "image": tbl_full.render(
            done_rows=list(range(10)),
            step_label="STEP 4 — Calculate Costs",
            formula_hint="Cost = Total Qty × Price per Unit  →  Sum all rows",
        ),
        "spoken": (
            "Now calculate the cost for each row: Total Quantity times Price per Unit. "
            "In Excel: equals H times I. "
            "SGF-210 alone costs 180 times 6.84 — that is one thousand two hundred thirty-one. "
            "Sum the entire cost column with a SUM formula. "
            "The total comes to two thousand seven hundred fifty Swiss francs."
        ),
    })

    # 6: Answer card
    steps.append({
        "image": make_answer_card(
            answer="A)  2'750 CHF",
            value=f"Σ costs = {TOTAL_COST:.2f} ≈ 2'750 CHF",
        ),
        "spoken": (
            "The answer is A: two thousand seven hundred fifty Swiss francs. "
            "Key takeaway: build the Total Quantity column first bottom-up, "
            "then multiply by price — never skip the level structure. "
            "Four free points if you know this formula cold."
        ),
    })

    # ── Render ─────────────────────────────────────────────────────────────────
    output = render_video(
        steps=steps,
        output_name="om_q19_hs23_bom_excel_tutorial.mp4",
        voice="bm_george",
    )
    print(f"\nOutput: {output}")


if __name__ == "__main__":
    main()
