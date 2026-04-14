# Decoupling Layout Manager (Branch 2 Instructions)

This guide explains how to decouple the **Layout Manager** from the main application shell and run it as a standalone program. This process ensures `layout_config.json` remains centrally managed while removing the UI from the primary sidebar.

## 1. Prerequisites
In **Branch 2**, module management is centralized. You will need to interact with the following components:
- `app/module_registry.json`: The source of truth for app navigation.
- `app/app_identity.py`: Used for consistent branding.
- `app/controllers/layout_manager_controller.py`: The core logic.

## 2. Unregistering from the Main Shell
To remove the Layout Manager from the sidebar and dispatcher logic:
1. Open `app/module_registry.json`.
2. Locate the object with `"name": "layout_manager"`.
3. Set `"navigation_visible": false` and `"launcher_visible": false`.
4. (Optional) Remove the entry entirely to fully decouple it from the registry.

## 3. Creating the Standalone Launcher
Create a file named `layout_editor.py` in the project root. This script mocks a minimal dispatcher to satisfy the controller's requirements.

```python
import ttkbootstrap as tb
from app.controllers.layout_manager_controller import LayoutManagerController
from app.app_identity import AppIdentity
from app.theme_manager import resolve_base_theme

class StandaloneDispatcher:
    def __init__(self, root):
        self.root = root
        self.identity = AppIdentity()
    
    def get_setting(self, key, default=None):
        # Default settings for standalone mode
        settings = {"toast_duration_sec": 3}
        return settings.get(key, default)

    def show_toast(self, title, message, bootstyle="info"):
        # Simple print or custom popup since the main Toast system 
        # is tied to the full ShellView
        print(f"[{title}] {message}")

if __name__ == "__main__":
    identity = AppIdentity()
    root = tb.Window(
        title=f"{identity.name} - Layout Editor",
        themename=resolve_base_theme("cosmo")
    )
    root.geometry("1100x800")
    
    dispatcher = StandaloneDispatcher(root)
    # The controller logic remains unchanged and handles the MVC setup
    app = LayoutManagerController(root, dispatcher)
    
    root.mainloop()
```

## 4. Launching from the Primary App
To call this standalone program from the main suite, add this to your `AppController` or a menu action:

```python
import subprocess
import sys
import os

def launch_layout_editor(self):
    script_path = os.path.join(os.getcwd(), "layout_editor.py")
    subprocess.Popen([sys.executable, script_path])
```

## 5. File Persistence
The `LayoutManagerModel` uses relative pathing for `layout_config.json`. As long as the standalone script is executed from the root directory, it will read and write to the exact same file used by the `production_log` module.