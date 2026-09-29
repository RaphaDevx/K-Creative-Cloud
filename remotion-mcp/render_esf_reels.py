"""
ESF Sitzung 1 — 4 Reels ohne API-Key
Skripte direkt definiert, generate_script wird überbrückt.
"""
import json, sys, os, importlib
from pathlib import Path

sys.path.insert(0, '/storage/projekte/ki_pipeline_env_312/lib/python3.12/site-packages')
sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(Path(__file__).parent.parent / 'video-shorts-mcp'))

# --- PRE-BUILT SCRIPTS ---

SCRIPTS = {
    "esf-s1-was-ist-esf": {
        "title": "Was ist Empirische Sozialforschung?",
        "scenes": [
            {"id": 0, "type": "hook",
             "headline": "EMPIRIE ≠ THEORIE",
             "subtext": "Der Unterschied kostet dich die Prüfung",
             "emoji": "⚠️",
             "spoken": "Empirie und Theorie — das Gleiche? Wenn du das glaubst, kostet dich das die ESF-Prüfung. Heute klärst du diesen Unterschied ein für alle Mal.",
             "accent_hex": "#FF4444"},
            {"id": 1, "type": "fact",
             "headline": "ESF DEFINITION",
             "subtext": "Häder 2019: Methoden für menschliches Verhalten",
             "emoji": "🔬",
             "spoken": "Empirische Sozialforschung ist laut Häder 2019 die Gesamtheit von Methoden, Techniken und Instrumenten zur wissenschaftlich korrekten Untersuchung menschlichen Verhaltens und sozialer Phänomene.",
             "accent_hex": "#FFD700"},
            {"id": 2, "type": "explanation",
             "headline": "DREI BESTANDTEILE",
             "subtext": "Theorie · Empirie · Forschungsmethode",
             "emoji": "🏛️",
             "spoken": "ESF besteht aus drei untrennbaren Bestandteilen. Die Theorie ist ein widerspruchsfreies Aussagensystem, das Sachverhalte erklärt und vorhersagt. Die Empirie beschreibt die Wirklichkeit. Die Forschungsmethode liefert Handlungsanweisungen.",
             "accent_hex": "#4FC3F7"},
            {"id": 3, "type": "warning",
             "headline": "DIE PRÜFUNGSFALLE",
             "subtext": "Theorie ist bewährt — Empirie noch nicht",
             "emoji": "🎯",
             "spoken": "Und jetzt die wichtigste Falle: Theorie ist widerspruchsfrei und bereits bewährt — sie erklärt und sagt vorher. Empirie hingegen beschreibt nur die Wirklichkeit und hat sich noch nicht ausreichend bewährt. Nie verwechseln!",
             "accent_hex": "#FF7043"},
            {"id": 4, "type": "fact",
             "headline": "VIER ZIELE DER ESF",
             "subtext": "Beschreiben · Theorien testen · Verstehen · Gesellschaft",
             "emoji": "🎯",
             "spoken": "Die vier offiziellen Ziele der ESF: Soziales Leben beschreiben und erklären. Theorien entwickeln und testen. Menschliches Verhalten verstehen. Und Forschung zur Lösung gesellschaftlicher Probleme nutzen.",
             "accent_hex": "#FFD700"},
            {"id": 5, "type": "warning",
             "headline": "KEINE ZIELE DER ESF",
             "subtext": "Naturgesetze · Hermeneutik · Literaturanalyse",
             "emoji": "🚫",
             "spoken": "Was keine Ziele der ESF sind — und das kommt direkt in der Prüfung: Naturgesetze erforschen, hermeneutische Textinterpretation, systematische Literaturanalyse und rein denkende Theorieentwicklung.",
             "accent_hex": "#FF7043"},
            {"id": 6, "type": "takeaway",
             "headline": "MERKE: ESF KERN",
             "subtext": "3 Bestandteile · 4 Ziele · Empirie ≠ Theorie",
             "emoji": "🧠",
             "spoken": "Zusammenfassung: ESF untersucht menschliches Verhalten mit Methoden, Techniken und Instrumenten. Drei Bestandteile, vier Ziele. Und der wichtigste Satz: Empirie beschreibt die Wirklichkeit — Theorie erklärt sie. Nie verwechseln.",
             "accent_hex": "#CE93D8"},
        ],
        "_tokens": {"input": 0, "output": 0, "total": 0}
    },

    "esf-s1-forschungsprozess": {
        "title": "Der Forschungsprozess nach Bryman",
        "scenes": [
            {"id": 0, "type": "hook",
             "headline": "REIHENFOLGE FALSCH?",
             "subtext": "7 Phasen — eine steht an erster Stelle",
             "emoji": "🔢",
             "spoken": "Du glaubst, Forschung beginnt mit der Forschungsfrage? Falsch. Sieben Phasen gibt es nach Bryman — und die Reihenfolge ist prüfungsrelevant. Lass uns das ein für alle Mal klären.",
             "accent_hex": "#FF4444"},
            {"id": 1, "type": "fact",
             "headline": "PHASE 1: LITERATUR",
             "subtext": "Immer mit Literaturrecherche beginnen",
             "emoji": "📚",
             "spoken": "Phase eins ist immer die Literaturrecherche. Sie zeigt, was bereits bekannt ist — und wo die Forschungslücke liegt. Ohne Literatur keine fundierte Forschung.",
             "accent_hex": "#FFD700"},
            {"id": 2, "type": "explanation",
             "headline": "PHASEN 2 UND 3",
             "subtext": "Konzeption → Forschungsfrage",
             "emoji": "🧩",
             "spoken": "Phase zwei: Konzeption und Theorie — der theoretische Rahmen. Erst dann, in Phase drei, kommt die Forschungsfrage. Sie ist das Herzstück des Projekts — sie bestimmt Methode, Daten und Auswertung.",
             "accent_hex": "#4FC3F7"},
            {"id": 3, "type": "warning",
             "headline": "HERZSTÜCK: FORSCHUNGSFRAGE",
             "subtext": "Phase 3 bestimmt alles andere",
             "emoji": "❤️",
             "spoken": "Wichtig: die Forschungsfrage in Phase drei ist das Herzstück. Ohne sie geht gar nichts. Aber sie kommt nach Literatur und Konzeption — nicht davor!",
             "accent_hex": "#FF7043"},
            {"id": 4, "type": "fact",
             "headline": "PHASEN 4 BIS 6",
             "subtext": "Stichprobe → Erhebung → Analyse",
             "emoji": "📊",
             "spoken": "Phase vier: Stichprobenauswahl — wer wird untersucht? Phase fünf: Datenerhebung durch Interviews, Umfragen oder Experimente. Phase sechs: Datenanalyse — Verwaltung, Auswertung, Interpretation.",
             "accent_hex": "#FFD700"},
            {"id": 5, "type": "explanation",
             "headline": "PHASE 7: SCHREIBEN",
             "subtext": "Aufarbeitung und Publikation am Ende",
             "emoji": "✍️",
             "spoken": "Die letzte Phase ist das Schreiben — Aufarbeitung, Dissemination und Publikation. Schreiben kommt erst ganz am Ende, wenn alle Daten analysiert sind.",
             "accent_hex": "#4FC3F7"},
            {"id": 6, "type": "takeaway",
             "headline": "7 PHASEN AUSWENDIG",
             "subtext": "Literatur → Konzept → FF → Stichprobe → Erhebung → Analyse → Schreiben",
             "emoji": "📋",
             "spoken": "Die Reihenfolge: Literaturrecherche, Konzeption und Theorie, Forschungsfrage, Stichprobenauswahl, Datenerhebung, Datenanalyse, Schreiben. Sieben Phasen. Reihenfolge auswendig — prüfungsrelevant!",
             "accent_hex": "#CE93D8"},
        ],
        "_tokens": {"input": 0, "output": 0, "total": 0}
    },

    "esf-s1-forschungsdesign": {
        "title": "Forschungsdesign: Qualitativ vs. Quantitativ",
        "scenes": [
            {"id": 0, "type": "hook",
             "headline": "QUALITATIV = INDUKTIV",
             "subtext": "90% der Studis liegen bei dieser Falle falsch",
             "emoji": "💡",
             "spoken": "Qualitative Forschung ist deduktiv. Richtig oder falsch? Diese Frage hat schon viele ESF-Prüfungen entschieden. Die Antwort kommt jetzt.",
             "accent_hex": "#FF4444"},
            {"id": 1, "type": "warning",
             "headline": "FALSCH! INDUKTIV!",
             "subtext": "Qualitativ = induktiv, vom Speziellen zum Allgemeinen",
             "emoji": "🚨",
             "spoken": "Qualitative Forschung ist INDUKTIV — vom Speziellen zum Allgemeinen. Sie entwickelt Hypothesen und baut neue Theorien auf. Das ist die häufigste Prüfungsfalle in ESF!",
             "accent_hex": "#FF7043"},
            {"id": 2, "type": "fact",
             "headline": "QUANTITATIV = DEDUKTIV",
             "subtext": "Vom Allgemeinen zum Speziellen — Theorie prüfen",
             "emoji": "📐",
             "spoken": "Quantitative Forschung ist deduktiv — vom Allgemeinen zum Speziellen. Sie testet bestehende Hypothesen anhand standardisierter, numerischer Daten mit großen Stichproben.",
             "accent_hex": "#FFD700"},
            {"id": 3, "type": "explanation",
             "headline": "VERGLEICH KOMPAKT",
             "subtext": "Klein·weich·offen vs. groß·hart·standardisiert",
             "emoji": "⚖️",
             "spoken": "Qualitativ: kleine Stichprobe, nicht-standardisierte Daten, dynamischer offener Prozess. Quantitativ: große Stichprobe, standardisierte numerische Daten, statischer vorab festgelegter Prozess.",
             "accent_hex": "#4FC3F7"},
            {"id": 4, "type": "fact",
             "headline": "MIXED METHODS",
             "subtext": "Kombination beider Ansätze zur Validierung",
             "emoji": "🔀",
             "spoken": "Mixed Methods kombiniert beide Ansätze. Ziel: die Ergebnisse einer Methode durch eine weitere Methode zu validieren und damit aussagekräftigere Ergebnisse zu erhalten.",
             "accent_hex": "#FFD700"},
            {"id": 5, "type": "tip",
             "headline": "WANN QUALITATIV?",
             "subtext": "Wenig Wissen · tiefe Einblicke · neue Theorien",
             "emoji": "🧭",
             "spoken": "Qualitativ wählst du, wenn wenig Vorwissen besteht, wenn tiefe Einblicke nötig sind, wenn der Gegenstand nicht messbar ist — oder wenn du neue Theorien generieren willst.",
             "accent_hex": "#66BB6A"},
            {"id": 6, "type": "takeaway",
             "headline": "KERN: INDUKTIV DEDUKTIV",
             "subtext": "Qualitativ=induktiv · Quantitativ=deduktiv · Mixed=beides",
             "emoji": "🧠",
             "spoken": "Das Wichtigste: Qualitativ ist induktiv und entwickelt Theorien. Quantitativ ist deduktiv und prüft Theorien. Mixed Methods validiert durch Kombination. Und das verwechseln kostet Punkte!",
             "accent_hex": "#CE93D8"},
        ],
        "_tokens": {"input": 0, "output": 0, "total": 0}
    },

    "esf-s1-primaer-sekundaer": {
        "title": "Primär- und Sekundärdaten",
        "scenes": [
            {"id": 0, "type": "hook",
             "headline": "PRIMÄR ODER SEKUNDÄR?",
             "subtext": "Ein Test — die Antwort überrascht viele",
             "emoji": "🤔",
             "spoken": "Du erstellst eine Unipark-Umfrage selbst. Primär oder Sekundär? Und der Socialbakers-Bericht, den du online findest? Die Unterscheidung ist einfacher als du denkst — wenn du die Regel kennst.",
             "accent_hex": "#FF4444"},
            {"id": 1, "type": "fact",
             "headline": "PRIMÄR: SELBST ERHOBEN",
             "subtext": "Eigens für diese Forschungsfrage erhoben",
             "emoji": "🎯",
             "spoken": "Primärdaten sind Daten, die von den Forschenden selbst und eigens für diese konkrete Forschungsfrage erhoben wurden. Der entscheidende Test: Wurde es selbst erhoben? Für genau diese Frage? Dann Primär.",
             "accent_hex": "#FFD700"},
            {"id": 2, "type": "explanation",
             "headline": "PRIMÄR: VOR- & NACHTEILE",
             "subtext": "Aktuell und passend — aber teuer",
             "emoji": "💰",
             "spoken": "Primärforschung: hohe Aktualität, perfekte Passung zur Forschungsfrage, Kontrolle über Datenqualität. Aber: langer Zeitbedarf, hohe Kosten, großer Personalaufwand.",
             "accent_hex": "#4FC3F7"},
            {"id": 3, "type": "fact",
             "headline": "SEKUNDÄR: VORHANDEN",
             "subtext": "Ursprünglich für anderen Zweck erhoben",
             "emoji": "📂",
             "spoken": "Sekundärdaten sind bereits vorhanden und wurden ursprünglich für einen anderen Zweck erhoben. Blogs, Social-Media-Berichte, Verkaufszahlen von Unternehmen — alles Sekundär.",
             "accent_hex": "#FFD700"},
            {"id": 4, "type": "warning",
             "headline": "SEKUNDÄR: DIE FALLE",
             "subtext": "Socialbakers, Digitec, Samsung-Fan-Seite = sekundär",
             "emoji": "⚠️",
             "spoken": "Achtung Prüfungsfalle: Socialbakers-Berichte, Verkaufszahlen von Digitec, Fan-Communities — alles Sekundär! Sie wurden nicht eigens für deine Forschungsfrage erhoben.",
             "accent_hex": "#FF7043"},
            {"id": 5, "type": "explanation",
             "headline": "SEKUNDÄR: VOR- & NACHTEILE",
             "subtext": "Schnell und günstig — aber möglicherweise nicht passend",
             "emoji": "⚡",
             "spoken": "Sekundärforschung: schnell verfügbar, niedrige Kosten, große Stichproben möglich. Aber: mangelnde Passung zur Forschungsfrage, wenig Kontrolle, fehlende Dokumentation.",
             "accent_hex": "#4FC3F7"},
            {"id": 6, "type": "takeaway",
             "headline": "DIE ENTSCHEIDUNGSREGEL",
             "subtext": "Selbst erhoben · für diese Frage · Primär. Sonst: Sekundär.",
             "emoji": "🧠",
             "spoken": "Die Entscheidungsregel: Wurde es von dir selbst erhoben, eigens für diese Forschungsfrage? Dann Primär. Alles andere ist Sekundär. So einfach ist das — und so wichtig für die Prüfung.",
             "accent_hex": "#CE93D8"},
        ],
        "_tokens": {"input": 0, "output": 0, "total": 0}
    },
}


def patched_generate_script(topic: str, extra_instructions: str = "") -> dict:
    """Return pre-built script by matching output_name in topic."""
    for key, script in SCRIPTS.items():
        if key in topic or script["title"].lower() in topic.lower():
            print(f"      [offline] Using pre-built script: {script['title']}")
            return script
    # fallback: first script
    return list(SCRIPTS.values())[0]


if __name__ == "__main__":
    import script_gen
    script_gen.generate_script = patched_generate_script

    from render_remotion import create_remotion_short

    reels = [
        ("esf-s1-was-ist-esf",        "Was ist Empirische Sozialforschung — ESF HSG"),
        ("esf-s1-forschungsprozess",   "Der Forschungsprozess nach Bryman — ESF HSG"),
        ("esf-s1-forschungsdesign",    "Forschungsdesign qualitativ quantitativ — ESF HSG"),
        ("esf-s1-primaer-sekundaer",   "Primär- und Sekundärdaten — ESF HSG"),
    ]

    results = []
    for output_name, topic in reels:
        print(f"\n{'='*60}")
        print(f"Rendering: {output_name}")
        print(f"{'='*60}")
        result = create_remotion_short(
            topic=topic,
            voice="am_adam",
            output_name=output_name,
            extra_instructions="HSG Lernvideo ESF Sitzung 1. Prüfungsrelevant.",
            style="minimal",
        )
        results.append(result)
        print(json.dumps(result, indent=2))

    print("\n\n=== ALLE REELS FERTIG ===")
    for r in results:
        if isinstance(r, dict):
            print(f"  {r.get('output_path', r.get('error', r))}")
