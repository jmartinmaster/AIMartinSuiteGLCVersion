# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_submodules

hiddenimports = ['openpyxl', 'openpyxl.cell.cell', 'PyInstaller', 'tkinter.messagebox', 'tkinter.filedialog']
hiddenimports += collect_submodules('openpyxl')
hiddenimports += collect_submodules('PyInstaller')
hiddenimports += collect_submodules('app')


a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=[('app', 'app'), ('assets', 'assets'), ('docs', 'docs'), ('templates', 'templates'), ('layout_config.json', '.'), ('rates.json', '.')],
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
    name='Production Logging Center_GLC_v2.0.4',
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
    icon=['assets/icons/icon.ico'],
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='Production Logging Center_GLC_v2.0.4',
)
