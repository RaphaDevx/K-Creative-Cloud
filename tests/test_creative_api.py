import asyncio
import importlib
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'studio'))
import creative_api as api


class BridgeTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.store = patch.object(api, 'STORE', Path(self.temp.name) / 'projects')
        self.media = patch.object(api, 'MEDIA', Path(self.temp.name) / 'media')
        self.store.start(); self.media.start()
        api._lock = asyncio.Lock()
        app = FastAPI(); app.include_router(api.router)
        self.client = TestClient(app)

    def tearDown(self):
        self.client.close(); self.store.stop(); self.media.stop(); self.temp.cleanup()

    def command(self, action, params, project_id=None):
        body = dict(action=action, params=params)
        if project_id: body['project_id'] = project_id
        return self.client.post('/api/creative/action', json=body)

    def test_persistence_undo_and_catalog(self):
        result = self.command('project.create', {'name': 'HTTP test'}).json()['result']
        ident = result['id']
        self.assertEqual(self.client.get('/api/creative/projects').json()['result'][0]['id'], ident)
        changed = self.command('note.add', {'pitch': 60, 'start': 0, 'duration': .5}, ident).json()['result']
        self.assertEqual(len(changed['notes']), 1)
        self.assertEqual(len(self.command('history.undo', {}, ident).json()['result']['notes']), 0)
        self.assertEqual(len(self.command('history.redo', {}, ident).json()['result']['notes']), 1)
        catalog = self.client.get('/api/creative/actions').json()['result']
        self.assertIn('note.add', [x['name'] for x in catalog])

    def test_input_and_path_rejection(self):
        self.assertEqual(self.command('asset.add', {'path': '/etc/passwd'}).status_code, 403)
        self.assertEqual(self.client.get('/api/creative/asset', params={'path': '/etc/passwd'}).status_code, 403)
        self.assertEqual(self.command('project.create', {'name': 'bad', 'width': -1}).status_code, 422)
        self.assertEqual(self.command('unknown', {}).status_code, 422)

    def test_upload_content_and_extension(self):
        response = self.client.post('/api/creative/upload', files={'file': ('test.png', b'fixture', 'image/png')})
        path = response.json()['result']['path']
        self.assertEqual(self.client.get('/api/creative/asset', params={'path': path}).content, b'fixture')
        self.assertEqual(self.client.post('/api/creative/upload', files={'file': ('bad.py', b'code')}).status_code, 422)

    def test_job_success_failure(self):
        async def check():
            job = api.schedule(lambda: '/tmp/output.wav')
            await asyncio.gather(*list(api._tasks))
            self.assertEqual(api._jobs[job['id']]['status'], 'completed')
            def fail(): raise ValueError('expected failure')
            job = api.schedule(fail)
            await asyncio.gather(*list(api._tasks))
            self.assertEqual(api._jobs[job['id']]['status'], 'failed')
            self.assertEqual(api._jobs[job['id']]['error'], 'expected failure')
        asyncio.run(check())

    def test_mcp_uses_same_command(self):
        import creative_mcp
        with patch.object(creative_mcp, 'request', side_effect=lambda endpoint, payload=None: self.client.post(endpoint, json=payload).json() if payload else self.client.get(endpoint).json()):
            project = creative_mcp.creative_execute('project.create', {'name': 'MCP'})['result']
            updated = creative_mcp.creative_execute('layer.add', {'kind': 'rect', 'name': 'MCP layer'}, project['id'])['result']
            read = self.command('project.get', {}, project['id']).json()['result']
            self.assertEqual(read, updated)


if __name__ == '__main__': unittest.main()

class SecurityTest(unittest.TestCase):
    def setUp(self):
        from creative_security import LocalSecurity
        app = FastAPI()
        app.add_middleware(LocalSecurity)
        @app.get('/ping')
        def ping(): return {'ok': True}
        self.client = TestClient(app, base_url='http://127.0.0.1:47200')

    def tearDown(self): self.client.close()

    def test_foreign_origin_and_host(self):
        self.assertEqual(self.client.get('/ping').status_code, 200)
        self.assertEqual(self.client.get('/ping', headers={'Origin': 'https://evil.example'}).status_code, 403)
        self.assertEqual(self.client.get('/ping', headers={'Host': 'evil.example'}).status_code, 403)
        self.assertEqual(self.client.get('/ping', headers={'Origin': 'http://127.0.0.1:9999'}).status_code, 403)

    def test_launch_token_header_cookie(self):
        with patch.dict('os.environ', {'K_CREATIVE_TOKEN': 'test-only-token'}):
            self.assertEqual(self.client.get('/ping').status_code, 403)
            self.assertEqual(self.client.get('/ping', headers={'X-K-Creative-Token': 'test-only-token'}).status_code, 200)
            self.assertEqual(self.client.get('/ping', headers={'Cookie': 'k_creative_session=test-only-token'}).status_code, 200)
