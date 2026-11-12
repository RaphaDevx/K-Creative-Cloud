# 06 — Textil, Schnittmuster und Unreal

## Datenmodell

Kleidungsstück referenziert parametrische 2D-Schnittteile, Nahtpaarungen, Zugaben, Fadenlauf, Passzeichen, Größen-/Körpermaße und Stoffprofil. 3D-Mesh und Simulation sind abgeleitete Ergebnisse. Körpermaß-Shape-Keys allein beweisen keine korrekte Passform.

Stoffmessungen mit Einheit, Verfahren, Probe, Richtung (Kette/Schuss/Diagonal), Belastung und Unsicherheit speichern: Flächenmasse, Dicke, Zug-/Dehnungskurven, Scherung, Biegung, Dämpfung, Reibung. Messdaten getrennt von solverabhängigen Parametern halten. Nur Gewicht/Farbe auszuwählen ergibt kein physikalisch kalibriertes Material.

## Bestand prüfen

`modul_textile_cad.py`, vorhandene Cloth-Presets, Körpermaß-/SVG-Exporter inventarisieren und auf Ziel-Blender testen. Skill-Texte bezeichnen Presets als kalibriert; ohne Messbeleg gelten sie im neuen Produkt ausdrücklich nur als illustrative Startwerte. UV-Unwrap ist keine Garantie für maßhaltige, nähbare Schnittteile.

## Phasen

1. Rechteckiges Referenz-Schnittteil mit realen Maßen, Nahtzugabe, Fadenlauf und 1:1 SVG/PDF inklusive Kontrollquadrat. DXF erst nach definiertem Dialekt/Einheit und Rückimport-Fixture.
2. Parametrisches einfaches Kleidungsstück und Größenvariante; Nahtlängen/Paarungen prüfen. Simulationsmesh automatisch ableiten, 2D-Quelle bleibt editierbar.
3. Blender-Cloth-Job mit gespeichertem Enginebuild, Meshauflösung, Zeitschritt und Stoffparametern. Mess-/Drape-Fixture und reale Probenaht vergleichen.
4. Unreal als optionaler separater Engineadapter, nicht als erforderliche Appbasis: USD/GLTF/FBX je nach Inhalt und verifiziertem Importer. Chaos-Cloth/Dataflow versionsgebunden testen.
5. Roundtrip explizit pro Feld: Geometrie, Skeleton, Skinning, Materialien, Nähte, Einheiten, Achsen, Animation und solverbezogene Parameter. Blender-/Chaos-Stiffness sind nicht pauschal austauschbar. Verlustbericht und unveränderte Ausgangsquelle erhalten.

## Abnahmen

10-cm-Kontrollquadrat gedruckt und gemessen; Schnittnahtpaare passen; Stoffvarianten speichern Messherkunft; Unreal-Referenzfixture behält Maßstab und Animation. Keine Zusage professioneller Fertigungsqualität allein aufgrund einer optisch plausiblen Simulation; physischer Prototyp gehört zur fachlichen Abnahme.
