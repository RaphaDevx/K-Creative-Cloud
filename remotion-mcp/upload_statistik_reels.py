"""
Nach Render: Statistik Reels zu Supabase Storage hochladen
und feed-data.js mit localvideo-Karten ergänzen.
"""
import os, sys, json, re
from pathlib import Path

RENDERS_DIR = Path.home() / "renders" / "shorts"
FEED_DATA   = Path("/home/raphael/lernplattform/data/feed-data.js")
SUPABASE_URL = "https://ifmwcgwfvunjbnfwwbtr.supabase.co"
STORAGE_PATH = f"{SUPABASE_URL}/storage/v1/object/public/videos"

REELS = [
    {
        "file": "statistik_t1_deskriptiv.mp4",
        "id": "stat-reel-t1",
        "course": "Statistik",
        "block": "Block 1 — Deskriptive Statistik",
        "title": "Deskriptive Statistik in 90 Sekunden",
        "tldr": "Skalenniveaus, Lageparameter, Varianz (n-1!) und Boxplot — alles was du für Teil I brauchst."
    },
    {
        "file": "statistik_t2_wahrscheinlichkeit.mp4",
        "id": "stat-reel-t2",
        "course": "Statistik",
        "block": "Block 2 — Wahrscheinlichkeitsrechnung",
        "title": "Wahrscheinlichkeit in 90 Sekunden",
        "tldr": "Kolmogorov-Axiome, Additionssatz, Bayes und Kombinatorik — die 4 Kernkonzepte."
    },
    {
        "file": "statistik_t3_verteilungen.mp4",
        "id": "stat-reel-t3",
        "course": "Statistik",
        "block": "Block 3 — Wahrscheinlichkeitsverteilungen",
        "title": "Verteilungen in 90 Sekunden",
        "tldr": "Binomial, Poisson, Normalverteilung, Z-Transformation — und wann welche Verteilung."
    },
    {
        "file": "statistik_t4_schaetztheorie.mp4",
        "id": "stat-reel-t4",
        "course": "Statistik",
        "block": "Block 4 — Schätztheorie & Konfidenzintervalle",
        "title": "Schätztheorie in 90 Sekunden",
        "tldr": "Zentraler Grenzwertsatz, Konfidenzintervalle für μ und p, Stichprobenumfang."
    },
    {
        "file": "statistik_t5_hypothesentests.mp4",
        "id": "stat-reel-t5",
        "course": "Statistik",
        "block": "Block 5 — Hypothesentests",
        "title": "Hypothesentests in 90 Sekunden",
        "tldr": "Das 6-Schritte-Testschema, α/β-Fehler, z/t-Test und Welch vs. Pooled."
    },
    {
        "file": "statistik_t6_anova_regression.mp4",
        "id": "stat-reel-t6",
        "course": "Statistik",
        "block": "Block 6 — ANOVA & Regression",
        "title": "ANOVA & Regression in 90 Sekunden",
        "tldr": "SST=SSB+SSW, F-Test, β-Koeffizienten per OLS, R² und Dummy-Variablen."
    },
]


def upload_to_supabase(filepath: Path, filename: str) -> str:
    """Upload via supabase CLI or curl. Returns public URL."""
    import subprocess
    key_var = os.environ.get("SUPABASE_SERVICE_KEY", "")
    if not key_var:
        # Try reading from lernplattform auth.js
        auth = Path("/home/raphael/lernplattform/js/auth.js").read_text()
        m = re.search(r"SUPABASE_KEY\s*=\s*['\"]([^'\"]+)['\"]", auth)
        if m:
            key_var = m.group(1)
    if not key_var:
        print(f"  ⚠️  Kein SUPABASE_KEY — überspringe Upload von {filename}")
        return f"videos/{filename}"

    cmd = [
        "curl", "-s", "-X", "POST",
        f"{SUPABASE_URL}/storage/v1/object/videos/{filename}",
        "-H", f"Authorization: Bearer {key_var}",
        "-H", "Content-Type: video/mp4",
        "--data-binary", f"@{filepath}",
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode == 0:
        print(f"  ✅ Uploaded {filename}")
        return f"{STORAGE_PATH}/{filename}"
    else:
        print(f"  ❌ Upload failed: {result.stderr[:200]}")
        return f"videos/{filename}"


def add_video_cards_to_feed(cards: list):
    """Append localvideo cards to FEED_DATA js file."""
    content = FEED_DATA.read_text()
    # Find closing ];
    insert_pos = content.rfind("];")
    if insert_pos == -1:
        print("❌ Konnte ]; in feed-data.js nicht finden")
        return

    card_js_parts = []
    for c in cards:
        card_js = f"""
  // ── Statistik Reel: {c['title']} ──
  {{
    id: "{c['id']}",
    type: "localvideo",
    course: "{c['course']}",
    courseColor: "#2563eb",
    block: "{c['block']}",
    title: "{c['title']}",
    tldr: "{c['tldr']}",
    video_src: "{c['video_src']}",
    emoji: "🎬"
  }},"""
        card_js_parts.append(card_js)

    insertion = "\n" + "".join(card_js_parts) + "\n"
    new_content = content[:insert_pos] + insertion + content[insert_pos:]
    FEED_DATA.write_text(new_content)
    print(f"✅ {len(cards)} Video-Karten in feed-data.js eingefügt")


def main():
    ready = []
    missing = []
    for reel in REELS:
        fp = RENDERS_DIR / reel["file"]
        if fp.exists():
            ready.append((reel, fp))
        else:
            missing.append(reel["file"])

    if missing:
        print(f"⚠️  Noch nicht gerendert: {missing}")

    if not ready:
        print("Keine gerenderten Statistik-Reels gefunden.")
        return

    print(f"\n📤 Lade {len(ready)} Videos hoch...")
    cards_with_urls = []
    for reel, fp in ready:
        url = upload_to_supabase(fp, reel["file"])
        cards_with_urls.append({**reel, "video_src": url})

    print(f"\n📝 Füge Video-Karten in feed-data.js ein...")
    add_video_cards_to_feed(cards_with_urls)

    print("\n✅ Fertig! Statistik-Reels sind jetzt auf der Lernplattform.")
    for c in cards_with_urls:
        print(f"   🎬 {c['title']} → {c['video_src']}")


if __name__ == "__main__":
    main()
