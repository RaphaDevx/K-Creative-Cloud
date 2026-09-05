# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec — K-DAW backend server
Bundles web_server.py + all deps + web UI into a single folder binary (kdaw-server/).

Build:
    cd K-DAW/backend
    pyinstaller server.spec --noconfirm
"""

import sys
from pathlib import Path

block_cipher = None
HERE = Path(SPECPATH)   # K-DAW/backend/

a = Analysis(
    [str(HERE / 'web_server.py')],
    pathex=[str(HERE)],
    binaries=[],
    datas=[
        # Bundle the web UI so the server can serve index.html
        (str(HERE.parent / 'web'), 'web'),
    ],
    hiddenimports=[
        # uvicorn internals not auto-detected
        'uvicorn.logging',
        'uvicorn.loops',
        'uvicorn.loops.auto',
        'uvicorn.loops.asyncio',
        'uvicorn.protocols',
        'uvicorn.protocols.http',
        'uvicorn.protocols.http.auto',
        'uvicorn.protocols.http.h11_impl',
        'uvicorn.protocols.websockets',
        'uvicorn.protocols.websockets.auto',
        'uvicorn.protocols.websockets.websockets_impl',
        'uvicorn.lifespan',
        'uvicorn.lifespan.on',
        # FastAPI / Starlette
        'starlette.routing',
        'starlette.responses',
        'starlette.staticfiles',
        'starlette.middleware',
        'starlette.websockets',
        'fastapi.routing',
        # anyio backends
        'anyio._backends._asyncio',
        'anyio._backends._trio',
        # HTTP
        'h11',
        'httptools',
        'websockets',
        'websockets.legacy',
        'websockets.legacy.server',
        # Anthropic SDK
        'anthropic',
        'anthropic._client',
        # Other
        'midiutil',
        'multipart',
        'email.mime.text',
        'email.mime.multipart',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        # Not needed in the app bundle
        'librosa', 'numpy', 'scipy', 'matplotlib',
        'tkinter', 'test', 'unittest',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

# One-folder build (faster startup than --onefile, easier to inspect)
exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='kdaw-server',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=True,       # keep True so logs show up during dev / crash diagnosis
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name='kdaw-server',
)
