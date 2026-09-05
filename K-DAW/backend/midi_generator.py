"""Music JSON → MIDI file using midiutil."""
import time
from pathlib import Path
from midiutil import MIDIFile

RENDERS_DIR = Path(__file__).parent.parent / "renders"
SOUNDFONT = "/usr/share/sounds/sf2/TimGM6mb.sf2"


def music_to_midi(music: dict, output_path: str = None) -> str:
    """Write music JSON to .mid file. Returns absolute path."""
    RENDERS_DIR.mkdir(parents=True, exist_ok=True)

    if output_path is None:
        ts = int(time.time())
        slug = "".join(c for c in music.get("title", "track") if c.isalnum() or c in "-_ ")
        slug = slug.replace(" ", "_")[:32]
        output_path = str(RENDERS_DIR / f"{slug}_{ts}.mid")

    tracks = music.get("tracks", [])
    bpm = music.get("bpm", 120)

    midi = MIDIFile(numTracks=max(len(tracks), 1))

    for i, track in enumerate(tracks):
        channel = track.get("channel", i % 16)
        program = track.get("program", 0)

        midi.addTrackName(i, 0, track.get("name", f"Track {i + 1}"))
        midi.addTempo(i, 0, bpm)
        if channel != 9:
            midi.addProgramChange(i, channel, 0, program)

        for note in track.get("notes", []):
            pitch = int(note["pitch"])
            velocity = max(1, min(127, int(note.get("velocity", 80))))
            start = float(note["start_beat"])
            duration = max(0.05, float(note["duration_beats"]))
            midi.addNote(i, channel, pitch, start, duration, velocity)

    with open(output_path, "wb") as f:
        midi.writeFile(f)

    return output_path


def midi_to_wav(midi_path: str) -> str | None:
    """Render MIDI → WAV via fluidsynth. Returns WAV path or None."""
    import shutil
    import subprocess

    if not shutil.which("fluidsynth"):
        return None
    if not Path(SOUNDFONT).exists():
        return None

    wav_path = midi_path.replace(".mid", ".wav")
    cmd = [
        "fluidsynth", "-ni",
        "-g", "1.0",
        "-F", wav_path,
        "-r", "44100",
        SOUNDFONT,
        midi_path,
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=90)
    if result.returncode == 0 and Path(wav_path).exists():
        return wav_path
    return None


def list_renders() -> list[dict]:
    """Return last 30 renders sorted by newest first."""
    RENDERS_DIR.mkdir(parents=True, exist_ok=True)
    files = []
    for f in RENDERS_DIR.iterdir():
        if f.suffix in {".wav", ".mid", ".ogg"}:
            files.append({
                "name": f.name,
                "size": f.stat().st_size,
                "mtime": f.stat().st_mtime,
                "type": f.suffix[1:],
            })
    return sorted(files, key=lambda x: x["mtime"], reverse=True)[:30]
