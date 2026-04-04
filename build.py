import PyInstaller.__main__
import os

# Define your project name
APP_NAME = "TheMartinSuite_GLC"

PyInstaller.__main__.run([
    'main.py',
    '--name=%s' % APP_NAME,
    '--noconfirm',
    '--onedir',
    '--windowed',
    # Folders to include
    '--add-data=modules;modules',
    '--add-data=templates;templates',
    # Files to include
    '--add-data=layout_config.json;.',
    '--add-data=rates.json;.',
    # Force include openpyxl
    '--collect-submodules=openpyxl',
    '--hidden-import=openpyxl',
    '--hidden-import=openpyxl.cell.cell',
    # Force include PyInstaller hooks
    '--hidden-import=PyInstaller',
    '--collect-submodules=PyInstaller',
    '--hidden-import=tkinter.messagebox'
])

print(f"\n--- Build Complete! Check dist/{APP_NAME} ---")