"""Versioned brand identity and portable tokens/docs/social-media handoff."""
import copy
import fcntl
import hashlib
import html
import json
import os
from pathlib import Path
import re
import tempfile
import uuid
import zipfile

ROLES = ('primary', 'secondary', 'accent', 'background', 'surface', 'text', 'muted')
PRESETS = {
    'y2k': {'label': 'Y2K · bunt', 'palette': ['#9B5CFF', '#00D9F5', '#FF3EB5', '#111021', '#25213B', '#F9F7FF', '#C3BED8'],
        'display': 'Arial Black, Arial, sans-serif', 'body': 'Arial, sans-serif',
        'description': 'Digitale Jahrtausendwende: kräftige Popfarben, metallische Akzente und weiche futuristische Formen.',
        'imagery': ['Chrom und glänzende Oberflächen als Akzent', 'Sterne, Orbitformen und kräftige Farbfelder', 'Eindeutige Silhouetten auch im kleinen Profilbild'],
        'voice': ['energetisch', 'spielerisch', 'direkt'], 'radius': 24},
    'colorful': {'label': 'Bunt · Pop', 'palette': ['#5738C5', '#F5B700', '#EB3D72', '#FFF8EC', '#FFFFFF', '#242035', '#655D76'],
        'display': 'Arial Black, Arial, sans-serif', 'body': 'Arial, sans-serif',
        'description': 'Lebendige, klare Farbfelder mit wiedererkennbaren Kontrasten und einfachen Formen.',
        'imagery': ['Pro Fläche eine dominante Farbe', 'Grosse einfache Formen mit viel Freiraum', 'Akzentfarbe für wichtige Inhalte'],
        'voice': ['freundlich', 'lebendig', 'verständlich'], 'radius': 16},
    'minimal': {'label': 'Minimal · ruhig', 'palette': ['#245743', '#A6BEB3', '#BE562D', '#F5F4F0', '#FFFFFF', '#202C25', '#59685F'],
        'display': 'Georgia, serif', 'body': 'Arial, sans-serif',
        'description': 'Ruhige Flächen, präzise Typografie und eine sparsam verwendete Akzentfarbe.',
        'imagery': ['Klare Kompositionen und natürliche Texturen', 'Viel Freiraum und ein Fokus pro Layout', 'Zurückhaltende Formen'],
        'voice': ['klar', 'ruhig', 'präzise'], 'radius': 8},
}


def _text(value, field, maximum=2000):
    if not isinstance(value, str) or not value.strip() or len(value) > maximum:
        raise ValueError(f'{field} must be nonempty text, at most {maximum} characters')
    return value.strip()


def _strings(values, field, limit=12):
    if not isinstance(values, list) or not 1 <= len(values) <= limit:
        raise ValueError(f'{field} needs 1..{limit} entries')
    return [_text(value, field, 500) for value in values]


def identity(preset='y2k', name='New brand', brief='', audience='', goal=''):
    if preset not in PRESETS:
        raise ValueError('Unknown brand preset')
    source = PRESETS[preset]
    palette = dict(zip(ROLES, source['palette']))
    brand = {'name': _text(name, 'name', 160), 'accent': palette['accent'], 'identity': {
        'schema_version': 1, 'style': source['label'], 'brief': brief or source['description'],
        'positioning': 'Entwurf: Nutzen und Positionierung anhand des Markenbriefs konkretisieren.',
        'audience': audience or 'Vor Produktion konkretisieren', 'goal': goal or 'Wiedererkennbare Marke und konsistente Inhalte',
        'language': 'de-CH', 'palette': palette,
        'typography': {'display': source['display'], 'body': source['body'], 'scale': [12, 16, 20, 28, 40, 56]},
        'layout': {'spacing_unit': 8, 'radius': source['radius']}, 'imagery': source['imagery'],
        'voice': source['voice'], 'content_pillars': ['Marke und Werte', 'Angebot und Nutzen', 'Prozess und Einblicke'],
        'logo_direction': 'Einfache editierbare Silhouette; für kleine Darstellung und einfarbigen Einsatz prüfen.',
        'do': ['Farben nach Rolle verwenden', 'Schriften und Abstände konsistent halten', 'Lesbarkeit vor Effekten'],
        'dont': ['Alle Akzentfarben gleichzeitig als Text nutzen', 'Kleine Inhalte mit Effekten überladen', 'Unbestätigte Aussagen über Produkte oder Erfolge'],
        'social_media': {'art_direction': source['description'],
            'post_layout': 'Eine klare Überschrift, ein Fokusmotiv und eine kurze Handlung pro Beitrag.',
            'avatar': 'Prägnante Silhouette mit ausreichend Abstand zum runden Beschnitt.',
            'cover': 'Wiederkehrende Typografie, Farbrollen und kurze Titel.'},
        'assumptions': ['Stilrichtung ist ein Entwurf.', 'Zielgruppe, Positionierung und konkrete Plattform vor Produktion bestätigen.', 'Schriften sind CSS-Fallbacks; keine Font-Dateien mitgeliefert.'],
    }}
    return normalize(brand)


def normalize(brand):
    if not isinstance(brand, dict) or not isinstance(brand.get('identity'), dict):
        raise ValueError('A brand identity object is required')
    result = copy.deepcopy(brand)
    result['name'] = _text(result.get('name'), 'name', 160)
    ident = result['identity']
    if type(ident.get('schema_version')) is not int or ident['schema_version'] != 1:
        raise ValueError('Unsupported brand identity version')
    for key in ('style', 'brief', 'positioning', 'audience', 'goal', 'language', 'logo_direction'):
        ident[key] = _text(ident.get(key), key)
    palette = ident.get('palette')
    if not isinstance(palette, dict) or set(palette) != set(ROLES):
        raise ValueError('Palette requires exactly seven semantic color roles')
    for role, color in palette.items():
        if not isinstance(color, str) or not re.fullmatch(r'#[0-9a-fA-F]{6}', color):
            raise ValueError(f'Invalid palette color: {role}')
        palette[role] = color.upper()
    # The existing dashboard accent remains canonical when manually edited.
    accent = result.get('accent', palette['accent'])
    if not isinstance(accent, str) or not re.fullmatch(r'#[0-9a-fA-F]{6}', accent):
        raise ValueError('Invalid brand accent')
    result['accent'] = palette['accent'] = accent.upper()
    typeface = ident.get('typography')
    if not isinstance(typeface, dict):
        raise ValueError('Typography is required')
    for role in ('display', 'body'):
        value = _text(typeface.get(role), 'font', 200)
        if not re.fullmatch(r'[\w\s,\"\'.-]+', value):
            raise ValueError('Font must be a family/fallback stack, not CSS code')
        typeface[role] = value
    scale = typeface.get('scale')
    if not isinstance(scale, list) or not 3 <= len(scale) <= 10 or any(isinstance(n, bool) or not isinstance(n, (int, float)) or not 10 <= n <= 200 for n in scale):
        raise ValueError('Typography scale requires 3..10 sizes between 10 and 200')
    layout = ident.get('layout')
    if not isinstance(layout, dict) or any(isinstance(layout.get(k), bool) or not isinstance(layout.get(k), (int, float)) or not 0 <= layout[k] <= 64 for k in ('spacing_unit', 'radius')):
        raise ValueError('Invalid brand spacing/radius')
    for key in ('imagery', 'voice', 'content_pillars', 'do', 'dont', 'assumptions'):
        ident[key] = _strings(ident.get(key), key)
    social = ident.get('social_media')
    if not isinstance(social, dict):
        raise ValueError('Social media direction is required')
    for key in ('art_direction', 'post_layout', 'avatar', 'cover'):
        social[key] = _text(social.get(key), key)
    if len(json.dumps(result)) > 100_000:
        raise ValueError('Brand identity is too large')
    return result


def contrast(a, b):
    def luminance(color):
        rgb = [int(color[i:i+2], 16) / 255 for i in (1, 3, 5)]
        rgb = [v / 12.92 if v <= .04045 else ((v + .055) / 1.055) ** 2.4 for v in rgb]
        return .2126 * rgb[0] + .7152 * rgb[1] + .0722 * rgb[2]
    first, second = sorted((luminance(a), luminance(b)))
    return (second + .05) / (first + .05)


def tokens(brand):
    brand = normalize(brand); ident = brand['identity']
    palette = ident['palette']
    ink = max(('#000000', '#FFFFFF'), key=lambda color: contrast(color, palette['primary']))
    return {'meta': {'project': brand['name'], 'schema': 'k-creative-brand/1', 'status': 'draft'},
        'primitive': {'color': palette, 'type': ident['typography'], 'space': {'unit': ident['layout']['spacing_unit']}, 'radius': {'default': ident['layout']['radius']}},
        'semantic': {'light': {'background': '{primitive.color.background}', 'surface': '{primitive.color.surface}',
            'text': '{primitive.color.text}', 'textMuted': '{primitive.color.muted}', 'accent': '{primitive.color.accent}'},
            'primary': '{primitive.color.primary}', 'onPrimary': ink},
        'component': {'button': {'background': '{primitive.color.primary}', 'text': ink, 'radius': '{primitive.radius.default}'},
                      'card': {'background': '{primitive.color.surface}', 'radius': '{primitive.radius.default}'}},
        'accessibility': {'text_on_background': round(contrast(palette['text'], palette['background']), 2),
                          'muted_on_background': round(contrast(palette['muted'], palette['background']), 2),
                          'on_primary': round(contrast(ink, palette['primary']), 2)}}


def social_brand(brand, project_id):
    brand = normalize(brand); ident = brand['identity']
    return {'schema_version': 1, 'brand_id': project_id, 'name': brand['name'], 'status': 'draft',
        'audience': ident['audience'], 'goal': ident['goal'], 'language': ident['language'],
        'voice': ident['voice'], 'content_pillars': ident['content_pillars'],
        'visuals': {'colors': list(ident['palette'].values()), 'color_roles': ident['palette'],
            'fonts': [ident['typography']['display'], ident['typography']['body']], 'reference_assets': [],
            'identity_path': '../brand/identity.json', 'tokens_path': '../brand/tokens.json', 'style': ident['style'],
            'art_direction': ident['social_media']},
        'platforms': {'instagram': {'account_id': None, 'connection_status': 'not_connected'}},
        'automation': {'mode': 'drafts-only', 'timezone': 'Europe/Zurich', 'authorization_reference': None}}


def logo_svg(project):
    layers = project.get('layers', [])
    if not layers or any(layer.get('kind') not in ('rect', 'ellipse', 'polygon', 'text') for layer in layers):
        return None
    shapes = []
    for layer in layers:
        color = layer.get('color', '#000000')
        if not isinstance(color, str) or not re.fullmatch(r'#[0-9a-fA-F]{6}', color):
            return None
        x, y = layer.get('x', 0), layer.get('y', 0)
        width, height = layer.get('width', 320), layer.get('height', 180)
        common = f'fill="{color}" opacity="{layer.get("opacity", 1)}"'
        name = html.escape(layer.get('name', 'Layer'))
        if layer['kind'] == 'rect': shape = f'<rect x="{x}" y="{y}" width="{width}" height="{height}" {common}/>'
        elif layer['kind'] == 'ellipse': shape = f'<ellipse cx="{x+width/2}" cy="{y+height/2}" rx="{width/2}" ry="{height/2}" {common}/>'
        elif layer['kind'] == 'polygon':
            points = ' '.join(f'{x+px*width},{y+py*height}' for px, py in layer['points'])
            shape = f'<polygon points="{points}" {common}/>'
        else:
            shape = f'<text x="{x}" y="{y}" dominant-baseline="hanging" font-family="sans-serif" font-size="{max(8,min(height,64))}" {common}>{html.escape(layer.get("text", ""))}</text>'
        shapes.append(f'<g><title>{name}</title>{shape}</g>')
    return f'<svg xmlns="http://www.w3.org/2000/svg" width="{project["width"]}" height="{project["height"]}" viewBox="0 0 {project["width"]} {project["height"]}">' + ''.join(shapes) + '</svg>\n'


def _markdown(brand, token):
    ident = brand['identity']
    lines = [f"# {brand['name']} — Brand identity", '', 'Status: draft. Generated from the native K-Creative project; edit identity.json or import changes back into the dashboard.',
             '', f"Style: {ident['style']}", '', ident['brief'], '', '## Positioning', '', ident['positioning'],
             '', f"Audience: {ident['audience']}", f"Goal: {ident['goal']}", '', '## Color roles', '', '| Role | Hex |', '| --- | --- |']
    lines += [f'| {role} | {color} |' for role, color in ident['palette'].items()]
    lines += ['', '## Typography', '', f"Display: {ident['typography']['display']}", f"Body: {ident['typography']['body']}",
              'Scale: ' + ', '.join(str(n) for n in ident['typography']['scale']), '', 'Font files are not included; family stacks have system fallbacks.',
              '', '## Layout', '', f"Spacing unit: {ident['layout']['spacing_unit']} px; radius: {ident['layout']['radius']} px.", '', '## Logo direction', '', ident['logo_direction']]
    for key, heading in [('imagery', 'Imagery'), ('voice', 'Voice'), ('content_pillars', 'Content pillars'), ('do', 'Do'), ('dont', 'Avoid'), ('assumptions', 'Assumptions to confirm')]:
        lines += ['', '## ' + heading, ''] + ['- ' + value for value in ident[key]]
    lines += ['', '## Contrast measurements', '', json.dumps(token['accessibility'], indent=2), '', 'Ratios are measured for these exact pairs. Small text normally needs 4.5:1; other combinations require separate checks.',
              '', '## Other tools', '', 'Use tokens.json for semantic color/type/layout roles, styles.css for web implementation and social-media/brand.json for content generation. Files never authorize posting, account changes or deployment.']
    return '\n'.join(lines) + '\n'


def export_project_brand(project, output_root):
    base = Path(output_root).resolve() / str(uuid.UUID(project['id']))
    base.mkdir(parents=True, exist_ok=True)
    if not base.resolve().is_relative_to(Path(output_root).resolve()):
        raise ValueError('Brand folder escapes project root')
    with (base / '.export.lock').open('a') as lock:
        fcntl.flock(lock.fileno(), fcntl.LOCK_EX)
        try:
            return _export_locked(project, output_root)
        finally:
            fcntl.flock(lock.fileno(), fcntl.LOCK_UN)


def _export_locked(project, output_root):
    output_root = Path(output_root).resolve()
    brand = normalize(project.get('brand')); token = tokens(brand); ident = brand['identity']
    pid = str(uuid.UUID(project['id']))
    revision = project['revision']
    if isinstance(revision, bool) or not isinstance(revision, int) or revision < 0:
        raise ValueError('Invalid project revision')
    base = Path(output_root) / pid
    base.mkdir(parents=True, exist_ok=True)
    digest = hashlib.sha256(json.dumps(brand, sort_keys=True).encode()).hexdigest()[:12]
    folder = base / f'revision-{revision}-{digest}'
    archive = base / f'brand-{revision}-{digest}.zip'
    if not folder.resolve().is_relative_to(base.resolve()):
        raise ValueError('Brand revision folder escapes project root')
    if folder.exists():
        # Never overwrite edits from other tools. The manifest lists the original snapshot.
        result = json.loads((folder / 'project.json').read_text())
        if not archive.is_file():
            raise ValueError('Existing brand package was modified; create a new project revision before exporting')
        return {'path': str(archive), 'project_dir': str(folder), 'manifest': result, 'reused': True}
    with tempfile.TemporaryDirectory(prefix='.brand-', dir=base) as directory:
        temp = Path(directory)
        (temp / 'brand').mkdir(); (temp / 'social-media/profile').mkdir(parents=True)
        def write(relative, value):
            path = temp / relative
            path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n' if isinstance(value, dict) else value, encoding='utf-8')
        write('brand/identity.json', brand); write('brand/tokens.json', token)
        css = '/* Generated from K-Creative identity.json. Font files are not included. */\n:root {\n'
        css += ''.join(f'  --brand-{role}: {color};\n' for role, color in ident['palette'].items())
        css += f"  --brand-on-primary: {token['semantic']['onPrimary']};\n  --brand-font-display: {ident['typography']['display']};\n  --brand-font-body: {ident['typography']['body']};\n  --brand-space: {ident['layout']['spacing_unit']}px;\n  --brand-radius: {ident['layout']['radius']}px;\n}}\n"
        write('brand/styles.css', css); write('brand/BRAND.md', _markdown(brand, token))
        swatches = ''.join(f'<rect x="{index*160}" width="160" height="120" fill="{color}"/><text x="{index*160+12}" y="150" font-size="14">{html.escape(role)} {color}</text>' for index, (role, color) in enumerate(ident['palette'].items()))
        logo = logo_svg(project)
        if logo: write('brand/logo.svg', logo)
        write('brand/palette.svg', f'<svg xmlns="http://www.w3.org/2000/svg" width="1120" height="180" viewBox="0 0 1120 180">{swatches}</svg>')
        preview = f'''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width"><title>{html.escape(brand['name'])} · Brand preview</title><link rel="stylesheet" href="styles.css"><style>body{{background:var(--brand-background);color:var(--brand-text);font-family:var(--brand-font-body);margin:0;padding:clamp(24px,5vw,64px)}}h1{{font-family:var(--brand-font-display);font-size:clamp(36px,7vw,72px)}}section{{background:var(--brand-surface);padding:24px;border-radius:var(--brand-radius);margin:24px 0}}.swatches{{display:flex;flex-wrap:wrap;gap:12px}}.swatch{{padding:12px;border:1px solid currentColor;border-radius:8px}}.color{{width:100%;height:56px;border-radius:4px}}.cta{{display:inline-block;background:var(--brand-primary);color:var(--brand-on-primary);padding:14px 24px;border-radius:var(--brand-radius)}}small{{color:var(--brand-muted)}}</style><small>Brand identity · draft</small><h1>{html.escape(brand['name'])}</h1><p>{html.escape(ident['style'])}</p><section><h2>Make it recognizable.</h2><p>{html.escape(ident['brief'])}</p><span class="cta">Example primary action</span></section><div class="swatches">'''
        preview += ''.join(f'<div class="swatch"><div class="color" style="background:{color}"></div><p>{role}<br>{color}</p></div>' for role, color in ident['palette'].items())
        preview += '</div><p>See BRAND.md for style, voice and assumptions. This is a visual sample, not a finished campaign or font package.</p></html>'
        write('brand/preview.html', preview)
        social = social_brand(brand, pid)
        if logo:
            social['visuals']['reference_assets'] = ['../brand/logo.svg']
        write('social-media/brand.json', social)
        write('social-media/profile/preview.md', '# Social-media handoff\n\nStatus: draft. Use ../brand.json as the brief and ../../brand/identity.json as the identity source.\n\n' + '\n'.join(f"- {key}: {value}" for key, value in ident['social_media'].items()) + '\n\nConfirm audience, positioning, target platform/account and concrete asset formats before production. No account connected; no publication authorized by this package.\n')
        files = sorted(str(p.relative_to(temp)) for p in temp.rglob('*') if p.is_file())
        manifest = {'schema_version': 1, 'project_id': pid, 'revision': revision, 'brand': brand['name'],
                    'status': 'draft', 'files': files, 'identity_source': 'brand/identity.json',
                    'social_media_brief': 'social-media/brand.json', 'tokens': 'brand/tokens.json'}
        write('project.json', manifest)
        # Preserve shared-workspace access after mkdtemp's private 0700 staging mode.
        temp.chmod(0o2775)
        for file in temp.rglob('*'):
            file.chmod(0o2775 if file.is_dir() else 0o664)
        # A fresh revision directory is published atomically; sources never overwritten.
        if folder.exists():
            raise ValueError('Brand export already exists')
        os.rename(temp, folder)
    with zipfile.ZipFile(archive, 'x', compression=zipfile.ZIP_DEFLATED) as package:
        for file in sorted(folder.rglob('*')):
            if file.is_file(): package.write(file, file.relative_to(folder))
    return {'path': str(archive), 'project_dir': str(folder), 'manifest': manifest, 'reused': False}
