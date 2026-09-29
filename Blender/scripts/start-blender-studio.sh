#!/bin/bash
# ── Blender Studio — Robuster Start ───────────────────────────────────────────
# Blender GUI auf virtuellen Framebuffer → x11vnc → noVNC → Browser / VS Code
# Browser:  http://localhost:6080/vnc.html
# VS Code:  Ctrl+Shift+P → "Simple Browser: Show" → http://localhost:6080/vnc.html

DISPLAY_NUM=":99"
VNC_PORT=5910          # bewusst anderer Port um Konflikte zu vermeiden
NOVNC_PORT=6080
LOG_DIR="/tmp/blender-studio"
NOVNC_PATH="/usr/share/novnc"
ADDON_DIR="/home/claude/.config/blender/4.0/scripts/addons"

mkdir -p "$LOG_DIR"
LOGFILE="$LOG_DIR/studio.log"

log() { echo "[$(date '+%H:%M:%S')] $*" | tee -a "$LOGFILE"; }

# ── 1. Alles sauber beenden ────────────────────────────────────────────────────
log "Cleanup..."
pkill -f "blender" 2>/dev/null; sleep 0.3
pkill -f "x11vnc.*$VNC_PORT" 2>/dev/null
pkill -f "x11vnc.*display.*99" 2>/dev/null
pkill -f "websockify.*$NOVNC_PORT" 2>/dev/null
fuser -k ${NOVNC_PORT}/tcp 2>/dev/null
fuser -k ${VNC_PORT}/tcp 2>/dev/null
sleep 1

# ── 2. Xvfb starten (falls nicht aktiv) ───────────────────────────────────────
if ! DISPLAY="$DISPLAY_NUM" xdpyinfo >/dev/null 2>&1; then
    log "Starting Xvfb $DISPLAY_NUM (1920×1080)..."
    Xvfb "$DISPLAY_NUM" -screen 0 1920x1080x24 -ac +extension GLX +render -noreset \
         >"$LOG_DIR/xvfb.log" 2>&1 &
    sleep 1
else
    log "Xvfb $DISPLAY_NUM already running."
fi

# ── 3. x11vnc — streamt Display :99 auf VNC-Port ──────────────────────────────
log "Starting x11vnc (display $DISPLAY_NUM → port $VNC_PORT)..."
x11vnc \
    -display "$DISPLAY_NUM" \
    -rfbport "$VNC_PORT" \
    -forever \
    -shared \
    -nopw \
    -noshm \
    -bg \
    -quiet \
    -o "$LOG_DIR/x11vnc.log"
sleep 1

# ── 4. websockify — VNC-Port → WebSocket für noVNC ───────────────────────────
log "Starting websockify ($NOVNC_PORT → localhost:$VNC_PORT)..."
python3 /usr/bin/websockify \
    --web="$NOVNC_PATH" \
    --log-file="$LOG_DIR/websockify.log" \
    "$NOVNC_PORT" "localhost:$VNC_PORT" \
    >/dev/null 2>&1 &
WS_PID=$!
sleep 1

# Verify websockify started
if ! kill -0 $WS_PID 2>/dev/null; then
    log "ERROR: websockify failed to start. Check $LOG_DIR/websockify.log"
    cat "$LOG_DIR/websockify.log"
    exit 1
fi

# ── 5. Blender mit GUI auf Display :99 ────────────────────────────────────────
log "Starting Blender GUI on display $DISPLAY_NUM..."

# Startup-Script: aktiviert Addons + K-Parametric-Server
STARTUP_PY="$LOG_DIR/startup.py"
cat > "$STARTUP_PY" << 'PYEOF'
import bpy, os, sys

# Addons aktivieren
for name in ["techdraw", "object_print3d_utils"]:
    try:
        bpy.ops.preferences.addon_enable(module=name)
        print(f"[Studio] Addon aktiviert: {name}")
    except Exception as e:
        print(f"[Studio] Addon {name}: {e}")

# K-Parametric laden (Mechanical + Textile Module)
addon_path = "/home/raphael/K-Creative-Cloud/Blender/mcp/addons/k_parametric.py"
if os.path.exists(addon_path):
    addon_dir = os.path.dirname(addon_path)
    if addon_dir not in sys.path:
        sys.path.insert(0, addon_dir)
    exec(open(addon_path).read(), {"__file__": addon_path})
    print("[Studio] K-Parametric geladen (Port 9877)")
else:
    print(f"[Studio] WARNUNG: k_parametric.py nicht gefunden: {addon_path}")
PYEOF

DISPLAY="$DISPLAY_NUM" LIBGL_ALWAYS_SOFTWARE=1 blender \
    --python "$STARTUP_PY" \
    >"$LOG_DIR/blender.log" 2>&1 &
BLENDER_PID=$!

sleep 3

# ── 6. Status ──────────────────────────────────────────────────────────────────
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  ✅  Blender Studio läuft"
echo ""
echo "  Browser:       http://localhost:$NOVNC_PORT/vnc.html"
echo "  VS Code:       Ctrl+Shift+P → Simple Browser → oben URL"
echo "                 → http://localhost:$NOVNC_PORT/vnc.html"
echo ""
echo "  Parametric API:  localhost:9877  (Mechanical + Textile)"
echo "  Logs:            $LOG_DIR/"
echo ""
echo "  Blender PID: $BLENDER_PID"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# Vordergrund halten bis Blender beendet
wait $BLENDER_PID
log "Blender beendet. Cleanup..."
kill $WS_PID 2>/dev/null
pkill -f "x11vnc.*$VNC_PORT" 2>/dev/null
