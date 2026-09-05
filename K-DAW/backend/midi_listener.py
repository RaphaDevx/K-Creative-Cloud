"""
MIDI Hardware Listener — K-DAW (server-side, optional)
Opens a physical MIDI input port and dispatches messages through MidiMapper.

Requires:  pip install python-rtmidi
This module is OPTIONAL — the browser-side Web MIDI API handles hardware
input for the interactive learn wizard. Use this module for headless /
server-side routing (e.g. running the DJ engine without a browser).

EXTEND: Attach handlers to mapper.handlers before calling start().
    mapper.handlers["crossfader"] = lambda val: engine.set_crossfader(val / 127)
"""

import threading

try:
    import rtmidi
    _RTMIDI_AVAILABLE = True
except ImportError:
    _RTMIDI_AVAILABLE = False

from midi_learn import MidiMapper


class MidiListener:
    """
    Listens on a MIDI input port and routes messages through a MidiMapper.

    Quick start:
        mapper = MidiMapper()
        mapper.load("config_ddj200.json")
        # EXTEND: mapper.handlers["crossfader"] = lambda v: dj.crossfader(v / 127)

        listener = MidiListener(mapper)
        print(listener.list_ports())     # → ["DDJ-200", "APC mini", ...]
        listener.start(port_index=0)
        # ... later ...
        listener.stop()
    """

    def __init__(self, mapper: MidiMapper):
        if not _RTMIDI_AVAILABLE:
            raise RuntimeError(
                "python-rtmidi not installed.\n"
                "Run: pip install python-rtmidi"
            )
        self.mapper = mapper
        self._midi_in = rtmidi.MidiIn()
        self._running = False
        self._thread: threading.Thread | None = None
        self.last_message: dict | None = None
        # EXTEND: Set this callback to broadcast raw MIDI events to WebSocket clients.
        # Signature: callable(msg: dict) where msg has keys type, channel, value, data.
        self.on_message: callable | None = None

    def list_ports(self) -> list[str]:
        return self._midi_in.get_ports()

    def start(self, port_index: int = 0):
        ports = self.list_ports()
        if not ports:
            raise RuntimeError("No MIDI input ports found")
        self._midi_in.open_port(port_index)
        self._running = True
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()

    def stop(self):
        self._running = False
        try:
            self._midi_in.close_port()
        except Exception:
            pass

    def _loop(self):
        while self._running:
            msg = self._midi_in.get_message()
            if msg:
                raw, _ = msg
                self._handle(raw)

    def _handle(self, data: list[int]):
        if len(data) < 3:
            return
        status = data[0]
        channel = status & 0x0F
        note_or_cc = data[1]
        raw_data = data[2]

        if (status & 0xF0) == 0x90 and raw_data > 0:   # NoteOn (velocity > 0)
            msg_type = "note"
        elif (status & 0xF0) == 0xB0:                   # Control Change
            msg_type = "cc"
        else:
            return  # Ignore PitchBend, AfterTouch, etc.

        self.last_message = {
            "type": msg_type,
            "channel": channel,
            "value": note_or_cc,
            "data": raw_data,
        }

        self.mapper.dispatch(msg_type, channel, note_or_cc, raw_data)

        if self.on_message:
            self.on_message(self.last_message)
