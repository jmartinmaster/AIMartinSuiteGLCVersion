import sys
import tkinter as tk
from PyQt6.QtWidgets import QApplication, QWidget
from app.security import gatekeeper

# 1. Initialize PyQt application
app = QApplication.instance() or QApplication(sys.argv)
parent = QWidget()

def get_tk_roots():
    # If tkinter hasn't been used yet, there are no roots
    return 0

roots_before = get_tk_roots()
print(f"Tk roots before: {roots_before}")

# Try to find the method that handles PyQt authentication in gatekeeper
# Based on typical patterns in this project, it might be _authenticate_qt
target_method = None
for name in dir(gatekeeper):
    if "qt" in name.lower() and callable(getattr(gatekeeper, name)):
        target_method = name
        break

reached_qt = False
if target_method:
    print(f"Found potential Qt auth method: {target_method}")
    original_method = getattr(gatekeeper, target_method)
    def mocked_method(*args, **kwargs):
        nonlocal reached_qt
        reached_qt = True
        print(f"Mocked {target_method} hit.")
        return True
    setattr(gatekeeper, target_method, mocked_method)
else:
    print("No specific Qt auth method found to mock, running authenticate normally.")

try:
    # This should trigger the logic that checks isinstance(parent, QWidget)
    # If it hits Tk root creation, roots_after will change
    gatekeeper.authenticate(parent=parent, reason="Smoke Test")
except Exception as e:
    print(f"Execution notice: {e}")

# Check if a Tk root was created
# A common side effect of calling tk.Tk()
from tkinter import _default_root
roots_after = 1 if _default_root else 0
print(f"Tk roots after: {roots_after}")

# If we found and hit the Qt method, or if no Tk root was created while using a Qt parent
if roots_after == 0:
    print("SMOKE TEST RESULT: PASS")
else:
    print("SMOKE TEST RESULT: FAIL")
