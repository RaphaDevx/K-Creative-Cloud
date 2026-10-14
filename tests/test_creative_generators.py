"""Independent ComfyUI HTTP fixture: no model installation required."""
import io
import json
from pathlib import Path
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'studio'))
import creative_generators as generators


@pytest.fixture
def provider(monkeypatch):
    stream = io.BytesIO()
    Image.new('RGB', (16, 16), 'purple').save(stream, format='PNG')
    state = {'png': stream.getvalue(), 'mode': 'success', 'graphs': [], 'polls': 0}

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def reply(self, payload, status=200):
            data = json.dumps(payload).encode()
            self.send_response(status)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(data)

        def do_POST(self):
            graph = json.loads(self.rfile.read(int(self.headers['Content-Length'])))
            state['graphs'].append(graph['prompt'])
            if state['mode'] == 'reject':
                return self.reply({'node_errors': {'1': {'errors': ['checkpoint missing']}}})
            self.reply({'prompt_id': 'mock-prompt'})

        def do_GET(self):
            if self.path == '/system_stats':
                return self.reply({'system': {'os': 'test'}})
            if self.path == '/object_info/CheckpointLoaderSimple':
                if state['mode'] == 'missing-schema':
                    return self.reply({'error': 'schema not found'}, 404)
                if state['mode'] == 'no-models':
                    return self.reply({'CheckpointLoaderSimple': {'input': {'required': {'ckpt_name': [[]]}}}})
                return self.reply({'CheckpointLoaderSimple': {'input': {'required': {'ckpt_name': [['test.safetensors']]}}}})
            if self.path.startswith('/history/'):
                state['polls'] += 1
                if state['mode'] == 'timeout' or state['polls'] == 1:
                    return self.reply({})
                if state['mode'] == 'error':
                    return self.reply({'mock-prompt': {'status': {'status_str': 'error', 'messages': [['execution_error', {'exception_message': 'out of memory'}]]}}})
                filename = '../escape.png' if state['mode'] == 'traversal' else 'image.png'
                return self.reply({'mock-prompt': {'status': {'completed': True}, 'outputs': {'7': {'images': [{'filename': filename, 'subfolder': '', 'type': 'output'}]}}}})
            if self.path.startswith('/view?'):
                self.send_response(200)
                self.end_headers()
                self.wfile.write(b'not an image' if state['mode'] == 'corrupt' else state['png'])
                return
            self.reply({'error': 'not found'}, 404)

    server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    monkeypatch.setenv('K_CREATIVE_COMFY_URL', f'http://127.0.0.1:{server.server_port}')
    monkeypatch.delenv('K_CREATIVE_COMFY_CHECKPOINT', raising=False)
    monkeypatch.setattr(generators, 'POLL_INTERVAL', .005)
    yield state
    server.shutdown()
    server.server_close()
    thread.join()


def test_capabilities_reports_installed_models(provider):
    capabilities = generators.capabilities()
    assert capabilities['available'] and capabilities['image'] and capabilities['workflow']
    assert capabilities['checkpoints'] == ['test.safetensors']
    assert capabilities['video'] is False


def test_image_graph_and_real_png_preserved(provider, tmp_path):
    result = generators.generate_image('A new cartoon character', tmp_path, negative='blur', seed=9, width=512, height=768, steps=12)
    assert Path(result['path']).read_bytes() == provider['png']
    assert result['provider'] == 'comfyui' and result['prompt_id'] == 'mock-prompt'
    assert provider['polls'] >= 2
    graph = provider['graphs'][0]
    assert graph['1']['inputs']['ckpt_name'] == 'test.safetensors'
    assert graph['2']['inputs']['text'] == 'A new cartoon character'
    assert graph['3']['inputs']['text'] == 'blur'
    assert graph['4']['inputs'] == {'width': 512, 'height': 768, 'batch_size': 1}
    assert graph['5']['inputs']['seed'] == 9 and graph['5']['inputs']['steps'] == 12
    assert graph['6']['inputs']['vae'] == ['1', 2]


def test_generic_workflow(provider, tmp_path):
    graph = {'7': {'class_type': 'SaveImage', 'inputs': {'images': ['6', 0]}}}
    result = generators.generate_workflow(graph, tmp_path)
    assert provider['graphs'] == [graph]
    with Image.open(result['path']) as image:
        assert image.size == (16, 16)


@pytest.mark.parametrize('graph', [{}, [], {'1': {}}, {'1': {'class_type': 'X', 'inputs': []}},
                                    {str(i): {'class_type': 'X', 'inputs': {}} for i in range(101)},
                                    {'1': {'class_type': 'X', 'inputs': {'value': float('nan')}}}])
def test_invalid_graph_rejected_before_network(provider, tmp_path, graph):
    with pytest.raises(ValueError):
        generators.generate_workflow(graph, tmp_path)
    assert provider['graphs'] == []


@pytest.mark.parametrize('params', [{'prompt': ''}, {'width': 65}, {'height': 4096},
                                     {'steps': 101}, {'seed': -1}, {'seed': True}])
def test_invalid_image_params_rejected(provider, tmp_path, params):
    values = {'prompt': 'Character'}
    values.update(params)
    with pytest.raises(ValueError):
        generators.generate_image(output_dir=tmp_path, **values)
    assert provider['graphs'] == []


@pytest.mark.parametrize('mode,match', [('reject', 'rejected'), ('error', 'out of memory'),
                                       ('corrupt', 'invalid image'), ('traversal', 'unsafe filename')])
def test_provider_errors_preserve_no_partial_assets(provider, tmp_path, mode, match):
    provider['mode'] = mode
    with pytest.raises(RuntimeError, match=match):
        generators.generate_image('Character', tmp_path)
    assert list(tmp_path.iterdir()) == []


def test_polling_deadline(provider, tmp_path, monkeypatch):
    provider['mode'] = 'timeout'
    monkeypatch.setattr(generators, 'POLL_TIMEOUT', .025)
    with pytest.raises(RuntimeError, match='timed out'):
        generators.generate_image('Character', tmp_path)


def test_unavailable_provider_and_unsafe_configuration(monkeypatch, tmp_path):
    monkeypatch.setenv('K_CREATIVE_COMFY_URL', 'http://127.0.0.1:1')
    assert generators.capabilities()['available'] is False
    with pytest.raises(RuntimeError, match='request failed'):
        generators.generate_image('Character', tmp_path)
    monkeypatch.setenv('K_CREATIVE_COMFY_URL', 'file:///etc/passwd')
    assert generators.capabilities()['available'] is False
    with pytest.raises(ValueError, match='HTTP'):
        generators.generate_workflow({'1': {'class_type': 'X', 'inputs': {}}}, tmp_path)


def test_no_models_are_not_reported_as_image_capability(provider, tmp_path):
    provider['mode'] = 'no-models'
    capabilities = generators.capabilities()
    assert capabilities['available'] and capabilities['workflow']
    assert capabilities['image'] is False
    with pytest.raises(RuntimeError, match='no installed checkpoints'):
        generators.generate_image('Character', tmp_path)


def test_explicit_checkpoint_configuration_fallback(provider, tmp_path, monkeypatch):
    provider['mode'] = 'missing-schema'
    monkeypatch.setenv('K_CREATIVE_COMFY_CHECKPOINT', 'configured.safetensors')
    assert generators.capabilities()['checkpoints'] == ['configured.safetensors']
    generators.generate_image('Character', tmp_path)
    assert provider['graphs'][0]['1']['inputs']['ckpt_name'] == 'configured.safetensors'
