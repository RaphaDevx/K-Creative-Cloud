#!/usr/bin/env python3
"""
K-Creative Live Engine
Manages plugins, hot-reload, and OSC bridging.

Each plugin in live_engine/plugins/ is a Python module that:
  - Exports MIDI_CONTROLS: list of knob/pad names from midi_registry.json
  - Exports process(ctrl_name, value, osc_client): called on MIDI input
  - Exports on_load(osc_client): called when plugin loads/reloads

Commands:
  python engine.py watch          Watch plugins/ and hot-reload on change
  python engine.py list           List loaded plugins + their controls
  python engine.py reload         Force-reload all plugins
  python engine.py run <plugin>   Run a single plugin module
"""
import argparse
import importlib
import importlib.util
import json
import os
import sys
import time
import threading
from pathlib import Path

REPO = Path(__file__).parent.parent
PLUGIN_DIR = Path(__file__).parent / "plugins"
REGISTRY_PATH = Path(__file__).parent / "midi_registry.json"

SC_HOST = "127.0.0.1"
SC_PORT = 57120

try:
    from pythonosc import udp_client  # type: ignore
    _osc_client = udp_client.SimpleUDPClient(SC_HOST, SC_PORT)
    HAS_OSC = True
except ImportError:
    _osc_client = None
    HAS_OSC = False

# Loaded plugins: name → module
_plugins: dict[str, object] = {}
_registry: dict = {}


def load_registry() -> dict:
    if REGISTRY_PATH.exists():
        return json.loads(REGISTRY_PATH.read_text())
    return {}


def load_plugin(path: Path) -> bool:
    """Import or re-import a plugin module from path."""
    name = path.stem
    spec = importlib.util.spec_from_file_location(f"live_plugin_{name}", path)
    if spec is None:
        return False
    module = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(module)
        _plugins[name] = module
        if hasattr(module, "on_load"):
            module.on_load(_osc_client)
        controls = getattr(module, "MIDI_CONTROLS", [])
        print(f"[PLUGIN] Loaded '{name}' — controls: {controls}", flush=True)
        return True
    except Exception as e:
        print(f"[PLUGIN ERROR] {name}: {e}", flush=True)
        return False


def load_all_plugins():
    """Load all .py files in plugins/ (except __init__.py)."""
    PLUGIN_DIR.mkdir(parents=True, exist_ok=True)
    for f in sorted(PLUGIN_DIR.glob("*.py")):
        if f.name.startswith("_"):
            continue
        load_plugin(f)


def dispatch_midi(ctrl_name: str, value: float):
    """Route a MIDI control event to all plugins that handle it."""
    for name, module in list(_plugins.items()):
        controls = getattr(module, "MIDI_CONTROLS", [])
        if ctrl_name in controls or "*" in controls:
            try:
                module.process(ctrl_name, value, _osc_client)
            except Exception as e:
                print(f"[PLUGIN ERROR] {name}.process: {e}", flush=True)


def cmd_watch(args):
    """Watch plugin directory and hot-reload on file change."""
    try:
        from watchdog.observers import Observer  # type: ignore
        from watchdog.events import FileSystemEventHandler  # type: ignore
    except ImportError:
        print("[ENGINE] watchdog not installed — run: pip install watchdog", flush=True)
        print("[ENGINE] Falling back to polling...", flush=True)
        _poll_watch()
        return

    load_all_plugins()

    class _Handler(FileSystemEventHandler):
        def on_modified(self, event):
            if event.src_path.endswith(".py") and not os.path.basename(event.src_path).startswith("_"):
                p = Path(event.src_path)
                print(f"[HOT-RELOAD] {p.name} changed — reloading…", flush=True)
                time.sleep(0.05)  # debounce
                load_plugin(p)
                print(f"[HOT-RELOAD] {p.name} reloaded", flush=True)
        def on_created(self, event):
            self.on_modified(event)

    obs = Observer()
    obs.schedule(_Handler(), str(PLUGIN_DIR), recursive=False)
    obs.start()
    print(f"[ENGINE] Watching {PLUGIN_DIR} for changes (Ctrl+C to stop)", flush=True)

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        obs.stop()
    obs.join()


def _poll_watch():
    """Fallback: poll file mtimes every second."""
    load_all_plugins()
    mtimes: dict[str, float] = {}
    for f in PLUGIN_DIR.glob("*.py"):
        mtimes[str(f)] = f.stat().st_mtime

    print("[ENGINE] Polling plugin directory every 1s", flush=True)
    while True:
        time.sleep(1)
        for f in PLUGIN_DIR.glob("*.py"):
            if f.name.startswith("_"):
                continue
            mtime = f.stat().st_mtime
            if mtimes.get(str(f)) != mtime:
                mtimes[str(f)] = mtime
                print(f"[HOT-RELOAD] {f.name}", flush=True)
                load_plugin(f)


def cmd_list(args):
    load_all_plugins()
    print(f"\nLoaded plugins ({len(_plugins)}):")
    for name, module in _plugins.items():
        controls = getattr(module, "MIDI_CONTROLS", [])
        desc = getattr(module, "__doc__", "").split("\n")[0].strip() if module.__doc__ else ""
        print(f"  {name:<20} controls={controls}  {desc}")


def cmd_reload(args):
    load_all_plugins()
    print(f"[ENGINE] Reloaded {len(_plugins)} plugins", flush=True)


def cmd_run(args):
    p = PLUGIN_DIR / f"{args.plugin}.py"
    if not p.exists():
        print(f"[ERROR] Plugin not found: {p}", file=sys.stderr)
        sys.exit(1)
    if load_plugin(p):
        print(f"[OK] Plugin {args.plugin} loaded")
    else:
        sys.exit(1)


def main():
    p = argparse.ArgumentParser(description="K-Creative Live Engine")
    sub = p.add_subparsers(dest="cmd", required=True)

    sub.add_parser("watch",  help="Watch plugins/ and hot-reload")
    sub.add_parser("list",   help="List loaded plugins")
    sub.add_parser("reload", help="Reload all plugins")
    pr = sub.add_parser("run", help="Load a single plugin")
    pr.add_argument("plugin")

    args = p.parse_args()
    _registry.update(load_registry())

    dispatch = {
        "watch":  cmd_watch,
        "list":   cmd_list,
        "reload": cmd_reload,
        "run":    cmd_run,
    }
    dispatch[args.cmd](args)


if __name__ == "__main__":
    main()
