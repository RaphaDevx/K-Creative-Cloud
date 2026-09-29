"""
K-Parametric — Haupt-Dispatcher (Port 9877)
Leitet JSON-Befehle an das zuständige Modul weiter:
  modul_mechanical_cad  → GeoNodes, CAD Sketcher, STL-Export, 3D-Print
  modul_textile_cad     → Cloth-Physik, Körpermaße, Mixamo, Schnittmuster
  exec_python           → direktes bpy-Script (beide Module)
"""

import bpy
import threading
import socket
import json
import queue
import traceback
import time
import sys
import os

bl_info = {
    "name": "K-Parametric Control",
    "author": "K-Creative-Cloud",
    "version": (1, 1),
    "blender": (4, 0, 0),
    "description": "KI-gesteuerte parametrische Kontrolle (Mechanical + Textile) via Socket Port 9877",
    "category": "Interface",
}

PORT = 9877

# ── Modul-Imports (aus gleichem Verzeichnis) ──────────────────────────────────
_addon_dir = os.path.dirname(os.path.abspath(__file__))
if _addon_dir not in sys.path:
    sys.path.insert(0, _addon_dir)

_mechanical = None
_textile    = None

def _load_modules():
    global _mechanical, _textile
    try:
        import modul_mechanical_cad as mc
        _mechanical = mc
    except ImportError as e:
        print(f"[K-Parametric] modul_mechanical_cad nicht geladen: {e}")
    try:
        import modul_textile_cad as tc
        _textile = tc
    except ImportError as e:
        print(f"[K-Parametric] modul_textile_cad nicht geladen: {e}")

_command_queue = queue.Queue()
_result_store  = {}
_server        = None


# ── Command-Dispatch (Blender-Hauptthread) ────────────────────────────────────

def _dispatch_commands():
    while not _command_queue.empty():
        try:
            cmd_id, cmd = _command_queue.get_nowait()
            result = _route(cmd)
            _result_store[cmd_id] = result
        except Exception as e:
            if 'cmd_id' in dir():
                _result_store[cmd_id] = {"error": str(e), "trace": traceback.format_exc()}
    return 0.1


def _route(cmd: dict) -> dict:
    """Leitet Befehle ans richtige Modul weiter."""
    action = cmd.get("action", "")

    # Direktes Python-Execution (immer verfügbar)
    if action == "exec_python":
        code = cmd.get("code", "")
        local_ns = {"bpy": bpy, "result": None}
        try:
            exec(compile(code, "<k_parametric>", "exec"), local_ns)
            return {"ok": True, "result": str(local_ns.get("result", ""))}
        except Exception as e:
            return {"error": str(e), "trace": traceback.format_exc()}

    # Mechanical CAD
    if _mechanical and action in _mechanical.ACTIONS:
        return _mechanical.dispatch(cmd)

    # Textile CAD
    if _textile and action in _textile.ACTIONS:
        return _textile.dispatch(cmd)

    # Fallback: zeige verfügbare Aktionen
    mech_actions = list(_mechanical.ACTIONS) if _mechanical else []
    text_actions = list(_textile.ACTIONS)    if _textile    else []
    return {
        "error": f"Unknown action '{action}'",
        "available_mechanical": mech_actions,
        "available_textile":    text_actions,
        "always_available":     ["exec_python"]
    }


# ── Socket-Server ─────────────────────────────────────────────────────────────

class KParametricServer:
    def __init__(self, port=PORT):
        self.port = port
        self.running = False
        self._sock = None

    def start(self):
        if self.running:
            return
        self.running = True
        self._sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._sock.bind(("localhost", self.port))
        self._sock.listen(5)
        threading.Thread(target=self._loop, daemon=True).start()
        print(f"[K-Parametric] Server gestartet Port {self.port}")

    def stop(self):
        self.running = False
        if self._sock:
            try:
                self._sock.close()
            except Exception:
                pass

    def _loop(self):
        while self.running:
            try:
                self._sock.settimeout(1.0)
                conn, _ = self._sock.accept()
                threading.Thread(target=self._handle, args=(conn,), daemon=True).start()
            except socket.timeout:
                continue
            except Exception:
                if self.running:
                    traceback.print_exc()

    def _handle(self, conn):
        try:
            data = b""
            while True:
                chunk = conn.recv(4096)
                if not chunk:
                    break
                data += chunk
                if b"\n" in data:
                    break
            if not data.strip():
                return
            cmd    = json.loads(data.decode().strip())
            cmd_id = str(time.monotonic())
            _command_queue.put((cmd_id, cmd))
            deadline = time.monotonic() + 10.0
            while time.monotonic() < deadline:
                if cmd_id in _result_store:
                    result = _result_store.pop(cmd_id)
                    conn.sendall((json.dumps(result) + "\n").encode())
                    return
                time.sleep(0.05)
            conn.sendall(json.dumps({"error": "timeout"}).encode())
        except Exception as e:
            try:
                conn.sendall(json.dumps({"error": str(e)}).encode())
            except Exception:
                pass
        finally:
            conn.close()


# ── Blender Panel ─────────────────────────────────────────────────────────────

class K_PT_ParametricPanel(bpy.types.Panel):
    bl_label       = "K-Parametric"
    bl_idname      = "K_PT_parametric"
    bl_space_type  = "VIEW_3D"
    bl_region_type = "UI"
    bl_category    = "K-Creative"

    def draw(self, context):
        layout = self.layout
        srv = _server

        if srv and srv.running:
            layout.label(text=f"✅ Port {PORT} aktiv", icon="KEYINGSET")
            layout.operator("k.stop_parametric", text="Stop", icon="CANCEL")
        else:
            layout.label(text="⬜ Gestoppt", icon="KEYINGSET")
            layout.operator("k.start_parametric", text="Start", icon="PLAY")

        layout.separator()
        layout.label(text="Mechanical:")
        mech = list(_mechanical.ACTIONS) if _mechanical else ["(nicht geladen)"]
        for a in sorted(mech):
            layout.label(text=f"  {a}", icon="DOT")

        layout.separator()
        layout.label(text="Textile:")
        text = list(_textile.ACTIONS) if _textile else ["(nicht geladen)"]
        for a in sorted(text):
            layout.label(text=f"  {a}", icon="DOT")


class K_OT_StartParametric(bpy.types.Operator):
    bl_idname = "k.start_parametric"
    bl_label  = "K-Parametric starten"
    def execute(self, context):
        global _server
        if _server is None:
            _server = KParametricServer(PORT)
        _server.start()
        if not bpy.app.timers.is_registered(_dispatch_commands):
            bpy.app.timers.register(_dispatch_commands, persistent=True)
        return {"FINISHED"}


class K_OT_StopParametric(bpy.types.Operator):
    bl_idname = "k.stop_parametric"
    bl_label  = "K-Parametric stoppen"
    def execute(self, context):
        global _server
        if _server:
            _server.stop()
        if bpy.app.timers.is_registered(_dispatch_commands):
            bpy.app.timers.unregister(_dispatch_commands)
        return {"FINISHED"}


_classes = [K_PT_ParametricPanel, K_OT_StartParametric, K_OT_StopParametric]


def register():
    global _server
    _load_modules()
    for cls in _classes:
        bpy.utils.register_class(cls)
    _server = KParametricServer(PORT)
    _server.start()
    if not bpy.app.timers.is_registered(_dispatch_commands):
        bpy.app.timers.register(_dispatch_commands, persistent=True)
    loaded = []
    if _mechanical: loaded.append("mechanical")
    if _textile:    loaded.append("textile")
    print(f"[K-Parametric] Addon geladen — Module: {', '.join(loaded)} — Port {PORT}")


def unregister():
    global _server
    for cls in reversed(_classes):
        try:
            bpy.utils.unregister_class(cls)
        except Exception:
            pass
    if _server:
        _server.stop()
    if bpy.app.timers.is_registered(_dispatch_commands):
        bpy.app.timers.unregister(_dispatch_commands)
