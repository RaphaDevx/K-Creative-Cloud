#!/usr/bin/env python3
"""
K-Creative DJ Engine — Track Library, MIDI Monitor, Delta Sync
Commands:
  scan          Index audio files into SQLite (BPM, key, metadata)
  midi-monitor  Stream Numark Mixtrack Quad events as JSON lines (for WebSocket bridge)
  delta-sync    rsync music library from remote host to local offline cache
"""
import argparse
import hashlib
import json
import os
import sqlite3
import subprocess
import sys
import time
from pathlib import Path

AUDIO_EXTS = {".mp3", ".flac", ".wav", ".aiff", ".ogg", ".m4a", ".opus", ".aac"}

# ── Metadata extraction ────────────────────────────────────────────────────────

def get_metadata_ffprobe(path: str) -> dict:
    try:
        r = subprocess.run(
            ["ffprobe", "-v", "quiet", "-print_format", "json",
             "-show_streams", "-show_format", path],
            capture_output=True, text=True, timeout=10
        )
        if r.returncode != 0:
            return {}
        data = json.loads(r.stdout)
        fmt  = data.get("format", {})
        tags = fmt.get("tags", {}) or {}
        # Some files use uppercase tag keys
        def tag(*keys):
            for k in keys:
                v = tags.get(k) or tags.get(k.upper()) or tags.get(k.lower())
                if v:
                    return v
            return ""
        return {
            "title":    tag("title")    or Path(path).stem,
            "artist":   tag("artist"),
            "album":    tag("album"),
            "duration": float(fmt.get("duration", 0)),
        }
    except Exception:
        return {"title": Path(path).stem, "artist": "", "album": "", "duration": 0.0}


def estimate_bpm(path: str) -> float:
    """Beat-period analysis via aubio (fast C library). Falls back to 0."""
    try:
        r = subprocess.run(
            ["aubio", "beat", path],
            capture_output=True, text=True, timeout=45
        )
        if r.returncode == 0 and r.stdout.strip():
            times = [float(l) for l in r.stdout.strip().splitlines() if l.strip()]
            if len(times) >= 4:
                intervals = [times[i+1] - times[i] for i in range(len(times) - 1)]
                avg = sum(intervals) / len(intervals)
                return round(60.0 / avg, 1) if avg > 0 else 0.0
    except Exception:
        pass
    return 0.0


def detect_key(path: str) -> str:
    """Musical key detection via keyfinder-cli (optional). Returns '' if unavailable."""
    try:
        r = subprocess.run(
            ["keyfinder-cli", path],
            capture_output=True, text=True, timeout=30
        )
        if r.returncode == 0:
            return r.stdout.strip()
    except FileNotFoundError:
        pass
    except Exception:
        pass
    return ""


def track_id(path: str) -> str:
    return hashlib.sha256(path.encode()).hexdigest()[:16]


# ── SQLite schema ──────────────────────────────────────────────────────────────

def init_db(db_path: str):
    con = sqlite3.connect(db_path)
    con.execute("""
        CREATE TABLE IF NOT EXISTS tracks (
            id         TEXT PRIMARY KEY,
            path       TEXT UNIQUE NOT NULL,
            title      TEXT,
            artist     TEXT,
            album      TEXT,
            bpm        REAL DEFAULT 0,
            key        TEXT DEFAULT '',
            duration   REAL DEFAULT 0,
            size       INTEGER DEFAULT 0,
            modified   REAL DEFAULT 0,
            indexed_at REAL DEFAULT 0
        )
    """)
    con.commit()
    return con


# ── scan command ───────────────────────────────────────────────────────────────

def cmd_scan(args):
    scan_dir = Path(args.dir)
    if not scan_dir.exists():
        print(f"[ERROR] Directory not found: {scan_dir}", file=sys.stderr, flush=True)
        sys.exit(1)

    con = init_db(args.db)

    audio_files = sorted(
        f for f in scan_dir.rglob("*")
        if f.is_file() and f.suffix.lower() in AUDIO_EXTS
    )

    print(f"[SCAN] {len(audio_files)} files found in {scan_dir}", flush=True)

    new_count = skip_count = err_count = 0

    for idx, fpath in enumerate(audio_files, 1):
        tid  = track_id(str(fpath))
        try:
            stat = fpath.stat()
        except OSError:
            err_count += 1
            continue

        existing = con.execute(
            "SELECT modified FROM tracks WHERE id = ?", (tid,)
        ).fetchone()

        if existing and abs(existing[0] - stat.st_mtime) < 1.0:
            skip_count += 1
            continue

        print(f"  [{idx}/{len(audio_files)}] {fpath.name}", flush=True)

        meta = get_metadata_ffprobe(str(fpath))
        bpm  = estimate_bpm(str(fpath))
        key  = detect_key(str(fpath))

        try:
            con.execute("""
                INSERT OR REPLACE INTO tracks
                    (id, path, title, artist, album, bpm, key, duration, size, modified, indexed_at)
                VALUES (?,?,?,?,?,?,?,?,?,?,?)
            """, (
                tid, str(fpath),
                meta.get("title", fpath.stem),
                meta.get("artist", ""),
                meta.get("album", ""),
                bpm, key,
                meta.get("duration", 0.0),
                stat.st_size, stat.st_mtime,
                time.time()
            ))
            con.commit()
            new_count += 1
        except sqlite3.Error as e:
            print(f"  [DB ERROR] {fpath.name}: {e}", file=sys.stderr, flush=True)
            err_count += 1

    total = con.execute("SELECT COUNT(*) FROM tracks").fetchone()[0]
    con.close()

    print(
        f"[SCAN] Done — {new_count} indexed, {skip_count} skipped, "
        f"{err_count} errors, {total} total in DB",
        flush=True
    )


# ── midi-monitor command ───────────────────────────────────────────────────────

# Numark Mixtrack Quad MIDI control map (status_byte, cc_or_note → label)
_NUMARK_MAP = {
    # ── Deck A (ch 0) ──────────────────────────────
    (0xB0, 0x02): "deck_a_volume",
    (0xB0, 0x08): "deck_a_pitch",
    (0xB0, 0x16): "deck_a_eq_high",
    (0xB0, 0x17): "deck_a_eq_mid",
    (0xB0, 0x18): "deck_a_eq_low",
    (0xB0, 0x1A): "deck_a_filter",
    (0xB0, 0x1F): "crossfader",
    (0x90, 0x0B): "deck_a_play",
    (0x90, 0x0C): "deck_a_cue",
    (0x90, 0x06): "deck_a_sync",
    (0x90, 0x07): "deck_a_headphone",
    # Performance pads A
    (0x90, 0x60): "pad_a1",  (0x90, 0x61): "pad_a2",
    (0x90, 0x62): "pad_a3",  (0x90, 0x63): "pad_a4",
    (0x90, 0x64): "pad_a5",  (0x90, 0x65): "pad_a6",
    (0x90, 0x66): "pad_a7",  (0x90, 0x67): "pad_a8",
    # ── Deck B (ch 1) ──────────────────────────────
    (0xB1, 0x02): "deck_b_volume",
    (0xB1, 0x08): "deck_b_pitch",
    (0xB1, 0x16): "deck_b_eq_high",
    (0xB1, 0x17): "deck_b_eq_mid",
    (0xB1, 0x18): "deck_b_eq_low",
    (0xB1, 0x1A): "deck_b_filter",
    (0x91, 0x0B): "deck_b_play",
    (0x91, 0x0C): "deck_b_cue",
    (0x91, 0x06): "deck_b_sync",
    # Performance pads B
    (0x91, 0x60): "pad_b1",  (0x91, 0x61): "pad_b2",
    (0x91, 0x62): "pad_b3",  (0x91, 0x63): "pad_b4",
    (0x91, 0x64): "pad_b5",  (0x91, 0x65): "pad_b6",
    (0x91, 0x66): "pad_b7",  (0x91, 0x67): "pad_b8",
    # ── Deck C (ch 2) ──────────────────────────────
    (0xB2, 0x02): "deck_c_volume",
    (0xB2, 0x1A): "deck_c_filter",
    (0x92, 0x0B): "deck_c_play",
    (0x92, 0x0C): "deck_c_cue",
    # ── Deck D (ch 3) ──────────────────────────────
    (0xB3, 0x02): "deck_d_volume",
    (0xB3, 0x1A): "deck_d_filter",
    (0x93, 0x0B): "deck_d_play",
    (0x93, 0x0C): "deck_d_cue",
}

def _cc_label(status: int, cc: int) -> str:
    return _NUMARK_MAP.get((status, cc), f"cc_{status:02x}_{cc:02x}")


def cmd_midi_monitor(args):
    try:
        import rtmidi  # type: ignore
    except ImportError:
        print(json.dumps({"type": "error", "msg": "python-rtmidi not installed"}), flush=True)
        print(json.dumps({"type": "info", "msg": "Run: pip3 install python-rtmidi"}), flush=True)
        # Keep alive so WebSocket doesn't disconnect
        while True:
            time.sleep(10)
            print(json.dumps({"type": "ping", "ts": time.time()}), flush=True)
        return

    midi_in = rtmidi.MidiIn()
    ports = midi_in.get_ports()
    print(json.dumps({"type": "ports", "ports": ports}), flush=True)

    numark_idx = next(
        (i for i, p in enumerate(ports)
         if "numark" in p.lower() or "mixtrack" in p.lower()),
        None
    )

    if numark_idx is None:
        print(json.dumps({
            "type": "error",
            "msg":  f"Numark not found. Available: {ports}",
            "hint": "Check USB connection and run: aconnect -i"
        }), flush=True)
        while True:
            time.sleep(5)
            # Re-probe for hotplug reconnection
            midi_in2 = rtmidi.MidiIn()
            ports2 = midi_in2.get_ports()
            found = any("numark" in p.lower() or "mixtrack" in p.lower() for p in ports2)
            if found:
                print(json.dumps({"type": "reconnect"}), flush=True)
                break  # caller restarts the process
            print(json.dumps({"type": "ping", "ts": time.time()}), flush=True)
        return

    midi_in.open_port(numark_idx)
    print(json.dumps({
        "type":   "connected",
        "device": ports[numark_idx],
        "idx":    numark_idx
    }), flush=True)

    # Dual-purpose: each physical knob controls both Mixxx AND SuperCollider FX
    # The label encodes which SC OSC address to mirror (handled by sc_bridge)
    while True:
        msg = midi_in.get_message()
        if msg:
            data, delta = msg
            if len(data) >= 2:
                status = data[0]
                cc     = data[1]
                value  = data[2] if len(data) > 2 else 0
                label  = _cc_label(status, cc)
                # Normalized value 0.0–1.0 for CC messages
                norm = value / 127.0 if (status & 0xF0) == 0xB0 else (1 if value > 0 else 0)
                print(json.dumps({
                    "type":   "midi",
                    "ctrl":   label,
                    "value":  value,
                    "norm":   round(norm, 4),
                    "raw":    [status, cc, value],
                    "ts":     time.time()
                }), flush=True)
        else:
            time.sleep(0.001)


# ── delta-sync command ─────────────────────────────────────────────────────────

def cmd_delta_sync(args):
    """rsync from remote server to local SSD cache — survives offline gigs."""
    source = args.source   # e.g. user@nas.local:/music/
    dest   = args.dest     # e.g. /home/raphael/Music/

    Path(dest).mkdir(parents=True, exist_ok=True)
    print(f"[SYNC] {source} → {dest}", flush=True)

    cmd = [
        "rsync", "-av", "--progress", "--checksum",
        "--include=*/",
        "--include=*.mp3",  "--include=*.flac",
        "--include=*.wav",  "--include=*.aiff",
        "--include=*.ogg",  "--include=*.m4a",
        "--include=*.opus", "--include=*.aac",
        "--exclude=*",
        source, dest
    ]

    # Bandwidth limit: 50 MB/s to avoid starving audio threads
    if args.bwlimit:
        cmd.insert(1, f"--bwlimit={args.bwlimit}")

    try:
        proc = subprocess.run(cmd, timeout=7200)
        sys.exit(proc.returncode)
    except subprocess.TimeoutExpired:
        print("[ERROR] Sync timeout (2h)", file=sys.stderr, flush=True)
        sys.exit(1)
    except FileNotFoundError:
        print("[ERROR] rsync not found — run: sudo apt install rsync", file=sys.stderr, flush=True)
        sys.exit(2)


# ── CLI ────────────────────────────────────────────────────────────────────────

def main():
    p = argparse.ArgumentParser(
        description="K-Creative DJ Engine — Library, MIDI, Sync",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python dj_engine.py scan --dir ~/Music --db ~/K-Creative-Cloud/studio/dj_library.db
  python dj_engine.py midi-monitor
  python dj_engine.py delta-sync --source user@nas:/music/ --dest ~/Music/
        """
    )
    sub = p.add_subparsers(dest="cmd", required=True)

    # scan
    ps = sub.add_parser("scan", help="Index audio library")
    ps.add_argument("--dir", default=str(Path.home() / "Music"), help="Root music directory")
    ps.add_argument("--db",  required=True, help="Path to SQLite database")

    # midi-monitor
    pm = sub.add_parser("midi-monitor", help="Stream Numark MIDI events as JSON")
    pm.add_argument("--port", default="", help="Explicit MIDI port name (optional)")

    # delta-sync
    pd = sub.add_parser("delta-sync", help="rsync music from remote host")
    pd.add_argument("--source",  required=True, help="rsync source (user@host:/path/)")
    pd.add_argument("--dest",    required=True, help="Local destination directory")
    pd.add_argument("--bwlimit", default="",    help="Bandwidth limit e.g. '50000' (KB/s)")

    args = p.parse_args()

    if args.cmd == "scan":
        cmd_scan(args)
    elif args.cmd == "midi-monitor":
        cmd_midi_monitor(args)
    elif args.cmd == "delta-sync":
        cmd_delta_sync(args)


if __name__ == "__main__":
    main()
