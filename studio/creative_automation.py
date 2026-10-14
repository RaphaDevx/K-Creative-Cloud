"""Bounded adapters to local creative tools; no shell or user-supplied scripts."""
from __future__ import annotations
import json
import math
import os
from pathlib import Path
import re
import shutil
import subprocess
import uuid

TOOLS = {'lmms': ('lmms',), 'ardour': ('ardour', 'ardour8', 'ardour7'),
         'gimp': ('gimp',), 'blender': ('blender',), 'inkscape': ('inkscape',),
         'kdenlive': ('kdenlive',), 'ffmpeg': ('ffmpeg',), 'ffprobe': ('ffprobe',)}
GUI_TOOLS = frozenset({'lmms', 'ardour', 'gimp', 'blender', 'inkscape', 'kdenlive'})


def _executable(tool):
    if tool not in TOOLS:
        raise ValueError('Unknown creative tool')
    configured = os.environ.get(f'K_CREATIVE_{tool.upper()}')
    if configured:
        candidate = Path(configured).expanduser()
        if candidate.is_file() and os.access(candidate, os.X_OK):
            return str(candidate.resolve())
        return None
    return next((found for name in TOOLS[tool] if (found := shutil.which(name))), None)


def capabilities() -> dict:
    installed = {name: _executable(name) for name in TOOLS}
    return {'tools': {name: {'available': bool(path), 'executable': path} for name, path in installed.items()},
            'auto_cut': bool(installed['ffmpeg'] and installed['ffprobe']),
            'blender_render': bool(installed['blender'] and installed['ffmpeg']),
            'auto_cut_method': 'FFmpeg visual scene-change detection; no semantic or LLM editing decisions'}


def _required(tool):
    result = _executable(tool)
    if result is None:
        raise RuntimeError(f'{tool} is unavailable; install it or set K_CREATIVE_{tool.upper()} to its executable')
    return result


def _source(path):
    result = Path(path).expanduser().resolve(strict=True)
    if not result.is_file():
        raise ValueError('Source must be a file')
    return result


def _run(args, timeout=600):
    result = subprocess.run(args, capture_output=True, text=True, timeout=timeout)
    if result.returncode:
        raise RuntimeError(result.stderr[-3000:] or f'{Path(args[0]).name} failed')
    return result


def _number(value, low, high):
    if isinstance(value, bool):
        raise ValueError('Expected number')
    result = float(value)
    if not math.isfinite(result) or not low <= result <= high:
        raise ValueError(f'Number must be {low}..{high}')
    return result


def auto_cut(path, output_dir, threshold=.3) -> dict:
    """Detect visual changes and save a non-destructive source segment manifest."""
    threshold = _number(threshold, 0, 1)
    source = _source(path)
    ffmpeg, ffprobe = _required('ffmpeg'), _required('ffprobe')
    probe = json.loads(_run([ffprobe, '-v', 'error', '-show_format', '-show_streams', '-of', 'json', str(source)]).stdout)
    if not any(stream.get('codec_type') == 'video' for stream in probe.get('streams', [])):
        raise ValueError('Auto-cut requires a video stream')
    duration = _number(probe['format']['duration'], .001, 21600)
    detected = _run([ffmpeg, '-hide_banner', '-loglevel', 'info', '-i', str(source), '-an',
                     '-vf', f"setpts=PTS-STARTPTS,select='gt(scene,{threshold})',showinfo", '-f', 'null', '-'])
    boundaries = sorted(set(float(value) for value in re.findall(r'pts_time:([0-9.+eE-]+)', detected.stderr)))
    points = [0.] + [point for point in boundaries if 0 < point < duration] + [duration]
    segments = [{'source_start': start, 'duration': end-start} for start, end in zip(points, points[1:])]
    folder = Path(output_dir); folder.mkdir(parents=True, exist_ok=True)
    output = folder / f'{uuid.uuid4().hex}-cuts.json'
    result = {'source': str(source), 'duration': duration, 'threshold': threshold,
              'method': 'ffmpeg-scene-detection', 'segments': segments, 'path': str(output)}
    output.write_text(json.dumps(result, indent=2), encoding='utf-8')
    return result


def _codec_args():
    try:
        from .creative_media import _video_codec
    except ImportError:
        from creative_media import _video_codec
    return _video_codec()


def render_blender(path, output_dir, frame_start=None, frame_end=None, fps=30) -> dict:
    """Render a bounded CPU animation. Default range is frames 1..30."""
    source = _source(path)
    if source.suffix.lower() != '.blend':
        raise ValueError('Blender rendering requires a .blend file')
    start = _number(1 if frame_start is None else frame_start, 1, 100000)
    end = _number(30 if frame_end is None else frame_end, 1, 100000)
    if not start.is_integer() or not end.is_integer() or end < start or end-start >= 600:
        raise ValueError('Frame range must contain 1..600 integer frames')
    fps = _number(fps, 1, 120)
    blender, ffmpeg = _required('blender'), _required('ffmpeg')
    folder = Path(output_dir) / f'{uuid.uuid4().hex}-blender'
    folder.mkdir(parents=True)
    prefix = folder / 'frame_'
    # Fixed trusted expression; embedded .blend scripts are disabled before load.
    settings = 'import bpy; bpy.context.scene.cycles.device="CPU"; bpy.context.scene.cycles.samples=min(bpy.context.scene.cycles.samples,32); bpy.context.scene.cycles.use_denoising=False; bpy.context.scene.render.resolution_x=min(bpy.context.scene.render.resolution_x,4096); bpy.context.scene.render.resolution_y=min(bpy.context.scene.render.resolution_y,4096); bpy.context.scene.render.resolution_percentage=min(bpy.context.scene.render.resolution_percentage,100)'
    _run([blender, '--background', '--disable-autoexec', str(source), '--engine', 'CYCLES',
          '--python-expr', settings, '--render-output', str(prefix), '--render-format', 'PNG',
          '--use-extension', '1', '--frame-start', str(int(start)), '--frame-end', str(int(end)),
          '--render-anim'], timeout=1800)
    frames = sorted(folder.glob('frame_*.png'))
    expected = int(end-start+1)
    if len(frames) != expected:
        raise RuntimeError(f'Blender produced {len(frames)} of {expected} requested frames')
    output = folder / 'animation.mp4'
    _run([ffmpeg, '-v', 'error', '-framerate', str(fps), '-start_number', str(int(start)),
          '-i', str(folder / 'frame_%04d.png'), '-frames:v', str(expected),
          '-vf', 'pad=ceil(iw/2)*2:ceil(ih/2)*2', *_codec_args(), '-pix_fmt', 'yuv420p',
          '-movflags', '+faststart', str(output)])
    return {'path': str(output), 'source': str(source), 'frame_start': int(start),
            'frame_end': int(end), 'fps': fps, 'duration': expected/fps,
            'frames_dir': str(folder), 'engine': 'cycles-cpu'}


def launch_editor(tool, path=None) -> dict:
    if tool not in GUI_TOOLS:
        raise ValueError('Only known GUI creative editors may be launched')
    executable = _required(tool)
    args = [executable]
    if path is not None:
        args.append(str(_source(path)))
    process = subprocess.Popen(args, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                               stderr=subprocess.DEVNULL, start_new_session=True)
    return {'tool': tool, 'pid': process.pid, 'status': 'launch_requested', 'path': str(_source(path)) if path else None}
