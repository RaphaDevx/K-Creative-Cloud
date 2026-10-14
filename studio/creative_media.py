"""Real local render adapters for the canonical Creative project contract."""
from __future__ import annotations
import importlib.util
from functools import lru_cache
import math
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import uuid
import wave

import numpy as np
from PIL import ImageEnhance, Image, ImageColor, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
_MODEL_CANDIDATES = [ROOT / 'models', ROOT / 'kokoro-tts', Path(getattr(sys, '_MEIPASS', ROOT)) / 'models', Path(sys.executable).resolve().parent / 'resources/models']
MODEL_DIR = Path(os.environ['K_CREATIVE_MODELS']) if 'K_CREATIVE_MODELS' in os.environ else next((p for p in _MODEL_CANDIDATES if (p / 'kokoro-v1.0.int8.onnx').is_file()), ROOT / 'models')
MODEL = MODEL_DIR / 'kokoro-v1.0.int8.onnx'
VOICES = MODEL_DIR / 'voices-v1.0.bin'
RATE = 48000
MAX_DURATION = 600


def capabilities() -> dict:
    return {'photo': True, 'audio': True, 'video': bool(shutil.which('ffmpeg') and shutil.which('ffprobe')),
            'ffmpeg': shutil.which('ffmpeg'), 'tts': {
                'kokoro': MODEL.is_file() and VOICES.is_file() and importlib.util.find_spec('kokoro_onnx') is not None,
                'chatterbox': False}, 'tts_notes': 'Chatterbox is not configured; Kokoro does not support German.'}


def _number(value, minimum=0, maximum=MAX_DURATION):
    value = float(value)
    if not math.isfinite(value) or not minimum <= value <= maximum:
        raise ValueError(f'Number outside range {minimum}..{maximum}')
    return value


def _size(project):
    w, h = int(project.get('width', 1280)), int(project.get('height', 720))
    if not 1 <= w <= 4096 or not 1 <= h <= 4096:
        raise ValueError('Dimensions must be 1..4096')
    return w, h


def _beat_seconds(project):
    return 60 / _number(project.get('bpm', 120), 20, 300)


def _duration(project):
    beat_seconds = _beat_seconds(project)
    clip_ends = [_number(x.get('start', 0)) + _number(x['duration'], .001) for x in project.get('clips', [])]
    note_ends = [(_number(x.get('start', 0)) + _number(x['duration'], .001)) * beat_seconds for x in project.get('notes', [])]
    end = max([0.0] + clip_ends + note_ends)
    return _number(end or 1, .001)


def _font(size):
    candidates = [ROOT / 'resources/fonts/DejaVuSans.ttf', 'DejaVuSans.ttf',
                  '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',
                  '/System/Library/Fonts/Supplemental/Arial.ttf', 'C:/Windows/Fonts/arial.ttf']
    for candidate in candidates:
        try:
            return ImageFont.truetype(str(candidate), size)
        except OSError:
            continue
    return ImageFont.load_default()


def _photo(project, background='#ffffff'):
    canvas = Image.new('RGBA', _size(project), background)
    for layer in project.get('layers', []):
        x, y = int(layer.get('x', 0)), int(layer.get('y', 0))
        w, h = int(layer.get('width', 320)), int(layer.get('height', 180))
        if not 1 <= w <= 8192 or not 1 <= h <= 8192:
            raise ValueError('Invalid layer dimensions')
        opacity = _number(layer.get('opacity', 1), 0, 1)
        kind = layer['kind']
        if kind == 'image':
            with Image.open(layer['path']) as source:
                bitmap = source.convert('RGBA').resize((w, h), Image.Resampling.LANCZOS)
                alpha = bitmap.getchannel('A')
                rgb = bitmap.convert('RGB')
                for key, enhancer in [('brightness', ImageEnhance.Brightness), ('contrast', ImageEnhance.Contrast), ('saturation', ImageEnhance.Color)]:
                    rgb = enhancer(rgb).enhance(_number(layer.get(key, 1), 0, 4))
                bitmap = rgb.convert('RGBA')
                bitmap.putalpha(alpha)
        else:
            bitmap = Image.new('RGBA', (w, h))
            color = ImageColor.getcolor(layer.get('color', '#ffffff'), 'RGBA')
            if kind == 'rect':
                bitmap.paste(color, (0, 0, w, h))
            elif kind == 'ellipse':
                ImageDraw.Draw(bitmap).ellipse((0, 0, w - 1, h - 1), fill=color)
            elif kind == 'polygon':
                points = [(round(_number(x, 0, 1) * (w - 1)),
                           round(_number(y, 0, 1) * (h - 1))) for x, y in layer['points']]
                if not 3 <= len(points) <= 256:
                    raise ValueError('Polygon needs 3..256 points')
                ImageDraw.Draw(bitmap).polygon(points, fill=color)
            elif kind == 'text':
                font = _font(max(8, min(h, 64)))
                ImageDraw.Draw(bitmap).text((0, 0), layer.get('text', ''), font=font, fill=color)
            else:
                raise ValueError(f'Unsupported layer kind: {kind}')
        bitmap.putalpha(bitmap.getchannel('A').point(lambda a: round(a * opacity)))
        canvas.alpha_composite(bitmap, (x, y))
    return canvas


def _run(args):
    result = subprocess.run(args, capture_output=True, text=True, timeout=600)
    if result.returncode:
        raise RuntimeError(result.stderr[-3000:] or 'Media process failed')
    return result.stdout


def _mix(project, output):
    duration = _duration(project)
    count = math.ceil(duration * RATE)
    mix = np.zeros((count, 2), dtype=np.float32)
    beat_seconds = _beat_seconds(project)
    for note in project.get('notes', []):
        pitch = int(note['pitch'])
        if not 0 <= pitch <= 127:
            raise ValueError('MIDI pitch must be 0..127')
        start = round(_number(note.get('start', 0)) * beat_seconds * RATE)
        length = min(round(_number(note['duration'], .001) * beat_seconds * RATE), count - start)
        velocity = _number(note.get('velocity', .8), 0, 1)
        t = np.arange(length) / RATE
        envelope = np.minimum(1, t / .008) * np.minimum(1, (length / RATE - t) / .03)
        signal = (np.sin(2 * np.pi * (440 * 2 ** ((pitch - 69) / 12)) * t) * envelope * velocity * .25).astype(np.float32)
        mix[start:start + length] += signal[:, None]
    assets = {a['id']: a for a in project.get('assets', [])}
    for clip in project.get('clips', []):
        asset = assets.get(clip['asset_id'])
        if asset is None:
            raise ValueError('Unknown clip asset')
        if asset['kind'] not in ('audio', 'video'):
            continue
        if not shutil.which('ffmpeg'):
            raise RuntimeError('FFmpeg required for imported audio')
        start = round(_number(clip.get('start', 0)) * RATE)
        length = min(round(_number(clip['duration'], .001) * RATE), count - start)
        args = ['ffmpeg', '-v', 'error', '-ss', str(_number(clip.get('source_start', 0))), '-i', asset['path'], '-t', str(length / RATE), '-vn', '-f', 'f32le', '-ac', '2', '-ar', str(RATE), '-']
        result = subprocess.run(args, capture_output=True, timeout=600)
        if result.returncode:
            # Video assets can legitimately have no audio stream.
            if asset['kind'] == 'video' and b'does not contain any stream' in result.stderr:
                continue
            raise RuntimeError(result.stderr.decode(errors='replace')[-2000:])
        samples = np.frombuffer(result.stdout, dtype='<f4').reshape(-1, 2)[:length]
        mix[start:start + len(samples)] += samples * _number(clip.get('volume', 1), 0, 4)
    with wave.open(str(output), 'wb') as handle:
        handle.setnchannels(2)
        handle.setsampwidth(2)
        handle.setframerate(RATE)
        handle.writeframes((np.clip(mix, -1, 1) * 32767).astype('<i2').tobytes())


@lru_cache(maxsize=1)
def _video_codec():
    available = _run(['ffmpeg', '-hide_banner', '-encoders'])
    if 'libx264' in available:
        return ['-c:v', 'libx264', '-preset', 'veryfast']
    if 'h264_videotoolbox' in available:
        return ['-c:v', 'h264_videotoolbox', '-b:v', '8M']
    raise RuntimeError('No supported H.264 encoder available')


def export_project(project: dict, kind: str, output_dir) -> str:
    if kind not in ('photo', 'audio', 'video'):
        raise ValueError('Unknown export kind')
    folder = Path(output_dir)
    folder.mkdir(parents=True, exist_ok=True)
    output = folder / f'{uuid.uuid4().hex}.{dict(photo="png", audio="wav", video="mp4")[kind]}'
    if kind == 'photo':
        _photo(project).save(output)
    elif kind == 'audio':
        _mix(project, output)
    else:
        if not capabilities()['video']:
            raise RuntimeError('FFmpeg and ffprobe required for video')
        width, height = _size(project)
        if width % 2 or height % 2:
            raise ValueError('MP4 dimensions must be even')
        duration = _duration(project)
        fps = _number(project.get('fps', 30), 1, 120)
        assets = {a['id']: a for a in project.get('assets', [])}
        with tempfile.TemporaryDirectory() as scratch:
            background, audio = Path(scratch) / 'background.png', Path(scratch) / 'audio.wav'
            _photo(project, '#181820').convert('RGB').save(background)
            _mix(project, audio)
            args = ['ffmpeg', '-v', 'error', '-loop', '1', '-framerate', str(fps), '-i', str(background)]
            filters = ['[0:v]format=yuv420p[base]']
            last, index = 'base', 1
            for clip in sorted(project.get('clips', []), key=lambda c: c.get('track', 0)):
                asset = assets.get(clip['asset_id'])
                if asset is None:
                    raise ValueError('Unknown clip asset')
                if asset['kind'] not in ('image', 'video'):
                    continue
                if asset['kind'] == 'image':
                    args += ['-loop', '1', '-i', asset['path']]
                else:
                    args += ['-i', asset['path']]
                start, length, source = _number(clip.get('start', 0)), _number(clip['duration'], .001), _number(clip.get('source_start', 0))
                filters.append(f'[{index}:v]trim=start={source}:duration={length},setpts=PTS-STARTPTS+{start}/TB,scale={width}:{height}:force_original_aspect_ratio=decrease,pad={width}:{height}:(ow-iw)/2:(oh-ih)/2,setsar=1[v{index}]')
                filters.append(f'[{last}][v{index}]overlay=eof_action=pass:repeatlast=0:enable=\'between(t,{start},{start+length})\'[o{index}]')
                last = f'o{index}'
                index += 1
            args += ['-i', str(audio), '-filter_complex_threads', '1', '-filter_complex', ';'.join(filters), '-map', f'[{last}]', '-map', f'{index}:a', '-t', str(duration), '-r', str(fps), *_video_codec(), '-pix_fmt', 'yuv420p', '-c:a', 'aac', '-movflags', '+faststart', str(output)]
            _run(args)
    return str(output)


def synthesize_speech(text, output, provider='kokoro', voice='af_heart', speed=1.0, language='en-us') -> dict:
    if not isinstance(text, str) or not text.strip() or len(text) > 20000:
        raise ValueError('Speech text must contain 1..20000 characters')
    speed = _number(speed, .5, 2)
    if provider != 'kokoro' or not capabilities()['tts']['kokoro']:
        raise RuntimeError(f'TTS provider {provider} is unavailable')
    if language not in ('en-us', 'en-gb', 'fr-fr', 'es', 'it', 'pt-br', 'hi', 'ja', 'cmn'):
        raise ValueError('Unsupported Kokoro language; German requires another provider')
    destination = Path(output)
    if destination.exists():
        raise ValueError('Speech output already exists')
    from kokoro_onnx import Kokoro
    import soundfile as sf
    engine = Kokoro(str(MODEL), str(VOICES))
    samples, rate = engine.create(text, voice=voice, speed=speed, lang=language)
    if len(samples) / rate > MAX_DURATION:
        raise ValueError('Speech exceeds maximum duration of 600 seconds; split the text')
    destination.parent.mkdir(parents=True, exist_ok=True)
    sf.write(destination, samples, rate)
    return {'path': str(destination), 'provider': provider, 'sample_rate': rate, 'duration': len(samples) / rate}
