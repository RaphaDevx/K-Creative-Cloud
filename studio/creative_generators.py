"""ComfyUI connector. Generation requires a running provider and real models.

The generic workflow endpoint accepts a ComfyUI API graph, not its editor JSON.
Video generation remains model/workflow specific; no video model is bundled.
"""
from __future__ import annotations

import io
import json
import os
from pathlib import Path, PurePosixPath
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid

from PIL import Image

POLL_TIMEOUT = 300.0
POLL_INTERVAL = 0.5
MAX_DOWNLOAD = 256 * 1024 * 1024
MAX_JSON = 4 * 1024 * 1024
SUFFIXES = {'.png', '.jpg', '.jpeg', '.gif', '.mp4', '.webm'}


def _base() -> str:
    value = os.environ.get('K_CREATIVE_COMFY_URL', 'http://127.0.0.1:8188').rstrip('/')
    parsed = urllib.parse.urlsplit(value)
    if parsed.scheme not in ('http', 'https') or not parsed.hostname or parsed.username or parsed.password or parsed.query or parsed.fragment:
        raise ValueError('K_CREATIVE_COMFY_URL must be an HTTP(S) base URL without credentials, query or fragment')
    # Validate the port as well: urlsplit delays malformed-port errors.
    _ = parsed.port
    return value


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def _request(base: str, route: str, payload=None, timeout=15.0, binary=False):
    headers = {'Accept': '*/*' if binary else 'application/json'}
    data = None
    if payload is not None:
        data = json.dumps(payload, allow_nan=False).encode()
        headers['Content-Type'] = 'application/json'
    request = urllib.request.Request(base + route, data=data, headers=headers)
    try:
        with urllib.request.build_opener(_NoRedirect()).open(request, timeout=timeout) as response:
            limit = MAX_DOWNLOAD if binary else MAX_JSON
            result = response.read(limit + 1)
            if len(result) > limit:
                raise RuntimeError('ComfyUI response exceeds size limit')
    except urllib.error.HTTPError as exc:
        detail = exc.read(2000).decode('utf-8', errors='replace')
        raise RuntimeError(f'ComfyUI request failed (HTTP {exc.code}): {detail}') from exc
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        raise RuntimeError(f'ComfyUI request failed: {exc}') from exc
    if binary:
        return result
    try:
        return json.loads(result)
    except (ValueError, UnicodeDecodeError) as exc:
        raise RuntimeError('ComfyUI returned invalid JSON') from exc


def _checkpoints(base: str, timeout=1.0) -> list[str]:
    data = _request(base, '/object_info/CheckpointLoaderSimple', timeout=timeout)
    try:
        models = data['CheckpointLoaderSimple']['input']['required']['ckpt_name'][0]
    except (KeyError, IndexError, TypeError) as exc:
        raise RuntimeError('ComfyUI checkpoint schema is unavailable') from exc
    if not isinstance(models, list) or any(not isinstance(model, str) for model in models):
        raise RuntimeError('ComfyUI checkpoint list is invalid')
    return models


def capabilities() -> dict:
    result = {'provider': 'comfyui', 'available': False, 'image': False,
              'workflow': False, 'video': False, 'checkpoints': [],
              'notes': 'Video generation requires a supplied API workflow and matching provider models.'}
    try:
        base = _base()
        result['url'] = base
        stats = _request(base, '/system_stats', timeout=1.0)
        if not isinstance(stats, dict):
            raise RuntimeError('ComfyUI system_stats is invalid')
        result['available'] = result['workflow'] = True
        configured = os.environ.get('K_CREATIVE_COMFY_CHECKPOINT', '').strip()
        try:
            models = _checkpoints(base)
        except RuntimeError:
            if not configured:
                raise
            models = [configured]
        result['checkpoints'] = models
        result['image'] = bool(models)
    except (ValueError, RuntimeError) as exc:
        result['error'] = str(exc)
    return result


def _validate_workflow(workflow: dict) -> None:
    if not isinstance(workflow, dict) or not 1 <= len(workflow) <= 100:
        raise ValueError('Workflow must contain 1..100 ComfyUI API nodes')
    try:
        encoded = json.dumps(workflow, allow_nan=False).encode()
    except (ValueError, TypeError, RecursionError) as exc:
        raise ValueError('Workflow must contain finite JSON values') from exc
    if len(encoded) > MAX_JSON:
        raise ValueError('Workflow exceeds size limit')
    for key, node in workflow.items():
        if not isinstance(key, str) or not key or not isinstance(node, dict):
            raise ValueError('Workflow nodes must have string IDs and object values')
        if not isinstance(node.get('class_type'), str) or not node['class_type'].strip() or not isinstance(node.get('inputs'), dict):
            raise ValueError('Each workflow node needs class_type and inputs')


def _wait(base: str, prompt_id: str) -> dict:
    deadline = time.monotonic() + POLL_TIMEOUT
    route = '/history/' + urllib.parse.quote(prompt_id, safe='')
    while time.monotonic() < deadline:
        remaining = deadline - time.monotonic()
        data = _request(base, route, timeout=max(.01, min(15.0, remaining)))
        if not isinstance(data, dict):
            raise RuntimeError('ComfyUI history is invalid')
        entry = data.get(prompt_id)
        if entry is not None:
            if not isinstance(entry, dict):
                raise RuntimeError('ComfyUI history entry is invalid')
            status = entry.get('status', {})
            if not isinstance(status, dict) or not isinstance(status.get('messages', []), list):
                raise RuntimeError('ComfyUI history status is invalid')
            if status.get('status_str') == 'error':
                raise RuntimeError('ComfyUI generation failed: ' + json.dumps(status.get('messages', []))[:2000])
            for message in status.get('messages', []):
                if isinstance(message, list) and message and message[0] in ('execution_error', 'execution_interrupted'):
                    raise RuntimeError('ComfyUI generation failed: ' + json.dumps(message)[:2000])
            if entry.get('outputs'):
                return entry
            if status.get('completed'):
                raise RuntimeError('ComfyUI completed without downloadable outputs')
        time.sleep(min(POLL_INTERVAL, max(0.0, deadline - time.monotonic())))
    raise RuntimeError('ComfyUI generation timed out; provider job may still be running')


def _outputs(entry: dict) -> list[dict]:
    outputs = entry.get('outputs')
    if not isinstance(outputs, dict):
        raise RuntimeError('ComfyUI outputs are invalid')
    files = []
    for node in outputs.values():
        if not isinstance(node, dict):
            continue
        for key in ('images', 'videos', 'gifs'):
            candidates = node.get(key, [])
            if not isinstance(candidates, list):
                raise RuntimeError('ComfyUI file list is invalid')
            for item in candidates:
                if not isinstance(item, dict):
                    raise RuntimeError('ComfyUI file metadata is invalid')
                name = item.get('filename', '')
                subfolder = item.get('subfolder', '')
                if not isinstance(name, str) or '/' in name or '\\' in name or not name or name in ('.', '..'):
                    raise RuntimeError('ComfyUI returned unsafe filename')
                if not isinstance(subfolder, str) or '\\' in subfolder or PurePosixPath(subfolder).is_absolute() or '..' in PurePosixPath(subfolder).parts:
                    raise RuntimeError('ComfyUI returned unsafe subfolder')
                if item.get('type', 'output') not in ('output', 'temp', 'input'):
                    raise RuntimeError('ComfyUI returned invalid file type')
                if Path(name).suffix.lower() in SUFFIXES:
                    files.append({'filename': name, 'subfolder': subfolder, 'type': item.get('type', 'output')})
    if not files or len(files) > 100:
        raise RuntimeError('ComfyUI returned no supported files or too many files')
    return files


def _validate_media(data: bytes, suffix: str) -> None:
    if suffix in ('.png', '.jpg', '.jpeg', '.gif'):
        try:
            with Image.open(io.BytesIO(data)) as image:
                expected = {'.png': 'PNG', '.jpg': 'JPEG', '.jpeg': 'JPEG', '.gif': 'GIF'}[suffix]
                if image.format != expected:
                    raise ValueError('Media format does not match filename')
                image.verify()
        except (OSError, ValueError, Image.DecompressionBombError) as exc:
            raise RuntimeError('ComfyUI returned invalid image data') from exc
    elif suffix == '.mp4' and (len(data) < 12 or data[4:8] != b'ftyp'):
        raise RuntimeError('ComfyUI returned invalid MP4 data')
    elif suffix == '.webm' and not data.startswith(b'\x1a\x45\xdf\xa3'):
        raise RuntimeError('ComfyUI returned invalid WebM data')


def generate_workflow(workflow: dict, output_dir) -> dict:
    _validate_workflow(workflow)
    base = _base()
    queued = _request(base, '/prompt', {'prompt': workflow, 'client_id': str(uuid.uuid4())})
    if not isinstance(queued, dict) or queued.get('error') or queued.get('node_errors'):
        raise RuntimeError('ComfyUI rejected workflow: ' + json.dumps(queued)[:2000])
    prompt_id = queued.get('prompt_id')
    if not isinstance(prompt_id, str) or not prompt_id:
        raise RuntimeError('ComfyUI did not return a prompt_id')
    entry = _wait(base, prompt_id)
    directory = Path(output_dir)
    directory.mkdir(parents=True, exist_ok=True)
    paths = []
    try:
        for item in _outputs(entry):
            suffix = Path(item['filename']).suffix.lower()
            data = _request(base, '/view?' + urllib.parse.urlencode(item), binary=True)
            _validate_media(data, suffix)
            destination = directory / (uuid.uuid4().hex + suffix)
            with destination.open('xb') as stream:
                paths.append(str(destination))
                stream.write(data)
                stream.flush()
                os.fsync(stream.fileno())
    except Exception:
        for path in paths:
            Path(path).unlink(missing_ok=True)
        raise
    return {'path': paths[0], 'paths': paths, 'provider': 'comfyui', 'prompt_id': prompt_id}


def generate_image(prompt, output_dir, checkpoint=None, negative='', seed=0,
                   width=1024, height=1024, steps=20) -> dict:
    if not isinstance(prompt, str) or not prompt.strip() or len(prompt) > 20000:
        raise ValueError('Prompt must contain 1..20000 characters')
    if not isinstance(negative, str) or len(negative) > 20000:
        raise ValueError('Negative prompt must contain at most 20000 characters')
    for name, value, minimum, maximum in [('width', width, 64, 2048), ('height', height, 64, 2048),
                                         ('steps', steps, 1, 100), ('seed', seed, 0, 2**64-1)]:
        if type(value) is not int or not minimum <= value <= maximum:
            raise ValueError(f'Invalid {name}')
    if width % 8 or height % 8:
        raise ValueError('Image dimensions must be multiples of eight')
    base = _base()
    model = checkpoint or os.environ.get('K_CREATIVE_COMFY_CHECKPOINT', '').strip()
    if not model:
        models = _checkpoints(base)
        if not models:
            raise RuntimeError('ComfyUI has no installed checkpoints')
        model = models[0]
    if not isinstance(model, str) or not model.strip() or len(model) > 1000:
        raise ValueError('Invalid checkpoint')
    workflow = {
        '1': {'class_type': 'CheckpointLoaderSimple', 'inputs': {'ckpt_name': model}},
        '2': {'class_type': 'CLIPTextEncode', 'inputs': {'text': prompt, 'clip': ['1', 1]}},
        '3': {'class_type': 'CLIPTextEncode', 'inputs': {'text': negative, 'clip': ['1', 1]}},
        '4': {'class_type': 'EmptyLatentImage', 'inputs': {'width': width, 'height': height, 'batch_size': 1}},
        '5': {'class_type': 'KSampler', 'inputs': {'model': ['1', 0], 'positive': ['2', 0], 'negative': ['3', 0],
              'latent_image': ['4', 0], 'seed': seed, 'steps': steps, 'cfg': 7.0,
              'sampler_name': 'euler', 'scheduler': 'normal', 'denoise': 1.0}},
        '6': {'class_type': 'VAEDecode', 'inputs': {'samples': ['5', 0], 'vae': ['1', 2]}},
        '7': {'class_type': 'SaveImage', 'inputs': {'images': ['6', 0], 'filename_prefix': 'KCreative'}},
    }
    return generate_workflow(workflow, output_dir)
