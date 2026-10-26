# -*- mode: python ; coding: utf-8 -*-

from pathlib import Path
from PyInstaller.utils.hooks import collect_all

SPEC_DIRECTORY = Path(SPECPATH).resolve()
PROJECT_ROOT = SPEC_DIRECTORY.parent.parent
SOURCE_DIRECTORY = PROJECT_ROOT / "src"
MAIN_SCRIPT = SOURCE_DIRECTORY / "main.py"
APP_ICON_PNG = PROJECT_ROOT / "assets" / "icons" / "open-fish-counter-512.png"

binaries = []
datas = [
    (str(APP_ICON_PNG), "assets/icons"),
]
hiddenimports = []

for package_name in ("imagingcontrol4", "cv2"):
    package_datas, package_binaries, package_hiddenimports = collect_all(
        package_name
    )
    datas += package_datas
    binaries += package_binaries
    hiddenimports += package_hiddenimports

a = Analysis(
    [str(MAIN_SCRIPT)],
    pathex=[str(SOURCE_DIRECTORY)],
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

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="OpenFishCounter",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    name="OpenFishCounter",
)
