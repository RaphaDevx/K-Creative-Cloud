#!/usr/bin/env bash
# Startet den Blender MCP Server.
# VORAUSSETZUNG: Blender muss laufen und das Addon aktiv sein (Port 9876).
# So aktivierst du das Addon in Blender:
#   Edit > Preferences > Add-ons > Install > addon.py auswählen > aktivieren
#   Dann im 3D Viewport: N-Panel > BlenderMCP > Connect

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

echo "Starte Blender MCP Server..."
echo "Blender muss laufen mit aktiviertem Addon auf Port 9876."
echo ""
cd "$PROJECT_DIR/blender-mcp"
uv run blender-mcp
