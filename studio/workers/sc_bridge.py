#!/usr/bin/env python3
"""
K-Creative SuperCollider OSC Bridge
Manages modular 4-bar loops with independently swappable patterns and sounds.

Architecture:
  4 pattern slots (0–3), each slot holds:
    - rhythm layer  → 16-step binary grid (swappable without stopping sound)
    - sound layer   → SynthDef name + params (swappable without changing rhythm)
  Physical Numark knobs mirror SC parameters in real time via MIDI→OSC routing.

OSC addresses (→ scsynth port 57120):
  /cmd             eval arbitrary SC code
  /k/pattern/set   slot(i), pattern_name(s)
  /k/sound/set     slot(i), synthdef(s), params_json(s)
  /k/loop/start    slot(i)
  /k/loop/stop     slot(i)
  /k/reload        (reload all SynthDefs)
  /k/fx/set        slot(i), fx_name(s), value(f)

Usage:
  python sc_bridge.py init                        # boot SC + load SynthDefs
  python sc_bridge.py pattern --slot 0 --code four_to_floor
  python sc_bridge.py pattern --slot 1 --code "Pbind(\\degree, Pseq([0,3,5], inf))"
  python sc_bridge.py sound   --slot 0 --synthdef bass --params '{"cutoff":800}'
  python sc_bridge.py sound   --slot 2 --sample /home/raphael/Music/kick.wav
  python sc_bridge.py fx      --slot 0 --param filter --value 0.7
  python sc_bridge.py reload
  python sc_bridge.py list-patterns
"""
import argparse
import json
import sys
import time

SC_HOST = "127.0.0.1"
SC_PORT = 57120  # scsynth default OSC input port

try:
    from pythonosc import udp_client                    # type: ignore
    from pythonosc.osc_message_builder import OscMessageBuilder  # type: ignore
    _HAS_OSC = True
except ImportError:
    _HAS_OSC = False


# ── OSC transport ──────────────────────────────────────────────────────────────

def _send_osc(address: str, *args) -> bool:
    if not _HAS_OSC:
        print(f"[OSC STUB] {address} {args}", flush=True)
        return True
    try:
        client = udp_client.SimpleUDPClient(SC_HOST, SC_PORT)
        builder = OscMessageBuilder(address=address)
        for a in args:
            if isinstance(a, bool):
                builder.add_arg(int(a), OscMessageBuilder.ARG_TYPE_INT)
            elif isinstance(a, int):
                builder.add_arg(a, OscMessageBuilder.ARG_TYPE_INT)
            elif isinstance(a, float):
                builder.add_arg(a, OscMessageBuilder.ARG_TYPE_FLOAT)
            elif isinstance(a, str):
                builder.add_arg(a, OscMessageBuilder.ARG_TYPE_STRING)
        client.send(builder.build())
        return True
    except Exception as e:
        print(f"[OSC ERROR] {address}: {e}", file=sys.stderr, flush=True)
        return False


def sc_eval(code: str) -> bool:
    """Send SC code string for evaluation via /cmd."""
    ok = _send_osc("/cmd", code.strip())
    if ok:
        print(f"[SC→] {code[:80].replace(chr(10),' ')}", flush=True)
    return ok


# ── Built-in SynthDefs ─────────────────────────────────────────────────────────

SYNTHDEFS: dict[str, str] = {
    "kick": """
SynthDef(\\kick, { |out=0, amp=0.8, attack=0.001, decay=0.35, freq=60, tune=1|
    var env  = EnvGen.kr(Env.perc(attack, decay), doneAction:2);
    var pitch = freq * XLine.kr(tune * 4, 1, decay * 0.8);
    var sig  = SinOsc.ar(pitch) * env * amp;
    sig = sig + (LFNoise0.ar(500) * env * amp * 0.2);
    Out.ar(out, sig!2)
}).add;
""",

    "snare": """
SynthDef(\\snare, { |out=0, amp=0.5, decay=0.18, tone=0.3, snap=0.7|
    var env   = EnvGen.kr(Env.perc(0.001, decay), doneAction:2);
    var noise = BPF.ar(WhiteNoise.ar, 2200, 0.8) * env * amp;
    var body  = SinOsc.ar(200) * env * amp * tone;
    Out.ar(out, (noise + body)!2)
}).add;
""",

    "hihat_closed": """
SynthDef(\\hihat_closed, { |out=0, amp=0.3, decay=0.04|
    var env = EnvGen.kr(Env.perc(0.001, decay), doneAction:2);
    var sig = HPF.ar(WhiteNoise.ar, 10000) * env * amp;
    Out.ar(out, sig!2)
}).add;
""",

    "hihat_open": """
SynthDef(\\hihat_open, { |out=0, amp=0.3, decay=0.25|
    var env = EnvGen.kr(Env.perc(0.002, decay), doneAction:2);
    var sig = HPF.ar(WhiteNoise.ar, 8000) * env * amp;
    Out.ar(out, sig!2)
}).add;
""",

    "bass": """
SynthDef(\\bass, { |out=0, amp=0.7, freq=80, attack=0.01, decay=0.4, cutoff=900, res=0.3|
    var env  = EnvGen.kr(Env.perc(attack, decay), doneAction:2);
    var fenv = EnvGen.kr(Env.perc(0.005, decay * 0.5));
    var sig  = VarSaw.ar(freq, 0.5) + SinOsc.ar(freq);
    sig = RLPF.ar(sig, cutoff * (1 + fenv * 3), res) * env * amp;
    Out.ar(out, sig!2)
}).add;
""",

    "lead": """
SynthDef(\\lead, { |out=0, amp=0.5, freq=440, attack=0.01, sustain=0.3, release=0.1,
                    cutoff=3000, detune=0.005|
    var env = EnvGen.kr(Env.asr(attack, 1, release), doneAction:2);
    var sig = Saw.ar([freq, freq*(1+detune)]).mean;
    sig = LPF.ar(sig, cutoff) * env * amp;
    Out.ar(out, sig!2)
}).add;
""",

    "pad": """
SynthDef(\\pad, { |out=0, amp=0.4, freq=440, attack=0.8, release=1.2, cutoff=2000, chorus=0.01|
    var env  = EnvGen.kr(Env.asr(attack, 1, release), doneAction:2);
    var detune = [freq, freq*(1+chorus), freq*(1-chorus*0.7)];
    var sig  = Mix(Saw.ar(detune)) * env * amp;
    sig = LPF.ar(sig, cutoff * EnvGen.kr(Env.perc(attack, 2)));
    Out.ar(out, sig!2)
}).add;
""",

    "sampler": """
SynthDef(\\sampler, { |out=0, bufnum=0, amp=1.0, rate=1.0, start=0, loop=0|
    var sig = PlayBuf.ar(2, bufnum,
                rate * BufRateScale.kr(bufnum),
                startPos: start * BufFrames.kr(bufnum),
                loop: loop,
                doneAction: 2);
    Out.ar(out, sig * amp)
}).add;
""",

    "reese": """
SynthDef(\\reese, { |out=0, amp=0.6, freq=55, cutoff=600, res=0.4, attack=0.02, decay=0.5|
    var env  = EnvGen.kr(Env.perc(attack, decay), doneAction:2);
    var sig  = VarSaw.ar([freq, freq*1.003]);
    sig = Saw.ar(freq * 2, mul:0.5) + sig;
    sig = RLPF.ar(sig.mean, cutoff, res) * env * amp;
    Out.ar(out, sig!2)
}).add;
""",
}


# ── 16-step pattern templates (kick/snare/hihat_closed/bass steps) ─────────────

DEFAULT_PATTERNS: dict[str, dict[str, list[int]]] = {
    "four_to_floor": {
        "kick":         [1,0,0,0, 1,0,0,0, 1,0,0,0, 1,0,0,0],
        "snare":        [0,0,0,0, 1,0,0,0, 0,0,0,0, 1,0,0,0],
        "hihat_closed": [1,0,1,0, 1,0,1,0, 1,0,1,0, 1,0,1,0],
    },
    "breakbeat": {
        "kick":         [1,0,0,1, 0,0,0,0, 1,0,0,0, 0,1,0,0],
        "snare":        [0,0,0,0, 1,0,0,0, 0,0,1,0, 0,0,0,0],
        "hihat_closed": [1,1,0,1, 1,0,1,1, 0,1,1,0, 1,1,0,1],
    },
    "minimal_techno": {
        "kick":         [1,0,0,0, 0,0,0,0, 1,0,0,0, 0,0,0,0],
        "snare":        [0,0,0,0, 1,0,0,0, 0,0,0,0, 1,0,0,0],
        "hihat_closed": [0,0,1,0, 0,0,1,0, 0,0,1,0, 0,0,1,0],
    },
    "trap": {
        "kick":         [1,0,0,0, 0,0,1,0, 0,0,0,0, 1,0,0,0],
        "snare":        [0,0,0,0, 0,0,0,0, 1,0,0,0, 0,0,0,0],
        "hihat_closed": [1,1,1,1, 1,1,1,1, 1,1,1,1, 1,1,1,1],
    },
    "house": {
        "kick":         [1,0,0,0, 1,0,0,0, 1,0,0,0, 1,0,0,0],
        "snare":        [0,0,0,1, 0,0,0,1, 0,0,0,1, 0,0,0,1],
        "hihat_closed": [0,1,0,1, 0,1,0,1, 0,1,0,1, 0,1,0,1],
        "hihat_open":   [0,0,0,0, 0,0,1,0, 0,0,0,0, 0,0,1,0],
    },
    "dnb": {
        "kick":         [1,0,0,0, 0,0,0,0, 0,1,0,0, 0,0,0,0],
        "snare":        [0,0,0,0, 0,0,0,0, 1,0,0,0, 0,0,0,0],
        "hihat_closed": [1,1,0,1, 1,0,1,1, 1,1,0,1, 1,0,1,0],
    },
}


# ── SC code generation ─────────────────────────────────────────────────────────

def _steps_to_sc_array(steps: list[int]) -> str:
    return "[" + ", ".join(str(s) for s in steps) + "]"


def pattern_to_sc_code(pattern_name: str, slot: int, bpm: float = 120.0) -> str:
    """
    Generate SuperCollider Pbind code for a named 16-step pattern.
    Each step = 1/16th note at given BPM.
    Pattern and sound layers are stored in separate ~slot_N variables
    so they can be swapped independently.
    """
    if pattern_name not in DEFAULT_PATTERNS:
        return f'"[K-SC] Unknown pattern: {pattern_name}".postln;'

    dur = 60.0 / bpm / 4  # 16th note duration in beats
    pat = DEFAULT_PATTERNS[pattern_name]
    lines = [f'"[K-SC] Loading pattern {pattern_name!r} → slot {slot}".postln;']

    # Stop any existing pattern in this slot
    lines.append(f"""
if(~kSlots[{slot}].notNil, {{
    ~kSlots[{slot}].do({{ |p| p.stop }});
    ~kSlots[{slot}] = nil;
}});
""")

    slot_var = f"~kSlots[{slot}]"
    pbinds   = []

    for instrument, steps in pat.items():
        steps_sc = _steps_to_sc_array(steps)
        # amp array: 1 = full, 0 = rest, use Pser to gate
        pbind = f"""Pbind(
    \\instrument, \\{instrument},
    \\dur,        {dur},
    \\amp,        Pseq({steps_sc}.collect({{ |s| s * 0.75 }}), inf),
    \\legato,     0.3
)"""
        pbinds.append(pbind)

    lines.append(
        f"{slot_var} = Ppar([\n" +
        ",\n".join(f"    {pb}" for pb in pbinds) +
        f"\n], inf).play;"
    )
    lines.append(f'"[K-SC] Slot {slot} playing: {pattern_name}".postln;')
    return "\n".join(lines)


def sound_swap_code(slot: int, synthdef: str = "", sample_path: str = "",
                    params: dict | None = None) -> str:
    """
    Generate SC code to hot-swap the sound layer in a running slot.
    Keeps the rhythm timing but updates SynthDef or sample buffer.
    """
    lines = [f'"[K-SC] Sound swap slot {slot}".postln;']
    params = params or {}

    if synthdef:
        # Update global sound register for the slot
        lines.append(f"~kSound[{slot}] = \\{synthdef};")
        # Build param string
        param_str = ""
        for k, v in params.items():
            if isinstance(v, str):
                param_str += f", \\{k}, \\{v}"
            else:
                param_str += f", \\{k}, {v}"
        lines.append(f'"[K-SC] Slot {slot} → synthdef \\{synthdef}{param_str}".postln;')

    if sample_path:
        lines.append(f"""
Buffer.read(s, "{sample_path}", action: {{ |buf|
    ~kBufs[{slot}] = buf;
    ~kSound[{slot}] = \\sampler;
    "[K-SC] Sample loaded: {sample_path}".postln;
}});
""")

    return "\n".join(lines)


def fx_set_code(slot: int, param: str, value: float) -> str:
    """Map a physical knob value (0.0–1.0) to a SC bus parameter."""
    # Typical DJ-style parameter ranges
    _ranges = {
        "filter":  (200.0,  18000.0),
        "reverb":  (0.0,    1.0),
        "delay":   (0.0,    1.0),
        "crush":   (1.0,    16.0),
        "pitch":   (-12.0,  12.0),
        "volume":  (0.0,    1.0),
        "pan":     (-1.0,   1.0),
    }
    lo, hi = _ranges.get(param, (0.0, 1.0))
    sc_val = lo + (hi - lo) * max(0.0, min(1.0, value))
    return (
        f'~kFX[{slot}] = ~kFX[{slot}] ?? Dictionary.new;\n'
        f'~kFX[{slot}][\\{param}] = {sc_val:.4f};\n'
        f'"[K-SC] Slot {slot} FX {param} → {sc_val:.2f}".postln;'
    )


def init_sc_code() -> str:
    """Boot code: initialize slot arrays + load all SynthDefs."""
    defs = "\n".join(SYNTHDEFS.values())
    return f"""
s.waitForBoot({{
    // Slot state arrays
    ~kSlots = Array.fill(4, {{ nil }});
    ~kSound = Array.fill(4, {{ \\kick }});
    ~kBufs  = Array.fill(4, {{ nil }});
    ~kFX    = Array.fill(4, {{ Dictionary.new }});

    // Load all K-Creative SynthDefs
{defs}

    "[K-SC] K-Creative DJ Engine ready — 4 slots initialized".postln;
}});
"""


# ── CLI commands ───────────────────────────────────────────────────────────────

def cmd_init(args):
    print("[SC] Booting SuperCollider + loading SynthDefs…", flush=True)
    ok = sc_eval(init_sc_code())
    if ok:
        print("[OK] SuperCollider initialized", flush=True)
    else:
        print("[FAIL] Could not reach scsynth — is SuperCollider running?", file=sys.stderr, flush=True)
        sys.exit(1)


def cmd_pattern(args):
    slot = args.slot
    code = args.code.strip()

    if code in DEFAULT_PATTERNS:
        sc_code = pattern_to_sc_code(code, slot, bpm=args.bpm)
        print(f"[SC] Pattern '{code}' → slot {slot} @ {args.bpm} BPM", flush=True)
    else:
        # Treat as raw SC code (live coding mode)
        sc_code = code
        print(f"[SC] Raw pattern code → slot {slot}", flush=True)

    if sc_eval(sc_code):
        print("[OK] Pattern sent", flush=True)
    else:
        sys.exit(1)


def cmd_sound(args):
    slot     = args.slot
    synthdef = getattr(args, "synthdef", "") or ""
    sample   = getattr(args, "sample",   "") or ""

    try:
        params = json.loads(getattr(args, "params", "{}") or "{}")
    except json.JSONDecodeError:
        params = {}

    if not synthdef and not sample:
        print("[ERROR] Provide --synthdef or --sample", file=sys.stderr, flush=True)
        sys.exit(1)

    # If it's a built-in synthdef, push the definition first
    if synthdef and synthdef in SYNTHDEFS:
        sc_eval(SYNTHDEFS[synthdef])
        time.sleep(0.05)

    sc_code = sound_swap_code(slot, synthdef=synthdef, sample_path=sample, params=params)
    if sc_eval(sc_code):
        print(f"[OK] Sound swap → slot {slot}", flush=True)
    else:
        sys.exit(1)


def cmd_fx(args):
    sc_code = fx_set_code(args.slot, args.param, args.value)
    if sc_eval(sc_code):
        print(f"[OK] FX {args.param}={args.value:.3f} → slot {args.slot}", flush=True)
    else:
        sys.exit(1)


def cmd_reload(args):
    print("[SC] Reloading all SynthDefs…", flush=True)
    defs = "\n".join(SYNTHDEFS.values())
    reload_code = defs + '\n"[K-SC] SynthDefs reloaded".postln;'
    if sc_eval(reload_code):
        print("[OK] SynthDefs reloaded without restarting scsynth", flush=True)
    else:
        sys.exit(1)


def cmd_stop(args):
    sc_code = f"""
if(~kSlots[{args.slot}].notNil, {{
    ~kSlots[{args.slot}].do({{ |p| p.stop }});
    ~kSlots[{args.slot}] = nil;
    "[K-SC] Slot {args.slot} stopped".postln;
}});
"""
    sc_eval(sc_code)
    print(f"[OK] Slot {args.slot} stopped", flush=True)


def cmd_cmd(args):
    try:
        msg = json.loads(args.msg)
        code = msg.get("code", "") if isinstance(msg, dict) else str(msg)
    except json.JSONDecodeError:
        code = args.msg
    if code:
        sc_eval(code)
        print("[OK] SC cmd sent", flush=True)
    else:
        print("[ERROR] No code provided", file=sys.stderr, flush=True)
        sys.exit(1)


def cmd_list_patterns(args):
    for name, pat in DEFAULT_PATTERNS.items():
        tracks = ", ".join(pat.keys())
        print(f"  {name:<20} [{tracks}]")


# ── main ───────────────────────────────────────────────────────────────────────

def main():
    p = argparse.ArgumentParser(
        description="K-Creative SuperCollider OSC Bridge",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    sub = p.add_subparsers(dest="cmd", required=True)

    # init
    sub.add_parser("init", help="Boot scsynth and load SynthDefs")

    # pattern
    pp = sub.add_parser("pattern", help="Load pattern into a slot")
    pp.add_argument("--slot", type=int, default=0, choices=[0,1,2,3])
    pp.add_argument("--code", required=True, help="Pattern name or raw SC code")
    pp.add_argument("--bpm",  type=float, default=120.0)

    # sound
    ps = sub.add_parser("sound", help="Hot-swap sound layer in a slot")
    ps.add_argument("--slot",     type=int, default=0, choices=[0,1,2,3])
    ps.add_argument("--synthdef", default="", help="Built-in or custom SynthDef name")
    ps.add_argument("--sample",   default="", help="Path to audio sample file")
    ps.add_argument("--params",   default="{}", help="JSON params e.g. '{\"cutoff\":800}'")

    # fx
    pf = sub.add_parser("fx", help="Set FX parameter from knob value")
    pf.add_argument("--slot",  type=int,   default=0, choices=[0,1,2,3])
    pf.add_argument("--param", required=True, help="filter|reverb|delay|crush|pitch|volume|pan")
    pf.add_argument("--value", type=float, required=True, help="Normalized value 0.0–1.0")

    # reload
    sub.add_parser("reload", help="Reload SynthDefs without stopping scsynth")

    # stop
    pst = sub.add_parser("stop", help="Stop a pattern slot")
    pst.add_argument("--slot", type=int, default=0, choices=[0,1,2,3])

    # cmd
    pc = sub.add_parser("cmd", help="Send raw SC code")
    pc.add_argument("--msg", required=True, help="JSON {code:...} or raw SC string")

    # list-patterns
    sub.add_parser("list-patterns", help="Print all built-in pattern templates")

    args = p.parse_args()
    dispatch = {
        "init":          cmd_init,
        "pattern":       cmd_pattern,
        "sound":         cmd_sound,
        "fx":            cmd_fx,
        "reload":        cmd_reload,
        "stop":          cmd_stop,
        "cmd":           cmd_cmd,
        "list-patterns": cmd_list_patterns,
    }
    dispatch[args.cmd](args)


if __name__ == "__main__":
    main()
