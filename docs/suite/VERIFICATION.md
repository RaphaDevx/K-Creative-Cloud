# Suite Foundation P0 — Verifikation

12. November 2026. K-Harness: `20261112-153952-b8e8`.

## Gemessene Ergebnisse

- `cd creative-core && cargo test --locked`: **16 bestanden**, davon 7 bestehende Unit-Tests, 1 bestehender CLI-Test und 8 neue Dokumentgraph-Integrationstests. CLI-Neustarts verwenden echte persistierte temporäre Projekte.
- `.venv/bin/python -m pytest tests/test_suite_documents.py tests/test_creative_api.py -q`: **11 bestanden**, davon 4 neue HTTP/MCP-Graph-Tests und 7 vorhandene API-/Security-Tests.
- `.venv/bin/python -m pytest tests/test_creative_assistant.py tests/test_creative_brand.py -q`: **33 bestanden**. Planner-/Brand-Vertrag bleibt kompatibel.
- Scoped `git diff --check` für die geänderten vorhandenen Dateien: bestanden. Neue Dateien bei Abschluss ebenfalls auf Whitespace und vorhandene Markdown-Links geprüft.
- `cargo fmt --all -- --check`: bei Abschluss geprüft.

Die Python-Prüfung verwendet die bestehende Projekt-`.venv`; System-Python hat kein pytest. Keine neuen Abhängigkeiten installiert.

## Abgedecktes Verhalten

Graph: Missing-/archivierte Ziele, Duplikate und Zyklen ablehnen; Legacy-Projekt ohne Graph bleibt lesbar; Manifestgrenze und Parameter validiert. Archivvorschau schreibt weder Datei noch Revision. Veraltete Archive-Anfrage und fehlgeschlagener Batch ändern die Datei nicht.

Erhalten: je direktem Nutzer neue Manifest-ID, logische Zuordnung und Herkunft; bestehende Manifestdaten und vorgelagerte Links bleiben erhalten, nachgelagerte Verwendung bleibt funktionsfähig im Graph. Separate CLI-Prozesse sehen dasselbe Ergebnis. Undo stellt exakte alte Graph-IDs/Links wieder her, Redo denselben archivierten Graph.

Cascade: Diamantabhängigkeit wird vollständig und ohne Duplikate archiviert; gemeinsam genutzte Eingangsquelle und unabhängiger Nutzer bleiben aktiv. Archive/Preview in Batches abgelehnt. HTTP liefert auf veraltete Version 422 und erhält dazwischen gesetzte Note; Cross-Project-Link abgelehnt. MCP verwendet denselben Katalog und Zustand.

## Grenzen

Implementiert sind projektlokale Manifestoperationen, keine nativen Blender-/FreeCAD-/GIMP-Dateioperationen, echte Blob-Pins, verteilte Merges, Makro/Mikro-Verlaufs-UI, Zeigeranimation, OAuth, mobile App oder Pluginhost. Bestehendes Undo bleibt Snapshot-basiert und auf 100 Änderungen begrenzt. `last_archive` ist eine Operationsquittung, kein unveränderliches vollständiges Auditjournal.

Ein beliebiger Dateipfad im Manifest wird weder gelesen noch eingefroren. P0 schreibt das Projekt-JSON samt Historie neu, nicht die referenzierten Medienbytes. Erhaltung nativer Quelldaten muss P1 durch unveränderlichen Speicher nachweisen.

Es wurde kein Repository-weites Grün behauptet: globales `git diff --check` trifft bereits vorhandene CRLF-/Whitespace-Probleme in fremden Addonänderungen und eine nicht lesbare fremde Datei. Diese Dateien wurden nicht geändert. Keine Wiederholung oder Reparatur ausserhalb des Scopes.

## Gates und Übergabe

G1 Masterplan-Abdeckung: erfüllt, sieben Teilpläne inklusive Löschsemantik/Collaboration/Plugins/CAD/Textil/Unreal/Auth/iPad und Suite/Einzelapps gegen Auftrag geprüft.

G2 Rust-Operationen: erfüllt, 16 Tests bestanden.

G3 gemeinsamer HTTP-/MCP-Vertrag: erfüllt, neue und vorhandene Integrationsprüfungen bestanden.

G4 Dokumentation und Erhaltung bestehender Arbeiten: erfüllt durch Scoped-Diff-Review und [HANDOVER.md](HANDOVER.md). Nachfolgende API-Übergabe erfolgt: signierter Commit `f8dc0f7547b7900a97714a83719e777be1371f7a`, zu `kdev` gepusht, einschliesslich dieser Foundation und des neuen Editors. 122 fremde Stage-Pfade nachweislich erhalten. Release-Paket bleibt ein separater Schritt.
