"""Assistant transport using the same native state and job queues as the editor."""
import asyncio
import copy
from pathlib import Path
import threading
import time
import uuid

from fastapi import APIRouter, File, HTTPException, UploadFile
from jsonschema.exceptions import ValidationError

import creative_assistant as assistant

router = APIRouter(prefix='/api/creative/assistant')
_plans = {}
_plans_lock = threading.Lock()


def _store_plan(provider, text, project, catalog, selected, history, sketch):
    plan = assistant.plan(provider, text, project, catalog, selected, history, sketch)
    ident = uuid.uuid4().hex
    public = {**plan, 'id': ident, 'project_id': project['id'],
              'revision': project['revision'], 'provider': provider}
    with _plans_lock:
        expired = [key for key, value in _plans.items() if value['expires'] < time.monotonic()]
        for key in expired:
            del _plans[key]
        if len(_plans) >= 128:
            del _plans[next(iter(_plans))]
        _plans[ident] = {'plan': public, 'expires': time.monotonic() + 900, 'state': 'pending'}
    return public


@router.get('/capabilities')
async def capabilities():
    return {'ok': True, 'result': assistant.capabilities()}


@router.post('/provider')
async def provider(payload: dict):
    try:
        result = assistant.configure(payload.get('provider'), payload.get('url', ''),
                                     payload.get('model', ''), payload.get('key', ''))
    except (ValueError, TypeError) as exc:
        raise HTTPException(422, str(exc))
    return {'ok': True, 'result': result}


@router.post('/plan')
async def plan(payload: dict):
    import creative_api as api
    project = (await api.execute({'action': 'project.get', 'project_id': payload.get('project_id'), 'params': {}}))['result']
    catalog = (await api.execute({'action': 'system.actions', 'params': {}}))['result']
    sketch = str(api.media_path(payload['sketch'])) if payload.get('sketch') else None
    selected = payload.get('selected')
    if selected is not None:
        collection = {'layer': 'layers', 'clip': 'clips', 'note': 'notes'}.get(selected.get('type')) if isinstance(selected, dict) else None
        if collection is None or not any(item['id'] == selected.get('id') for item in project[collection]):
            raise HTTPException(422, 'Selected element no longer exists')
    try:
        assistant._context(project, payload.get('text'), selected, payload.get('history', []))
    except ValueError as exc:
        raise HTTPException(422, str(exc))
    return api.schedule(_store_plan, payload.get('provider', 'builtin'), payload.get('text'),
                        project, catalog, selected, payload.get('history', []), sketch)


async def _apply(job, plan):
    import creative_api as api
    job['status'] = 'running'
    try:
        current = (await api.execute({'action': 'project.get', 'project_id': plan['project_id'], 'params': {}}))['result']
        if current['revision'] != plan['revision']:
            raise ValueError('Project changed; request a new plan')
        commands = copy.deepcopy(plan['commands'])
        output = None
        if plan['primitive'] != 'none':
            from creative_primitives import create_primitive
            output = await asyncio.to_thread(create_primitive, plan['primitive'], api.OUTPUT,
                                             plan['color'], plan['size'])
            commands = [
                {'action': 'asset.add', 'params': {'name': plan['primitive'] + ' · editable 3D', 'kind': 'blender', 'path': output['source']}},
                {'action': 'asset.add', 'params': {'name': plan['primitive'] + ' · preview', 'kind': 'image', 'path': output['path']}},
                {'action': 'layer.add', 'params': {'name': plan['primitive'] + ' · preview', 'kind': 'image', 'path': output['path'],
                    'x': (current['width'] - min(current['width'], current['height'])) / 2,
                    'y': (current['height'] - min(current['width'], current['height'])) / 2,
                    'width': min(current['width'], current['height']), 'height': min(current['width'], current['height'])}},
            ]
        result = await api.execute({'action': 'project.batch', 'project_id': plan['project_id'],
                                    'params': {'expected_revision': plan['revision'], 'commands': commands}})
        job['details'] = {'project': result['result'], 'message': plan['message'], 'artifact': output}
        job['status'] = 'completed'
    except Exception as exc:
        job['status'] = 'failed'
        job['error'] = str(exc.detail if isinstance(exc, HTTPException) else exc)
    finally:
        with _plans_lock:
            if plan['id'] in _plans:
                _plans[plan['id']]['state'] = job['status']


@router.post('/apply')
async def apply(payload: dict):
    import creative_api as api
    with _plans_lock:
        record = _plans.get(payload.get('plan_id'))
        if record is None or record['expires'] < time.monotonic():
            raise HTTPException(404, 'Plan expired; request a new plan')
        if record['state'] != 'pending':
            raise HTTPException(409, 'Plan already submitted')
        plan = record['plan']
        if plan['kind'] != 'edit':
            raise HTTPException(422, 'Help and clarification cannot be applied')
        record['state'] = 'running'
    job = {'id': uuid.uuid4().hex, 'status': 'queued'}
    api._jobs[job['id']] = job
    task = asyncio.create_task(_apply(job, plan))
    api._tasks.add(task)
    task.add_done_callback(api._tasks.discard)
    return dict(job)


@router.post('/transcribe')
async def transcribe(file: UploadFile = File(...), language: str = 'de'):
    import creative_api as api
    suffix = Path(file.filename or '').suffix.lower()
    if suffix not in ('.wav', '.webm', '.ogg', '.m4a', '.mp3', '.mp4'):
        raise HTTPException(422, 'Unsupported recording format')
    folder = api.MEDIA / 'assistant-recordings'
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / (uuid.uuid4().hex + suffix)
    size = 0
    try:
        with path.open('wb') as output:
            while chunk := await file.read(1024 * 1024):
                size += len(chunk)
                if size > 16 * 1024 * 1024:
                    raise HTTPException(413, 'Recording exceeds 16 MiB')
                output.write(chunk)
        # The recording is deleted after inference, even on failure.
        try:
            result = await asyncio.to_thread(assistant.transcribe, path, language)
        except (ValueError, RuntimeError) as exc:
            raise HTTPException(422, str(exc))
        return {'ok': True, 'result': result}
    finally:
        await file.close()
        path.unlink(missing_ok=True)
