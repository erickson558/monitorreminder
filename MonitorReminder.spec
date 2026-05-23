from pathlib import Path

from PyInstaller.utils.hooks import collect_submodules

root = Path(SPECPATH)

hiddenimports = collect_submodules("monitorreminder")

icon_file = root / "network_25845.ico"

a = Analysis(
    ['main.py'],
    pathex=[str(root / 'src')],
    binaries=[],
    datas=[(str(icon_file), '.')],
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)
pyz = PYZ(a.pure)
exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='MonitorReminder',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    icon=str(icon_file),
)
