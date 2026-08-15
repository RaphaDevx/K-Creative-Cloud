#!/usr/bin/env bash
# K-Creative Studio — Backend Server starten
set -e

STUDIO_DIR="$(cd "$(dirname "$0")" && pwd)"

echo "════════════════════════════════════════"
echo "  K-Creative Studio"
echo "  http://localhost:7000"
echo "════════════════════════════════════════"
echo ""
echo "Optional: Blender Studio parallel starten:"
echo "  ~/K-Creative-Cloud/Blender/scripts/start-blender-studio.sh"
echo "  → Blender VNC: http://localhost:6080"
echo ""

cd "$STUDIO_DIR"
python3 server.py
