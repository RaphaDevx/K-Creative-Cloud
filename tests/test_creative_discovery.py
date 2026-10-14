"""Discovery stays inert and consistent across the CLI and HTTP transport."""
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'studio'))
import creative_discovery as discovery
import creative_api


class DiscoveryTest(unittest.TestCase):
    def test_manifest_review_and_path_confinement(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            manifests = root / 'packages/integrations'
            manifests.mkdir(parents=True)
            adapter = root / 'adapter.py'
            adapter.write_text('raise RuntimeError("must never execute")')
            entry = dict(id='test-engine', kind='photo', adapter='adapter.py',
                         review_status='candidate', command='touch /tmp/never-run')
            manifest = manifests / 'test.json'
            manifest.write_text(json.dumps(entry))
            def candidate():
                return next(t for t in discovery.discover('photo', root=root,
                            which=lambda _: None)['tools'] if t['id'] == 'test-engine')
            self.assertEqual(candidate()['status'], 'review_required')
            entry.update(review_status='accepted', acceptance_evidence='fixture comparison')
            manifest.write_text(json.dumps(entry))
            self.assertEqual(candidate()['status'], 'available_to_probe')
            self.assertFalse(candidate()['verified_for_task'])
            entry['adapter'] = '../outside.py'
            manifest.write_text(json.dumps(entry))
            result = discovery.discover('photo', root=root, which=lambda _: None)
            self.assertEqual(len(result['manifest_errors']), 1)
            self.assertNotIn('test-engine', [t['id'] for t in result['tools']])

    def test_http_filter_validation_and_cli_parity(self):
        app = FastAPI()
        app.include_router(creative_api.router)
        spec = importlib.util.spec_from_file_location('creative_cli', ROOT / 'scripts/creative_tools.py')
        cli = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cli)
        self.assertIs(cli.discover, discovery.discover)
        with TestClient(app) as client:
            response = client.get('/api/creative/workflows?kind=photo')
            self.assertEqual(response.status_code, 200)
            result = response.json()['result']
            self.assertTrue(all(t['kind'] == 'photo' for t in result['tools']))
            self.assertEqual(result, cli.discover('photo'))
            self.assertEqual(client.get('/api/creative/workflows?kind=invalid').status_code, 422)
            candidates = [t for t in result['tools'] if t['id'] == 'photocraft']
            self.assertEqual(candidates[0]['status'], 'review_required')

    def test_mcp_uses_http_and_encodes_kind(self):
        import creative_mcp
        with patch.object(creative_mcp, 'request', return_value={'ok': True}) as request:
            creative_mcp.creative_workflows('photo&other=1')
            request.assert_called_once_with('/api/creative/workflows?kind=photo%26other%3D1')


if __name__ == '__main__':
    unittest.main()
