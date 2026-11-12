# 3d-editor

Eigenständiger 3D-Editor mit Rust-Anwendungscode, nativer egui-Oberfläche und wgpu-Viewport. Kein Blender-, Python-, Electron- oder JavaScript-Prozess wird zum Bearbeiten benötigt. Dies ist der erste funktionale Stand des neuen Editors, kein vollständiger Blender-Ersatz.

## Enthalten

- Startseite mit neutralem `3d-editor`-Auftritt; austauschbares JSON-Markenprofil.
- Tiefengeprüfte 3D-Ansicht mit Beleuchtung, Bodenraster, Auswahlkonturen und optionalen Polygonkanten.
- Würfel, Kugel, Zylinder, Fläche; Auswahl durch tatsächlichen Strahl-/Dreiecktest.
- Position, Rotation, positive Skalierung, Name, Farbe und Sichtbarkeit im Inspektor; explizit als eine Gruppe anwenden.
- Mehrere Objekte mit Shift auswählen, gemeinsam verschieben/duplizieren/entfernen; Weltachsen-Gizmo mit Vorschau, Abbruch und relativem Fangraster.
- Fläche auswählen und entlang ihrer lokalen Normalen extrudieren.
- Punkt-/Kantenauswahl mit Tiefenprüfung, lokale Punktposition und Kantenverschiebung; angrenzende Polygone werden bei Bedarf in derselben Gruppe trianguliert.
- Flächen proportional zur Mitte einrücken und Meshes mit gemeinsam verwendeten Kantenpunkten linear unterteilen, ohne Glättung.
- Persistente Bearbeitungsgruppen mit Actor, Aufgabenpfad, technischen Befehlen und Vorher/Nachher-Unterschieden; Undo/Redo mit weiterlaufenden Revisionen.
- Atomare `.scene3d`-Dateien inklusive editierbarer Meshes, Verlauf und 100 Undo-Zuständen.
- OBJ-Geometrieimport und Export sichtbarer Objekte mit eingerechneten Transformationen.
- Dieselben Rust-Befehle ohne Oberfläche per CLI nutzbar.

## Starten

Nach Bereitstellung eines Desktop-Testbinaries durch Tests oder des späteren K-Dev-Builds:

```bash
./3d-editor/start.sh
./3d-editor/start.sh --scene /pfad/Modell.scene3d
./3d-editor/start.sh --brand /pfad/markenprofil.json
```

Der Launcher kompiliert nichts. Er nimmt `EDITOR_3D_BIN`, das vorhandene Releasebinary oder das Desktop-Testbinary aus `target/debug`. Das Binary muss mit dem Standardfeature `desktop` entstanden sein. Paketierung/Signierung/Release laufen über K-Dev.

## Bedienung

Neue Szene erstellt einen bearbeitbaren Würfel. Links Objekte hinzufügen/auswählen, rechts Eigenschaften ändern und **Änderungen anwenden**. **Fläche** in der Viewportleiste wählen und eine sichtbare Fläche anklicken; rechts erscheint die Extrusion. Maßangaben sind Meter; Extrusionslänge bezieht sich auf lokale Meshkoordinaten, also vor Objektskalierung.

**Objekt**: Shift-Klick im Baum oder Viewport erweitert/verkleinert die Auswahl; Ctrl/Cmd+A wählt alle sichtbaren Objekte. Die aktive Baumzeile ist bei Mehrfachauswahl markiert. Rechts kann ein gemeinsamer numerischer Versatz angewandt werden. Die X/Y/Z-Pfeile verschieben entlang der Weltachsen. Loslassen erzeugt einen Undo-Schritt, Escape oder Fensterwechsel verwirft die Vorschau. **Raster** rundet den gemeinsamen Versatz; es richtet einzelne Objektpositionen nicht absolut am Raster aus. Nahezu frontal betrachtete Achsen werden ausgeblendet. Ein Klick auf eine verborgene Baumzeile blendet das Objekt wieder ein.

**Punkt** beziehungsweise **Kante** aktiviert die Elementauswahl in einem Abstand von zehn logischen Pixeln. Verdeckte Elemente werden nicht ausgewählt. Der Inspektor bearbeitet Punktkoordinaten beziehungsweise verschiebt beide Kantenpunkte gemeinsam. **Modellieren** bietet Extrusion, proportionales Einrücken und lineare Unterteilung auch über das Menü. Einrücken `0.2` bewegt jeden Flächenpunkt 20 Prozent zur Punktmittelposition; das ist kein metrisch gleich breiter Rand. Lineare Unterteilung glättet die Form nicht.

- Rechts ziehen: Kamera drehen. Mittlere Maustaste ziehen: Kamera verschieben. Scrollen: Zoom.
- F: Auswahl fokussieren. Front/Oben/Perspektive: benannte Kamerablicke.
- Ctrl/Cmd+N/O/S: Neu/Öffnen/Speichern. Ctrl/Cmd+Shift+S: Speichern unter.
- Ctrl/Cmd+Z und Ctrl/Cmd+Shift+Z: Undo/Redo. Ctrl/Cmd+D: Duplizieren. Delete: Entfernen.
- Verlauf aufklappen: Gruppe → Befehl/Objektdifferenz. Dateiverlauf bleibt auch nach Undo erhalten.

Ungespeicherte Änderungen werden vor Neu/Öffnen/Schliessen abgefragt. Noch nicht angewandte Inspektorfelder sind ein Entwurf und werden beim Auswahlwechsel verworfen. Für Tastaturbearbeitung haben Textfelder Vorrang vor Objekt-Shortcuts.

## Headless-Befehle

```bash
./3d-editor/start.sh new /tmp/scene.scene3d
./3d-editor/start.sh apply /tmp/scene.scene3d /tmp/group.json /tmp/result.scene3d
./3d-editor/start.sh inspect /tmp/result.scene3d
./3d-editor/start.sh undo /tmp/result.scene3d /tmp/undone.scene3d
./3d-editor/start.sh redo /tmp/undone.scene3d /tmp/redone.scene3d
./3d-editor/start.sh export-obj /tmp/result.scene3d /tmp/result.obj
```

Eine Befehlsgruppe für eine leere Datei mit Revision 0:

```json
{
  "expected_revision": 0,
  "actor": "local-agent",
  "task_path": ["Modell", "Grundkörper"],
  "label": "Grundkörper erstellen",
  "commands": [{ "action": "add", "primitive": "cube" }]
}
```

Weitere Aktionen: `import_mesh`, `transform`, `translate_objects`, `duplicate_objects`, `remove_objects`, `rename`, `color`, `visibility`, `duplicate`, `remove`, `extrude`, `inset`, `subdivide`, `move_vertex`, `move_edge`. Parameter stehen in `src/commands.rs`. `inspect` liefert die vollständige Szene mit Objekt-IDs und Verlauf. Gruppen sind atomar und revisionsgesichert; bei Fehlern wird die Ausgabedatei nicht überschrieben. Actor ist im lokalen CLI eine Herkunftsangabe, keine authentifizierte Identität. Es gibt noch keinen HTTP-/MCP-Server für diese neue Fachengine.

## Branding

`branding/neutral.json` ist der eingebettete Standard. `--brand` oder **Programm → Markenprofil laden** setzt ein eigenes Profil. Plätze: grosser Startauftritt mit Monogramm, Wortmarke und Leitsatz; Fenstertitel/Programmname; optional eine feste Signatur im Viewport und Auswahlakzent. Keine Änderung der Objektmaterialien oder Szenendateien. Kein künstlicher Splash-Timer.

Dateiformat Version 1 prüft Pflichtfelder, Textlängen, Steuerzeichen und Mindestkontrast der Akzentfarbe zur Startfläche. Statische Logo-/Schrift-/Artwork-Assets, Paketicon und persistierte Nutzerpräferenzen sind spätere Erweiterungen. Das Profil ist keine Erlaubnis, fremde Markendateien auszuführen.

## Entwicklung und Prüfung

Rust mindestens 1.88 für den gelockten Desktop-Abhängigkeitsstand; geprüft mit 1.98.1. System-Rust 1.75 dieses Hosts genügt nicht. Keine globale Toolchain umstellen; vorhandene moderne Toolchain gezielt verwenden. Für Linux sind X11/Wayland- und GPU-Treiber erforderlich. Erstverifikation hier unter Linux/Xvfb mit Software-GPU; macOS/Windows wurden nicht ausgeführt.

```bash
cd 3d-editor
cargo test --locked --no-default-features
cargo test --locked
cargo fmt --all -- --check
```

`--no-default-features` baut einen reinen Headless-CLI ohne Desktop-Abhängigkeiten. Die Desktop-Tests erzeugen ausserdem das GUI-Testbinary. Screenshots und interaktive Prüfbelege stehen unter `artifacts/` (gitignored), der Bericht in `VERIFICATION.md`.

Reproduzierbarer Linux-GUI-Smoke mit tatsächlichen Maus-/Tastaturereignissen, vorhandener Projekt-`.venv`, Pillow und xdotool:

```bash
xvfb-run -a -s "-screen 0 1440x900x24" ../.venv/bin/python scripts/gui_smoke.py
```

Dieser Prüfhelfer erzeugt ausschliesslich neue Fixture-/Screenshotordner und benötigt Python nur für die Prüfung, nicht für die Anwendung. Native Dateidialoge und macOS-/Windows-Integration sind gesonderte Zielsystemprüfungen.

## Grenzen und nächste Schritte

Kein .blend-Import, UV-/Texturimport, Fremdmaterial-/OBJ-MTL-Support, Rigging, Animation, Physik, CAD-Kern, Pluginhost, Google-/Apple-Anmeldung oder verteilter Merge. OBJ importiert Polygongeometrie als ein Objekt; Gruppen/UVs/Normals/Materialien werden nicht erhalten. Nur ebene, konvexe Polygone werden akzeptiert. Extrusion garantiert keine allgemeine Selbstüberschneidungsfreiheit. Kein präzises Fertigungs-CAD.

Grenzen v0.1: 256 Objekte, 100000 Punkte/Flächen pro Mesh, 500000 Szenenpunkte, 64 MiB Szenendatei und 10000 Historieneinträge. Historie/Checkpoints speichern Geometrie im JSON; grosse Szenen benötigen den geplanten Blob-Store und Journalumbau. Vorhandene Suite-/Blenderdateien bleiben unabhängig erhalten.

[Architektur](ARCHITECTURE.md) · [Roadmap](ROADMAP.md) · [Nächste Schritte](docs/NEXT-STEPS.md) · [Testmatrix](docs/TEST-MATRIX.md) · [Abnahmekriterien](GATES.md)
