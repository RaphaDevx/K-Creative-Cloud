"""
Video assembly via FFmpeg.
Each scene: PNG frame (looped) + WAV audio → scene clip → all clips concatenated → final MP4.
"""
import os
import subprocess
import tempfile
from pathlib import Path


def assemble_video(
    scene_data: list[dict],  # [{"frame": path, "audio": path, "duration": float}]
    output_path: str,
    fps: int = 30,
    transition_duration: float = 0.3,
) -> str:
    """
    Assembles per-scene frames + audio into a single MP4.
    Uses fade-to-black transitions between scenes.
    Returns output_path.
    """
    tmpdir = tempfile.mkdtemp(prefix="kcloud_video_")
    clip_paths = []

    for i, scene in enumerate(scene_data):
        clip_out = os.path.join(tmpdir, f"clip_{i:03d}.mp4")
        dur = scene["duration"]

        # Build scene clip: loop PNG for duration, attach audio
        cmd = [
            "ffmpeg", "-y",
            "-loop", "1", "-i", scene["frame"],
            "-i", scene["audio"],
            "-c:v", "libx264", "-tune", "stillimage",
            "-c:a", "aac", "-b:a", "192k",
            "-pix_fmt", "yuv420p",
            "-t", str(dur + transition_duration),  # slightly longer for overlap
            "-vf", f"fade=t=in:st=0:d={transition_duration},fade=t=out:st={dur}:d={transition_duration}",
            "-af", f"afade=t=in:st=0:d=0.1,afade=t=out:st={max(0, dur-0.2)}:d=0.2",
            clip_out,
        ]
        subprocess.run(cmd, capture_output=True, check=True)
        clip_paths.append(clip_out)

    # Write concat list
    concat_list = os.path.join(tmpdir, "concat.txt")
    with open(concat_list, "w") as f:
        for p in clip_paths:
            f.write(f"file '{p}'\n")

    # Concatenate all clips
    cmd = [
        "ffmpeg", "-y",
        "-f", "concat", "-safe", "0",
        "-i", concat_list,
        "-c:v", "libx264", "-crf", "22", "-preset", "fast",
        "-c:a", "aac", "-b:a", "192k",
        "-movflags", "+faststart",
        output_path,
    ]
    subprocess.run(cmd, capture_output=True, check=True)
    return output_path


def get_audio_duration(wav_path: str) -> float:
    """Get duration of a WAV file via ffprobe."""
    result = subprocess.run(
        ["ffprobe", "-v", "quiet", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", wav_path],
        capture_output=True, text=True,
    )
    try:
        return float(result.stdout.strip())
    except ValueError:
        return 5.0  # fallback
