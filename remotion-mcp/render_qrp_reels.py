"""
QRP Reels — Questionable Research Practices
4 Reels: P-Hacking, HARKing, Optional Stopping, Outcome Switching
ESF HSG FS26 — Sitzung: Gütekriterien & Forschungsintegrität
"""
import json, sys, os
from pathlib import Path

sys.path.insert(0, '/storage/projekte/ki_pipeline_env_312/lib/python3.12/site-packages')
sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(Path(__file__).parent.parent / 'video-shorts-mcp'))

SCRIPTS = {

    # ─────────────────────────────────────────────
    # REEL 1: P-HACKING
    # ─────────────────────────────────────────────
    "qrp-p-hacking": {
        "title": "P-Hacking — Die Manipulation des p-Werts",
        "scenes": [
            {
                "id": 0, "type": "hook",
                "headline": "p < 0.05 — UM JEDEN PREIS",
                "subtext": "50% aller publizierten Studien könnten gefälscht sein",
                "emoji": "💀",
                "spoken": "p kleiner 0.05 — das Zauberwort für Publikationen. Aber was, wenn Forscher diesen Wert künstlich erzwingen? Willkommen bei P-Hacking — der unsichtbaren Epidemie in der Wissenschaft.",
                "accent_hex": "#FF4444"
            },
            {
                "id": 1, "type": "explanation",
                "headline": "WAS IST P-HACKING?",
                "subtext": "Daten so lange drehen, bis p < 0.05 erscheint",
                "emoji": "🎰",
                "spoken": "P-Hacking bedeutet: Man manipuliert Analyse-Entscheidungen so lange, bis der p-Wert die magische Grenze von 0.05 unterschreitet. Nicht die Theorie leitet die Analyse — sondern das gewünschte Ergebnis.",
                "accent_hex": "#FFD700"
            },
            {
                "id": 2, "type": "example",
                "headline": "BEISPIEL 1: AUSREISSER",
                "subtext": "Ohne Ausreißer: p = 0.08 → Mit Ausreißer raus: p = 0.04",
                "emoji": "🔍",
                "spoken": "Beispiel 1: Ein Forscher testet, ob Meditation den Stresspegel senkt. Ergebnis: p = 0.08 — nicht signifikant. Lösung: Er entfernt drei 'Ausreißer' ohne theoretische Begründung. Plötzlich: p = 0.04. Veröffentlicht!",
                "accent_hex": "#4FC3F7"
            },
            {
                "id": 3, "type": "example",
                "headline": "BEISPIEL 2: SUBGRUPPEN",
                "subtext": "Kein Effekt gesamt → signifikant bei Frauen unter 30",
                "emoji": "🔬",
                "spoken": "Beispiel 2: Eine Pharmafirma findet keinen Effekt ihres Medikaments in der Gesamtstichprobe. Also testet sie Dutzende Subgruppen — Alter, Geschlecht, Region. Bei Frauen unter 30 in Bayern: p = 0.03. Dieser Befund wird publiziert, der Rest verschwiegen.",
                "accent_hex": "#4FC3F7"
            },
            {
                "id": 4, "type": "warning",
                "headline": "WARUM ES FUNKTIONIERT",
                "subtext": "5% Fehlerrate × 20 Tests = 1 falsches Positiv erwartet",
                "emoji": "⚠️",
                "spoken": "Warum klappt P-Hacking? Weil das Signifikanzniveau 0.05 bedeutet: Selbst bei rein zufälligen Daten findet man bei 20 Tests statistisch einen 'signifikanten' Befund. Wer genug Tests macht, findet immer etwas.",
                "accent_hex": "#FF7043"
            },
            {
                "id": 5, "type": "fact",
                "headline": "SIMMONS ET AL. 2011",
                "subtext": "Forscher erzeugten signifikante Befunde aus reinen Zufallsdaten",
                "emoji": "📊",
                "spoken": "Simmons und Kollegen zeigten 2011 in einer Klassiker-Studie: Durch flexible Analyseentscheidungen konnten sie bei völlig zufälligen Daten in über 60 Prozent der Fälle ein signifikantes Ergebnis erzeugen. Das System ist kaputt.",
                "accent_hex": "#CE93D8"
            },
            {
                "id": 6, "type": "takeaway",
                "headline": "ERKENNEN & VERMEIDEN",
                "subtext": "Pre-Registration · OSF · Transparenz über alle Tests",
                "emoji": "🛡️",
                "spoken": "Die Lösung: Präregistrierung auf dem Open Science Framework. Man registriert Hypothesen und Analysepläne vor der Datenerhebung. So sieht jeder, ob die Analyse geplant war — oder nachträglich erzeugt wurde. Merke: P-Hacking ist keine Kavaliersdelikt — es zerstört wissenschaftlichen Fortschritt.",
                "accent_hex": "#66BB6A"
            },
        ],
        "_tokens": {"input": 0, "output": 0, "total": 0}
    },

    # ─────────────────────────────────────────────
    # REEL 2: HARKing
    # ─────────────────────────────────────────────
    "qrp-harking": {
        "title": "HARKing — Hypothesen nach Resultaten",
        "scenes": [
            {
                "id": 0, "type": "hook",
                "headline": "DIE GROSSTE LÜGE DER WISSENSCHAFT",
                "subtext": "Hypothesen nach dem Ergebnis schreiben — und so tun als ob vorher",
                "emoji": "🎭",
                "spoken": "Was wäre, wenn Forscher ihre Hypothesen erst nach dem Experiment formulieren — und dann so tun, als hätten sie es vorher gewusst? Das ist HARKing. Und es passiert täglich in wissenschaftlichen Labors weltweit.",
                "accent_hex": "#FF4444"
            },
            {
                "id": 1, "type": "explanation",
                "headline": "HARKING DEFINIERT",
                "subtext": "Hypothesizing After Results are Known — Kerr 1998",
                "emoji": "📖",
                "spoken": "HARKing steht für Hypothesizing After Results are Known — geprägt von Norbert Kerr 1998. Man erhebt Daten, entdeckt ein interessantes Muster, und schreibt danach eine Hypothese, die exakt dieses Muster 'vorhersagt'. Im Paper klingt es wie geplante, konfirmatorische Forschung.",
                "accent_hex": "#FFD700"
            },
            {
                "id": 2, "type": "example",
                "headline": "BEISPIEL 1: DER PSYCHOLOGE",
                "subtext": "Zufallsbefund wird zur 'geplanten Hypothese' umgeschrieben",
                "emoji": "🧠",
                "spoken": "Beispiel 1: Ein Psychologe untersucht Persönlichkeit und Kaufverhalten. Zufällig findet er: Extravertierte kaufen mehr in Rot verpackte Produkte. Er schreibt ins Paper: 'Wir hypothetisierten, dass Extraversion die Präferenz für lebhafte Farben steigert.' Dieser Satz ist eine Lüge — aber er klingt nach guter Wissenschaft.",
                "accent_hex": "#4FC3F7"
            },
            {
                "id": 3, "type": "example",
                "headline": "BEISPIEL 2: DIE SOZIOLOGIN",
                "subtext": "10 Variablen getestet → 1 signifikant → als Theorie verkauft",
                "emoji": "📈",
                "spoken": "Beispiel 2: Eine Soziologin testet 10 sozioökonomische Faktoren auf Bildungserfolg. Nur Faktor 7 — Bibliotheksdichte im Wohnort — ist signifikant. Im Paper formuliert sie: 'Theoriegeleitet hypothetisieren wir, dass Zugang zu Wissen entscheidend ist.' Das Theoriegerüst wurde nachträglich gebaut.",
                "accent_hex": "#4FC3F7"
            },
            {
                "id": 4, "type": "warning",
                "headline": "WARUM ES SCHADET",
                "subtext": "Explorative Forschung wird als konfirmatorisch verkauft",
                "emoji": "⚠️",
                "spoken": "Das Problem: HARKing verwandelt Entdeckungen in Bestätigungen. Explorative Forschung — die legitim ist! — wird als konfirmatorische Hypothesenprüfung verkleidet. Das täuscht Leser, Reviewer und Entscheidungsträger, die auf wissenschaftliche Evidenz vertrauen.",
                "accent_hex": "#FF7043"
            },
            {
                "id": 5, "type": "fact",
                "headline": "VERBREITUNG: ERSCHRECKEND",
                "subtext": "Bis zu 35% der Psychologen gaben HARKing zu — anonym",
                "emoji": "📉",
                "spoken": "In anonymen Umfragen gaben bis zu 35 Prozent der befragten Psychologen zu, mindestens einmal HARKing betrieben zu haben. Bei nicht-anonymen Befragungen sinkt die Zahl dramatisch — was zeigt: Man weiß, dass es falsch ist.",
                "accent_hex": "#CE93D8"
            },
            {
                "id": 6, "type": "takeaway",
                "headline": "UNTERSCHIED KENNEN",
                "subtext": "Explorative ≠ Konfirmatorische Forschung — beide legitim, wenn ehrlich",
                "emoji": "🧠",
                "spoken": "Die Lösung ist Transparenz. Explorative und konfirmatorische Forschung sind beide wissenschaftlich wertvoll — aber nur wenn sie korrekt gekennzeichnet sind. Präregistrierung verhindert HARKing strukturell: Was vor den Daten steht, kann nicht nachträglich erfunden werden.",
                "accent_hex": "#66BB6A"
            },
        ],
        "_tokens": {"input": 0, "output": 0, "total": 0}
    },

    # ─────────────────────────────────────────────
    # REEL 3: OPTIONAL STOPPING
    # ─────────────────────────────────────────────
    "qrp-optional-stopping": {
        "title": "Optional Stopping — Daten sammeln bis es passt",
        "scenes": [
            {
                "id": 0, "type": "hook",
                "headline": "EINFACH WEITER MESSEN...",
                "subtext": "...bis p < 0.05. Dann aufhören. Das ist Betrug.",
                "emoji": "⏱️",
                "spoken": "Stell dir vor: Du erhebst Daten und checkst nach jeder Messung den p-Wert. Nicht signifikant? Weitermachen. Signifikant? Stopp — veröffentlichen! Das klingt pragmatisch. Es ist Scientific Fraud.",
                "accent_hex": "#FF4444"
            },
            {
                "id": 1, "type": "explanation",
                "headline": "WAS IST OPTIONAL STOPPING?",
                "subtext": "Stichprobengröße flexibel halten, bis Ergebnis passt",
                "emoji": "🎲",
                "spoken": "Optional Stopping bedeutet: Man legt die Stichprobengröße nicht vorab fest, sondern sammelt so lange Daten, bis entweder Signifikanz erreicht ist oder man aufgibt. Das Problem ist statistisch: Der p-Wert verliert bei dieser Praxis seine Bedeutung vollständig.",
                "accent_hex": "#FFD700"
            },
            {
                "id": 2, "type": "example",
                "headline": "BEISPIEL 1: MÜNZWURF",
                "subtext": "Faire Münze → 60% Signifikanzchance bei optional stopping",
                "emoji": "🪙",
                "spoken": "Beispiel 1: Eine faire Münze — 50-50. Man wirft, prüft nach jedem Wurf auf Signifikanz, und hört auf wenn p kleiner 0.05. Simulation zeigt: In etwa 60 Prozent der Fälle findet man ein 'signifikantes' Ergebnis — obwohl die Münze perfekt fair ist. Pure Statistik-Manipulation.",
                "accent_hex": "#4FC3F7"
            },
            {
                "id": 3, "type": "example",
                "headline": "BEISPIEL 2: KLINISCHE STUDIE",
                "subtext": "Zwischenanalysen ohne Korrektur = falsches Positiv",
                "emoji": "💊",
                "spoken": "Beispiel 2: Eine pharmazeutische Studie plant 200 Patienten. Nach 80 Patienten ist p = 0.048. Studie wird gestoppt, Medikament als wirksam publiziert. Problem: Bei drei Zwischenanalysen ohne Bonferroni-Korrektur liegt das wahre Signifikanzniveau nicht bei 5 — sondern bei 14 Prozent.",
                "accent_hex": "#4FC3F7"
            },
            {
                "id": 4, "type": "warning",
                "headline": "DAS STATISTIK-PARADOX",
                "subtext": "Je mehr du checkst, desto mehr Fehler machst du",
                "emoji": "📉",
                "spoken": "Das Paradox: Jedes Mal, wenn du den p-Wert prüfst, erhöhst du die Wahrscheinlichkeit eines falschen Positivs. Das sogenannte Alpha-Fehler-Kumulieren. Klassische Tests setzen voraus, dass die Stichprobengröße vorab fixiert ist — genau das bricht Optional Stopping.",
                "accent_hex": "#FF7043"
            },
            {
                "id": 5, "type": "fact",
                "headline": "LÖSUNG: SEQUENZIELLE TESTS",
                "subtext": "Wald SPRT oder Bayes Factor — dafür gemacht",
                "emoji": "🔧",
                "spoken": "Es gibt legitime Methoden für sequenzielle Datenerhebung: Der Sequential Probability Ratio Test nach Wald oder Bayes Factors kontrollieren das Fehlerrisiko auch bei kontinuierlichem Monitoring. Diese Methoden sind für Optional Stopping konstruiert — klassische t-Tests nicht.",
                "accent_hex": "#CE93D8"
            },
            {
                "id": 6, "type": "takeaway",
                "headline": "REGEL: N VORHER FESTLEGEN",
                "subtext": "Stichprobengröße in Präregistrierung · keine Zwischenanalysen",
                "emoji": "📌",
                "spoken": "Die Regel ist simpel: Lege die Stichprobengröße vor der Datenerhebung fest und halte dich daran. Wenn Zwischenanalysen nötig sind, plane sie vorab und korrigiere das Signifikanzniveau entsprechend. Alles andere ist Optional Stopping — und das ist kein zufälliger Fehler, sondern eine Verzerrung mit System.",
                "accent_hex": "#66BB6A"
            },
        ],
        "_tokens": {"input": 0, "output": 0, "total": 0}
    },

    # ─────────────────────────────────────────────
    # REEL 4: OUTCOME SWITCHING
    # ─────────────────────────────────────────────
    "qrp-outcome-switching": {
        "title": "Outcome Switching — Den Zielposten verschieben",
        "scenes": [
            {
                "id": 0, "type": "hook",
                "headline": "DAS ZIEL WIRD VERSCHOBEN",
                "subtext": "Primärer Endpunkt nicht signifikant? Einfach wechseln.",
                "emoji": "⚽",
                "spoken": "Du hast eine Hypothese aufgestellt, Daten erhoben, und das Ergebnis ist: nicht signifikant. Was tust du? Manche Forscher verschieben einfach den Zielposten — ein anderes Outcome, das zufällig signifikant ist, wird zur Hauptvariable erklärt. Das nennt sich Outcome Switching.",
                "accent_hex": "#FF4444"
            },
            {
                "id": 1, "type": "explanation",
                "headline": "OUTCOME SWITCHING ERKLÄRT",
                "subtext": "Primär- & Sekundärvariablen werden nachträglich getauscht",
                "emoji": "🔄",
                "spoken": "Outcome Switching bezeichnet die nachträgliche Änderung der primären Zielvariable einer Studie. Man registriert Variable A als Hauptoutcome, findet aber keinen Effekt. Variable B ist aber signifikant — also wird B im Paper als primäre Hypothese präsentiert, A verschwindet oder wird zur Nebenvariable degradiert.",
                "accent_hex": "#FFD700"
            },
            {
                "id": 2, "type": "example",
                "headline": "BEISPIEL 1: TAMIFLU-SKANDAL",
                "subtext": "Roche änderte Endpunkte — Milliarden wurden ausgegeben",
                "emoji": "💉",
                "spoken": "Beispiel 1: Das Grippemittel Tamiflu. Roche registrierte als Primärendpunkt die Reduktion von Komplikationen. Als dieser nicht signifikant war, wurde im Paper plötzlich die Verkürzung der Krankheitsdauer als Hauptergebnis präsentiert. Regierungen weltweit kauften Tamiflu-Reserven für Milliarden Euro — basierend auf diesem Switching.",
                "accent_hex": "#4FC3F7"
            },
            {
                "id": 3, "type": "example",
                "headline": "BEISPIEL 2: SOZIALPSYCHOLOGIE",
                "subtext": "Power Pose Studie: Original-Outcome still — Folge-Outcome publiziert",
                "emoji": "💪",
                "spoken": "Beispiel 2: Die berühmte Power-Pose-Studie. Das registrierte Primärziel war Cortisol-Reduktion — kein signifikanter Effekt. Publiziert wurde stattdessen der Effekt auf subjektives Machtgefühl, der zufällig signifikant war. Co-Autorin Dana Carney gab später öffentlich zu, dass Outcome Switching stattgefunden hatte.",
                "accent_hex": "#4FC3F7"
            },
            {
                "id": 4, "type": "warning",
                "headline": "ALLOTRIAL — 57% SWITCHEN",
                "subtext": "57% klinischer Studien weichen vom registrierten Endpunkt ab",
                "emoji": "📊",
                "spoken": "Das COMPARE-Projekt analysierte klinische Studien systematisch: 57 Prozent der untersuchten Studien zeigten signifikante Abweichungen zwischen registrierten und publizierten Endpunkten. Outcome Switching ist kein Randphänomen — es ist Standard in der klinischen Forschung.",
                "accent_hex": "#FF7043"
            },
            {
                "id": 5, "type": "fact",
                "headline": "LÖSUNG: VERGLEICHSTOOLS",
                "subtext": "ClinicalTrials.gov · AllTrials · COMPARE Projekt",
                "emoji": "🔎",
                "spoken": "Die Gegenmittel: Plattformen wie ClinicalTrials.gov protokollieren Studiendesigns vor Beginn. Das COMPARE-Projekt und AllTrials vergleichen systematisch Registrierung mit Publikation. Journals fordern zunehmend Nachweis der Registrierung — ohne sie keine Veröffentlichung.",
                "accent_hex": "#CE93D8"
            },
            {
                "id": 6, "type": "takeaway",
                "headline": "PRIMÄR = PRIMÄR",
                "subtext": "Was registriert ist, wird berichtet — alle Outcomes, alle Ergebnisse",
                "emoji": "📋",
                "spoken": "Die Regel: Was als primärer Endpunkt registriert ist, muss als primärer Endpunkt berichtet werden — auch wenn das Ergebnis null ist. Alle geplanten Outcomes müssen im Paper erscheinen. Outcome Switching ist nicht nur schlechte Wissenschaft: In der klinischen Forschung gefährdet es Menschenleben.",
                "accent_hex": "#66BB6A"
            },
        ],
        "_tokens": {"input": 0, "output": 0, "total": 0}
    },

}


def patched_generate_script(topic: str, extra_instructions: str = "") -> dict:
    for key, script in SCRIPTS.items():
        if key in topic or script["title"].lower() in topic.lower():
            print(f"      [offline] Using pre-built script: {script['title']}")
            return script
    return list(SCRIPTS.values())[0]


if __name__ == "__main__":
    import script_gen
    script_gen.generate_script = patched_generate_script

    from render_remotion import create_remotion_short

    reels = [
        ("qrp-p-hacking",        "P-Hacking Manipulation p-Wert — ESF HSG QRP"),
        ("qrp-harking",          "HARKing Hypothesizing After Results Known — ESF HSG QRP"),
        ("qrp-optional-stopping","Optional Stopping Daten sammeln bis p05 — ESF HSG QRP"),
        ("qrp-outcome-switching","Outcome Switching Endpunkte tauschen — ESF HSG QRP"),
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
            extra_instructions=(
                "HSG Lernvideo ESF. Questionable Research Practices. "
                "Prüfungsrelevant, konkrete Beispiele, klare Definitionen. "
                "Ton: schockierend-lehrreich, nicht moralisierend."
            ),
            style="minimal",
        )
        results.append(result)
        print(json.dumps(result, indent=2))

    print("\n\n=== ALLE QRP REELS FERTIG ===")
    for r in results:
        if isinstance(r, dict):
            print(f"  {r.get('output_path', r.get('error', str(r)))}")
