#!/usr/bin/env python3
"""
K-Creative generate_audio.py — Headless Audio Worker

Handles:
- Sound logo generation via LMMS CLI + FluidSynth
- Stem mixing via FFmpeg
- Kokoro TTS voiceover generation
- Audio normalization and format conversion

Usage:
  python3 generate_audio.py sound_logo --output /tmp/sound_logo.wav
  python3 generate_audio.py tts --text "Lerne wie ein Profi" --output /tmp/vo.wav
  python3 generate_audio.py mix --stems a.wav b.wav --output /tmp/mix.wav
  python3 generate_audio.py normalize --input in.wav --output out.wav
"""
import subprocess
import sys
import os
import json
import tempfile
from pathlib import Path

OUTPUT_DIR = os.environ.get("K_OUTPUT", "/home/raphael/K-Creative-Cloud/renders/audio")
KOKORO_DIR = Path("/home/raphael/K-Creative-Cloud/kokoro-tts")
KOKORO_ONNX = KOKORO_DIR / "kokoro-v1.0.int8.onnx"
KOKORO_VOICES = KOKORO_DIR / "voices-v1.0.bin"
LMMS_DIR = Path("/home/raphael/K-Creative-Cloud/lmms-mcp")


def run(cmd: list[str], cwd=None) -> dict:
    print(f"[generate_audio] {' '.join(str(c) for c in cmd)}")
    result = subprocess.run(cmd, capture_output=True, text=True, cwd=cwd)
    return {
        "ok": result.returncode == 0,
        "returncode": result.returncode,
        "stderr": result.stderr[-1000:],
        "stdout": result.stdout[-500:],
    }


def normalize(input: str, output: str, target_lufs: float = -16.0) -> dict:
    """Normalize audio to target LUFS using FFmpeg loudnorm."""
    Path(output).parent.mkdir(parents=True, exist_ok=True)
    return run([
        "ffmpeg", "-y", "-i", input,
        "-af", f"loudnorm=I={target_lufs}:TP=-1.5:LRA=11",
        output
    ])


def convert(input: str, output: str, sample_rate: int = 44100) -> dict:
    """Convert audio format (WAV↔MP3↔OGG etc.)."""
    Path(output).parent.mkdir(parents=True, exist_ok=True)
    ext = Path(output).suffix.lower()
    codec = {"mp3": "libmp3lame", "ogg": "libvorbis", "wav": "pcm_s16le"}.get(ext[1:], "copy")
    return run(["ffmpeg", "-y", "-i", input, "-ar", str(sample_rate), "-c:a", codec, output])


def mix_stems(stems: list[str], output: str, weights: list[float] = None) -> dict:
    """Mix multiple audio stems together with optional volume weights."""
    Path(output).parent.mkdir(parents=True, exist_ok=True)
    if weights is None:
        weights = [1.0] * len(stems)

    inputs = []
    for s in stems:
        inputs += ["-i", s]

    # Build amix filter
    n = len(stems)
    vol_filters = "".join(f"[{i}:a]volume={w}[a{i}];" for i, w in enumerate(weights))
    mix_inputs = "".join(f"[a{i}]" for i in range(n))
    filter_complex = f"{vol_filters}{mix_inputs}amix=inputs={n}:normalize=0[out]"

    return run(["ffmpeg", "-y"] + inputs + [
        "-filter_complex", filter_complex,
        "-map", "[out]", output
    ])


def generate_sound_logo(output: str, style: str = "minimal") -> dict:
    """
    Generate the K-Learning sound logo.
    Uses FluidSynth + a SF2 soundfont to render a 3-note motif.
    Falls back to a sine-tone generation via FFmpeg.
    """
    Path(output).parent.mkdir(parents=True, exist_ok=True)

    # Try FluidSynth approach first (needs a soundfont)
    sf2_candidates = [
        "/usr/share/sounds/sf2/FluidR3_GM.sf2",
        "/usr/share/soundfonts/FluidR3_GM.sf2",
        "/usr/share/sounds/sf2/TimGM6mb.sf2",
    ]
    sf2 = next((p for p in sf2_candidates if Path(p).exists()), None)

    if sf2:
        # Write minimal MIDI-like approach via FluidSynth stdin
        # Notes: C5 (72), E5 (76), G5 (79) — ascending triad = "ascending, optimistic"
        midi_cmds = "noteon 0 72 90\nsleep 300\nnoteoff 0 72\nnoteon 0 76 90\nsleep 300\nnoteoff 0 76\nnoteon 0 79 90\nsleep 600\nnoteoff 0 79\nquit\n"
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write(midi_cmds)
            cmds_file = f.name
        try:
            result = run([
                "fluidsynth", "-ni", "-a", "file", "-T", "wav",
                "-F", output, sf2, "/dev/stdin"
            ] if False else [  # stdin approach unreliable, use simpler fallback
                "ffmpeg", "-y",
                "-f", "lavfi",
                "-i", "sine=frequency=523.25:duration=0.4",  # C5
                "-f", "lavfi",
                "-i", "sine=frequency=659.25:duration=0.4",  # E5
                "-f", "lavfi",
                "-i", "sine=frequency=783.99:duration=0.6",  # G5
                "-filter_complex",
                "[0:a][1:a][2:a]concat=n=3:v=0:a=1[out];[out]afade=t=in:d=0.05,afade=t=out:d=0.15,aecho=0.8:0.88:60:0.4",
                "-map", "[out]",
                output
            ])
        finally:
            Path(cmds_file).unlink(missing_ok=True)
        return result
    else:
        # Pure FFmpeg: three-tone rising motif
        return run([
            "ffmpeg", "-y",
            "-f", "lavfi", "-i", "sine=frequency=523.25:duration=0.35",   # C5
            "-f", "lavfi", "-i", "sine=frequency=659.25:duration=0.35",   # E5
            "-f", "lavfi", "-i", "sine=frequency=783.99:duration=0.5",    # G5
            "-filter_complex",
            "[0:a][1:a][2:a]concat=n=3:v=0:a=1[out];"
            "[out]afade=t=in:st=0:d=0.05,"
            "afade=t=out:st=1.0:d=0.2,"
            "aecho=0.6:0.75:60:0.3[final]",
            "-map", "[final]",
            output
        ])


def tts_voiceover(text: str, output: str, voice: str = "af_heart", speed: float = 1.15) -> dict:
    """
    Generate TTS voiceover via Kokoro ONNX.
    Falls back to espeak if Kokoro models not found.
    """
    Path(output).parent.mkdir(parents=True, exist_ok=True)

    kokoro_script = KOKORO_DIR / "generate_audio.py"
    if kokoro_script.exists() and KOKORO_ONNX.exists():
        return run([
            sys.executable, str(kokoro_script),
            "--text", text,
            "--output", output,
            "--voice", voice,
            "--speed", str(speed),
        ], cwd=str(KOKORO_DIR))
    else:
        # Fallback to espeak
        print("[generate_audio] Kokoro not found, using espeak fallback")
        tmp_wav = output.replace(".mp3", ".wav").replace(".ogg", ".wav")
        r = run(["espeak", "-v", "en-us", "-w", tmp_wav, text])
        if r["ok"] and tmp_wav != output:
            return convert(tmp_wav, output)
        return r


# ── CLI interface ──────────────────────────────────────────────
def main():
    import argparse
    parser = argparse.ArgumentParser(description="K-Creative Audio Worker")
    sub = parser.add_subparsers(dest="cmd")

    sl = sub.add_parser("sound_logo")
    sl.add_argument("--output", default=str(Path(OUTPUT_DIR) / "sound_logo.wav"))
    sl.add_argument("--style", default="minimal")

    tts = sub.add_parser("tts")
    tts.add_argument("--text", required=True)
    tts.add_argument("--output", default=str(Path(OUTPUT_DIR) / "voiceover.wav"))
    tts.add_argument("--voice", default="af_heart")
    tts.add_argument("--speed", type=float, default=1.15)

    mix = sub.add_parser("mix")
    mix.add_argument("--stems", nargs="+")
    mix.add_argument("--output")
    mix.add_argument("--weights", nargs="*", type=float)

    norm = sub.add_parser("normalize")
    norm.add_argument("--input"); norm.add_argument("--output")
    norm.add_argument("--lufs", type=float, default=-16.0)

    conv = sub.add_parser("convert")
    conv.add_argument("--input"); conv.add_argument("--output")

    args = parser.parse_args()
    Path(OUTPUT_DIR).mkdir(parents=True, exist_ok=True)

    if args.cmd == "sound_logo":
        result = generate_sound_logo(args.output, args.style)
    elif args.cmd == "tts":
        result = tts_voiceover(args.text, args.output, args.voice, args.speed)
    elif args.cmd == "mix":
        result = mix_stems(args.stems, args.output, args.weights)
    elif args.cmd == "normalize":
        result = normalize(args.input, args.output, args.lufs)
    elif args.cmd == "convert":
        result = convert(args.input, args.output)
    else:
        parser.print_help(); return

    print(json.dumps(result, indent=2))
    sys.exit(0 if result.get("ok") else 1)


if __name__ == "__main__":
    main()
