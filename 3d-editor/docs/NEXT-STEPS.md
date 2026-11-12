# 3d-editor — nächste Schritte und Arbeitsrhythmus

Stand: Iteration 0003, 13. November 2026. Eigener Rust-Editor, Standardauftritt weiterhin neutral. Jede Zeile ist eine begrenzte Ausbaustufe mit eigener Abnahme.

| Reihenfolge | Arbeitspaket | Nachweis vor Abschluss |
|---|---|---|
| 1 — erledigt in Iteration 0002 | Inset, gemeinsame Polygonunterteilung, Punkt-/Kantenauswahl, Punktposition bearbeiten | Geometrie-/Pickingtests, gespeicherte Commands/Undo und echte GUI-Bedienung bestanden |
| 2a — Iteration 0003 | Objekt-Mehrfachauswahl, gemeinsam verschieben/duplizieren/entfernen, Weltachsen-Verschieben mit relativem Fangraster | Ein Drag = eine Gruppe; Escape verwirft Vorschau; gemeinsame Abstände bleiben erhalten |
| 2b — als Nächstes | Drehen-/Skalieren-Gizmos, lokale Achsen und Rechteckauswahl | Gemeinsamer Pivot und explizite Koordinatenräume; ein Undo je Geste |
| 3 | Topologie-Grundlage: stabile Element-IDs, Kanten-/Flächenoperationen, Inset/Extrusion mit metrischen Optionen, Normalenwerkzeuge | keine stillen T-Junctions/ungültigen Flächen; IDs bleiben über spezifizierte Operationen zuordenbar |
| 4 | Modifier und Szenenhierarchie, Parenting, Sammlungen, Instanzen | nicht destruktiver Stack und Transformations-/Abhängigkeitsfixtures; Undo und Dateimigration |
| 5 | Materialsystem/PBR, Licht und Kameras; UV-Editor, Texturen, glTF | Referenzassets mit geprüften Farben/Einheiten und explizitem Verlustbericht |
| 6 | Robuste Projektdaten: Autosave/Wiederherstellung, unveränderliche Medienblöcke, vollständiges Änderungsjournal, Suite-Verknüpfung | simulierte Unterbrechung ohne Datenverlust, keine doppelte Zustandsautorität |
| 7 | Animation, Keyframes, Kurven, Rigging/Skinning | deterministische Posen/Exports; Timeline nur im Animationsbereich |
| 8 | Physik, Stoffprofile/Schnittmuster und CAD-/Druckpfad | reale Maß-/Materialfixtures; saubere Trennung zwischen Mesh, Solverparametern und präzisem CAD |
| 9 | Parallele KI-/Nutzeränderungen, Konflikte, selektives Undo, optionale KI-Zeiger | unabhängige Änderungen bleiben erhalten, widersprüchliche Varianten sichtbar; keine Screenshotsteuerung nötig |
| 10 | Plattformausbau: eigener Mac-Prüfjob und Paket, später iPad/Pencil, Identität und Erweiterungs-SDK | echte Zielgeräte/-systeme und klar ausgewiesene Plattformfähigkeiten |

Der Mac-Prüfjob wird früh vorbereitet und soll die laufenden Iterationen begleiten; er wartet nicht auf alle Fachfunktionen. Die Zeile Plattformausbau enthält die anschliessende Paket-/Mobilproduktarbeit. Ein vollständiger professioneller Ersatz bleibt ein grösseres Produktvorhaben; keine Kalenderzusage für Blender-Parität.

## Ablauf pro Iteration

1. Ein kleines konkretes Ziel und messbare Akzeptanz festhalten.
2. Unabhängige Aufgaben mit exakten Dateigrenzen an Subagenten geben. Abhängige Integration bleibt beim Hauptagenten.
3. Rückgaben fachlich prüfen und in den gemeinsamen Rust-Vertrag integrieren.
4. Formatprüfung, Geometrie-/Datei-/CLI-Tests und Clippy lokal ausführen. UI-Änderungen zusätzlich unter Linux mit echten Eingaben/GPU-Viewport prüfen.
5. Den geprüften Schritt direkt über `POST /api/handover` committen lassen. Keine direkten git-Commit-/Push-Befehle; fremdes Staging vorher erhalten und nachher unabhängig prüfen.
6. Sobald ein passender Mac-Job registriert ist, denselben Stand dort prüfen: Rust-Tests, Desktopstart/Metal, Dialoge, Eingaben und Zielsystemintegration. Testergebnis muss zum betreffenden Commit gehören.
7. Fehler als begrenzten Folgeschritt beheben und erneut prüfen; dann nächstes Arbeitspaket.

Lokal ist Linux jederzeit verfügbar. Der Mac-Worker ist online, aber die aktuelle Registry verweist für `kcreative` nur auf den bestehenden `dmgscript`-Productionpfad. Das belegt noch keinen Mac-Test des neuen Editors. Keine automatische Veröffentlichung/TestFlight-Freigabe durch Testläufe.

[Testmatrix](TEST-MATRIX.md) · [Iteration 0003](../iterations/0003/PLAN.md)
