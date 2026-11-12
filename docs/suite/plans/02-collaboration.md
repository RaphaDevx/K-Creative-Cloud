# 02 — KI-Verlauf und parallele Bearbeitung

## Vertrag

Jede ausgeführte Operation erhält Operation-ID, Actor/Session/Modell, Dokument-/Objekt-ID, Ausgangsversion, Eingabe, validierten Zustandsunterschied, Ergebnisstatus, Task-/Gruppen-ID und Kausalitätsreferenzen. Deklarierte Absicht getrennt vom Beleg speichern; keine Behauptung, interne Modellgedanken zu protokollieren. Tokens/Passwörter und unnötige private Prompts gehören nicht in Logs.

Zielhierarchie: Projekt → Aufgabe → fachlicher Arbeitsschritt → Operation. Beispiel: Track → Drumloop → Kickpattern → vier `note.add`. Gruppen entstehen durch explizite Tasks und deterministische Regeln; KI darf Labels vorschlagen. Nutzer kann umgruppieren, ohne historische Operationen umzuschreiben.

## Umsetzung

1. Append-only Journal mit Schema-Version, atomarem Projektcheckpoint und Wiederanlauf; Historie bleibt trotz Undo nachvollziehbar. P0-Snapshots ersetzen dies noch nicht.
2. Rust-Transaktionen anhand von Objekt-/Feld-Voraussetzungen. Unabhängige Änderungen automatisch anwenden, widersprüchliche behalten und anzeigen. Für verteilten Offline-Zustand Loro/Automerge anhand echter Musik-/Graph-Fixtures vergleichen; keine blinde LWW-Auflösung für gestalterische Konflikte.
3. Abhängigkeitsprüfung über Operationen: nach Clip-Split referenzierte IDs/Quellbereiche neu zuordnen; gelöschte Ziele, Tempoänderungen und Ripple-Edits verlangen Fachregeln. KI kann auf unbetroffenen Aufgaben weiterarbeiten.
4. Selektives Undo ist eine neue kompensierende Operation. Spätere menschliche Änderungen erhalten; bei abhängigen Änderungen Wahl anbieten statt ganzen Snapshot zurückzusetzen.
5. Ereignisstrom an UI mit Sequenznummer/Replay und Backpressure. Optionaler Zeiger hebt echte Zielobjekte hervor; Ausschalten ändert weder Ausführung noch Version. Hintergrundjobs funktionieren ohne geöffnetes UI.

## Abnahmen

Zwei Actors: Bass ändern und Drums setzen ohne Verlust; gleiche Note unterschiedlich ändern als Konflikt; Undo der KI erhält späteren manuellen Velocity-Wert; Neustart reproduziert Zustand und Verlauf; doppeltes Zustellen bleibt idempotent; Makrogruppe bis Operation aufklappbar. Plugin-/native Fremdänderungen nur als vollständig erfasst bezeichnen, wenn Adapter den konkreten Vorgang nachweislich erfasst.
