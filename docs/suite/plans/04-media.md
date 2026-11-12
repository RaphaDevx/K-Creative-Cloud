# 04 — Foto, Vektor, Video und Notes

## Eigene Fachoberflächen

Foto/Vektor: Canvas, Ebenen, Masken und nicht destruktive Filter. Notes: Blöcke, Anhänge, Quellverweise. Video: Tracks, Clips, Zeitbasis und Vorschau. Gemeinsame Asset-/Verlaufskomponenten, keine verpflichtende Timeline für alle Apps.

## Formate und Erweiterungen

- Anfangs PNG/JPEG/WebP, SVG, WAV/FLAC/MIDI, MP4 mit konkret getesteten Codecs; zusätzliche Formate über Capability-Matrix.
- Native Quellen wie XCF, BLEND und FCStd extern weiterbearbeitbar erhalten. PSD/AI/AEP/Premiere/CLO usw. nur nach Echtdatenprüfung; Import bedeutet keine vollständige Editierbarkeit aller Fremdfunktionen.
- Bildfilter zunächst eingebaute Operationen; GEGL über GIMP und OpenFX für passende Bild-/Videoworker prüfen. LUT ist eine Farbtransformation, kein Ersatz für beliebige Filter. Photoshop-Plugins sind ein anderer Hostvertrag und nicht automatisch kompatibel.
- Farbverwaltung mit profilierten Ein-/Ausgängen; OpenColorIO für geeignete Video/3D-Pipelines prüfen, ICC-Profil-/Druckworkflow für Foto separat behandeln. Pluginbinaries plattformgebunden und lizenzabhängig.

## Seamless-Wechsel

„Quelle bearbeiten“ öffnet exaktes Dokument plus Auswahl, „Zur Verwendung“ führt zur Timeline/Seite zurück. Drag-and-drop bietet Kopie, verknüpfte Version oder Ableitung. Neue Quellrevision erzeugt invalidierbare Proxy-/Renderjobs und Update-Hinweis; freigegebene Produktionen pinnen Versionen.

## Abnahmen

Foto in Video referenzieren → Quelle ändern → aktualisierten Proxy übernehmen → alte Version wiedergeben. Notes-Skizze in Sketcher öffnen; keine zweite unbemerkte Autorität. Jeder Adapter dokumentiert Farb-, Text-, Masken- und Effektverluste. Keine neue KI-Chat-/Zeigerfunktion behaupten, bevor sie im UI geprüft ist.
