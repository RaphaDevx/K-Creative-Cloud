# Blender MCP — Setup

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
