"""
Sidechain Ducking Plugin
Deck A Kick (pad_a1) → ducks Deck B volume via SC /k/deck/b/volume OSC.
Knob 3 (deck_c_filter alias) controls compression threshold (0.0–1.0).
Knob 4 controls release time (10–500 ms).

MIDI_CONTROLS used:
  pad_a1          — Kick trigger from Deck A pad 1
  knob_3          — Sidechain threshold (maps to deck_c_filter CC)
  knob_4          — Release time (maps to deck_d_filter CC)

Usage: Drop this file into live_engine/plugins/ → auto-loaded immediately.
"""

MIDI_CONTROLS = ["pad_a1", "knob_3", "knob_4"]

# Internal state
_threshold  = 0.5   # volume below which ducking holds (set by knob_3)
_release_ms = 100   # release time in ms (set by knob_4)
_duck_level = 1.0   # current volume of Deck B (1.0 = full)
_ducking    = False


def on_load(osc):
    print("[sidechain] Loaded — pad_a1 → ducks Deck B | knob_3=threshold | knob_4=release")


def process(ctrl: str, value: float, osc):
    global _threshold, _release_ms, _duck_level, _ducking

    if ctrl == "knob_3":
        _threshold = value  # 0.0–1.0
        print(f"[sidechain] threshold → {_threshold:.2f}")

    elif ctrl == "knob_4":
        _release_ms = int(10 + value * 490)  # 10–500 ms
        print(f"[sidechain] release → {_release_ms} ms")

    elif ctrl == "pad_a1" and value > 0:
        # Kick hit → duck Deck B to threshold level
        _duck_level = 1.0 - _threshold
        _ducking = True
        if osc:
            try:
                osc.send_message("/k/deck/b/volume", float(_duck_level))
            except Exception as e:
                print(f"[sidechain] OSC error: {e}")
        print(f"[sidechain] DUCK B → {_duck_level:.2f}")

        # Schedule release after _release_ms (non-blocking via SC envelope)
        if osc:
            try:
                release_sec = _release_ms / 1000.0
                sc_code = (
                    f"~scDuck = Task({{"
                    f"  {release_sec}.wait;"
                    f"  ~deckBVol = XLine.kr(~deckBVol, 1.0, {release_sec});"
                    f"}}).play;"
                )
                osc.send_message("/cmd", sc_code)
            except Exception:
                pass
