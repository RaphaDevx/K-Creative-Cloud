#!/usr/bin/env bash
# Kopiert das Blender Addon in das Blender Addons-Verzeichnis.
# Danach in Blender: Edit > Preferences > Add-ons > Install > addon.py

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
ADDON_SRC="$PROJECT_DIR/blender-mcp/addon.py"

# Blender 4.x Addon-Pfad
BLENDER_ADDONS="$HOME/.config/blender/4.0/scripts/addons"
mkdir -p "$BLENDER_ADDONS"

cp "$ADDON_SRC" "$BLENDER_ADDONS/blender_mcp_addon.py"
echo "Addon installiert: $BLENDER_ADDONS/blender_mcp_addon.py"
echo ""
echo "Nächste Schritte:"
echo "  1. Blender starten"
echo "  2. Edit > Preferences > Add-ons"
echo "  3. Nach 'BlenderMCP' suchen und aktivieren"
echo "  4. Im 3D Viewport: N-Panel > BlenderMCP > Connect"
