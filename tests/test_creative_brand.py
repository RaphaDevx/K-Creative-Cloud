"""Brand identity portability, source preservation and shared social-media contract."""
import copy
import json
from pathlib import Path
import sys
import uuid
import zipfile

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'studio'))
from creative_brand import identity, normalize, tokens, social_brand, export_project_brand, PRESETS
from test_creative_assistant import client, command, wait
import creative_assistant as assistant


@pytest.mark.parametrize('style', list(PRESETS))
def test_presets_have_semantic_tokens_and_measured_contrast(style):
    brand = identity(style, 'Example Studio')
    result = tokens(brand)
    assert len(brand['identity']['palette']) == 7
    assert result['semantic']['light']['text'] == '{primitive.color.text}'
    assert result['component']['button']['background'] == '{primitive.color.primary}'
    assert result['accessibility']['text_on_background'] >= 4.5
    assert result['accessibility']['on_primary'] >= 4.5
    assert social_brand(brand, 'example')['automation']['mode'] == 'drafts-only'


@pytest.mark.parametrize('invalid', ['color', 'font-code', 'empty-voice', 'wrong-version'])
def test_identity_validation_rejects_broken_handoffs(invalid):
    brand = identity()
    if invalid == 'color': brand['identity']['palette']['text'] = 'red;}'
    elif invalid == 'font-code': brand['identity']['typography']['body'] = 'Arial; color:red'
    elif invalid == 'empty-voice': brand['identity']['voice'] = []
    else: brand['identity']['schema_version'] = True
    with pytest.raises(ValueError): normalize(brand)


def test_portable_package_handoff_preserves_existing_tool_edits(tmp_path):
    project = {'id': str(uuid.uuid4()), 'name': 'Studio', 'revision': 4, 'brand': identity('y2k', 'Studio')}
    result = export_project_brand(project, tmp_path)
    folder = Path(result['project_dir'])
    social = json.loads((folder / 'social-media/brand.json').read_text())
    assert social['name'] == 'Studio' and social['platforms']['instagram']['account_id'] is None
    assert (folder / 'social-media' / social['visuals']['tokens_path']).is_file()
    assert social['visuals']['color_roles'] == project['brand']['identity']['palette']
    assert (folder / 'brand/preview.html').is_file()
    assert folder.stat().st_mode & 0o070 == 0o070
    assert (folder / 'brand/identity.json').stat().st_mode & 0o060 == 0o060
    with zipfile.ZipFile(result['path']) as archive:
        assert 'brand/identity.json' in archive.namelist() and 'social-media/brand.json' in archive.namelist()
    guide = folder / 'brand/BRAND.md'
    guide.write_text('External tool notes')
    second = export_project_brand(project, tmp_path)
    assert second['reused'] and guide.read_text() == 'External tool notes'
    project['revision'] += 1
    project['brand']['name'] = 'New name'
    third = export_project_brand(project, tmp_path)
    assert third['project_dir'] != result['project_dir']
    assert guide.read_text() == 'External tool notes'


def test_preview_escapes_brand_text(tmp_path):
    project = {'id': str(uuid.uuid4()), 'revision': 0, 'brand': identity(name='<script>alert(1)</script>')}
    folder = Path(export_project_brand(project, tmp_path)['project_dir'])
    preview = (folder / 'brand/preview.html').read_text()
    assert '<script>alert(1)</script>' not in preview
    assert '&lt;script&gt;' in preview


def test_brand_create_edit_import_undo_and_export(client, monkeypatch, tmp_path):
    import creative_api as api
    monkeypatch.setattr(api, 'DATA', tmp_path)
    project = command(client, 'project.create', {'name': 'Pop Shop'})
    response = client.post('/api/creative/brand/create', json={'project_id': project['id'], 'preset': 'y2k', 'brief': 'Ich will bunt und Y2K'})
    assert response.status_code == 200
    branded = response.json()['result']
    assert branded['brand']['identity']['style'] == 'Y2K · bunt'
    assert branded['revision'] == 1
    changed = copy.deepcopy(branded['brand'])
    changed['identity']['palette']['secondary'] = '#F0A000'
    imported = client.post('/api/creative/brand/import', json={'project_id': project['id'], 'expected_revision': 1, 'brand': changed})
    assert imported.status_code == 200
    assert imported.json()['result']['brand']['identity']['palette']['secondary'] == '#F0A000'
    assert client.post('/api/creative/brand/import', json={'project_id': project['id'], 'expected_revision': 1, 'brand': changed}).status_code == 422
    result = wait(client, client.post('/api/creative/brand/export', json={'project_id': project['id']}).json())
    assert result['status'] == 'completed', result
    assert Path(result['details']['project_dir'], 'social-media/brand.json').is_file()
    undone = command(client, 'history.undo', pid=project['id'])
    assert undone['brand']['identity']['palette']['secondary'] == branded['brand']['identity']['palette']['secondary']


def test_local_language_brand_request_uses_shared_native_action(client):
    catalog = command(client, 'system.actions')
    project = command(client, 'project.create', {'name': 'Y2K Studio'})
    plan = assistant.plan('builtin', 'Ich will eine bunte Y2K Brand identity.', project, catalog)
    assert plan['kind'] == 'edit' and plan['commands'][0]['action'] == 'brand.update'
    assert plan['commands'][0]['params']['brand']['identity']['style'] == 'Y2K · bunt'


def test_vector_logo_is_portable_and_referenced(tmp_path):
    import xml.etree.ElementTree as ET
    project = {'id': str(uuid.uuid4()), 'revision': 2, 'width': 200, 'height': 120,
        'brand': identity(name='Vector Studio'), 'layers': [{'kind': 'polygon', 'name': 'Peak',
        'points': [[0, 1], [.5, 0], [1, 1]], 'x': 10, 'y': 10, 'width': 100, 'height': 100, 'color': '#FF0000'}]}
    result = export_project_brand(project, tmp_path)
    folder = Path(result['project_dir'])
    root = ET.fromstring((folder / 'brand/logo.svg').read_text())
    polygon = root.find('.//{http://www.w3.org/2000/svg}polygon')
    assert polygon.attrib['points'] == '10,110 60.0,10 110,110'
    brief = json.loads((folder / 'social-media/brand.json').read_text())
    assert (folder / 'social-media' / brief['visuals']['reference_assets'][0]).is_file()
