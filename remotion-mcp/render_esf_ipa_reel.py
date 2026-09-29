"""
ESF Sitzung 4 — Reel: IPA (Interpretative Phänomenologische Analyse)
Skript direkt definiert, generate_script wird überbrückt (kein API-Key nötig).
"""
import json, sys
from pathlib import Path

sys.path.insert(0, '/storage/projekte/ki_pipeline_env_312/lib/python3.12/site-packages')
sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(Path(__file__).parent.parent / 'video-shorts-mcp'))

SCRIPT = {
    "title": "IPA — Interpretative Phänomenologische Analyse",
    "scenes": [
        {"id": 0, "type": "hook",
         "headline": "IPA = GROUNDED THEORY?",
         "subtext": "Diese Verwechslung kostet Punkte in der ESF-Prüfung",
         "emoji": "🤯",
         "spoken": "IPA und Grounded Theory sind im Grunde das Gleiche, oder? Falsch — und genau diese Verwechslung kostet in der ESF-Prüfung Punkte. Heute klären wir, was IPA wirklich ist.",
         "accent_hex": "#FF4444"},
        {"id": 1, "type": "fact",
         "headline": "IPA DEFINITION",
         "subtext": "Wie erleben Menschen ein Phänomen subjektiv?",
         "emoji": "🔍",
         "spoken": "IPA steht für Interpretative Phänomenologische Analyse. Sie untersucht, wie Menschen ein bestimmtes Erlebnis subjektiv erfahren und welchen Sinn sie ihm geben. Im Zentrum steht die gelebte Erfahrung, nicht objektive Fakten.",
         "accent_hex": "#FFD700"},
        {"id": 2, "type": "explanation",
         "headline": "DREI WURZELN VON IPA",
         "subtext": "Phänomenologie · Hermeneutik · Idiographie",
         "emoji": "🌳",
         "spoken": "IPA basiert auf drei Säulen. Phänomenologie: das subjektive Erleben selbst. Hermeneutik: die Interpretation von Sinn. Und Idiographie: der Fokus auf den Einzelfall statt auf allgemeine Gesetze.",
         "accent_hex": "#4FC3F7"},
        {"id": 3, "type": "fact",
         "headline": "DOUBLE HERMENEUTIC",
         "subtext": "Forschende interpretieren die Interpretation der Befragten",
         "emoji": "🔄",
         "spoken": "Ein Schlüsselbegriff ist die double hermeneutic: Die teilnehmende Person interpretiert ihre eigene Erfahrung — und die Forschenden interpretieren wiederum, wie diese Person ihre Erfahrung interpretiert hat.",
         "accent_hex": "#4FC3F7"},
        {"id": 4, "type": "warning",
         "headline": "IPA ≠ GROUNDED THEORY",
         "subtext": "GT will Theorie bilden, IPA versteht den Einzelfall tief",
         "emoji": "🚨",
         "spoken": "Die wichtigste Prüfungsfalle: Grounded Theory will induktiv eine allgemeine Theorie aus mehreren Fällen entwickeln. IPA dagegen will zuerst jeden Einzelfall im Detail verstehen, bevor — eingeschränkt — über Fälle hinweg verglichen wird.",
         "accent_hex": "#FF7043"},
        {"id": 5, "type": "fact",
         "headline": "TYPISCHES VORGEHEN",
         "subtext": "Kleine Stichprobe · Tiefeninterviews · Fall für Fall",
         "emoji": "🗣️",
         "spoken": "IPA arbeitet mit kleinen, homogenen Stichproben und semi-strukturierten Tiefeninterviews. Jeder Fall wird zuerst einzeln analysiert — emergente Themen pro Person, dann übergeordnete Themen über alle Fälle hinweg.",
         "accent_hex": "#FFD700"},
        {"id": 6, "type": "takeaway",
         "headline": "MERKE: IPA KERN",
         "subtext": "Subjektives Erleben · Double Hermeneutic · Einzelfall zuerst",
         "emoji": "🧠",
         "spoken": "Zusammenfassung: IPA untersucht das subjektive Erleben eines Phänomens mittels double hermeneutic und beginnt immer beim Einzelfall. Frage nach 'Wie erleben Sie X?' — das ist IPA. Frage nach Theorieentwicklung aus mehreren Fällen — das ist Grounded Theory.",
         "accent_hex": "#CE93D8"},
    ],
    "_tokens": {"input": 0, "output": 0, "total": 0}
}


def patched_generate_script(topic: str, extra_instructions: str = "") -> dict:
    print(f"      [offline] Using pre-built script: {SCRIPT['title']}")
    return SCRIPT


if __name__ == "__main__":
    import script_gen
    script_gen.generate_script = patched_generate_script

    from render_remotion import create_remotion_short

    result = create_remotion_short(
        topic="IPA Interpretative Phänomenologische Analyse — ESF HSG",
        voice="am_adam",
        output_name="esf-s4-ipa.mp4",
        extra_instructions="HSG Lernvideo ESF Sitzung 4. Prüfungsrelevant.",
        style="minimal",
    )
    print(json.dumps(result, indent=2))
