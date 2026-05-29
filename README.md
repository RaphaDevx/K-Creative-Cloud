# K-Creative-Cloud

Open-Source Creative Cloud — vollständig über MCP (Model Context Protocol) steuerbar.
Claude behält volle Kontrolle über alle Tools; die GUIs bleiben gleichzeitig bedienbar.

## Installierte Programme

| Tool | Version | MCP-Status |
|------|---------|-----------|
| Blender | 4.0.2 | ✅ MCP bereit (Etappe 2) |
| GIMP | 3.2.4 (snap) | ✅ MCP bereit (Etappe 2) |
| Inkscape | 1.2.2 | 🔜 Etappe 3 |
| FreeCAD | 1.1 (snap) | 🔜 Etappe 3 |
| Kdenlive | 23.08.5 | 🔜 Etappe 3 |
| LMMS | 1.2.2 | 🔜 Etappe 3 |

## Architektur

```
K-Creative-Cloud/
├── blender-mcp/       # Blender MCP-Server (Python, Port 9876)
├── gimp-mcp/          # GIMP MCP via Script-Fu / REST
├── inkscape-mcp/      # Inkscape MCP via CLI + Python
├── freecad-mcp/       # FreeCAD MCP + G-Code Export
├── kdenlive-mcp/      # Kdenlive MCP via MLT-XML
├── lmms-mcp/          # LMMS MCP via CLI
├── docs/              # Setup-Guides pro Tool
└── scripts/           # Hilfsskripte (start-all, stop-all)
```

## Lokale MCP-Konfiguration

Alle Server sind in `.claude/mcp.json` als **project-scoped** eingetragen.
Sie laden nur wenn du im `K-Creative-Cloud/` Ordner bist — kein Impact auf andere Projekte.

## Etappen

- **Etappe 1** ✅ Programme installiert, Repo angelegt, GitHub bereinigt
- **Etappe 2** ✅ Blender-MCP (v1.5.5) + GIMP-MCP (56 Tools, GIMP 3.2.4)
- **Etappe 3** 🔜 Inkscape, FreeCAD (CAM/G-Code), Kdenlive, LMMS
