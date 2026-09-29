# K-Creative-Cloud

Open-Source Creative Cloud — vollständig über MCP (Model Context Protocol) steuerbar.
Claude behält volle Kontrolle über alle Tools; die GUIs bleiben gleichzeitig bedienbar.

## Installierte Programme

| Tool | Version | MCP-Typ | Port / Methode |
|------|---------|---------|---------------|
| Blender | 4.0.2 | Socket-Addon | 9876 |
| GIMP | 3.2.4 (snap) | Socket-Plugin | 9877 |
| FreeCAD | 1.1 (snap) | Socket-Addon | 9878 |
| Inkscape | 1.2.2 | CLI + DOM | — (kein live Prozess) |
| Kdenlive | 23.08.5 | MLT-XML + melt | — (kein live Prozess) |
| LMMS | 1.2.2 | CLI-Rendering | — (kein live Prozess) |

## Architektur

```
K-Creative-Cloud/
├── blender-mcp/     # ahujasid/blender-mcp v1.5.5 — Socket-Addon, Port 9876
├── gimp-mcp/        # maorcc/gimp-mcp — 56 Tools, GIMP 3.2, Port 9877
├── freecad-mcp/     # bonninr/freecad_mcp — Socket-Addon, Port 9878
├── inkscape-mcp/    # grumpydevorg/inkscape-mcps — CLI + SVG-DOM, kein live Prozess
├── kdenlive-mcp/    # custom — MLT-XML Projekte + melt CLI
├── lmms-mcp/        # custom — CLI-Rendering, Presets, Samples
├── scripts/         # start-blender-mcp.sh, start-gimp-mcp.sh, install-blender-addon.sh
└── .claude/         # mcp.json (project-scoped, lädt nur in diesem Ordner)
```

## Quick Start

```bash
cd ~/K-Creative-Cloud
claude   # alle 6 MCP-Server laden automatisch
```

### Blender
1. Blender starten
2. Edit > Preferences > Add-ons > "BlenderMCP" aktivieren
3. N-Panel > BlenderMCP > Connect

### GIMP
1. `gimp` starten (snap-Version)
2. Bild öffnen, dann: Tools > Start MCP Server

### FreeCAD
1. FreeCAD starten
2. Tools > Addon Manager > `freecad_mcp` aktivieren + Neustart

### Inkscape, Kdenlive, LMMS
Direkt per Claude-Befehl steuerbar — kein manueller Setup nötig.

## K-Creative Studio (Web UI)

```bash
# Studio starten (Port 7000):
~/K-Creative-Cloud/studio/start-studio.sh
# → http://localhost:7000

# Blender VNC parallel:
~/K-Creative-Cloud/Blender/scripts/start-blender-studio.sh
# → http://localhost:6080/vnc_lite.html
```

Studio = Browser-UI mit Viewer (Blender VNC embed, GIMP/Inkscape Preview) + Chat-Panel.
Claude Code Terminal bleibt parallel offen — der "Double Layer".

## Security Audit (2026-08-14)

| Tool | Status | Fixes |
|------|--------|-------|
| Inkscape | ✅ SAFE | — |
| LMMS | ✅ SAFE | — |
| Blender | ⚠️ FIXED | Prompt-Injection entfernt (2 Stellen), Telemetry deaktiviert |
| Kdenlive | ⚠️ CAUTION | Filename-Sanitization fehlt (eigener Code, akzeptabel) |
| Video-Shorts | ⚠️ CAUTION | Hardcoded venv-Pfad |
| Remotion | ⚠️ CAUTION | Supabase-URL hardcoded |
| GIMP | ⚠️ NOTE | eval/exec = GIMP Python-Fu by design, isoliert in GIMP-Kontext |
| FreeCAD | ⚠️ NOTE | exec = FreeCAD Scripting by design, isoliert in FreeCAD-Kontext |

## Etappen

- **Etappe 1** ✅ Programme installiert, Repo angelegt, GitHub bereinigt
- **Etappe 2** ✅ Blender-MCP (v1.5.5) + GIMP-MCP (56 Tools, GIMP 3.2.4)
- **Etappe 3** ✅ Inkscape-MCP + FreeCAD-MCP + Kdenlive-MCP (custom) + LMMS-MCP (custom)
- **Etappe 4** ✅ K-Creative Studio (Web UI), Security Audit + Fixes, Brand/Designer System

## TODO

### Kokoro TTS (`kokoro-tts/`)
Kokoro TTS + Video-Renderer für Stats/Shorts — noch nicht als MCP integriert.
- `generate_audio.py` — Kokoro ONNX TTS (Stimme `af_heart`, Speed 1.15x)
- `render_video.sh` — Kombination Audio + Background-Video → MP4
- Modelle: `kokoro-v1.0.int8.onnx` + `voices-v1.0.bin` (grosse Binaries, nicht committen)
- **Nächster Schritt:** Als MCP-Server wrappen (Python stdio MCP) damit Claude direkt Audio/Videos generieren kann
