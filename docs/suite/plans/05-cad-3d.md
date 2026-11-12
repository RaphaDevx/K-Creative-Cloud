# 05 — CAD, Blender und 3D-Druck

Nachfolgender Nutzerentscheid: eigener Rust-3D-Ersatz unter `3d-editor/`, siehe ADR 0007 und dessen Roadmap. Der folgende Adapterplan beschreibt weiterhin die bestehenden Kompatibilitäts-/CAD-Workflows; er wird nicht als Implementierung des neuen Editors ausgegeben.

## Basisentscheidung

Blender behalten: Mesh, Modifier, Material, Rig, Animation, Cloth, Rendering und Headless-Jobs. FreeCAD als präzisen CAD-Partner behalten: bemaßte Skizzen/Constraints, parametrische Volumenkörper, technische Zeichnungen und STEP. Rust verbindet Identitäten, Versionen, Jobs und validierte Fachbefehle. Engine-Code in Rust neu zu schreiben wäre ein separates mehrjähriges Vorhaben.

Die vorhandenen Primitive-Rezepte im eigenen Workspace begrenzen die heutige Anbindung, nicht die Fähigkeiten der Engines. Vorhandene Addons unter Blender/mcp und FreeCAD-Adapter inventarisieren; dokumentierte Skill-Behauptungen zu Laufzeitfähigkeiten jeweils testen.

## Durchstich

1. 2D-Sketch mit Einheit mm, Constraints und stabilen Element-IDs speichern.
2. FreeCAD erstellt geschlossenen Sketch und Extrusion als parametrisierte Ableitung; native FCStd-Datei erhalten.
3. „Quelle bearbeiten“ ändert definierte Bemaßung; neue Ableitung und Preview erzeugen, keine unkontrollierte Überschreibung.
4. Für Blender tessellierte Darstellung mit dokumentierter Toleranz; CAD-Quelle bleibt erhalten. Mesh ist kein verlustfreier Ersatz für B-Rep oder Constraints.
5. STEP für geeigneten CAD-Austausch; STL/3MF nach geprüftem Exporter für Druck. Einheit, Bounding Box, Manifold, Orientierung und Mindestwandstärke prüfen. Slicer bleibt separate Fähigkeit.

## Adaptertiefe

Zunächst benannte geprüfte Befehle und Snapshot-Vergleich. Beliebige manuelle Edit-Mode-Eingriffe/Plugins nicht als semantisch zusammenführbar ausgeben. Große Topologieänderungen liefern neue Geometrieversion plus Konflikt, nicht erfundene feldweise Merges.

## Abnahmen

Referenzkörper mit bekannter Länge/Bohrung; Maßänderung bleibt in FCStd editierbar, exportierte Maße stimmen innerhalb definierter Toleranz, Druckmesh geschlossen. Gemeinsame Quellenarchivierung erhält lokale Sketch-Manifestkopie; native Datei-Erhaltung erst nach Blob-Store-Verifikation.
