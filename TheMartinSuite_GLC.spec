# -*- mode: python ; coding: utf-8 -*-
# Production Logging Center (GLC Edition)
# Copyright (C) 2026 Jamie Martin
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

from PyInstaller.utils.hooks import collect_submodules

from app.app_identity import format_versioned_exe_stem, load_version_from_main

hiddenimports = ['openpyxl', 'openpyxl.cell.cell', 'PyInstaller', 'tkinter.messagebox', 'tkinter.filedialog']
hiddenimports += collect_submodules('openpyxl')
hiddenimports += collect_submodules('PyInstaller')
hiddenimports += collect_submodules('app')

datas = [('app', 'app'), ('assets', 'assets'), ('docs', 'docs'), ('templates', 'templates'), ('layout_config.json', '.'), ('rates.json', '.')]
app_build_name = format_versioned_exe_stem(load_version_from_main())


a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
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
    a.binaries,
    a.datas,
    [],
    name=app_build_name,
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=['assets/icons/icon.ico'],
)
