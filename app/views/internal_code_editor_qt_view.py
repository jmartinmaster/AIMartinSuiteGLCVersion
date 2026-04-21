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
import builtins
import io
import keyword
import tokenize

from app.theme_manager import get_qt_palette, get_qt_stylesheet

__module_name__ = "Internal Code Editor Qt View"
__version__ = "1.2.3"

from PyQt6.QtCore import QSignalBlocker, QTimer, Qt
from PyQt6.QtGui import QColor, QSyntaxHighlighter, QTextCharFormat, QTextDocument
from PyQt6.QtWidgets import (
    QApplication,
    QComboBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QPlainTextEdit,
    QSplitter,
    QStatusBar,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

PYQT6_AVAILABLE = True


def is_internal_code_editor_qt_runtime_available():
    return PYQT6_AVAILABLE


def _blend_hex(base_hex, overlay_hex, ratio):
    base = QColor(str(base_hex or "#000000"))
    overlay = QColor(str(overlay_hex or "#000000"))
    ratio = max(0.0, min(1.0, float(ratio)))
    red = round(base.red() + (overlay.red() - base.red()) * ratio)
    green = round(base.green() + (overlay.green() - base.green()) * ratio)
    blue = round(base.blue() + (overlay.blue() - base.blue()) * ratio)
    return QColor(red, green, blue)


def _is_dark_color(color_value):
    color = QColor(str(color_value or "#000000"))
    luminance = (0.2126 * color.redF()) + (0.7152 * color.greenF()) + (0.0722 * color.blueF())
    return luminance < 0.5


def _rotate_hue(color_value, degrees, saturation_scale=1.0, lightness_shift=0.0, min_saturation=0.35):
    color = QColor(color_value if isinstance(color_value, QColor) else str(color_value or "#000000"))
    hue, saturation, lightness, alpha = color.getHslF()
    if hue < 0.0:
        hue = 0.0
    hue = (hue + (float(degrees) / 360.0)) % 1.0
    saturation = max(min_saturation, min(1.0, saturation * float(saturation_scale)))
    lightness = max(0.0, min(1.0, lightness + float(lightness_shift)))
    derived = QColor()
    derived.setHslF(hue, saturation, lightness, alpha)
    return derived


def _derive_editor_palette(theme_tokens):
    tokens = dict(theme_tokens or {})
    dark_mode = _is_dark_color(tokens.get("surface_bg", "#ffffff"))
    accent = QColor(str(tokens.get("accent", "#0f7c8f")))
    readonly = QColor(str(tokens.get("layout_preview_readonly_fg", accent.name())))
    surface_fg = QColor(str(tokens.get("surface_fg", "#152129")))
    muted_fg = QColor(str(tokens.get("muted_fg", "#637782")))
    banner_fg = QColor(str(tokens.get("banner_fg", accent.name())))

    if dark_mode:
        keyword = _rotate_hue(accent, 0, saturation_scale=1.10, lightness_shift=0.14)
        string = _rotate_hue(accent, 28, saturation_scale=0.92, lightness_shift=0.18)
        number = _rotate_hue(accent, 118, saturation_scale=0.78, lightness_shift=0.18)
        class_name = _rotate_hue(readonly, -24, saturation_scale=1.05, lightness_shift=0.12)
        function_name = _rotate_hue(banner_fg, 52, saturation_scale=0.95, lightness_shift=0.16)
        method_name = _rotate_hue(readonly, 78, saturation_scale=0.98, lightness_shift=0.12)
        builtin = _blend_hex(_rotate_hue(accent, 118, saturation_scale=0.78, lightness_shift=0.18), "#C8E1A0", 0.45)
        decorator = _rotate_hue(accent, -32, saturation_scale=1.15, lightness_shift=0.12)
        import_name = _rotate_hue(accent, 64, saturation_scale=0.88, lightness_shift=0.16)
        parameter = _rotate_hue(surface_fg, 188, saturation_scale=1.18, lightness_shift=0.06, min_saturation=0.40)
        variable = _rotate_hue(accent, 102, saturation_scale=0.72, lightness_shift=0.12)
        comment = _blend_hex(muted_fg, accent, 0.18)
    else:
        keyword = _rotate_hue(accent, 0, saturation_scale=1.15, lightness_shift=-0.12)
        string = _rotate_hue(accent, 22, saturation_scale=0.95, lightness_shift=-0.16)
        number = _rotate_hue(accent, 120, saturation_scale=0.88, lightness_shift=-0.18)
        class_name = _rotate_hue(readonly, -18, saturation_scale=1.10, lightness_shift=-0.10)
        function_name = _rotate_hue(banner_fg, 46, saturation_scale=1.05, lightness_shift=-0.22)
        method_name = _rotate_hue(readonly, 72, saturation_scale=1.08, lightness_shift=-0.08)
        builtin = _rotate_hue(surface_fg, 214, saturation_scale=1.35, lightness_shift=0.00, min_saturation=0.45)
        decorator = _rotate_hue(accent, -34, saturation_scale=1.10, lightness_shift=-0.08)
        import_name = _rotate_hue(accent, 58, saturation_scale=0.95, lightness_shift=-0.14)
        parameter = _rotate_hue(surface_fg, 192, saturation_scale=1.15, lightness_shift=-0.04, min_saturation=0.42)
        variable = _rotate_hue(accent, 100, saturation_scale=0.82, lightness_shift=-0.10)
        comment = _blend_hex(muted_fg, accent, 0.10)

    return {
        "py_keyword": keyword,
        "py_string": string,
        "py_comment": comment,
        "py_number": number,
        "py_class_name": class_name,
        "py_function_name": function_name,
        "py_method_name": method_name,
        "py_builtin": builtin,
        "py_decorator": decorator,
        "py_import_name": import_name,
        "py_parameter_name": parameter,
        "py_variable_name": variable,
    }


class PythonTokenHighlighter(QSyntaxHighlighter):
    def __init__(self, document):
        super().__init__(document)
        self.python_builtins = {name for name in dir(builtins) if not name.startswith("_")}
        self.line_formats = {}
        self.formats = {}
        self.set_theme_tokens({})

    def set_theme_tokens(self, theme_tokens):
        tokens = dict(theme_tokens or {})
        palette = _derive_editor_palette(tokens)

        def build_format(color_value, underline=False, italic=False, weight=None):
            text_format = QTextCharFormat()
            text_format.setForeground(QColor(color_value) if not isinstance(color_value, QColor) else color_value)
            if underline:
                text_format.setFontUnderline(True)
            if italic:
                text_format.setFontItalic(True)
            if weight is not None:
                text_format.setFontWeight(int(weight))
            return text_format

        self.formats = {
            "py_keyword": build_format(palette["py_keyword"], weight=700),
            "py_string": build_format(palette["py_string"]),
            "py_comment": build_format(palette["py_comment"], italic=True),
            "py_number": build_format(palette["py_number"]),
            "py_class_name": build_format(palette["py_class_name"], underline=True, weight=700),
            "py_function_name": build_format(palette["py_function_name"], underline=True),
            "py_method_name": build_format(palette["py_method_name"], underline=True),
            "py_builtin": build_format(palette["py_builtin"]),
            "py_decorator": build_format(palette["py_decorator"]),
            "py_import_name": build_format(palette["py_import_name"]),
            "py_parameter_name": build_format(palette["py_parameter_name"]),
            "py_variable_name": build_format(palette["py_variable_name"]),
        }
        self.rehighlight()

    def rebuild(self, source_text, definition_entries, semantic_entries=None):
        self.line_formats = {}
        source_text = str(source_text or "")
        definition_entries = list(definition_entries or [])
        semantic_entries = list(semantic_entries or [])
        if not source_text:
            self.rehighlight()
            return

        decorator_active = False
        import_statement_active = False
        try:
            token_stream = tokenize.generate_tokens(io.StringIO(source_text).readline)
            for token_info in token_stream:
                token_type = token_info.type
                token_string = token_info.string
                start_line, start_col = token_info.start
                end_line, end_col = token_info.end

                if decorator_active and token_type not in {tokenize.NEWLINE, tokenize.NL}:
                    self._add_span(start_line, start_col, end_line, end_col, "py_decorator")

                if token_type == tokenize.COMMENT:
                    self._add_span(start_line, start_col, end_line, end_col, "py_comment")
                elif token_type == tokenize.STRING:
                    self._add_span(start_line, start_col, end_line, end_col, "py_string")
                elif token_type == tokenize.NUMBER:
                    self._add_span(start_line, start_col, end_line, end_col, "py_number")
                elif token_type == tokenize.OP and token_string == "@":
                    decorator_active = True
                    self._add_span(start_line, start_col, end_line, end_col, "py_decorator")
                elif token_type == tokenize.NAME:
                    if token_string in {"import", "from", "as"}:
                        self._add_span(start_line, start_col, end_line, end_col, "py_keyword")
                        import_statement_active = True
                    elif keyword.iskeyword(token_string):
                        self._add_span(start_line, start_col, end_line, end_col, "py_keyword")
                        import_statement_active = False
                    elif token_string in self.python_builtins:
                        self._add_span(start_line, start_col, end_line, end_col, "py_builtin")
                    elif import_statement_active:
                        self._add_span(start_line, start_col, end_line, end_col, "py_import_name")
                elif token_type in {tokenize.NEWLINE, tokenize.NL}:
                    decorator_active = False
                    import_statement_active = False
        except (tokenize.TokenError, IndentationError, SyntaxError):
            pass

        kind_map = {
            "class": "py_class_name",
            "function": "py_function_name",
            "method": "py_method_name",
        }
        for entry in definition_entries:
            style_key = kind_map.get(str(entry.get("kind") or ""))
            if not style_key:
                continue
            try:
                line_number = max(1, int(entry.get("line") or 1))
                start_column = int(str(entry.get("name_start_index") or "1.0").split(".", 1)[1])
                end_column = int(str(entry.get("name_end_index") or f"{line_number}.{start_column}").split(".", 1)[1])
            except (IndexError, ValueError):
                continue
            self._add_line_format(line_number - 1, start_column, max(0, end_column - start_column), style_key)

        semantic_kind_map = {
            "parameter": "py_parameter_name",
            "variable": "py_variable_name",
        }
        for entry in semantic_entries:
            style_key = semantic_kind_map.get(str(entry.get("kind") or ""))
            if not style_key:
                continue
            try:
                line_number = max(1, int(entry.get("line") or 1))
                start_column = int(str(entry.get("name_start_index") or "1.0").split(".", 1)[1])
                end_column = int(str(entry.get("name_end_index") or f"{line_number}.{start_column}").split(".", 1)[1])
            except (IndexError, ValueError):
                continue
            self._add_line_format(line_number - 1, start_column, max(0, end_column - start_column), style_key)

        self.rehighlight()

    def highlightBlock(self, text):
        for start, length, style_key in self.line_formats.get(self.currentBlock().blockNumber(), []):
            text_format = self.formats.get(style_key)
            if text_format is not None and length > 0:
                self.setFormat(start, length, text_format)

    def _add_span(self, start_line, start_col, end_line, end_col, style_key):
        if end_line < start_line:
            return
        if start_line == end_line:
            self._add_line_format(start_line - 1, start_col, max(0, end_col - start_col), style_key)
            return
        self._add_line_format(start_line - 1, start_col, 10000, style_key)
        for line_number in range(start_line + 1, end_line):
            self._add_line_format(line_number - 1, 0, 10000, style_key)
        self._add_line_format(end_line - 1, 0, max(0, end_col), style_key)

    def _add_line_format(self, block_number, start, length, style_key):
        if block_number < 0 or length <= 0:
            return
        self.line_formats.setdefault(block_number, []).append((int(start), int(length), style_key))


class InternalCodeEditorQtView(QMainWindow):
    def __init__(self, controller, payload, parent_widget=None):
        if not PYQT6_AVAILABLE:
            raise RuntimeError("PyQt6 is not installed in the active Python environment.")
        super().__init__(parent_widget)
        self.controller = controller
        self.payload = dict(payload or {})
        self.theme_tokens = dict(self.payload.get("theme_tokens") or {})
        self.embedded = parent_widget is not None
        self.file_options = {}
        self.definition_entries = {}
        self.navigation_entries = {}
        self.index_pane_visible = True
        self._suspend_modified_signal = False
        self.analysis_timer = QTimer(self)
        self.analysis_timer.setSingleShot(True)
        self.analysis_timer.setInterval(220)
        self.analysis_timer.timeout.connect(self.controller.refresh_editor_analysis)
        self._build_ui()
        self.apply_theme(theme_tokens=self.theme_tokens)
        if self.embedded:
            self._attach_to_parent_container(parent_widget)

        if not self.embedded:
            self.command_timer = QTimer(self)
            self.command_timer.setInterval(700)
            self.command_timer.timeout.connect(self.controller.poll_commands)
            self.command_timer.start()

    def schedule_analysis_refresh(self):
        self.analysis_timer.start()

    def clear_editor_modified_state(self):
        document = self.text_editor.document()
        if document is not None:
            document.setModified(False)

    def _attach_to_parent_container(self, parent_widget):
        if parent_widget is None:
            return
        self.setWindowFlag(Qt.WindowType.Window, False)
        layout = parent_widget.layout()
        if layout is None:
            layout = QVBoxLayout(parent_widget)
            layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self)
        self.show()

    def _build_ui(self):
        self.setWindowTitle(str(self.payload.get("window_title") or "Internal Code Editor"))
        if self.embedded:
            self.setMinimumSize(0, 0)
        else:
            self._fit_window_to_screen(1360, 900)

        central_widget = QWidget(self)
        root_layout = QVBoxLayout(central_widget)
        root_layout.setContentsMargins(14, 14, 14, 14)
        root_layout.setSpacing(10)

        title_label = QLabel(str(self.payload.get("title") or "Internal Code Editor"))
        title_label.setObjectName("pageTitle")
        root_layout.addWidget(title_label)

        subtitle_label = QLabel(str(self.payload.get("subtitle") or "Edit Python modules in-place."))
        subtitle_label.setObjectName("mutedLabel")
        subtitle_label.setWordWrap(True)
        root_layout.addWidget(subtitle_label)

        controls_row = QHBoxLayout()
        controls_row.addWidget(QLabel("File"))
        self.file_selector = QComboBox()
        self.file_selector.currentIndexChanged.connect(self.controller.on_file_selected)
        controls_row.addWidget(self.file_selector, 1)

        reload_button = QPushButton("Reload")
        reload_button.clicked.connect(self.controller.reload_current_file)
        controls_row.addWidget(reload_button)

        save_button = QPushButton("Save")
        save_button.clicked.connect(self.controller.save_current_file)
        controls_row.addWidget(save_button)
        root_layout.addLayout(controls_row)

        self.source_label = QLabel("")
        self.source_label.setObjectName("mutedLabel")
        self.source_label.setWordWrap(True)
        root_layout.addWidget(self.source_label)

        self.save_target_label = QLabel("")
        self.save_target_label.setObjectName("mutedLabel")
        self.save_target_label.setWordWrap(True)
        root_layout.addWidget(self.save_target_label)

        search_row = QHBoxLayout()
        search_row.addWidget(QLabel("Search"))
        self.search_entry = QLineEdit()
        search_row.addWidget(self.search_entry)

        text_search_button = QPushButton("Text Results")
        text_search_button.clicked.connect(self.controller.run_text_search)
        search_row.addWidget(text_search_button)

        symbol_search_button = QPushButton("Symbol Results")
        symbol_search_button.clicked.connect(self.controller.run_symbol_search)
        search_row.addWidget(symbol_search_button)

        definitions_button = QPushButton("Definitions")
        definitions_button.clicked.connect(self.controller.show_definitions)
        search_row.addWidget(definitions_button)

        self.index_toggle_button = QPushButton("Hide Index")
        self.index_toggle_button.clicked.connect(self.toggle_index_pane)
        search_row.addWidget(self.index_toggle_button)

        prev_button = QPushButton("Previous")
        prev_button.clicked.connect(self.controller.find_previous)
        search_row.addWidget(prev_button)

        next_button = QPushButton("Next")
        next_button.clicked.connect(self.controller.find_next)
        search_row.addWidget(next_button)
        root_layout.addLayout(search_row)

        self.splitter = QSplitter()

        self.definition_tree = QTreeWidget()
        self.definition_tree.setHeaderLabels(["Name", "Kind", "Line"])
        self.definition_tree.itemSelectionChanged.connect(self.controller.on_navigation_item_selected)
        self.splitter.addWidget(self.definition_tree)

        self.text_editor = QPlainTextEdit()
        self.text_editor.textChanged.connect(self.controller.handle_editor_modified)
        self.syntax_highlighter = PythonTokenHighlighter(self.text_editor.document())
        self.splitter.addWidget(self.text_editor)
        self.splitter.setStretchFactor(0, 1)
        self.splitter.setStretchFactor(1, 4)

        root_layout.addWidget(self.splitter, 1)

        self.definition_summary_label = QLabel("Definitions will appear for the open file.")
        self.definition_summary_label.setObjectName("mutedLabel")
        root_layout.addWidget(self.definition_summary_label)

        self.setCentralWidget(central_widget)
        self.status_bar = QStatusBar(self)
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Internal Code Editor Qt window ready.", 5000)

    def _available_screen_geometry(self):
        window_handle = self.windowHandle()
        screen = window_handle.screen() if window_handle is not None else None
        if screen is None and hasattr(self, "screen"):
            try:
                screen = self.screen()
            except Exception:
                screen = None
        application = QApplication.instance()
        if screen is None and application is not None:
            screen = application.primaryScreen()
        return screen.availableGeometry() if screen is not None else None

    def _fit_window_to_screen(self, requested_width, requested_height, padding=48):
        geometry = self._available_screen_geometry()
        if geometry is None:
            self.resize(requested_width, requested_height)
            return
        max_width = max(840, geometry.width() - int(padding))
        max_height = max(620, geometry.height() - int(padding))
        self.resize(min(int(requested_width), max_width), min(int(requested_height), max_height))

    def apply_theme(self, theme_tokens=None):
        if isinstance(theme_tokens, dict):
            self.theme_tokens = dict(theme_tokens)
        self.setStyleSheet(get_qt_stylesheet(theme_tokens=self.theme_tokens))
        application = QApplication.instance()
        if application is not None:
            application.setPalette(get_qt_palette(theme_tokens=self.theme_tokens))
        if hasattr(self, "syntax_highlighter"):
            self.syntax_highlighter.set_theme_tokens(self.theme_tokens)

    def toggle_index_pane(self):
        self.set_index_pane_visible(not self.index_pane_visible)

    def set_index_pane_visible(self, visible):
        self.index_pane_visible = bool(visible)
        self.definition_tree.setVisible(self.index_pane_visible)
        if self.index_pane_visible:
            self.index_toggle_button.setText("Hide Index")
        else:
            self.index_toggle_button.setText("Show Index")

    def set_file_options(self, entries, selected_key):
        self.file_options = {entry["label"]: entry["key"] for entry in entries}
        with QSignalBlocker(self.file_selector):
            self.file_selector.clear()
            for entry in entries:
                self.file_selector.addItem(entry["label"])
        if selected_key is not None:
            self.select_file_key(selected_key)

    def select_file_key(self, file_key):
        if not file_key:
            return
        for index in range(self.file_selector.count()):
            label = self.file_selector.itemText(index)
            if self.file_options.get(label) == file_key:
                with QSignalBlocker(self.file_selector):
                    self.file_selector.setCurrentIndex(index)
                return

    def get_selected_file_key(self):
        label = self.file_selector.currentText()
        return self.file_options.get(label)

    def update_file_details(self, source_text, save_target_text):
        self.source_label.setText(str(source_text or ""))
        self.save_target_label.setText(str(save_target_text or ""))

    def set_editor_text(self, text):
        self._suspend_modified_signal = True
        try:
            with QSignalBlocker(self.text_editor):
                self.text_editor.setPlainText(str(text or ""))
            self.clear_editor_modified_state()
        finally:
            self._suspend_modified_signal = False

    def get_editor_text(self):
        return self.text_editor.toPlainText()

    def get_search_text(self):
        return self.search_entry.text()

    def focus_search(self):
        self.search_entry.setFocus()
        self.search_entry.selectAll()

    def find_text(self, search_text, backwards=False):
        if not search_text:
            return False
        text_cursor = self.text_editor.textCursor()
        document = self.text_editor.document()
        flags = QTextDocument.FindFlag.FindBackward if backwards else QTextDocument.FindFlag(0)
        found_cursor = document.find(search_text, text_cursor, flags)
        if found_cursor.isNull():
            start_cursor = self.text_editor.textCursor()
            start_cursor.movePosition(start_cursor.MoveOperation.End if backwards else start_cursor.MoveOperation.Start)
            found_cursor = document.find(search_text, start_cursor, flags)
        if found_cursor.isNull():
            return False
        self.text_editor.setTextCursor(found_cursor)
        return True

    def set_definition_entries(self, definition_entries):
        current_key = self.get_selected_definition_key()
        self.definition_entries = {entry["key"]: entry for entry in definition_entries}
        self.navigation_entries = {entry["key"]: {"entry_type": "definition", **entry} for entry in definition_entries}
        with QSignalBlocker(self.definition_tree):
            self.definition_tree.clear()
            self.definition_tree.setHeaderLabels(["Name", "Kind", "Line"])
            for entry in definition_entries:
                item = QTreeWidgetItem([
                    str(entry["qualified_name"]),
                    str(entry["kind"].title()),
                    str(entry["line"]),
                ])
                item.setData(0, 0x0100, entry["key"])
                self.definition_tree.addTopLevelItem(item)
        if current_key and current_key in self.definition_entries:
            self.select_definition_key(current_key)

    def set_search_results(self, result_entries, search_kind, selected_key=None):
        self.navigation_entries = {entry["key"]: {"entry_type": "search_result", **entry} for entry in result_entries}
        result_label = "Text Match" if str(search_kind) == "text" else "Symbol"
        with QSignalBlocker(self.definition_tree):
            self.definition_tree.clear()
            self.definition_tree.setHeaderLabels(["File", "Line", result_label])
            for entry in result_entries:
                item = QTreeWidgetItem([
                    str(entry.get("relative_path") or ""),
                    str(entry.get("line") or ""),
                    str(entry.get("summary") or ""),
                ])
                item.setData(0, 0x0100, str(entry.get("key") or ""))
                item.setToolTip(0, str(entry.get("relative_path") or ""))
                item.setToolTip(2, str(entry.get("summary") or ""))
                self.definition_tree.addTopLevelItem(item)
        if selected_key:
            self.select_navigation_key(selected_key)

    def select_navigation_key(self, entry_key):
        if not entry_key:
            return
        with QSignalBlocker(self.definition_tree):
            for index in range(self.definition_tree.topLevelItemCount()):
                item = self.definition_tree.topLevelItem(index)
                if item.data(0, 0x0100) == entry_key:
                    self.definition_tree.setCurrentItem(item)
                    return

    def select_definition_key(self, definition_key):
        for index in range(self.definition_tree.topLevelItemCount()):
            item = self.definition_tree.topLevelItem(index)
            if item.data(0, 0x0100) == definition_key:
                self.definition_tree.setCurrentItem(item)
                return

    def get_selected_definition_key(self):
        item = self.definition_tree.currentItem()
        if item is None:
            return None
        return item.data(0, 0x0100)

    def get_selected_navigation_payload(self):
        key = self.get_selected_definition_key()
        if not key:
            return None
        return self.navigation_entries.get(key)

    def update_definition_summary(self, definition_count, parse_error=None):
        if parse_error:
            self.definition_summary_label.setText(f"Index unavailable: {parse_error}")
            return
        noun = "definition" if definition_count == 1 else "definitions"
        self.definition_summary_label.setText(f"Indexed {definition_count} {noun} for the active file.")

    def refresh_syntax_highlighting(self, definition_entries=None, semantic_entries=None):
        if hasattr(self, "syntax_highlighter"):
            self.syntax_highlighter.rebuild(
                self.get_editor_text(),
                list(definition_entries or []),
                list(semantic_entries or []),
            )

    def show_definition_location(self, definition_entry):
        line_number = max(1, int(definition_entry.get("line") or 1))
        cursor = self.text_editor.textCursor()
        block = self.text_editor.document().findBlockByLineNumber(line_number - 1)
        if block.isValid():
            cursor.setPosition(block.position())
            self.text_editor.setTextCursor(cursor)
            self.text_editor.centerCursor()
            self.text_editor.setFocus()

    def show_search_result_location(self, result_entry):
        line_number = max(1, int(result_entry.get("line") or 1))
        column_number = max(1, int(result_entry.get("column") or 1))
        cursor = self.text_editor.textCursor()
        block = self.text_editor.document().findBlockByLineNumber(line_number - 1)
        if not block.isValid():
            return
        cursor.setPosition(block.position() + max(0, column_number - 1))
        self.text_editor.setTextCursor(cursor)
        self.text_editor.centerCursor()
        self.text_editor.setFocus()

    def update_status(self, message):
        self.status_bar.showMessage(str(message or ""), 6000)

    def show_info(self, title, message):
        QMessageBox.information(self, title, message)

    def show_toast(self, title, message):
        self.controller.show_toast(title, message)

    def show_error(self, title, message):
        QMessageBox.critical(self, title, message)

    def confirm_discard_changes(self):
        response = QMessageBox.question(
            self,
            "Discard Unsaved Changes",
            "You have unsaved changes in the editor. Discard them and continue?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        return response == QMessageBox.StandardButton.Yes

    def closeEvent(self, event):
        self.controller.handle_close()
        super().closeEvent(event)
