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
import datetime
import os
import platform
import subprocess
import sys
import traceback

# PyQt6 Imports
try:
    from PyQt6.QtCore import Qt
    from PyQt6.QtWidgets import (
        QApplication,
        QDialog,
        QHBoxLayout,
        QLabel,
        QPushButton,
        QStyle,
        QTextEdit,
        QVBoxLayout,
    )

    from app.theme_manager import (
        DEFAULT_THEME,
        get_qt_palette,
        get_qt_stylesheet,
        normalize_theme,
    )

    PYQT6_AVAILABLE = True
except ImportError:
    PYQT6_AVAILABLE = False
    DEFAULT_THEME = "martin_modern_light"

__module_name__ = "Crash Handler"
__version__ = "1.0.0"


def get_latest_crash_path():
    try:
        from app.utils import external_data_path

        return os.path.join(external_data_path(), "latest_crash.txt")
    except Exception:
        return os.path.abspath("latest_crash.txt")


def get_file_mtime(path):
    try:
        if os.path.exists(path):
            return os.path.getmtime(path)
    except Exception:
        pass
    return 0.0


def generate_crash_report(exctype, value, tb):
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    formatted_tb = (
        "".join(traceback.format_exception(exctype, value, tb))
        if tb
        else "No stack trace available."
    )

    # Try to load app version
    try:
        from launcher import __version__ as app_version
    except Exception:
        app_version = "Unknown"

    report = f"""======================================================================
PRODUCTION LOGGING CENTER (GLC Edition) - CRASH REPORT
======================================================================
Time:         {timestamp}
App Version:  {app_version}
Python:       {sys.version}
Platform:     {platform.platform()}
Architecture: {platform.machine()}
Process ID:   {os.getpid()}
----------------------------------------------------------------------
Exception Type:  {exctype.__name__ if hasattr(exctype, '__name__') else str(exctype)}
Exception Value: {str(value)}
----------------------------------------------------------------------
Stack Trace:
{formatted_tb}
======================================================================
"""
    return report, formatted_tb


def save_crash_report(report):
    try:
        from app.utils import ensure_external_data_directory

        crashes_dir = ensure_external_data_directory("crashes")
        timestamp_str = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        report_filename = f"crash_{timestamp_str}.txt"
        report_path = os.path.join(crashes_dir, report_filename)

        # Write timestamped report
        with open(report_path, "w", encoding="utf-8") as f:
            f.write(report)

        # Also write to a "latest_crash.txt" in the data/ directory for easy access
        latest_path = get_latest_crash_path()
        try:
            os.makedirs(os.path.dirname(latest_path), exist_ok=True)
            with open(latest_path, "w", encoding="utf-8") as f:
                f.write(report)
        except Exception:
            pass

        return report_path
    except Exception as e:
        # Fallback to current working directory if app data directory fails
        try:
            fallback_filename = f"crash_report_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
            fallback_path = os.path.abspath(fallback_filename)
            with open(fallback_path, "w", encoding="utf-8") as f:
                f.write(report)
            return fallback_path
        except Exception:
            return None


def fallback_message_box(crash_log_path, traceback_text):
    message = (
        f"Production Logging Center has crashed.\n\n"
        f"A crash report has been saved to:\n{crash_log_path}\n\n"
        f"Would you like to relaunch the program?"
    )
    title = "Application Crash Detected"

    if sys.platform == "win32":
        try:
            import ctypes

            # MB_YESNO = 4, MB_ICONERROR = 0x10, IDYES = 6
            res = ctypes.windll.user32.MessageBoxW(
                0, message, title, 0x00000004 | 0x00000010
            )
            return res == 6
        except Exception:
            pass

    # Simple console fallback or input fallback
    print("\n" + "=" * 50)
    print("CRASH DETAILS")
    print(message)
    print("=" * 50 + "\n")
    try:
        ans = input("Relaunch the program? (y/n): ").strip().lower()
        return ans in ("y", "yes")
    except Exception:
        return False


if PYQT6_AVAILABLE:

    class CrashReportDialog(QDialog):

        def __init__(self, crash_log_path, traceback_text, theme_name=DEFAULT_THEME):
            super().__init__()
            self.setWindowTitle("Application Crash Detected")
            self.resize(600, 450)
            self.setMinimumSize(500, 350)

            # Apply window flags (minimize/maximize buttons)
            self.setWindowFlags(
                self.windowFlags() | Qt.WindowType.WindowMinimizeButtonHint
            )

            # Set theme
            try:
                self.setStyleSheet(get_qt_stylesheet(theme_name=theme_name))
                self.setPalette(get_qt_palette(theme_name=theme_name))
            except Exception:
                pass

            # Main layout
            layout = QVBoxLayout(self)
            layout.setContentsMargins(20, 20, 20, 20)
            layout.setSpacing(15)

            # Header layout (Icon + Text)
            header_layout = QHBoxLayout()
            header_layout.setSpacing(15)

            # Icon
            icon_label = QLabel()
            try:
                standard_icon = self.style().standardIcon(
                    QStyle.StandardPixmap.SP_MessageBoxCritical
                )
                icon_label.setPixmap(standard_icon.pixmap(48, 48))
            except Exception:
                pass
            header_layout.addWidget(icon_label)

            # Friendly Message
            message_layout = QVBoxLayout()
            title_label = QLabel("An unexpected error occurred")
            title_label.setObjectName("pageTitle")
            title_label.setStyleSheet("font-size: 14pt; font-weight: bold;")

            desc_label = QLabel(
                "Production Logging Center has crashed. A detailed crash report has been generated and saved to help diagnose the issue."
            )
            desc_label.setWordWrap(True)

            message_layout.addWidget(title_label)
            message_layout.addWidget(desc_label)
            header_layout.addLayout(message_layout)
            header_layout.setStretch(1, 1)

            layout.addLayout(header_layout)

            # Crash File Location Info
            file_info_layout = QVBoxLayout()
            file_info_layout.setSpacing(5)

            file_label = QLabel("Crash report saved to:")
            file_label.setStyleSheet("font-weight: bold;")

            file_path_display = QTextEdit()
            file_path_display.setReadOnly(True)
            file_path_display.setText(crash_log_path)
            file_path_display.setMaximumHeight(45)
            file_path_display.setVerticalScrollBarPolicy(
                Qt.ScrollBarPolicy.ScrollBarAlwaysOff
            )
            file_path_display.setHorizontalScrollBarPolicy(
                Qt.ScrollBarPolicy.ScrollBarAsNeeded
            )

            file_info_layout.addWidget(file_label)
            file_info_layout.addWidget(file_path_display)
            layout.addLayout(file_info_layout)

            # Stack Trace Expandable Detail
            trace_label = QLabel("Error details:")
            trace_label.setStyleSheet("font-weight: bold;")
            layout.addWidget(trace_label)

            self.trace_display = QTextEdit()
            self.trace_display.setReadOnly(True)
            self.trace_display.setPlainText(traceback_text)
            self.trace_display.setStyleSheet(
                "font-family: Consolas, Monaco, monospace; font-size: 9pt;"
            )
            layout.addWidget(self.trace_display)

            # Buttons layout
            button_layout = QHBoxLayout()
            button_layout.addStretch(1)

            self.relaunch_btn = QPushButton("Relaunch Program")
            self.relaunch_btn.setStyleSheet("font-weight: bold; padding: 8px 20px;")
            self.relaunch_btn.clicked.connect(self.accept)
            button_layout.addWidget(self.relaunch_btn)

            self.close_btn = QPushButton("Close")
            self.close_btn.setStyleSheet("padding: 8px 20px;")
            self.close_btn.clicked.connect(self.reject)
            button_layout.addWidget(self.close_btn)

            layout.addLayout(button_layout)

else:
    CrashReportDialog = None


def get_user_theme():
    try:
        from app.external_data_registry import ExternalDataRegistry
        from app.theme_manager import DEFAULT_THEME, normalize_theme

        data_registry = ExternalDataRegistry()
        settings_path = data_registry.resolve_read_path("settings")
        if os.path.exists(settings_path):
            with open(settings_path, "r", encoding="utf-8") as handle:
                import json

                settings_payload = json.load(handle)
                if isinstance(settings_payload, dict):
                    return normalize_theme(
                        settings_payload.get("theme", DEFAULT_THEME)
                    )
    except Exception:
        pass
    return "martin_modern_light"


def show_crash_dialog_in_parent(crash_log_path, traceback_text):
    if not PYQT6_AVAILABLE:
        return fallback_message_box(crash_log_path, traceback_text)

    try:
        app = QApplication.instance()
        created_app = False
        if app is None:
            app = QApplication([sys.argv[0]])
            created_app = True

        theme_name = get_user_theme()
        dialog = CrashReportDialog(
            crash_log_path, traceback_text, theme_name=theme_name
        )
        result = dialog.exec()

        if created_app:
            app.quit()

        return result == QDialog.DialogCode.Accepted
    except Exception as e:
        print(
            f"Failed to display PyQt6 styled crash dialog: {e}", file=sys.stderr
        )
        return fallback_message_box(crash_log_path, traceback_text)


def run_monitor_loop():
    if os.environ.get("AIMARTIN_CHILD_PROCESS") == "1":
        return

    latest_crash_path = get_latest_crash_path()

    while True:
        initial_mtime = get_file_mtime(latest_crash_path)

        # Prepare subprocess env
        env = os.environ.copy()
        env["AIMARTIN_CHILD_PROCESS"] = "1"

        # Arguments to launch the child process
        if getattr(sys, "frozen", False):
            args = [sys.executable] + sys.argv[1:]
        else:
            args = [sys.executable] + sys.argv

        # Spawn child process
        try:
            process = subprocess.Popen(args, env=env)
            exit_code = process.wait()
        except Exception as e:
            # Subprocess failed to launch at all
            exit_code = -1
            report, traceback_text = generate_crash_report(
                RuntimeError, f"Failed to launch application process: {e}", None
            )
            crash_log_path = save_crash_report(report)
            relaunch = show_crash_dialog_in_parent(
                crash_log_path, traceback_text
            )
            if relaunch:
                continue
            else:
                break

        # Normal exit
        if exit_code == 0:
            sys.exit(0)

        # Abnormal exit / crash
        new_mtime = get_file_mtime(latest_crash_path)
        if new_mtime != initial_mtime and os.path.exists(latest_crash_path):
            crash_log_path = latest_crash_path
            try:
                with open(latest_crash_path, "r", encoding="utf-8") as f:
                    crash_content = f.read()

                # Parse traceback
                traceback_text = ""
                if "Stack Trace:" in crash_content:
                    parts = crash_content.split("Stack Trace:")
                    if len(parts) > 1:
                        traceback_text = (
                            parts[1]
                            .split(
                                "======================================================================"
                            )[0]
                            .strip()
                        )
                if not traceback_text:
                    traceback_text = crash_content
            except Exception:
                traceback_text = f"Failed to read crash log from: {crash_log_path}"
        else:
            # Catastrophic crash (e.g. segfault) without a Python exception log
            report, traceback_text = generate_crash_report(
                RuntimeError,
                f"The application process terminated unexpectedly (exit code: {exit_code}).",
                None,
            )
            crash_log_path = save_crash_report(report)

        # Show dialog offering relaunch
        relaunch = show_crash_dialog_in_parent(crash_log_path, traceback_text)
        if not relaunch:
            sys.exit(exit_code)


_handling_crash = False


def handle_child_crash(exctype, value, tb):
    global _handling_crash
    if _handling_crash:
        sys.__excepthook__(exctype, value, tb)
        return
    _handling_crash = True

    try:
        report, _ = generate_crash_report(exctype, value, tb)
        save_crash_report(report)
        print(report, file=sys.stderr)
    except Exception as e:
        print(f"Exception inside crash hook: {e}", file=sys.stderr)

    sys.exit(1)


def install_child_crash_handler():
    sys.excepthook = handle_child_crash

    import threading

    def handle_thread_crash(args):
        if issubclass(args.exc_type, (KeyboardInterrupt, SystemExit)):
            return
        handle_child_crash(args.exc_type, args.exc_value, args.exc_traceback)

    threading.excepthook = handle_thread_crash


def list_crash_reports():
    """Returns a sorted list of crash report filenames from the data/crashes/ directory (newest first)."""
    try:
        from app.utils import ensure_external_data_directory

        crashes_dir = ensure_external_data_directory("crashes")
        if not os.path.isdir(crashes_dir):
            return []

        files = []
        for name in os.listdir(crashes_dir):
            path = os.path.join(crashes_dir, name)
            if os.path.isfile(path) and name.startswith("crash_") and name.endswith(".txt"):
                files.append(name)

        # Sort by mtime (newest first)
        files.sort(key=lambda name: os.path.getmtime(os.path.join(crashes_dir, name)), reverse=True)
        return files
    except Exception:
        return []


def read_crash_report_by_name(filename):
    """Reads the contents of a crash report file by its filename."""
    try:
        from app.utils import ensure_external_data_directory

        crashes_dir = ensure_external_data_directory("crashes")
        # Prevent directory traversal attacks
        safe_name = os.path.basename(filename)
        path = os.path.join(crashes_dir, safe_name)
        if os.path.isfile(path):
            with open(path, "r", encoding="utf-8") as f:
                return f.read()
    except Exception as e:
        return f"Error reading crash report: {e}"
    return "Crash report file not found."


def delete_crash_report_by_name(filename):
    """Deletes a crash report file by its filename. Returns True if successful."""
    try:
        from app.utils import ensure_external_data_directory

        crashes_dir = ensure_external_data_directory("crashes")
        safe_name = os.path.basename(filename)
        path = os.path.join(crashes_dir, safe_name)
        if os.path.isfile(path):
            os.remove(path)

            # If this was the latest crash, delete the latest_crash.txt too
            try:
                latest_path = get_latest_crash_path()
                if os.path.isfile(latest_path):
                    os.remove(latest_path)
            except Exception:
                pass

            return True
    except Exception:
        pass
    return False

