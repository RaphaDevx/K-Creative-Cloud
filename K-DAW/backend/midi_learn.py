"""
MIDI-Learn Engine — K-DAW
Abstraction layer between hardware MIDI controllers and internal DJ events.

Architecture:
    Hardware MIDI → [midi_key string] → MidiMapper.translate() → internal event name
    Internal events like "crossfader", "deckA_play" are what the DJ engine reacts to.

EXTEND sections are marked explicitly throughout this file.
"""

import json
from pathlib import Path
from datetime import datetime

# ─── Internal Event Catalog ───────────────────────────────────────────────────
# EXTEND: Add new events here. Group by functional section.
# The group name is display-only. Event IDs must be unique across all groups.
INTERNAL_EVENTS: dict[str, list[str]] = {
    "transport": [
        "master_play",        # Toggle play/pause (main output)
        "master_stop",        # Hard stop
        "master_bpm_tap",     # Tap tempo
    ],
    "deck_a": [
        "deckA_play",         # Toggle play/pause
        "deckA_cue",          # Set / jump to cue point
        "deckA_sync",         # Sync to master BPM
        "deckA_pad1",         # Hot cue 1
        "deckA_pad2",
        "deckA_pad3",
        "deckA_pad4",
        "deckA_pitch",        # CC — pitch / tempo offset fader
        "deckA_volume",       # CC — channel fader (0–127)
        "deckA_filter",       # CC — filter sweep knob
    ],
    "deck_b": [
        "deckB_play",
        "deckB_cue",
        "deckB_sync",
        "deckB_pad1",
        "deckB_pad2",
        "deckB_pad3",
        "deckB_pad4",
        "deckB_pitch",
        "deckB_volume",
        "deckB_filter",
    ],
    "mixer": [
        "crossfader",         # CC — crossfader (0 = full A, 127 = full B)
        "master_volume",      # CC — master output level
        "master_eq_high",     # CC — master EQ high band
        "master_eq_mid",      # CC — master EQ mid band
        "master_eq_low",      # CC — master EQ low band
    ],
    "effects": [
        "fx1_on",             # Toggle effect 1
        "fx1_depth",          # CC — effect 1 wet/dry
        "fx2_on",
        "fx2_depth",
        "loop_in",            # Set loop start point
        "loop_out",           # Set loop end point
        "loop_active",        # Toggle loop on/off
    ],
}

# Flat ordered list — used by the learn wizard to step through events.
ALL_EVENTS: list[str] = [e for section in INTERNAL_EVENTS.values() for e in section]

MAPPINGS_DIR = Path(__file__).parent.parent / "config" / "mappings"


# ─── MIDI Key Format ──────────────────────────────────────────────────────────
# Every incoming MIDI message is encoded as a single string key:
#   "note:{channel}:{pitch}"  — NoteOn  (e.g. "note:0:60")
#   "cc:{channel}:{cc_num}"   — CC      (e.g. "cc:1:74")
# These keys are the dict keys in the saved JSON mapping file.

def make_midi_key(msg_type: str, channel: int, value: int) -> str:
    return f"{msg_type}:{channel}:{value}"

def parse_midi_key(key: str) -> dict:
    t, ch, v = key.split(":")
    return {"type": t, "channel": int(ch), "value": int(v)}


# ─── File I/O ─────────────────────────────────────────────────────────────────

def list_mappings() -> list[str]:
    if not MAPPINGS_DIR.exists():
        return []
    return sorted(f.name for f in MAPPINGS_DIR.glob("*.json"))


def load_mapping(filename: str) -> dict:
    path = MAPPINGS_DIR / filename
    if not path.exists():
        return {}
    with open(path) as f:
        return json.load(f)


def save_mapping(filename: str, data: dict) -> str:
    MAPPINGS_DIR.mkdir(parents=True, exist_ok=True)
    if not filename.endswith(".json"):
        filename += ".json"
    path = MAPPINGS_DIR / filename
    with open(path, "w") as f:
        json.dump(data, f, indent=2)
    return str(path)


def delete_mapping(filename: str) -> bool:
    path = MAPPINGS_DIR / filename
    if path.exists():
        path.unlink()
        return True
    return False


# ─── MidiMapper — live routing ────────────────────────────────────────────────

class MidiMapper:
    """
    Translates raw MIDI messages → internal event strings using a loaded JSON mapping.

    Usage:
        mapper = MidiMapper()
        mapper.load("config_ddj200.json")
        event = mapper.translate("cc", channel=0, value=1)  # → "crossfader"

    EXTEND: Register handler callables in self.handlers before calling dispatch().
        mapper.handlers["crossfader"] = lambda val: engine.set_crossfader(val / 127)
        mapper.handlers["deckA_play"] = lambda _: deck_a.toggle_play()
    Handler signature: callable(data: int)
        data = velocity for NoteOn events, CC value (0–127) for CC events.
    """

    def __init__(self):
        self.mapping: dict[str, str] = {}   # midi_key → event_name
        self.meta: dict = {}
        # EXTEND: Add your DJ engine callbacks here.
        self.handlers: dict[str, callable] = {}

    def load(self, filename: str) -> bool:
        data = load_mapping(filename)
        if not data:
            return False
        self.meta = {k: v for k, v in data.items() if k != "mappings"}
        self.mapping = data.get("mappings", {})
        return True

    def translate(self, msg_type: str, channel: int, value: int) -> str | None:
        return self.mapping.get(make_midi_key(msg_type, channel, value))

    def dispatch(self, msg_type: str, channel: int, value: int, data: int = 0) -> bool:
        """
        Translate + invoke registered handler.
        Returns True if a matching handler was found and called.
        """
        event = self.translate(msg_type, channel, value)
        if event and event in self.handlers:
            self.handlers[event](data)
            return True
        return False

    def reverse_lookup(self) -> dict[str, str]:
        """Return event_name → midi_key (for display in UI)."""
        return {v: k for k, v in self.mapping.items()}


# ─── MidiLearnSession — interactive wizard state machine ──────────────────────

class MidiLearnSession:
    """
    Steps through events one by one, binding each to the next incoming MIDI msg.
    Designed for WebSocket or REST usage — every method returns JSON-safe dicts.

    Usage:
        session = MidiLearnSession()
        session.current_prompt()          # → "Move or press control for: crossfader"
        session.register("cc", 0, 1)     # bind CC ch0 #1 to current event
        session.skip()                    # leave current event unbound
        path = session.export("My Controller", "config_my_ctrl.json")

    EXTEND: Pass a custom events list to learn only a subset of controls.
        MidiLearnSession(events=["crossfader", "deckA_play", "deckB_play"])
    """

    def __init__(self, events: list[str] | None = None):
        self.events = events or ALL_EVENTS
        self.index = 0
        self.bindings: dict[str, str] = {}    # midi_key → event_name

    @property
    def current(self) -> str | None:
        return self.events[self.index] if self.index < len(self.events) else None

    @property
    def done(self) -> bool:
        return self.index >= len(self.events)

    def current_prompt(self) -> str | None:
        return f"Move or press control for: {self.current}" if self.current else None

    def register(self, msg_type: str, channel: int, value: int) -> dict:
        if self.done:
            return {"error": "Session already complete"}
        key = make_midi_key(msg_type, channel, value)
        bound = self.current
        self.bindings[key] = bound
        self.index += 1
        return self._result(bound=bound, key=key)

    def skip(self) -> dict:
        """Advance without binding — leaves current event unmapped."""
        self.index += 1
        return self._result()

    def _result(self, bound: str | None = None, key: str | None = None) -> dict:
        return {
            "bound": bound,
            "midi_key": key,
            "next_event": self.current,
            "prompt": self.current_prompt(),
            "progress": {"current": self.index, "total": len(self.events)},
            "done": self.done,
        }

    def export(self, controller_name: str, filename: str) -> str:
        data = {
            "controller_name": controller_name,
            "created": datetime.now().isoformat(),
            "version": "1.0",
            "mappings": self.bindings,
        }
        return save_mapping(filename, data)
