import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'studio'))
import creative_characters as ch


class CharactersTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        home = Path(self.temp.name)
        (home / 'characters').mkdir()
        (home / 'personas').mkdir()
        (home / 'channels').mkdir()
        self.patch = patch.object(ch, 'VOICE_HOME', home)
        self.patch.start()
        self.home = home
        app = FastAPI(); app.include_router(ch.router)
        self.client = TestClient(app)

    def tearDown(self):
        self.patch.stop(); self.temp.cleanup()

    def add(self, **extra):
        data = {'id': 'piggy', 'name': 'Piggy', 'persona': 'p1', 'actions': ['pose_idle'], 'expressions': ['happy'],
                'assets': {'model': 'brand/piggy/dist/3d/piggy.glb', 'sprites_dir': 'brand/piggy/dist/3d/sprites'}}
        data.update(extra)
        (self.home / 'characters' / f"{data['id']}.json").write_text(json.dumps(data))

    def test_list_includes_assets_persona_and_channels(self):
        self.add()
        (self.home / 'personas' / 'p1.json').write_text(json.dumps(
            {'id': 'p1', 'name': 'Prof', 'version': 2, 'voices': {'de': {'engine': 'piper', 'voice': 'v'}}}))
        (self.home / 'channels' / 'k.json').write_text(json.dumps({'id': 'k', 'persona': 'p1'}))
        with patch.object(ch, 'voice_status', return_value={'available': True, 'reason': ''}):
            body = self.client.get('/api/creative/characters').json()
        piggy = body['characters'][0]
        self.assertEqual(piggy['persona']['version'], 2)
        self.assertEqual(piggy['channels'], ['k'])
        self.assertTrue(piggy['assets']['model'].endswith('/asset/model'))
        self.assertTrue(all(s['url'].startswith('/api/creative/characters/piggy/asset/sprite:') for s in piggy['assets']['sprites']))

    def test_asset_serves_model_and_rejects_unknown_keys(self):
        self.add()
        self.assertEqual(self.client.get('/api/creative/characters/piggy/asset/model').status_code, 200)
        self.assertEqual(self.client.get('/api/creative/characters/piggy/asset/overview').status_code, 404)
        self.assertEqual(self.client.get('/api/creative/characters/piggy/asset/..%2F..%2Fetc%2Fpasswd').status_code, 404)
        self.assertEqual(self.client.get('/api/creative/characters/piggy/asset/sprite:idle-neutral').status_code, 200)

    def test_asset_path_cannot_escape_repo(self):
        self.add(assets={'model': '../../../etc/passwd'})
        self.assertEqual(self.client.get('/api/creative/characters/piggy/asset/model').status_code, 404)

    def test_bad_ids_and_missing_character(self):
        self.assertEqual(self.client.get('/api/creative/characters/Bad..Id/asset/model').status_code, 422)
        self.assertEqual(self.client.get('/api/creative/characters/nope/asset/model').status_code, 404)

    def test_voice_preview_validation_and_truthful_unavailable(self):
        self.add(persona=None)
        self.assertEqual(self.client.post('/api/creative/characters/piggy/voice-preview', json={'text': ''}).status_code, 422)
        self.assertEqual(self.client.post('/api/creative/characters/piggy/voice-preview', json={'text': 'Hi'}).status_code, 409)
        self.add()
        (self.home / 'personas' / 'p1.json').write_text(json.dumps({'id': 'p1', 'voices': {}}))
        with patch.object(ch, 'voice_status', return_value={'available': False, 'reason': 'Missing Python packages'}):
            r = self.client.post('/api/creative/characters/piggy/voice-preview', json={'text': 'Hi'})
        self.assertEqual(r.status_code, 503)


if __name__ == '__main__':
    unittest.main()
