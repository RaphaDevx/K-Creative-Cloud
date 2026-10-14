# -*- mode: python ; coding: utf-8 -*-
from pathlib import Path
from PyInstaller.utils.hooks import collect_all, collect_submodules

root = Path(SPECPATH)
datas = [(str(root / name), name if (root / name).is_dir() else '.')
         for name in ['index.html', 'live.html', 'static'] if (root / name).exists()]
datas.append((str(root.parent / 'packages/integrations'), 'packages/integrations'))
datas.append((str(root.parent / 'candidates/creative-assistant'), 'candidates/creative-assistant'))
binaries = []
hidden = ['creative_brand', 'creative_assistant', 'creative_assistant_api', 'creative_primitives', 'creative_discovery', 'creative_api', 'creative_media', 'creative_runtime', 'creative_pty', 'creative_agent', 'creative_mcp', 'creative_generators', 'creative_lmms', 'creative_security', 'creative_automation', 'aiofiles',
          'python_multipart', 'multipart', 'anyio._backends._asyncio', 'sqlite3']
for package in ['uvicorn', 'fastapi', 'starlette', 'PIL', 'numpy', 'soundfile',
                'kokoro_onnx', 'onnxruntime', 'phonemizer', 'espeakng_loader', 'mcp']:
    package_datas, package_binaries, package_hidden = collect_all(package, filter_submodules=lambda name: not name.startswith('mcp.cli'))
    datas.extend(package_datas)
    binaries.extend(package_binaries)
    hidden.extend(package_hidden)
# Local dictation is optional, but bundle its native dependencies when installed.
import importlib.util
if importlib.util.find_spec('faster_whisper'):
    for package in ['faster_whisper', 'ctranslate2', 'av', 'tokenizers', 'huggingface_hub']:
        package_datas, package_binaries, package_hidden = collect_all(package)
        datas.extend(package_datas)
        binaries.extend(package_binaries)
        hidden.extend(package_hidden)
a = Analysis([str(root / 'server.py')], pathex=[str(root)], binaries=binaries,
             datas=datas, hiddenimports=hidden, hookspath=[], runtime_hooks=[],
             excludes=['tkinter', 'matplotlib', 'pytest'], noarchive=False)
pyz = PYZ(a.pure)
exe = EXE(pyz, a.scripts, a.binaries, a.datas, [], name='k-creative-server',
          debug=False, bootloader_ignore_signals=False, strip=False, upx=False,
          runtime_tmpdir=None, console=True, disable_windowed_traceback=False,
          target_arch=None, codesign_identity=None, entitlements_file=None)
