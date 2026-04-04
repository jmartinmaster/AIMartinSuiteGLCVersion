import PyInstaller.__main__
import os
import shutil
import stat
import subprocess

# Define your project name
APP_NAME = "TheMartinSuite_GLC"


def clean_previous_builds():
    exe_name = f"{APP_NAME}.exe"
    if os.name == "nt":
        subprocess.run(["taskkill", "/F", "/IM", exe_name], check=False, capture_output=True)

    def remove_readonly(_func, path, _exc_info):
        os.chmod(path, stat.S_IWRITE)
        if os.path.isdir(path):
            os.rmdir(path)
        else:
            os.remove(path)

    for folder_name in ("build", "dist"):
        folder_path = os.path.abspath(folder_name)
        if os.path.exists(folder_path):
            shutil.rmtree(folder_path, onexc=remove_readonly)


clean_previous_builds()

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
    '--hidden-import=tkinter.messagebox',
    '--hidden-import=tkinter.filedialog'
])

print(f"\n--- Build Complete! Check dist/{APP_NAME} ---")