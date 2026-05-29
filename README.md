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

## Etappen

- **Etappe 1** ✅ Programme installiert, Repo angelegt, GitHub bereinigt
- **Etappe 2** ✅ Blender-MCP (v1.5.5) + GIMP-MCP (56 Tools, GIMP 3.2.4)
- **Etappe 3** ✅ Inkscape-MCP + FreeCAD-MCP + Kdenlive-MCP (custom) + LMMS-MCP (custom)
