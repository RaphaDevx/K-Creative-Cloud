#!/usr/bin/env bash
# K-Creative Studio — Desktop App Launcher
set -e

DESKTOP_DIR="$(cd "$(dirname "$0")" && pwd)"
STUDIO_DIR="$(cd "$(dirname "$0")/../studio" && pwd)"
APPIMAGE="$DESKTOP_DIR/release/K-Creative Studio-0.1.0.AppImage"

echo "════════════════════════════════════════"
echo "  K-Creative Studio"
echo "════════════════════════════════════════"

# 1. Ensure backend is running
if ! curl -s http://localhost:7000/api/check >/dev/null 2>&1; then
    echo "→ Starting Python backend..."
    python3 "$STUDIO_DIR/server.py" &>/tmp/studio.log &
    sleep 2
fi

echo "→ Backend: http://localhost:7000"

# 2. Launch AppImage if built, else Electron dev, else browser
if [ -f "$APPIMAGE" ]; then
    echo "→ Launching AppImage..."
    DISPLAY="${DISPLAY:-:99}" "$APPIMAGE" --no-sandbox --enable-unsafe-swiftshader
elif command -v electron &>/dev/null; then
    echo "→ Launching Electron dev mode..."
    cd "$DESKTOP_DIR" && DISPLAY="${DISPLAY:-:99}" \
        electron . --no-sandbox --enable-unsafe-swiftshader
else
    echo "→ Öffne im Browser (kein Desktop-App gefunden)..."
    xdg-open http://localhost:7000 2>/dev/null || \
        open http://localhost:7000 2>/dev/null || \
        echo "   Manuell öffnen: http://localhost:7000"
fi
