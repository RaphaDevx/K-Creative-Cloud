#!/bin/bash
# Builds the Python backend into a standalone binary using PyInstaller
set -e

STUDIO_DIR="$(cd "$(dirname "$0")/../../studio" && pwd)"
DESKTOP_DIR="$(cd "$(dirname "$0")/.." && pwd)"

echo "[build-backend] Installing PyInstaller and dependencies..."
cd "$STUDIO_DIR"

pip3 install pyinstaller fastapi uvicorn aiofiles h11 starlette anyio 2>&1 | tail -5

echo "[build-backend] Building standalone server binary..."
pyinstaller server.spec --distpath "$STUDIO_DIR/dist" --workpath "$STUDIO_DIR/build" --noconfirm

echo "[build-backend] Done → $STUDIO_DIR/dist/k-creative-server"
