"""Shared local HTTP transport for the Rust creative command core."""
import asyncio
import copy
import fcntl
import json
import os
from pathlib import Path
import uuid

from fastapi import APIRouter, HTTPException, UploadFile, File
from fastapi.responses import FileResponse

RESOURCE = Path(__file__).resolve().parent
REPO = RESOURCE.parent
DATA = Path(os.environ.get("K_CREATIVE_DIR", REPO)).resolve()
STORE = Path(os.environ.get('K_CREATIVE_STORE', DATA / 'workspace/native-projects')).resolve()
MEDIA = Path(os.environ.get('K_CREATIVE_MEDIA', DATA / 'workspace/native-media')).resolve()
OUTPUT = DATA / 'renders/native'
CORE = Path(os.environ.get('K_CREATIVE_CORE', REPO / 'creative-core/target/debug/creative-core'))
router = APIRouter()
_lock = asyncio.Lock()
_jobs = {}
_tasks = set()


def media_path(value, must_exist=True):
    path = Path(value).expanduser().resolve()
    roots = [MEDIA, OUTPUT.resolve(), (DATA / 'workspace').resolve(), (REPO / 'K-DAW/downloads').resolve(), (REPO / 'K-DAW/stems').resolve()]
    if not any(path.is_relative_to(root) for root in roots):
        raise HTTPException(403, 'Asset must be inside the creative workspace or DAW library')
    if must_exist and not path.is_file():
        raise HTTPException(404, 'Asset not found')
    return path


async def execute(payload):
    if not isinstance(payload, dict) or not isinstance(payload.get('action'), str):
        raise HTTPException(422, 'An action string is required')
    payload = copy.deepcopy(payload)
    params = payload.get('params', {})
    if not isinstance(params, dict):
        raise HTTPException(422, 'params must be an object')
    if payload['action'] in ('asset.add', 'layer.add', 'layer.update') and params.get('path'):
        params['path'] = str(media_path(params['path']))
    if payload['action'] == 'project.batch':
        commands = params.get('commands')
        if not isinstance(commands, list) or not 1 <= len(commands) <= 64:
            raise HTTPException(422, 'Batch requires 1..64 commands')
        for command in commands:
            if not isinstance(command, dict) or not isinstance(command.get('params', {}), dict):
                raise HTTPException(422, 'Invalid batch command')
            nested = command.get('params', {})
            if command.get('action') in ('asset.add', 'layer.add', 'layer.update') and nested.get('path'):
                nested['path'] = str(media_path(nested['path']))
    brand_commands = params.get('commands', []) if payload['action'] == 'project.batch' else [payload]
    for command in brand_commands:
        if command.get('action') == 'brand.update':
            brand = command.get('params', {}).get('brand')
            if isinstance(brand, dict) and 'identity' in brand:
                from creative_brand import normalize
                try:
                    command['params']['brand'] = normalize(brand)
                except (ValueError, TypeError) as exc:
                    raise HTTPException(422, str(exc))
    payload['params'] = params
    if not CORE.is_file():
        raise HTTPException(503, 'Rust core not built; run scripts/start-creative.sh')
    async with _lock:
        STORE.mkdir(parents=True, exist_ok=True)
        # Coordinate independent local app processes that open the same workspace.
        with (STORE / '.commands.lock').open('a') as lockfile:
            await asyncio.to_thread(fcntl.flock, lockfile.fileno(), fcntl.LOCK_EX)
            try:
                proc = await asyncio.create_subprocess_exec(str(CORE), '--store', str(STORE), stdin=asyncio.subprocess.PIPE, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
                try:
                    out, err = await asyncio.wait_for(proc.communicate(json.dumps(payload).encode()), timeout=20)
                except asyncio.TimeoutError:
                    proc.kill()
                    await proc.wait()
                    raise HTTPException(504, 'Core command timed out')
            finally:
                fcntl.flock(lockfile.fileno(), fcntl.LOCK_UN)
    try:
        result = json.loads(out)
    except (ValueError, UnicodeDecodeError):
        raise HTTPException(500, 'Invalid core response')
    if not result.get('ok'):
        raise HTTPException(422, result.get('error', 'Core action failed'))
    return result


@router.post('/api/creative/action')
async def action(payload: dict):
    return await execute(payload)


@router.get('/api/creative/actions')
async def actions():
    return await execute({'action': 'system.actions', 'params': {}})


@router.get('/api/creative/projects')
async def projects():
    return await execute({'action': 'project.list', 'params': {}})


@router.get('/api/creative/capabilities')
async def capabilities():
    from creative_media import capabilities as media_capabilities
    result = await asyncio.to_thread(media_capabilities)
    return {'ok': True, 'result': {**result, 'rust_core': CORE.is_file()}}


@router.get('/api/creative/workflows')
async def workflows(kind: str | None = None):
    """Shared read-only inventory for creative skills, GUI and MCP."""
    from creative_discovery import KINDS, discover
    if kind is not None and kind not in KINDS:
        raise HTTPException(422, 'Unknown creative workflow kind')
    return {'ok': True, 'result': await asyncio.to_thread(discover, kind)}


@router.post('/api/creative/upload')
async def upload(file: UploadFile = File(...)):
    MEDIA.mkdir(parents=True, exist_ok=True)
    suffix = Path(file.filename or '').suffix.lower()
    allowed = {'.png', '.jpg', '.jpeg', '.webp', '.gif', '.wav', '.mp3', '.ogg', '.flac', '.m4a', '.mp4', '.mov', '.webm', '.mkv', '.blend'}
    if suffix not in allowed:
        raise HTTPException(422, 'Unsupported media format')
    path = MEDIA / (uuid.uuid4().hex + suffix)
    size = 0
    try:
        with path.open('wb') as output:
            while chunk := await file.read(1024 * 1024):
                size += len(chunk)
                if size > 1024 * 1024 * 1024:
                    raise HTTPException(413, 'Upload exceeds 1 GiB')
                output.write(chunk)
    except BaseException:
        path.unlink(missing_ok=True)
        raise
    finally:
        await file.close()
    return {'ok': True, 'result': {'path': str(path), 'name': Path(file.filename or path.name).name}}


@router.get('/api/creative/asset')
async def asset(path: str):
    return FileResponse(media_path(path))


async def run_job(job, func, *args):
    job['status'] = 'running'
    try:
        result = await asyncio.to_thread(func, *args)
        if not isinstance(result, dict) or result.get('path'):
            job['output'] = str(result['path'] if isinstance(result, dict) else result)
        if isinstance(result, dict):
            job['details'] = result
        job['status'] = 'completed'
    except Exception as exc:
        job['status'] = 'failed'
        job['error'] = str(exc)


def schedule(func, *args):
    job = {'id': uuid.uuid4().hex, 'status': 'queued'}
    _jobs[job['id']] = job
    task = asyncio.create_task(run_job(job, func, *args))
    _tasks.add(task)
    task.add_done_callback(_tasks.discard)
    return dict(job)


@router.post('/api/creative/export')
async def export(payload: dict):
    from creative_media import export_project
    kind = payload.get('kind')
    if kind not in ('photo', 'audio', 'video'):
        raise HTTPException(422, 'kind must be photo, audio or video')
    project = (await execute({'action': 'project.get', 'project_id': payload.get('project_id'), 'params': {}}))['result']
    for collection in ('assets', 'layers'):
        for item in project.get(collection, []):
            if item.get('path'):
                media_path(item['path'])
    directory = OUTPUT / uuid.uuid4().hex
    return schedule(export_project, project, kind, directory)


@router.post('/api/creative/tts')
async def tts(payload: dict):
    from creative_media import synthesize_speech
    text = payload.get('text')
    if not isinstance(text, str) or not text.strip() or len(text) > 20000:
        raise HTTPException(422, 'text must contain 1–20000 characters')
    OUTPUT.mkdir(parents=True, exist_ok=True)
    path = OUTPUT / (uuid.uuid4().hex + '.wav')
    return schedule(synthesize_speech, text, str(path), payload.get('provider', 'kokoro'), payload.get('voice', 'af_heart'), payload.get('speed', 1.0), payload.get('language', 'en-us'))


@router.get('/api/creative/jobs/{job_id}')
async def get_job(job_id: str):
    if job_id not in _jobs:
        raise HTTPException(404, 'Job not found')
    return _jobs[job_id]


@router.get('/creative')
async def editor():
    return FileResponse(RESOURCE / 'static/creative/index.html')


@router.get("/api/creative/health")
async def health():
    return {"service": "k-creative", "version": "0.4.0"}


@router.get('/api/creative/tools')
async def tools():
    from creative_automation import capabilities
    return {'ok': True, 'result': capabilities()}


@router.post('/api/creative/autocut')
async def autocut(payload: dict):
    from creative_automation import auto_cut
    path = media_path(payload.get('path', ''))
    return schedule(auto_cut, str(path), OUTPUT / uuid.uuid4().hex, payload.get('threshold', .3))


@router.post('/api/creative/blender')
async def blender(payload: dict):
    from creative_automation import render_blender
    path = media_path(payload.get('path', ''))
    if path.suffix.lower() != '.blend':
        raise HTTPException(422, 'A .blend source is required')
    return schedule(render_blender, str(path), OUTPUT / uuid.uuid4().hex, payload.get('frame_start'), payload.get('frame_end'), payload.get('fps', 30))


@router.post('/api/creative/launch')
async def launch(payload: dict):
    from creative_automation import launch_editor
    path = str(media_path(payload['path'])) if payload.get('path') else None
    try:
        result = await asyncio.to_thread(launch_editor, payload.get('tool'), path)
    except (ValueError, RuntimeError) as exc:
        raise HTTPException(422, str(exc))
    return {'ok': True, 'result': result}


@router.get('/api/creative/agents')
async def agents():
    from creative_agent import capabilities
    return {'ok': True, 'result': capabilities()}


@router.get('/api/creative/generators')
async def generators():
    from creative_generators import capabilities
    return {'ok': True, 'result': await asyncio.to_thread(capabilities)}


@router.post('/api/creative/generate/image')
async def generate_image(payload: dict):
    from creative_generators import generate_image as generate
    return schedule(generate, payload.get('prompt'), OUTPUT / uuid.uuid4().hex, payload.get('checkpoint'), payload.get('negative', ''), payload.get('seed', 0), payload.get('width', 1024), payload.get('height', 1024), payload.get('steps', 20))


@router.post('/api/creative/generate/workflow')
async def generate_workflow(payload: dict):
    from creative_generators import generate_workflow as generate
    return schedule(generate, payload.get('workflow'), OUTPUT / uuid.uuid4().hex)


@router.post('/api/creative/lmms')
async def lmms_export(payload: dict):
    from creative_lmms import export_lmms
    project = (await execute({'action': 'project.get', 'project_id': payload.get('project_id'), 'params': {}}))['result']
    render = payload.get('render', True)
    if not isinstance(render, bool):
        raise HTTPException(422, 'render must be boolean')
    return schedule(export_lmms, project, OUTPUT / uuid.uuid4().hex, render)

# Import after shared state/actions are defined to preserve one project authority.
from creative_assistant_api import router as assistant_router
router.include_router(assistant_router)
from creative_characters import router as characters_router
router.include_router(characters_router)

@router.get('/api/creative/brand/presets')
async def brand_presets():
    from creative_brand import PRESETS, ROLES
    return {'ok': True, 'result': {'presets': [{'id': key, 'label': value['label'], 'palette': dict(zip(ROLES, value['palette']))} for key, value in PRESETS.items()]}}


@router.post('/api/creative/brand/create')
async def brand_create(payload: dict):
    from creative_brand import identity
    project = (await execute({'action': 'project.get', 'project_id': payload.get('project_id'), 'params': {}}))['result']
    try:
        brand = identity(payload.get('preset', 'y2k'), payload.get('name') or project['name'],
                         payload.get('brief', ''), payload.get('audience', ''), payload.get('goal', ''))
    except (ValueError, TypeError) as exc:
        raise HTTPException(422, str(exc))
    return await execute({'action': 'project.batch', 'project_id': project['id'], 'params': {
        'expected_revision': project['revision'], 'commands': [{'action': 'brand.update', 'params': {'brand': brand}}]}})


@router.post('/api/creative/brand/import')
async def brand_import(payload: dict):
    from creative_brand import normalize
    project = (await execute({'action': 'project.get', 'project_id': payload.get('project_id'), 'params': {}}))['result']
    try:
        brand = normalize(payload.get('brand'))
    except (ValueError, TypeError) as exc:
        raise HTTPException(422, str(exc))
    return await execute({'action': 'project.batch', 'project_id': project['id'], 'params': {
        'expected_revision': payload.get('expected_revision', project['revision']),
        'commands': [{'action': 'brand.update', 'params': {'brand': brand}}]}})


@router.post('/api/creative/brand/export')
async def brand_export(payload: dict):
    from creative_brand import export_project_brand, normalize
    project = (await execute({'action': 'project.get', 'project_id': payload.get('project_id'), 'params': {}}))['result']
    try:
        normalize(project.get('brand'))
    except (ValueError, TypeError) as exc:
        raise HTTPException(422, str(exc))
    return schedule(export_project_brand, project, DATA / 'workspace/brand-projects')
