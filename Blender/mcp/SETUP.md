# Blender MCP — Setup & Studio

## Blender Studio (GUI im Browser)

```bash
~/K-Creative-Cloud/Blender/scripts/start-blender-studio.sh
```

| Service | Port | Zweck |
|---|---|---|
| Xvfb :99 | — | Virtuelles Display 1920×1080 |
| Blender | — | GUI auf virtuellem Display |
| x11vnc | 5901 | VNC-Stream |
| websockify | 6080 | VNC → WebSocket → Browser |
| BlenderMCP | 9876 | Claude MCP-Steuerung |
| K-Parametric | 9877 | GeoNodes/CAD-API |

Browser: `http://localhost:6080/vnc_lite.html`  
Studio-UI: `K-Creative-Cloud/Blender/studio/index.html`

---


## Wie es funktioniert

```
Claude ←→ MCP-Server (Python, Port stdio) ←→ Blender Addon (Socket, Port 9876) ←→ Blender
```

Das Addon läuft **innerhalb** von Blender und nimmt Python-Befehle entgegen.
Der MCP-Server übersetzt Claude-Anfragen in diese Befehle.

## Einmalig: Addon aktivieren

```bash
# Addon-Pfad (bereits installiert durch install-blender-addon.sh):
~/.config/blender/4.0/scripts/addons/blender_mcp_addon.py
```

In Blender:
1. `Edit > Preferences > Add-ons`
2. Suche: `BlenderMCP`
3. Häkchen setzen
4. Im 3D Viewport: `N`-Taste → Tab "BlenderMCP" → **Connect**

## Workflow

1. Blender starten
2. Addon verbinden (N-Panel > BlenderMCP > Connect)
3. Im K-Creative-Cloud-Ordner: `claude` starten → MCP-Server lädt automatisch
4. Claude steuert Blender via natürlicher Sprache

## Beispiel-Befehle für Claude

```
"Erstelle eine Kugel mit Radius 2 in der Mitte der Szene"
"Füge ein Metallic-Material mit Farbe #3A7BFF hinzu"
"Rendere die Szene und zeige mir den Viewport-Screenshot"
"Exportiere das Mesh als STL nach /home/raphael/renders/objekt.stl"
```

## Ports
- Blender Addon: `localhost:9876`
- MCP Server: stdio (kein separater Port)

---

## Installierte Addons

### TechDraw (v0.5 — Laurent Tesson)
Technische Zeichnungen aus 3D-Modellen: Ansichten (Front/Side/Top), Maßblätter, Titelblock.

```
Addon-Pfad:  /home/claude/.config/blender/4.0/scripts/addons/techdraw/
Backup:      /home/raphael/K-Creative-Cloud/Blender/mcp/addons/techdraw/
GitHub:      https://github.com/Laurent26/techdraw
```

**Aktivieren (einmalig in Blender GUI):**
`Edit > Preferences > Add-ons → "TechDraw" → Häkchen`

**Aktivieren per Script (headless):**
```python
bpy.ops.preferences.addon_enable(module="techdraw")
```

**Workflow:**
1. Objekt auswählen → in TechDraw als Target setzen
2. Checkboxen: Front / Side / Top / Perspective
3. "Add View" → Duplikate auf Zeichnungsblatt
4. "Add Camera" + "Add Sheet" (A4/A3 Titelblock)
5. Rendern → fertige technische Zeichnung

**Template-Blätter:** `techdraw/templates/FormatSheets.blend`

---

## Headless-Rendering (wichtig!)

- **EEVEE funktioniert NICHT headless** (EGL-Fehler, kein Display)
- **Cycles verwenden** + Denoiser deaktivieren:

```python
scene.render.engine = "CYCLES"
scene.cycles.samples = 256
scene.cycles.use_denoising = False   # kein OpenImageDenoiser in dieser Build
scene.cycles.device = "CPU"
```
