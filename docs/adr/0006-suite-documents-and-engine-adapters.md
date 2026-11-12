# ADR 0006 — Suite-Dokumentgraph und Fachengine-Adapter

## Status

Accepted für die Richtung und den projektlokalen P0-Dokumentgraph. Verteiltes Merge, Binärspeicher, Pluginhost und mobile Shell sind spätere, separat zu prüfende Implementierungen.

## Kontext

Separate Kreativprogramme sollen Quellen wiederverwenden, KI und Nutzer nachvollziehbar bearbeiten lassen und Löschvorgänge ohne gebrochene Referenzen anbieten. Der bestehende Rust-Kern hat einen gemeinsamen Zustand mit Snapshot-Undo, aber keinen Dokumentgraph und keine verteilte Zusammenarbeit. Bestehende native Adapter decken nur Teilmengen ab.

## Entscheidung

Rust bleibt gemeinsame Kontroll- und Versionsschicht. Blender/FreeCAD und weitere Engines über explizite Adapter erhalten, statt sie neu in Rust zu schreiben. Apps teilen Dokument-/Befehlsverträge, aber behalten fachliche Datenmodelle und unterschiedliche Arbeitsflächen.

P0 ergänzt projektlokale Dokumentmanifeste mit gerichteten Abhängigkeiten (Nutzer → Quelle), Zyklusprüfung und explizitem Archivieren. Archivierung bietet `preserve_dependents` mit lokalen Manifestkopien und umgehängten Referenzen oder `cascade_dependents` mit transitiven Nutzern. Beide verwenden dieselbe atomare Persistenz und Undo-Historie. Vorschau ist read-only; Archive verlangt die erwartete Projektversion. Keine Mediendateien physisch entfernen. Kopien erhalten vorgelagerte Quellenlinks und Herkunft; Teilen von Manifestreferenzen ist keine Garantie unveränderlicher externer Dateien.

## Begründung

Dateikopien pro Verwendung verschwenden Speicher und verlieren Updateherkunft. Ein universelles Komplettdokument für Noten, B-Rep und Rasterdaten würde die Fachmodelle verwischen. Ein vollständiger Engine-Rewrite verhindert einen frühen brauchbaren Workflow. Bestehende ID-/Revision-/Batch-Verträge ermöglichen einen kleinen prüfbaren Einstieg ohne zweite Zustandsautorität.

## Konsequenzen

P0 schreibt weiterhin das JSON-Projekt samt Undo-Snapshots neu, aber keine Medienbytes. Späterer append-only Verlauf und content-adressierter Blob-Store vermeiden unbeschränkt wachsende Metadatenkopien und ermöglichen echte Versionpins. Aktuelle Archive-Operationen werden zunächst nicht an den automatischen Sprachplaner freigegeben. Native-App-Roundtrip, Cross-Project-Referenzen und selektives kollaboratives Undo sind nicht aus P0 ableitbar.

## Austausch

Bei späterem Rust-Service bleiben Aktionsnamen und Schema stabil oder werden versioniert migriert. Graphzustand niemals parallel im Frontend pflegen. Neue Blob-/Journalpersistenz benötigt Migration bestehender Projekte und Wiederanlauftests; Engineaustausch verlangt Format-/Fähigkeitsfixtures statt stiller Konvertierung.
