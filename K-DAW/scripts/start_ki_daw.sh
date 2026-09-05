#!/bin/bash
# KI-DAW — Startet alle Komponenten
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
VENV="${HOME}/ki_pipeline_env_312"
DISPLAY_NUM=":99"
VNC_PORT=5900
NOVNC_PORT=6080
API_PORT=9879

echo "=== KI-DAW Startup ==="

# API Key prüfen
if [ -z "$ANTHROPIC_API_KEY" ]; then
  if [ -f "$PROJECT_DIR/.env" ]; then
    export $(grep -v '^#' "$PROJECT_DIR/.env" | xargs)
  fi
fi
if [ -z "$ANTHROPIC_API_KEY" ]; then
  echo "FEHLER: ANTHROPIC_API_KEY nicht gesetzt."
  echo "  export ANTHROPIC_API_KEY='sk-ant-...'"
  exit 1
fi

# Bestehende Prozesse aufräumen
pkill -f "Xvfb $DISPLAY_NUM" 2>/dev/null || true
pkill -f "x11vnc.*$VNC_PORT" 2>/dev/null || true
pkill -f "websockify.*$NOVNC_PORT" 2>/dev/null || true
pkill -f "web_server.py" 2>/dev/null || true
sleep 1

# 1. Xvfb (virtuelles Display)
echo "→ Starte Xvfb $DISPLAY_NUM ..."
Xvfb $DISPLAY_NUM -screen 0 1600x900x24 -ac &
XVFB_PID=$!
sleep 1

# 2. LMMS GUI (headless)
echo "→ Starte LMMS..."
DISPLAY=$DISPLAY_NUM lmms &
LMMS_PID=$!
sleep 2

# 3. x11vnc (VNC-Server)
echo "→ Starte x11vnc auf Port $VNC_PORT..."
x11vnc -display $DISPLAY_NUM -nopw -listen localhost -xkb -forever -shared -rfbport $VNC_PORT &
X11VNC_PID=$!
sleep 1

# 4. websockify (noVNC-Bridge)
echo "→ Starte websockify auf Port $NOVNC_PORT..."
websockify --web /usr/share/novnc $NOVNC_PORT localhost:$VNC_PORT &
WEBSOCKIFY_PID=$!
sleep 1

# 5. FastAPI Backend
echo "→ Starte KI-DAW Backend auf Port $API_PORT..."
source "$VENV/bin/activate"
cd "$PROJECT_DIR/backend"
python3 web_server.py &
BACKEND_PID=$!
sleep 2

echo ""
echo "╔════════════════════════════════════════╗"
echo "║  KI-DAW läuft!                         ║"
echo "║                                        ║"
echo "║  Browser UI:  http://localhost:$API_PORT  ║"
echo "║  noVNC/LMMS:  http://localhost:$NOVNC_PORT  ║"
echo "║                                        ║"
echo "║  Ctrl+C zum Beenden                    ║"
echo "╚════════════════════════════════════════╝"

# Cleanup on exit
trap "echo '→ Beende alle Prozesse...'; kill $XVFB_PID $LMMS_PID $X11VNC_PID $WEBSOCKIFY_PID $BACKEND_PID 2>/dev/null; exit 0" INT TERM

wait $BACKEND_PID
