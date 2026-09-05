#!/bin/bash
# KI-DAW — Einmalige Installation
set -e

echo "=== KI-DAW Install ==="

# System packages
echo "→ System-Pakete..."
sudo apt-get update -q
sudo apt-get install -y \
  fluidsynth \
  fluid-soundfont-gm \
  x11vnc \
  xvfb \
  websockify \
  lmms \
  python3-pip \
  python3-venv 2>/dev/null || true

# Python venv
VENV="$HOME/ki_pipeline_env_312"
if [ ! -d "$VENV" ]; then
  echo "→ Erstelle Python-venv..."
  python3 -m venv "$VENV"
fi

source "$VENV/bin/activate"
echo "→ Python-Pakete..."
pip install -q --upgrade pip
pip install -q \
  fastapi \
  "uvicorn[standard]" \
  websockets \
  anthropic \
  midiutil

echo ""
echo "✓ Installation abgeschlossen."
echo ""
echo "Nächster Schritt:"
echo "  export ANTHROPIC_API_KEY='sk-ant-...'"
echo "  bash $(dirname $0)/start_ki_daw.sh"
