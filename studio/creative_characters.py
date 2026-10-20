"""Characters: Maskottchen-Galerie mit 3D-Modell, Sprites und gebundener Persona/Stimme.

Figuren liegen als JSON in voice-data/characters/<id>.json. Assets werden nie per Pfad vom Client
angefordert, sondern über Schlüssel aus der Figurendatei (Allowlist) und bleiben im Repo."""
import asyncio
import json
import mimetypes
import os
import re
import sys
import uuid
from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

REPO = Path(__file__).resolve().parent.parent
VOICE_HOME = Path(os.environ.get('K_CREATIVE_VOICE_HOME', REPO / 'voice-data')).resolve()
ID = re.compile(r'^[a-z0-9][a-z0-9-]{0,40}$')
SPRITE = re.compile(r'^[a-z0-9]+-mascot-([a-z0-9]+)-([a-z0-9]+)\.png$')
FIXED_KEYS = ('model', 'poster', 'idle_video', 'overview')

router = APIRouter()


def _read(path: Path):
    try:
        return json.loads(path.read_text(encoding='utf-8'))
    except (OSError, ValueError):
        return None


def _character(cid: str) -> dict:
    if not ID.match(cid):
        raise HTTPException(422, 'Invalid character id')
    data = _read(VOICE_HOME / 'characters' / f'{cid}.json')
    if not isinstance(data, dict) or data.get('id') != cid:
        raise HTTPException(404, 'Character not found')
    return data


def _asset_file(char: dict, key: str) -> Path:
    assets = char.get('assets', {})
    if key.startswith('sprite:'):
        m = re.match(r'^sprite:([a-z0-9]+)-([a-z0-9]+)$', key)
        folder = assets.get('sprites_dir')
        if not m or not folder:
            raise HTTPException(404, 'Asset not found')
        for f in (REPO / folder).glob('*.png'):
            s = SPRITE.match(f.name)
            if s and s.groups() == m.groups():
                return _inside(f)
        raise HTTPException(404, 'Asset not found')
    if key not in FIXED_KEYS or not assets.get(key):
        raise HTTPException(404, 'Asset not found')
    return _inside(REPO / assets[key])


def _inside(path: Path) -> Path:
    path = path.resolve()
    if not path.is_relative_to(REPO) or not path.is_file():
        raise HTTPException(404, 'Asset not found')
    return path


def voice_status() -> dict:
    sys.path.insert(0, str(REPO / 'video-shorts-mcp')) if str(REPO / 'video-shorts-mcp') not in sys.path else None
    missing = []
    for mod in ('piper', 'kokoro_onnx', 'langid', 'soundfile'):
        try:
            __import__(mod)
        except ImportError:
            missing.append(mod)
    if missing:
        return {'available': False, 'reason': 'Missing Python packages in the studio environment: ' + ', '.join(missing)}
    return {'available': True, 'reason': ''}


def _persona(pid):
    if not pid or not ID.match(pid):
        return None
    p = _read(VOICE_HOME / 'personas' / f'{pid}.json')
    if not p:
        return None
    return {'id': p['id'], 'name': p.get('name', p['id']), 'version': p.get('version', 1),
            'voices': {lang: {'engine': v.get('engine'), 'voice': v.get('voice')} for lang, v in p.get('voices', {}).items()}}


def _channels(pid):
    out = []
    for f in sorted((VOICE_HOME / 'channels').glob('*.json')):
        c = _read(f)
        if c and c.get('persona') == pid:
            out.append(c['id'])
    return out


def _describe(char: dict, status: dict) -> dict:
    cid = char['id']
    url = lambda key: f'/api/creative/characters/{cid}/asset/{key}'
    assets = {k: (url(k) if char.get('assets', {}).get(k) else None) for k in FIXED_KEYS}
    assets['model'] = url('model') if char.get('assets', {}).get('model') else None
    sprites = []
    folder = char.get('assets', {}).get('sprites_dir')
    if folder:
        for f in sorted((REPO / folder).glob('*.png')):
            s = SPRITE.match(f.name)
            if s:
                sprites.append({'pose': s.group(1), 'expr': s.group(2), 'url': url(f'sprite:{s.group(1)}-{s.group(2)}')})
    assets['sprites'] = sprites
    persona = _persona(char.get('persona'))
    return {'id': cid, 'name': char.get('name', cid), 'description': char.get('description', ''),
            'actions': char.get('actions', []), 'expressions': char.get('expressions', []), 'assets': assets,
            'persona': persona, 'channels': _channels(char.get('persona')),
            'voice': status if persona else {'available': False, 'reason': 'No persona bound to this character'}}


@router.get('/api/creative/characters')
async def characters():
    status = await asyncio.to_thread(voice_status)
    folder = VOICE_HOME / 'characters'
    chars = []
    for f in sorted(folder.glob('*.json')) if folder.is_dir() else []:
        data = _read(f)
        if isinstance(data, dict) and ID.match(str(data.get('id', ''))):
            chars.append(_describe(data, status))
    return {'characters': chars}


@router.get('/api/creative/characters/{cid}/asset/{key}')
async def character_asset(cid: str, key: str):
    path = _asset_file(_character(cid), key)
    return FileResponse(path, media_type=mimetypes.guess_type(path.name)[0] or 'application/octet-stream',
                        headers={'Cache-Control': 'no-cache'})


def _preview(persona: str, text: str, out: str) -> dict:
    sys.path.insert(0, str(REPO / 'video-shorts-mcp'))
    os.environ.setdefault('K_CREATIVE_VOICE_HOME', str(VOICE_HOME))
    from voice import synthesize
    meta = synthesize(text, out, persona=persona)
    return {'path': out, 'persona': meta['persona'], 'persona_version': meta['persona_version'],
            'duration': meta['duration'], 'segments': meta['segments']}


@router.post('/api/creative/characters/{cid}/voice-preview')
async def voice_preview(cid: str, payload: dict):
    from creative_api import OUTPUT, schedule
    char = _character(cid)
    text = payload.get('text')
    if not isinstance(text, str) or not text.strip() or len(text) > 600:
        raise HTTPException(422, 'text must contain 1–600 characters')
    if not _persona(char.get('persona')):
        raise HTTPException(409, 'No persona bound to this character')
    status = await asyncio.to_thread(voice_status)
    if not status['available']:
        raise HTTPException(503, status['reason'])
    OUTPUT.mkdir(parents=True, exist_ok=True)
    return schedule(_preview, char['persona'], text, str(OUTPUT / (uuid.uuid4().hex + '.wav')))
