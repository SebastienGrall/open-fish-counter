# -*- mode: python ; coding: utf-8 -*-

from pathlib import Path

from PyInstaller.utils.hooks import collect_all


SPEC_DIRECTORY = Path(SPECPATH).resolve()

PROJECT_ROOT = (
    SPEC_DIRECTORY
    .parent
    .parent
)

SOURCE_DIRECTORY = (
    PROJECT_ROOT
    / "src"
)

MAIN_SCRIPT = (
    SOURCE_DIRECTORY
    / "main.py"
)


datas = []
binaries = []
hiddenimports = []


imagingcontrol4_data = collect_all(
    "imagingcontrol4"
)

datas += imagingcontrol4_data[0]
binaries += imagingcontrol4_data[1]
hiddenimports += imagingcontrol4_data[2]


opencv_data = collect_all(
    "cv2"
)

datas += opencv_data[0]
binaries += opencv_data[1]
hiddenimports += opencv_data[2]


a = Analysis(
    [str(MAIN_SCRIPT)],
    pathex=[
        str(SOURCE_DIRECTORY),
    ],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)

pyz = PYZ(
    a.pure
)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="OpenFishCounter",
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

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="OpenFishCounter",
)