#!/usr/bin/env bash
# Startet den GIMP MCP Server.
# VORAUSSETZUNG: GIMP 3 (snap) muss laufen.
# Plugin aktivieren:
#   GIMP > Tools > Start MCP Server
# Server läuft dann auf localhost:9877

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

echo "Starte GIMP MCP Server..."
echo "GIMP 3 muss laufen (snap) mit aktiviertem Plugin."
echo "In GIMP: Tools > Start MCP Server"
echo ""
cd "$PROJECT_DIR/gimp-mcp"
uv run --python 3.12 gimp_mcp_server.py
