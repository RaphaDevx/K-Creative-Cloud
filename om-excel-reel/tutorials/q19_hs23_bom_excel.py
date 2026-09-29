"""
Q19 HS23 — BOM Excel Tutorial
Uses pixel-perfect Excel recreation + real cell references from OM_23HS_Exam.xlsx
Answer: A) 2'750 CHF

Run: /storage/projekte/ki_pipeline_env_312/bin/python3 tutorials/q19_hs23_bom_excel.py
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from excel_sheet_renderer import ExcelSheetRenderer, FORMULAS_TOTAL_QTY, FORMULAS_COSTS, FORMULA_TOTAL
from render_om_excel_reel import render_video, make_title_card, make_answer_card

R = ExcelSheetRenderer()

def blank():
    return {i: 'blank' for i in range(10)}

def state(done=(), active=None):
    s = blank()
    for i in done:
        s[i] = 'done'
    if active is not None:
        s[active] = 'active'
    return s

steps = []

# ── 0: Title ──────────────────────────────────────────────────────────────────
steps.append({
    "image": make_title_card(
        "Q19 — Multi-Level BOM",
        "OM_23HS_Exam.xlsx  ·  Worksheet «19»  ·  4 Points",
        4,
    ),
    "spoken": (
        "Question 19 from the HS 2023 exam — four points. Open worksheet 19 in "
        "the Excel file. You see a multi-level Bill of Materials for one battery "
        "tester. Two columns are blank and highlighted in green: Total quantity "
        "in column H, and Costs for total quantity in column J. "
        "The yellow cell at the bottom shows zero — that is where the answer goes. "
        "Let me walk you through every single formula, step by step."
    ),
})

# ── 1: The blank Excel sheet as it appears in the exam ────────────────────────
steps.append({
    "image": R.render_frame(
        total_qty_state=blank(),
        cost_state=blank(),
        total_state='blank',
        step_label="EXAM STATE — all blanks",
        tip_text=(
            "## This is what you open\n"
            "\n"
            "# Green columns = YOUR INPUT\n"
            "→ H: Total quantity\n"
            "→ J: Costs for total quantity\n"
            "\n"
            "# Yellow cell = ANSWER\n"
            "→ J16: Total costs\n"
            "\n"
            "---\n"
            "# Real column letters:\n"
            "C/D/E = Level (indented)\n"
            "F = Part name\n"
            "G = Level quantity\n"
            "H = Total quantity ← fill\n"
            "I = Price per unit\n"
            "J = Costs ← fill\n"
        ),
    ),
    "spoken": (
        "This is the sheet exactly as the exam opens it. "
        "Column H — Total quantity — is green and empty. "
        "Column J — Costs for total quantity — also green and empty. "
        "The yellow cell J16 says zero and will become your answer. "
        "Notice how the level column is split across C, D, and E: "
        "a level one part has its number in C, level two in D, level three in E — "
        "that indentation is how you read the tree structure."
    ),
})

# ── 2: Explain the tree structure ─────────────────────────────────────────────
steps.append({
    "image": R.render_frame(
        total_qty_state=blank(),
        cost_state=blank(),
        total_state='blank',
        step_label="STEP 1 — Read the BOM tree",
        tip_text=(
            "## BOM Tree Logic\n"
            "\n"
            "Battery Tester (root)\n"
            "│\n"
            "├─ L1: NKW-231 × 3\n"
            "│   ├─ L2: LFS-121 × 10\n"
            "│   │   ├─ L3: KWG-294 × 3\n"
            "│   │   └─ L3: SGQ-201 × 4\n"
            "│   ├─ L2: FBS-892 × 2\n"
            "│   └─ L2: ZHK-137 × 5\n"
            "│\n"
            "├─ L1: GWL-120 × 2\n"
            "│\n"
            "└─ L1: SBN-832 × 6\n"
            "    └─ L2: QLI-200 × 10\n"
            "        └─ L3: SGF-210 × 3\n"
            "\n"
            "---\n"
            "⚠ Level Qty = qty per PARENT\n"
            "⚠ Total Qty = qty per TESTER\n"
        ),
    ),
    "spoken": (
        "Before entering any formula, read the tree. "
        "NKW-231 is a Level 1 part — you need 3 per battery tester. "
        "Under NKW-231 sits LFS-121 at Level 2 — you need 10 per NKW-231. "
        "Under LFS-121 sit KWG-294 and SGQ-201 at Level 3. "
        "The key distinction: Level Quantity means per parent, "
        "Total Quantity means per finished battery tester. "
        "That is the conversion you calculate in column H."
    ),
})

# ── 3: H5 — NKW-231 Level 1 ───────────────────────────────────────────────────
steps.append({
    "image": R.render_frame(
        total_qty_state=state(active=0),
        cost_state=blank(),
        total_state='blank',
        formula_bar=f"H5  {FORMULAS_TOTAL_QTY[0]}",
        step_label="H5 — Level 1 part",
        tip_text=(
            "## Click cell H5\n"
            "\n"
            "NKW-231 is Level 1.\n"
            "Level 1 parts go directly\n"
            "into the finished product.\n"
            "\n"
            "→ Total Qty = Level Qty\n"
            "→ Formula:  =G5\n"
            "\n"
            "Result: 3\n"
            "\n"
            "---\n"
            "# Rule for ALL Level 1 rows:\n"
            "=G[row]  (copy Level Qty)\n"
        ),
    ),
    "spoken": (
        "Click cell H5, which is the Total quantity for NKW-231. "
        "This is a Level 1 part — it goes directly into the battery tester. "
        "So Total Quantity simply equals Level Quantity. "
        "Type equals G5. Press Enter. The result is 3. "
        "Remember this rule: every Level 1 row is just equals G."
    ),
})

# ── 4: H6 — LFS-121 Level 2 ──────────────────────────────────────────────────
steps.append({
    "image": R.render_frame(
        total_qty_state=state(done=(0,), active=1),
        cost_state=blank(),
        total_state='blank',
        formula_bar=f"H6  {FORMULAS_TOTAL_QTY[1]}",
        step_label="H6 — Level 2: × parent H5",
        tip_text=(
            "## Click cell H6\n"
            "\n"
            "LFS-121 is Level 2.\n"
            "Parent = NKW-231 (H5 = 3)\n"
            "\n"
            "→ Formula: =G6*H5\n"
            "→ 10 × 3 = 30\n"
            "\n"
            "---\n"
            "# Rule for Level 2:\n"
            "=G[row] * H[parent L1 row]\n"
            "\n"
            "⚠ Parent = the L1 row\n"
            "  ABOVE this L2 block\n"
        ),
    ),
    "spoken": (
        "Cell H6 — LFS-121 is Level 2. "
        "Its parent is NKW-231 in H5 which has total quantity 3. "
        "Formula: equals G6 times H5. "
        "That is 10 times 3 equals 30. "
        "For every Level 2 part: multiply the level quantity by the Total Quantity "
        "of its Level 1 parent above."
    ),
})

# ── 5: H7, H8 — Level 3 under LFS-121 ────────────────────────────────────────
steps.append({
    "image": R.render_frame(
        total_qty_state=state(done=(0,1), active=2),
        cost_state=blank(),
        total_state='blank',
        formula_bar=f"H7  {FORMULAS_TOTAL_QTY[2]}",
        step_label="H7/H8 — Level 3: × parent H6",
        tip_text=(
            "## H7: KWG-294 (Level 3)\n"
            "\n"
            "Parent = LFS-121 (H6 = 30)\n"
            "→ Formula: =G7*H6\n"
            "→ 3 × 30 = 90\n"
            "\n"
            "---\n"
            "## H8: SGQ-201 (Level 3)\n"
            "\n"
            "Same parent H6!\n"
            "→ Formula: =G8*H6\n"
            "→ 4 × 30 = 120\n"
            "\n"
            "---\n"
            "⚠ Both L3 parts under\n"
            "  LFS-121 reference H6\n"
        ),
    ),
    "spoken": (
        "H7 for KWG-294 — Level 3 under LFS-121. "
        "Parent is H6 with 30 total units. "
        "Formula: equals G7 times H6. That is 3 times 30 equals 90. "
        "H8 for SGQ-201 — also Level 3 under LFS-121, same parent H6. "
        "Formula: equals G8 times H6. That is 4 times 30 equals 120. "
        "Key point: both Level 3 parts in this branch reference the same parent H6."
    ),
})

# ── 6: H9, H10 — FBS-892 and ZHK-137 back up to L2 under NKW-231 ────────────
steps.append({
    "image": R.render_frame(
        total_qty_state=state(done=(0,1,2,3), active=4),
        cost_state=blank(),
        total_state='blank',
        formula_bar=f"H9  {FORMULAS_TOTAL_QTY[4]}",
        step_label="H9/H10 — back to L2, parent = H5",
        tip_text=(
            "## H9: FBS-892 (Level 2)\n"
            "\n"
            "BACK to L2 — parent is\n"
            "NKW-231 again → H5!\n"
            "→ Formula: =G9*H5\n"
            "→ 2 × 3 = 6\n"
            "\n"
            "---\n"
            "## H10: ZHK-137 (Level 2)\n"
            "\n"
            "→ Formula: =G10*H5\n"
            "→ 5 × 3 = 15\n"
            "\n"
            "---\n"
            "⚠ Common mistake:\n"
            "  using H9 as parent for\n"
            "  H10 — WRONG!\n"
            "  Both reference H5.\n"
        ),
    ),
    "spoken": (
        "H9 for FBS-892 — back to Level 2 under NKW-231. "
        "The parent is NKW-231 in H5, not the row above. "
        "Formula: equals G9 times H5. That is 2 times 3 equals 6. "
        "H10 for ZHK-137 — same Level 2 block, same parent H5. "
        "Formula: equals G10 times H5. That is 5 times 3 equals 15. "
        "This is the most common mistake in the exam: "
        "referencing the wrong parent row. Always trace back to the Level 1 above."
    ),
})

# ── 7: H11, H12 — new L1 parts ───────────────────────────────────────────────
steps.append({
    "image": R.render_frame(
        total_qty_state=state(done=(0,1,2,3,4,5), active=6),
        cost_state=blank(),
        total_state='blank',
        formula_bar=f"H11  {FORMULAS_TOTAL_QTY[6]}",
        step_label="H11/H12 — new Level 1 parts",
        tip_text=(
            "## H11: GWL-120 (Level 1)\n"
            "\n"
            "→ Formula: =G11\n"
            "→ Result: 2\n"
            "\n"
            "---\n"
            "## H12: SBN-832 (Level 1)\n"
            "\n"
            "→ Formula: =G12\n"
            "→ Result: 6\n"
            "\n"
            "---\n"
            "# Rule confirmed:\n"
            "All L1 rows: =G[row]\n"
        ),
    ),
    "spoken": (
        "H11 for GWL-120 — a fresh Level 1 part. "
        "Formula: equals G11. Result: 2. "
        "H12 for SBN-832 — another Level 1 part. "
        "Formula: equals G12. Result: 6. "
        "Simple — every Level 1 total quantity is just the level quantity itself."
    ),
})

# ── 8: H13, H14 — second L2/L3 branch ────────────────────────────────────────
steps.append({
    "image": R.render_frame(
        total_qty_state=state(done=range(8), active=8),
        cost_state=blank(),
        total_state='blank',
        formula_bar=f"H13  {FORMULAS_TOTAL_QTY[8]}",
        step_label="H13/H14 — second branch",
        tip_text=(
            "## H13: QLI-200 (Level 2)\n"
            "\n"
            "Parent = SBN-832 → H12 = 6\n"
            "→ Formula: =G13*H12\n"
            "→ 10 × 6 = 60\n"
            "\n"
            "---\n"
            "## H14: SGF-210 (Level 3)\n"
            "\n"
            "Parent = QLI-200 → H13 = 60\n"
            "→ Formula: =G14*H13\n"
            "→ 3 × 60 = 180\n"
            "\n"
            "---\n"
            "→ Column H complete!\n"
        ),
    ),
    "spoken": (
        "H13 for QLI-200 — Level 2 under SBN-832. "
        "Parent is H12 which equals 6. "
        "Formula: equals G13 times H12. That is 10 times 6 equals 60. "
        "H14 for SGF-210 — Level 3 under QLI-200. "
        "Parent is H13 which equals 60. "
        "Formula: equals G14 times H13. That is 3 times 60 equals 180. "
        "Column H is now complete. Notice: SGF-210 alone requires 180 units — "
        "the deepest parts often dominate the cost."
    ),
})

# ── 9: Column H done — now column J costs ─────────────────────────────────────
steps.append({
    "image": R.render_frame(
        total_qty_state={i: 'done' for i in range(10)},
        cost_state=state(active=0),
        total_state='blank',
        formula_bar=f"J5  {FORMULAS_COSTS[0]}",
        step_label="STEP 2 — Column J: Costs",
        tip_text=(
            "## All H done! Now column J\n"
            "\n"
            "Formula for EVERY row:\n"
            "→ =H[row] * I[row]\n"
            "\n"
            "Total Qty × Price/Unit\n"
            "\n"
            "---\n"
            "## J5: NKW-231\n"
            "=H5*I5\n"
            "= 3 × 10.32 = 30.96\n"
            "\n"
            "---\n"
            "# Tip: Enter J5 formula,\n"
            "then drag down to J14!\n"
            "All formulas are identical\n"
            "in structure.\n"
        ),
    ),
    "spoken": (
        "Column H is complete. Now column J — Costs for total quantity. "
        "This is the easiest part: every single row uses the same formula. "
        "Click J5. Type equals H5 times I5. Press Enter. "
        "That is 3 times 10.32 equals 30.96. "
        "Then select J5 again and drag the fill handle all the way down to J14. "
        "Excel fills every row automatically since the formula structure is identical."
    ),
})

# ── 10: All costs filled ──────────────────────────────────────────────────────
steps.append({
    "image": R.render_frame(
        total_qty_state={i: 'done' for i in range(10)},
        cost_state={i: 'done' for i in range(10)},
        total_state='active',
        formula_bar=f"J16  {FORMULA_TOTAL}",
        step_label="STEP 3 — J16: Total costs",
        tip_text=(
            "## All J rows filled!\n"
            "\n"
            "Last step: yellow cell J16\n"
            "\n"
            "→ Formula: =SUM(J5:J14)\n"
            "\n"
            "---\n"
            "# Spot-check:\n"
            "SGF-210: 180 × 6.84\n"
            "= 1231.20 (biggest!)\n"
            "\n"
            "SUM of all 10 rows:\n"
            "= 2750.31\n"
            "≈ 2750 CHF\n"
            "\n"
            "---\n"
            "→ Answer: A) 2'750 CHF\n"
        ),
    ),
    "spoken": (
        "All cost cells filled. Click the yellow cell J16 — Total costs. "
        "Type equals SUM open parenthesis J5 colon J14 close parenthesis. "
        "Press Enter. "
        "The result is 2750.31 Swiss francs, which rounds to 2750. "
        "The answer is A — two thousand seven hundred fifty Swiss francs. "
        "Largest single contributor: SGF-210 at 180 units times 6.84 equals 1231 francs. "
        "Always double-check your deepest level parts — they carry the most weight."
    ),
})

# ── 11: Answer card ───────────────────────────────────────────────────────────
steps.append({
    "image": make_answer_card(
        "A)  2'750 CHF",
        "=SUM(J5:J14)  →  2750.31 ≈ 2750",
    ),
    "spoken": (
        "Answer A: 2750 Swiss francs. "
        "The three formulas you need: "
        "equals G for all Level 1 rows in column H. "
        "Equals G times parent H for Level 2 and 3 rows. "
        "Equals H times I for every cost row in column J. "
        "And equals SUM J5 to J14 for the total. "
        "Four points — free if you know the tree."
    ),
})

# ── Render ─────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    from render_om_excel_reel import render_video
    render_video(
        steps=steps,
        output_name="om_q19_hs23_bom_excel_v2.mp4",
        voice="bm_george",
    )
