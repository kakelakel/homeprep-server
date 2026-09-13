from pathlib import Path

root = Path.cwd()

block_cipher = None

a = Analysis(
    [str(root / "src" / "homeprep_server" / "launcher.py")],
    pathex=[str(root / "src")],
    binaries=[],
    datas=[
        (str(root / "web" / "dist"), "web/dist"),
        (str(root / "migrations"), "migrations"),
        (str(root / "alembic.ini"), "."),
    ],
    hiddenimports=[
        "uvicorn.logging",
        "uvicorn.loops.auto",
        "uvicorn.protocols.http.auto",
        "uvicorn.protocols.websockets.auto",
        "uvicorn.lifespan.on",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="HomePrepServer",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
