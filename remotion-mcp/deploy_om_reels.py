#!/usr/bin/env python3
"""
Deploy OM reels to Supabase + update K-Learning feed-data.js + git push.
Run after rendering any OM reel with render_om_reel.py.

Usage:
  /storage/projekte/ki_pipeline_env_312/bin/python3 deploy_om_reels.py
  /storage/projekte/ki_pipeline_env_312/bin/python3 deploy_om_reels.py --file om_mrp1_material_requirements.mp4
"""
import subprocess, json, re, os, sys, time
from pathlib import Path

SUPABASE_URL = "https://ifmwcgwfvunjbnfwwbtr.supabase.co"
SUPABASE_KEY = os.environ.get("SUPABASE_ANON_KEY", "sb_publishable__h4cSWEEpNBjY3XGPvh0_A_ipyoeEjO")
BUCKET = "videos"
OM_REELS_DIR = Path("/home/raphael/Sara_Home/HSG/Bachelor/FS 26/OM/Reels")
FEED_DATA = Path("/home/raphael/K-Learning/data/feed-data.js")

# All OM reels metadata — add new reels here
REELS_META = [
    {
        "id": "om-sv-bullwhip",
        "filename": "om_bullwhip_effekt.mp4",
        "title": "Bullwhip-Effekt",
        "subtitle": "Warum kleine Schwankungen sich upstream aufschaukeln",
        "description": "Bullwhip-Effekt: Ursachen (Preis, Forecasts, Batching), Richtung (UPSTREAM!), und wie Koordination ihn reduziert.",
        "topics": ["Bullwhip-Effekt", "SCM", "Upstream", "Koordination", "Prüfungsfalle"],
        "block": "Block 4 — Supply Chain Management",
        "emoji": "🐂",
        "duration": "1:35",
    },
    {
        "id": "om-sv-epq",
        "filename": "om_epq_lagerbestand.mp4",
        "title": "EPQ Durchschnittslager",
        "subtitle": "Q*/2 × (1−d/p) — der Korrekturfaktor erklärt",
        "description": "EPQ vs EOQ: Warum EPQ = Q*/2 × (1−d/p) und nicht einfach Q*/2. Excel-Formel Schritt für Schritt.",
        "topics": ["EPQ", "EOQ", "Durchschnittslager", "Excel", "Prüfungsfalle"],
        "block": "Block 2 — Inventory Management",
        "emoji": "📦",
        "duration": "1:25",
    },
    {
        "id": "om-sv-mrp2-schritte",
        "filename": "om_mrp2_schritte.mp4",
        "title": "MRP II — 5 Schritte",
        "subtitle": "Business Planning → S&OP → MPS → MRP → PAC",
        "description": "MRP II in 80 Sekunden: Die 5 Schritte, ihre Frequenzen, und warum MRP = Schritt 4 (wöchentlich).",
        "topics": ["MRP II", "5 Schritte", "Produktionsplanung", "Prüfungsfalle"],
        "block": "Block 3 — Production Management",
        "emoji": "🏭",
        "duration": "1:18",
    },
    {
        "id": "om-sv-newsvendor-cr",
        "filename": "om_newsvendor_critical_ratio.mp4",
        "title": "Newsvendor Critical Ratio",
        "subtitle": "CR = Cu/(Cu+Co) — optimaler Servicegrad",
        "description": "Newsvendor-Modell: Critical Ratio herleiten und den optimalen Bestellpunkt bestimmen. Wann ist CR < 0.5?",
        "topics": ["Newsvendor", "Critical Ratio", "Servicegrad", "Cu", "Co"],
        "block": "Block 2 — Inventory Management",
        "emoji": "📰",
        "duration": "2:10",
    },
    {
        "id": "om-sv-newsvendor-excel",
        "filename": "om_newsvendor_excel_stepbystep.mp4",
        "title": "Newsvendor Excel",
        "subtitle": "ROP = μ + NORM.S.INV(SL)×σ — Schritt für Schritt",
        "description": "Newsvendor in Excel: Die richtige Formel für ROP, die häufigste Falle (=μ*SL) und wie NORM.S.INV korrekt eingesetzt wird.",
        "topics": ["Newsvendor", "ROP", "NORM.S.INV", "Excel", "Prüfungsfalle"],
        "block": "Block 2 — Inventory Management",
        "emoji": "📊",
        "duration": "1:52",
    },
    {
        "id": "om-sv-quantity-discount",
        "filename": "om_q12_quantity_discount.mp4",
        "title": "Quantity Discount (Q12 HS23)",
        "subtitle": "Welche Bestellmenge minimiert Gesamtkosten mit Rabattstufen?",
        "description": "Quantity Discount in Excel: EOQ pro Preisstufe berechnen, Feasibility prüfen, Gesamtkosten vergleichen.",
        "topics": ["Quantity Discount", "EOQ", "Gesamtkosten", "Excel", "HS23"],
        "block": "Block 2 — Inventory Management",
        "emoji": "💰",
        "duration": "5:12",
    },
    {
        "id": "om-sv-bom-excel",
        "filename": "om_q19_hs23_bom_excel_v2.mp4",
        "title": "BOM Excel (Q19 HS23)",
        "subtitle": "Multi-Level Stückliste bottom-up berechnen",
        "description": "Bill of Materials in Excel: Bottom-up Berechnung, Menge×Preis (nicht +!), Multi-Level-Hierarchie am HS23 Prüfungsbeispiel.",
        "topics": ["BOM", "Bill of Materials", "Multi-Level", "Excel", "HS23"],
        "block": "Block 3 — Production Management",
        "emoji": "🌳",
        "duration": "5:10",
    },
    {
        "id": "om-sv-sc-postponement",
        "filename": "om_sc_without_postponement.mp4",
        "title": "Supply Chain ohne Postponement",
        "subtitle": "Safety Stock addiert sich — Pooling reduziert ihn",
        "description": "Was passiert ohne Postponement? Safety Stocks addieren sich. Mit Pooling werden sie durch Varianzreduktion kleiner.",
        "topics": ["Postponement", "Safety Stock", "Pooling", "SCM"],
        "block": "Block 4 — Supply Chain Management",
        "emoji": "🔗",
        "duration": "7:12",
    },
    {
        "id": "om-sv-mrp1",
        "filename": "om_mrp1_material_requirements.mp4",
        "title": "MRP I — Material Requirements Planning",
        "subtitle": "Gross → Net → Offset → Release in unter 2 Min.",
        "description": "MRP I von Grund auf: 3 Inputs (MPS, BOM, Inventory), Gross→Net Berechnung, Lead Time Offset rückwärts, Multi-Level Top-Down.",
        "topics": ["MRP I", "MRP", "BOM", "Lead Time", "Net Requirements"],
        "block": "Block 3 — Production Management",
        "emoji": "📋",
        "duration": "1:40",
    },
    {
        "id": "om-sv-mrp2-vollstaendig",
        "filename": "om_mrp2_vollstaendig.mp4",
        "title": "MRP II — 3 Prüfungsfallen",
        "subtitle": "5 Schritte, Schritt 4 = wöchentlich, Feedback-Loop",
        "description": "MRP II vollständig: 5 Schritte, MRP = Schritt 4 wöchentlich (NICHT jährlich!), S&OP aggregiert, Closed-Loop mit Feedback.",
        "topics": ["MRP II", "Prüfungsfalle", "5 Schritte", "Feedback", "Wöchentlich"],
        "block": "Block 3 — Production Management",
        "emoji": "⚙️",
        "duration": "1:55",
    },
    {
        "id": "stat-sigma-standardfehler",
        "filename": "sigma_vs_standardfehler.mp4",
        "title": "σ vs σ_x̄",
        "subtitle": "Warum Gruppen 6× stabiler sind als Einzelpersonen",
        "description": "σ = Streuung einzelner Personen. σ_x̄ = σ/√n = Streuung von Gruppenmittelwerten. Mit n=36 und σ=15: σ_x̄ = 2.5 — 6× kleiner. Prüfungsfalle: im Rechner σ_x̄ eingeben, nicht σ!",
        "topics": ["Standardfehler", "Stichprobenverteilung", "Normalverteilung", "Prüfungsfalle", "TI-30X Pro"],
        "block": "Block 4 — Stichprobenverteilungen",
        "emoji": "📊",
        "duration": "1:37",
    },
]


def get_duration_str(filename):
    local_path = OM_REELS_DIR / filename
    if not local_path.exists():
        return "1:40"
    r = subprocess.run(
        ["ffprobe", "-v", "quiet", "-show_entries", "format=duration", "-of", "csv=p=0", str(local_path)],
        capture_output=True, text=True)
    try:
        secs = float(r.stdout.strip())
        m, s = divmod(int(secs), 60)
        return f"{m}:{s:02d}"
    except Exception:
        return "1:40"


def upload_video(filename):
    local_path = OM_REELS_DIR / filename
    if not local_path.exists():
        print(f"  SKIP (not found): {local_path}")
        return None
    size_mb = local_path.stat().st_size / 1024 / 1024
    upload_url = f"{SUPABASE_URL}/storage/v1/object/{BUCKET}/{filename}"
    print(f"  Uploading {filename} ({size_mb:.1f} MB)...")
    result = subprocess.run([
        "curl", "-s", "-w", "\n%{http_code}",
        "-X", "POST",
        "-H", f"Authorization: Bearer {SUPABASE_KEY}",
        "-H", f"apikey: {SUPABASE_KEY}",
        "-H", "Content-Type: video/mp4",
        "--data-binary", f"@{local_path}", upload_url,
    ], capture_output=True, text=True)
    lines = result.stdout.strip().split("\n")
    http_code = lines[-1] if lines else "?"
    body = "\n".join(lines[:-1])
    public_url = f"{SUPABASE_URL}/storage/v1/object/public/{BUCKET}/{filename}"
    if http_code in ("200", "201"):
        print(f"  ✓ Uploaded → {public_url}")
        return public_url
    elif http_code == "409":
        print(f"  ↩ Already exists → {public_url}")
        return public_url
    else:
        print(f"  ✗ FAIL HTTP {http_code}: {body[:200]}")
        return None


def feed_entry(meta, public_url):
    duration = get_duration_str(meta["filename"])
    return f"""  {{
    id: "{meta['id']}",
    type: "localvideo",
    course: "OM", courseColor: "#ea580c",
    emoji: "{meta['emoji']}",
    title: "{meta['title']}",
    subtitle: "{meta['subtitle']}",
    description: "{meta['description']}",
    topics: {json.dumps(meta['topics'])},
    duration: "{duration}",
    level: "Prüfungsrelevant ⚡",
    video_src: "{public_url}",
    thumbnail_emoji: "{meta['emoji']}",
    block: "{meta['block']}"
  }}"""


def id_in_feed(feed_content, reel_id):
    return f'id: "{reel_id}"' in feed_content


def main():
    # Optional: single file mode
    single_file = None
    if "--file" in sys.argv:
        idx = sys.argv.index("--file")
        single_file = sys.argv[idx + 1]

    feed_content = FEED_DATA.read_text(encoding="utf-8")
    new_entries = []

    metas = [m for m in REELS_META if single_file is None or m["filename"] == single_file]

    for meta in metas:
        print(f"\n── {meta['title']} ({meta['filename']})")
        if id_in_feed(feed_content, meta["id"]):
            print(f"  ↩ Already in feed-data.js — skipping")
            continue
        url = upload_video(meta["filename"])
        if url:
            new_entries.append(feed_entry(meta, url))

    if not new_entries:
        print("\nNothing new to add to feed-data.js.")
        return

    # Insert before closing ];
    insert_block = ",\n".join(new_entries)
    feed_content = feed_content.rstrip()
    if feed_content.endswith("];"):
        feed_content = feed_content[:-2] + ",\n" + insert_block + "\n];"
    else:
        feed_content += ",\n" + insert_block

    FEED_DATA.write_text(feed_content, encoding="utf-8")
    print(f"\n✓ Added {len(new_entries)} entries to feed-data.js")

    # Git commit + push
    repo = FEED_DATA.parent.parent
    subprocess.run(["git", "add", str(FEED_DATA)], cwd=repo)
    subprocess.run(["git", "commit", "-m", f"feat(om-reels): add {len(new_entries)} OM reels to feed"], cwd=repo)
    subprocess.run(["git", "push"], cwd=repo)
    print("✓ Git pushed")


if __name__ == "__main__":
    main()
