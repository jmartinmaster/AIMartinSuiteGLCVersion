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
import os

__module_name__ = "Help Viewer Qt View"
__version__ = "1.0.0"

try:
    from PyQt6.QtCore import QSignalBlocker, Qt
    from PyQt6.QtWidgets import (
        QHBoxLayout,
        QLabel,
        QListWidget,
        QListWidgetItem,
        QMainWindow,
        QMessageBox,
        QPushButton,
        QStatusBar,
        QTextBrowser,
        QVBoxLayout,
        QWidget,
    )

    PYQT6_AVAILABLE = True
except ImportError:
    Qt = None
    QHBoxLayout = None
    QLabel = None
    QListWidget = None
    QListWidgetItem = None
    QMainWindow = object
    QMessageBox = None
    QPushButton = None
    QStatusBar = None
    QTextBrowser = None
    QVBoxLayout = None
    QWidget = None
    QSignalBlocker = None
    PYQT6_AVAILABLE = False


class HelpViewerQtView(QMainWindow):
    def __init__(self, controller, payload, parent_widget=None):
        if not PYQT6_AVAILABLE:
            raise RuntimeError("PyQt6 is not installed in the active Python environment.")
        super().__init__(parent_widget)
        self.controller = controller
        self.payload = dict(payload or {})
        self.doc_index = list(self.payload.get("doc_index") or [])
        self.theme_tokens = dict(self.payload.get("theme_tokens") or {})
        self.embedded = parent_widget is not None
        self.active_doc_name = None
        self.active_doc_path = None
        self.active_doc_meta_label = ""
        self.active_sections = []
        self._build_ui()
        self._attach_to_parent_container(parent_widget)

    def _attach_to_parent_container(self, parent_widget):
        if not self.embedded or parent_widget is None:
            return
        if Qt is not None:
            self.setWindowFlag(Qt.WindowType.Window, False)
        parent_layout = getattr(parent_widget, "layout", lambda: None)()
        if parent_layout is not None:
            parent_layout.addWidget(self)
        self.show()

    def _build_ui(self):
        self.setWindowTitle(str(self.payload.get("window_title") or "Help Viewer"))
        if self.embedded:
            self.setMinimumSize(0, 0)
        else:
            self.resize(1360, 900)

        central_widget = QWidget(self)
        root_layout = QVBoxLayout(central_widget)
        root_layout.setContentsMargins(18, 18, 18, 18)
        root_layout.setSpacing(12)

        title_label = QLabel(str(self.payload.get("title") or "Help Center"))
        title_label.setObjectName("pageTitle")
        root_layout.addWidget(title_label)

        subtitle_label = QLabel(str(self.payload.get("subtitle") or "Bundled guides and references"))
        subtitle_label.setObjectName("mutedLabel")
        subtitle_label.setWordWrap(True)
        root_layout.addWidget(subtitle_label)

        action_row = QHBoxLayout()
        open_button = QPushButton("Open Current File")
        open_button.clicked.connect(self.controller.open_active_document)
        action_row.addWidget(open_button)
        action_row.addStretch(1)
        root_layout.addLayout(action_row)

        content_row = QHBoxLayout()
        content_row.setSpacing(12)

        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(8)

        left_layout.addWidget(QLabel("References"))
        self.doc_list = QListWidget()
        self.doc_list.currentItemChanged.connect(self._handle_doc_selection_changed)
        left_layout.addWidget(self.doc_list, 3)

        left_layout.addWidget(QLabel("Sections"))
        self.section_list = QListWidget()
        self.section_list.currentItemChanged.connect(self._handle_section_selection_changed)
        left_layout.addWidget(self.section_list, 2)

        for doc_name, doc_path in self.doc_index:
            item = QListWidgetItem(doc_name)
            item.setData(256, doc_path)
            self.doc_list.addItem(item)

        content_row.addWidget(left_panel, 1)

        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(8)

        self.doc_title_label = QLabel("Document")
        self.doc_title_label.setObjectName("pageTitle")
        right_layout.addWidget(self.doc_title_label)

        self.doc_meta_label = QLabel("")
        self.doc_meta_label.setObjectName("mutedLabel")
        right_layout.addWidget(self.doc_meta_label)

        self.doc_path_label = QLabel("")
        self.doc_path_label.setObjectName("mutedLabel")
        right_layout.addWidget(self.doc_path_label)

        self.doc_browser = QTextBrowser()
        self.doc_browser.setOpenExternalLinks(False)
        right_layout.addWidget(self.doc_browser, 1)

        content_row.addWidget(right_panel, 3)
        root_layout.addLayout(content_row, 1)

        self.setCentralWidget(central_widget)
        self.status_bar = QStatusBar(self)
        self.setStatusBar(self.status_bar)

    def _handle_doc_selection_changed(self, current, _previous):
        if current is None:
            return
        doc_path = current.data(256)
        self.controller.show_document(str(current.text()), str(doc_path))

    def _handle_section_selection_changed(self, current, _previous):
        if current is None:
            return
        doc_path = current.data(256)
        doc_name = current.text()
        self.controller.show_document(str(doc_name), str(doc_path))

    def show_document(self, doc_name, doc_path, content, meta_label, sections, restore_scroll=None):
        self.active_doc_name = str(doc_name)
        self.active_doc_path = str(doc_path)
        self.active_doc_meta_label = str(meta_label)
        self.active_sections = [
            (str(section_name), str(section_path))
            for section_name, section_path in list(sections or [])
        ]
        self.doc_title_label.setText(str(doc_name))
        self.doc_meta_label.setText(str(meta_label))
        self.doc_path_label.setText(str(doc_path))
        if str(doc_path).lower().endswith(".md"):
            self.doc_browser.setMarkdown(content)
        else:
            self.doc_browser.setPlainText(content)
        target_scroll = 0 if restore_scroll is None else max(0, int(restore_scroll))
        self.doc_browser.verticalScrollBar().setValue(target_scroll)

        blocker = QSignalBlocker(self.section_list)
        self.section_list.clear()
        for section_name, section_path in sections:
            item = QListWidgetItem(str(section_name))
            item.setData(256, str(section_path))
            self.section_list.addItem(item)
            if str(section_path) == str(doc_path):
                self.section_list.setCurrentItem(item)
        del blocker

        blocker = QSignalBlocker(self.doc_list)
        for index in range(self.doc_list.count()):
            item = self.doc_list.item(index)
            item.setSelected(str(item.data(256)) == str(doc_path))
            if str(item.data(256)) == str(doc_path):
                self.doc_list.setCurrentItem(item)
        del blocker
        self.status_bar.showMessage(f"Viewing {doc_name}", 5000)

    def get_document_scroll(self):
        scroll_bar = getattr(self.doc_browser, "verticalScrollBar", lambda: None)()
        if scroll_bar is None:
            return 0
        return int(scroll_bar.value() or 0)

    def apply_theme(self, theme_tokens=None):
        if theme_tokens is not None:
            self.theme_tokens = dict(theme_tokens or {})
        style = self.style()
        if style is not None:
            style.unpolish(self)
            style.polish(self)
        self.update()

    def show_error(self, title, message):
        QMessageBox.critical(self, title, message)

    def show_info(self, title, message):
        QMessageBox.information(self, title, message)

    def closeEvent(self, event):
        self.controller.handle_close()
        super().closeEvent(event)
