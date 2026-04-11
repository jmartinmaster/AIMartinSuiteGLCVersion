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
import tkinter as tk
from tkinter import filedialog, messagebox

import ttkbootstrap as tb
from ttkbootstrap.constants import *
import tkinter.ttk as ttk
from ttkbootstrap.dialogs import Messagebox

from app.models.production_log_model import BALANCE_DOWNTIME_CAUSE, DEFAULT_GHOST_LABEL
from app.theme_manager import get_theme_tokens

__module_name__ = "Production Log"
__version__ = "1.2.6"


class ProductionLogView:
    def __init__(self, parent, dispatcher, controller, model):
        self.parent = parent
        self.dispatcher = dispatcher
        self.controller = controller
        self.controller.view = self
        self.model = model
        self.config_path = self.model.config_path
        self.dt_codes = list(self.model.dt_codes)
        self.data_handler = self.model.data_handler
        self.production_rows = []
        self.downtime_rows = []
        self.entries = {}
        self.settings = dict(self.model.settings)
        self.default_hours = str(self.model.default_hours)
        self.default_goal = str(self.model.default_goal)
        self.auto_save_interval = int(self.model.auto_save_interval)
        self.current_draft_path = None
        self.latest_draft_path = None
        self.last_export_path = None
        self.has_unsaved_changes = False
        self.last_saved_signature = None
        self.summary_visible = False
        self.summary_refresh_after_id = None
        self.summary_resize_after_id = None
        self.summary_theme_tokens = {}
        self.content_stack = None
        self.displayed_ghost_minutes = 0
        self.balanceable_ghost_minutes = 0
        self.balance_target_downtime_total_minutes = 0
        self.balance_action_mode = "balance"
        self.balance_downtime_btn = None
        self.balance_mix_var = tk.DoubleVar(value=100.0)
        self.balance_mix_value_lbl = None

        self.setup_ui()
        self.parent.after(self.auto_save_interval, self.auto_save)

    def auto_save(self):
        self.controller.auto_save()
        self.parent.after(self.auto_save_interval, self.auto_save)

    def get_pending_dir(self):
        return self.controller.get_pending_dir()

    def get_pending_history_dir(self):
        return self.controller.get_pending_history_dir()

    def get_raw_header_data(self):
        return {field_id: entry.get() for field_id, entry in self.entries.items()}

    def collect_header_data(self):
        return self.controller.collect_header_data()

    def apply_header_data(self, header_data, mark_dirty=False):
        return self.controller.apply_header_data(header_data, mark_dirty=mark_dirty)

    def collect_ui_data(self):
        header_data = self.collect_header_data()
        production_data = []
        for row in self.production_rows:
            production_data.append({
                "shop_order": row["shop_order"].get(),
                "part_number": row["part_number"].get(),
                "rate_lookup": row["rate_lookup"].get(),
                "rate_override_enabled": bool(row["rate_override_enabled_var"].get()),
                "molds": row["molds"].get(),
                "time_calc": row["time_calc"].cget("text"),
            })
        downtime_data = [{key: (value.get() if hasattr(value, "get") else value.cget("text")) for key, value in row.items()} for row in self.downtime_rows]
        return {
            "header": header_data,
            "production": production_data,
            "downtime": downtime_data,
            "balance_state": self.collect_balance_state(),
        }

    def serialize_ui_data(self, data=None):
        if data is None:
            data = self.collect_ui_data()
        return self.model.serialize_ui_data(data)

    def is_form_blank(self):
        return self.model.is_form_blank(self.collect_ui_data())

    def mark_dirty(self, _event=None):
        self.has_unsaved_changes = True
        self.update_recovery_ui()

    def mark_clean(self, data=None):
        self.has_unsaved_changes = False
        self.last_saved_signature = self.serialize_ui_data(data)
        self.update_recovery_ui()

    def bind_dirty_tracking(self, widget, events):
        for event_name in events:
            widget.bind(event_name, self.mark_dirty, add="+")

    def row_has_input(self, row, field_names):
        for field_name in field_names:
            widget = row.get(field_name)
            if widget is None or not hasattr(widget, "get"):
                continue
            if str(widget.get()).strip():
                return True
        return False

    def ensure_open_production_row(self):
        if not self.production_rows:
            self.add_production_row()
            return
        if any(not self.row_has_input(row, ("shop_order", "part_number", "molds")) for row in self.production_rows):
            return
        self.add_production_row()

    def ensure_open_downtime_row(self):
        if not self.downtime_rows:
            self.add_downtime_row()
            return
        if any(not self.row_has_input(row, ("start", "stop", "code", "cause")) for row in self.downtime_rows):
            return
        self.add_downtime_row()

    def on_production_row_edited(self, _event=None):
        self.ensure_open_production_row()

    def on_downtime_row_edited(self, _event=None):
        self.ensure_open_downtime_row()

    def build_draft_path(self, header_data):
        return self.controller.build_draft_path(header_data)

    def save_draft(self, is_auto=False, suppress_toast=False):
        return self.controller.save_draft(is_auto=is_auto, suppress_toast=suppress_toast)

    def setup_ui(self):
        self.content_stack = tb.Frame(self.parent, style="Martin.Content.TFrame")
        self.content_stack.pack(fill=X, anchor=N)
        self.build_recovery_section()
        self.build_header_section()
        self.build_production_section()
        self.build_downtime_section()
        self.build_footer_section()
        self.build_summary_section()
        self.add_production_row()
        self.add_downtime_row()
        self.apply_header_data(self.get_raw_header_data(), mark_dirty=False)
        self.update_target_time_display()
        self.update_ghost_total_display()
        self.update_export_action_state()
        self.mark_clean()
        self.update_recovery_ui()
        self.parent.bind("<Configure>", self.on_parent_resized, add="+")
        self.apply_theme()
        self.parent.update_idletasks()
        self.refresh_summary_panel()
        self.reset_shell_scroll_position()
        self.schedule_summary_refresh()

    def build_recovery_section(self):
        self.recovery_wrapper = tb.Labelframe(self.content_stack, text=" Draft Status ", padding=10, style="Martin.Recovery.TLabelframe")
        self.recovery_wrapper.pack(fill=X, padx=10, pady=(10, 0))
        self.recovery_wrapper.columnconfigure(0, weight=1)

        self.recovery_status_lbl = tb.Label(
            self.recovery_wrapper,
            text="Checking draft state...",
            style="Martin.Muted.TLabel",
            anchor=W,
            justify=LEFT,
            wraplength=420,
        )
        self.recovery_status_lbl.grid(row=0, column=0, sticky="ew", pady=(0, 8))

        self.recovery_actions = tb.Frame(self.recovery_wrapper)
        self.recovery_actions.grid(row=1, column=0, sticky=W)

        self.resume_latest_btn = tb.Button(self.recovery_actions, text="Resume Latest", bootstyle=PRIMARY, command=self.controller.resume_latest_draft)
        self.resume_latest_btn.pack(side=LEFT, padx=(0, 5))
        tb.Button(self.recovery_actions, text="Pending Drafts", bootstyle=SECONDARY, command=self.controller.show_pending).pack(side=LEFT, padx=5)
        tb.Button(self.recovery_actions, text="Refresh View", bootstyle=INFO, command=self.controller.refresh_view).pack(side=LEFT, padx=5)
        self.delete_current_draft_btn = tb.Button(self.recovery_actions, text="Delete Current Draft", bootstyle=DANGER, command=self.controller.delete_current_draft)
        self.delete_current_draft_btn.pack(side=LEFT, padx=5)

        self.recovery_wrapper.bind("<Configure>", self.on_recovery_wrapper_resized, add="+")
        self.recovery_wrapper.after_idle(self.update_recovery_wraplength)

    def on_recovery_wrapper_resized(self, _event=None):
        self.update_recovery_wraplength()

    def update_recovery_wraplength(self):
        if not hasattr(self, "recovery_wrapper"):
            return
        width = self.recovery_wrapper.winfo_width()
        if width <= 1:
            return
        self.recovery_status_lbl.configure(wraplength=max(280, width - 40))

    def build_recovery_status_text(self, latest, current_name, dirty_text, pending_count, snapshot_count):
        latest_text = f"Latest: {latest['filename']} ({latest['saved_at']})" if latest else "Latest: No pending drafts"
        detail_text = (
            f"Current: {current_name} | State: {dirty_text} | Pending: {pending_count} | Recovery: {snapshot_count}"
        )
        return f"{latest_text}\n{detail_text}"

    def refresh_view(self):
        return self.controller.refresh_view()

    def build_header_section(self):
        header_wrapper = tb.Labelframe(self.content_stack, text=" Form 510-09: Production Logging Center Header ", padding=15, style="Martin.Card.TLabelframe")
        header_wrapper.pack(fill=X, padx=10, pady=10)
        try:
            config = self.model.load_layout_config()
            for field in config["header_fields"]:
                tb.Label(header_wrapper, text=field["label"]).grid(row=field["row"], column=field["col"], padx=5, pady=5, sticky=W)
                entry = tb.Entry(header_wrapper, width=field.get("width", 10))
                default_value = field.get("default", "")
                if field["id"] == "hours":
                    default_value = self.default_hours
                elif field["id"] == "goal_mph":
                    default_value = self.default_goal
                elif field["id"] == "total_molds":
                    default_value = "0"
                if default_value:
                    entry.insert(0, default_value)
                if field.get("readonly"):
                    entry.config(state="readonly", bootstyle=INFO)
                entry.grid(row=field["row"], column=field["col"] + 1, padx=5, pady=5, sticky=W)
                self.entries[field["id"]] = entry
                if not field.get("readonly"):
                    self.bind_dirty_tracking(entry, ("<KeyRelease>",))
                    entry.bind("<FocusOut>", self.controller.on_header_field_focus_out, add="+")

            if "hours" in self.entries:
                self.entries["hours"].bind("<KeyRelease>", self.controller.on_hours_changed, add="+")
            if "goal_mph" in self.entries:
                self.entries["goal_mph"].bind("<KeyRelease>", self.controller.on_goal_changed, add="+")
        except Exception as exc:
            tb.Label(header_wrapper, text=f"Layout Error: {exc}", bootstyle=DANGER).pack()

    def build_production_section(self):
        prod_wrapper = tb.Labelframe(self.content_stack, text=" Production Logging Center Jobs ", padding=10, style="Martin.Card.TLabelframe")
        prod_wrapper.pack(fill=X, padx=10, pady=5)
        prod_columns = tb.Frame(prod_wrapper, style="Martin.Surface.TFrame")
        prod_columns.pack(fill=X, pady=(0, 4))
        for text, width, side in (
            ("X", 3, LEFT),
            ("Shop Order", 15, LEFT),
            ("Part Number", 15, LEFT),
            ("Rate", 12, LEFT),
            ("Override", 8, LEFT),
            ("Molds", 10, LEFT),
            ("Time", 10, RIGHT),
        ):
            tb.Label(prod_columns, text=text, width=width, anchor=W if side == LEFT else E, style="Martin.Muted.TLabel").pack(side=side, padx=5)
        self.production_container = tb.Frame(prod_wrapper, style="Martin.Surface.TFrame")
        self.production_container.pack(fill=X)

    def build_downtime_section(self):
        dt_wrapper = tb.Labelframe(self.content_stack, text=" Production Logging Center Downtime Issues ", padding=10, style="Martin.Card.TLabelframe")
        dt_wrapper.pack(fill=X, padx=10, pady=5)
        self.downtime_container = tb.Frame(dt_wrapper, style="Martin.Surface.TFrame")
        self.downtime_container.pack(fill=X)

    def build_footer_section(self):
        self.footer = tb.Frame(self.content_stack, padding=20, style="Martin.Content.TFrame")
        self.footer.pack(fill=X)
        self.footer.columnconfigure(0, weight=1)

        footer_metrics = tb.Frame(self.footer, style="Martin.Content.TFrame")
        footer_metrics.grid(row=0, column=0, sticky=W, pady=(0, 10))

        self.eff_display_lbl = tb.Label(footer_metrics, text="EFF%: 0.00", font=("-size 14 -weight bold"))
        self.eff_display_lbl.pack(side=LEFT, padx=(0, 10))
        self.ghost_total_lbl = tb.Label(footer_metrics, text=DEFAULT_GHOST_LABEL, font=("-size 12 -weight bold"))
        self.ghost_total_lbl.pack(side=LEFT, padx=(0, 10))

        footer_actions = tb.Frame(self.footer, style="Martin.Content.TFrame")
        footer_actions.grid(row=1, column=0, sticky=W)

        button_specs = [
            (None, "Calculate All", self.controller.calculate_metrics, INFO),
            (None, "Save Draft", self.controller.save_draft, SECONDARY),
            (None, "Save and Open", self.controller.export_to_excel, SUCCESS),
            ("open_export_btn", "Open Last Export", self.controller.open_last_exported_file, INFO),
            ("print_export_btn", "Print Last Export", self.controller.print_last_exported_file, WARNING),
            ("balance_downtime_btn", "Balance Downtime", self.controller.balance_downtime_to_shift, WARNING),
            (None, "Import Excel", self.controller.import_from_excel_ui, INFO),
        ]

        for index, (attribute_name, text, command, bootstyle) in enumerate(button_specs):
            button = tb.Button(footer_actions, text=text, command=command, bootstyle=bootstyle)
            button.grid(row=index // 4, column=index % 4, padx=(0, 8), pady=4, sticky=W)
            if attribute_name is not None:
                setattr(self, attribute_name, button)

        balance_controls = tb.Frame(self.footer, style="Martin.Content.TFrame")
        balance_controls.grid(row=2, column=0, sticky="ew", pady=(8, 0))
        balance_controls.columnconfigure(2, weight=1)

        tb.Label(balance_controls, text="Balance Mix", style="Martin.Muted.TLabel").grid(row=0, column=0, sticky=W, padx=(0, 10))
        tb.Label(balance_controls, text="Even", style="Martin.Muted.TLabel").grid(row=0, column=1, sticky=W)

        self.balance_mix_scale = ttk.Scale(
            balance_controls,
            from_=0,
            to=100,
            orient=HORIZONTAL,
            variable=self.balance_mix_var,
            command=self.on_balance_mix_changed,
            length=180,
        )
        self.balance_mix_scale.grid(row=0, column=2, sticky="ew", padx=8)

        tb.Label(balance_controls, text="Weighted", style="Martin.Muted.TLabel").grid(row=0, column=3, sticky=E, padx=(0, 8))
        self.balance_mix_value_lbl = tb.Label(balance_controls, style="Martin.Muted.TLabel")
        self.balance_mix_value_lbl.grid(row=0, column=4, sticky=E)
        self.update_balance_mix_display()
        self.update_balance_downtime_button()

    def build_summary_section(self):
        self.summary_shell = tb.Frame(self.parent, padding=(10, 0, 10, 10), style="Martin.Content.TFrame")
        self.summary_frame = tb.Labelframe(self.summary_shell, text=" Visual Summary ", padding=12, style="Martin.Card.TLabelframe")
        self.summary_frame.pack(fill=BOTH, expand=True)

        self.summary_header = tb.Frame(self.summary_frame, style="Martin.Surface.TFrame")
        self.summary_header.pack(fill=X, pady=(0, 10))
        self.summary_title_lbl = tb.Label(self.summary_header, text="At-a-glance production balance", font=("-size 11 -weight bold"))
        self.summary_title_lbl.pack(side=LEFT)
        self.summary_status_lbl = tb.Label(self.summary_header, text="Expand the window to reveal charts.", style="Martin.Muted.TLabel")
        self.summary_status_lbl.pack(side=RIGHT)

        self.summary_cards = tb.Frame(self.summary_frame, style="Martin.Surface.TFrame")
        self.summary_cards.pack(fill=BOTH, expand=True)
        self.summary_cards.columnconfigure(0, weight=1)
        self.summary_cards.columnconfigure(1, weight=1)
        self.summary_cards.rowconfigure(0, weight=1)

        self.mold_chart_frame = tb.Labelframe(self.summary_cards, text=" Mold Contribution ", padding=10, style="Martin.Card.TLabelframe")
        self.mold_chart_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 6))
        self.mold_chart_canvas = tk.Canvas(self.mold_chart_frame, highlightthickness=0, bd=0, height=240)
        self.mold_chart_canvas.pack(fill=BOTH, expand=True)

        self.time_chart_frame = tb.Labelframe(self.summary_cards, text=" Production vs Downtime ", padding=10, style="Martin.Card.TLabelframe")
        self.time_chart_frame.grid(row=0, column=1, sticky="nsew", padx=(6, 0))
        self.time_chart_canvas = tk.Canvas(self.time_chart_frame, highlightthickness=0, bd=0, height=240)
        self.time_chart_canvas.pack(fill=BOTH, expand=True)

        self.mold_chart_canvas.bind("<Configure>", self.on_summary_canvas_resized, add="+")
        self.time_chart_canvas.bind("<Configure>", self.on_summary_canvas_resized, add="+")

    def apply_theme(self):
        root = self.parent.winfo_toplevel()
        self.summary_theme_tokens = get_theme_tokens(root=root)
        content_bg = self.summary_theme_tokens.get("content_bg", "#edf1f4")
        surface_bg = self.summary_theme_tokens.get("surface_bg", "#ffffff")
        surface_fg = self.summary_theme_tokens.get("surface_fg", "#152129")
        muted_fg = self.summary_theme_tokens.get("muted_fg", "#637782")
        border_color = self.summary_theme_tokens.get("border_color", "#c6d2d8")

        if hasattr(self, "summary_shell"):
            self.content_stack.configure(style="Martin.Content.TFrame")
            self.summary_shell.configure(style="Martin.Content.TFrame")
            self.summary_header.configure(style="Martin.Surface.TFrame")
            self.summary_cards.configure(style="Martin.Surface.TFrame")
            self.mold_chart_canvas.configure(background=surface_bg)
            self.time_chart_canvas.configure(background=surface_bg)
            self.summary_status_lbl.configure(style="Martin.Muted.TLabel")
            self.summary_title_lbl.configure(foreground=surface_fg)
            self.summary_status_lbl.configure(foreground=muted_fg)
            self.summary_frame.configure(style="Martin.Card.TLabelframe")
            self.mold_chart_frame.configure(style="Martin.Card.TLabelframe")
            self.time_chart_frame.configure(style="Martin.Card.TLabelframe")

        try:
            self.parent.configure(style="Martin.Content.TFrame")
        except Exception:
            try:
                self.parent.configure(bg=content_bg)
            except Exception:
                pass

        self.parent.option_add("*Canvas.highlightBackground", border_color)
        self.parent.option_add("*Canvas.highlightColor", border_color)
        self.schedule_summary_refresh()

    def on_parent_resized(self, _event=None):
        if self.summary_resize_after_id is not None:
            self.parent.after_cancel(self.summary_resize_after_id)
        self.summary_resize_after_id = self.parent.after(80, self.refresh_summary_panel)

    def on_summary_canvas_resized(self, _event=None):
        self.schedule_summary_refresh(delay=40)

    def schedule_summary_refresh(self, delay=80):
        if not hasattr(self, "summary_shell"):
            return
        if self.summary_refresh_after_id is not None:
            self.parent.after_cancel(self.summary_refresh_after_id)
        self.summary_refresh_after_id = self.parent.after(delay, self.refresh_summary_panel)

    def should_show_summary_panel(self):
        canvas = getattr(self.dispatcher, "canvas", None)
        width = self.parent.winfo_width() or self.parent.winfo_reqwidth()
        height = self.parent.winfo_height() or self.parent.winfo_reqheight()
        if canvas is not None:
            width = canvas.winfo_width() or width
            height = canvas.winfo_height() or height

        minimum_width = 900
        minimum_height = 620
        wide_layout_width = 980
        if width < minimum_width or height < minimum_height:
            return False

        occupied_height = 0
        stack = getattr(self, "content_stack", None)
        if stack is not None:
            try:
                occupied_height = stack.winfo_reqheight()
            except Exception:
                occupied_height = 0

        spare_height = height - occupied_height
        return spare_height >= 120 or width >= wide_layout_width

    def refresh_summary_panel(self):
        self.summary_refresh_after_id = None
        self.summary_resize_after_id = None
        if not hasattr(self, "summary_shell"):
            return

        should_show = self.should_show_summary_panel()
        visibility_changed = False
        if should_show and not self.summary_visible:
            self.summary_shell.pack(fill=X, anchor=N)
            self.summary_visible = True
            visibility_changed = True
        elif not should_show and self.summary_visible:
            self.summary_shell.pack_forget()
            self.summary_visible = False
            visibility_changed = True

        if not should_show:
            if visibility_changed:
                self.reset_shell_scroll_position()
            return

        mold_segments = self.get_mold_contribution_segments()
        time_segments = self.get_time_breakdown_segments()
        self.summary_status_lbl.config(text=self.build_summary_status_text(mold_segments, time_segments))
        self.draw_mold_chart(mold_segments)
        self.draw_time_chart(time_segments)
        if visibility_changed:
            self.reset_shell_scroll_position()

    def reset_shell_scroll_position(self):
        canvas = getattr(self.dispatcher, "canvas", None)
        if canvas is None:
            return
        try:
            canvas.yview_moveto(0)
        except Exception:
            return

    def build_summary_status_text(self, mold_segments, time_segments):
        total_jobs = len(mold_segments)
        total_minutes = sum(segment["value"] for segment in time_segments)
        if total_jobs == 0 and total_minutes == 0:
            return "Enter production and downtime data to populate the charts."
        return f"{total_jobs} contributing job{'s' if total_jobs != 1 else ''} | {total_minutes} tracked min"

    def get_mold_contribution_segments(self):
        palette = self.get_chart_palette()
        segments = []
        for index, row in enumerate(self.production_rows, start=1):
            try:
                molds = int(float(row["molds"].get() or 0))
            except Exception:
                molds = 0
            if molds <= 0:
                continue
            shop_order = row["shop_order"].get().strip()
            part_number = row["part_number"].get().strip()
            label_bits = [bit for bit in (shop_order, part_number) if bit]
            label = " / ".join(label_bits) if label_bits else f"Job {index}"
            segments.append({
                "label": label,
                "value": molds,
                "color": palette[(len(segments)) % len(palette)],
            })

        segments.sort(key=lambda item: item["value"], reverse=True)
        if len(segments) > 5:
            top_segments = segments[:5]
            other_total = sum(item["value"] for item in segments[5:])
            if other_total > 0:
                top_segments.append({
                    "label": "Other",
                    "value": other_total,
                    "color": self.summary_theme_tokens.get("muted_fg", "#637782"),
                })
            segments = top_segments
        return segments

    def get_time_breakdown_segments(self):
        palette = self.get_time_chart_palette()
        segments = [
            {"label": "Production", "value": max(0, self.get_production_total_minutes()), "color": palette[0]},
            {"label": "Downtime", "value": max(0, self.get_total_downtime_minutes()), "color": palette[1]},
            {"label": "Ghost", "value": max(0, self.get_ghost_time_minutes()), "color": palette[2]},
        ]
        return segments

    def get_time_chart_palette(self):
        style = tb.Style.get_instance()
        if style is not None:
            return [style.colors.success, style.colors.danger, style.colors.warning]
        return ["#6abf69", "#d9534f", "#ffb84d"]

    def get_chart_palette(self):
        accent = self.summary_theme_tokens.get("accent", "#0f7c8f")
        accent_soft = self.summary_theme_tokens.get("accent_soft", "#d6eef2")
        info_color = tb.Style.get_instance().colors.info if tb.Style.get_instance() else "#3db5dc"
        warning_color = tb.Style.get_instance().colors.warning if tb.Style.get_instance() else "#ffb84d"
        success_color = tb.Style.get_instance().colors.success if tb.Style.get_instance() else "#6abf69"
        muted = self.summary_theme_tokens.get("muted_fg", "#637782")
        return [accent, warning_color, info_color, success_color, accent_soft, muted]

    def draw_donut_chart(self, canvas, segments, empty_message, center_value, center_label, legend_formatter):
        self.prepare_chart_canvas(canvas)
        width = max(canvas.winfo_width(), 1)
        height = max(canvas.winfo_height(), 1)
        if width < 120 or height < 120:
            return

        total = sum(max(0, segment["value"]) for segment in segments)
        if total <= 0:
            self.draw_empty_chart_state(canvas, width, height, empty_message)
            return

        donut_size = max(120, min(int(width * 0.42), int(height * 0.72)))
        left = 24
        top = max(20, (height - donut_size) // 2)
        right = left + donut_size
        bottom = top + donut_size
        start = 90.0

        for segment in segments:
            value = max(0, segment["value"])
            if value <= 0:
                continue
            extent = (value / total) * 360
            canvas.create_arc(left, top, right, bottom, start=start, extent=-extent, fill=segment["color"], outline="")
            start -= extent

        inner_margin = max(26, donut_size // 5)
        inner_color = self.summary_theme_tokens.get("surface_bg", "#ffffff")
        canvas.create_oval(left + inner_margin, top + inner_margin, right - inner_margin, bottom - inner_margin, fill=inner_color, outline="")

        fg = self.summary_theme_tokens.get("surface_fg", "#152129")
        muted_fg = self.summary_theme_tokens.get("muted_fg", "#637782")
        canvas.create_text((left + right) / 2, top + donut_size / 2 - 10, text=center_value, fill=fg, font=("Segoe UI", 22, "bold"))
        canvas.create_text((left + right) / 2, top + donut_size / 2 + 16, text=center_label, fill=muted_fg, font=("Segoe UI", 10))

        legend_x = right + 28
        legend_y = 28
        for segment in segments:
            percentage = (max(0, segment["value"]) / total) * 100 if total else 0
            canvas.create_rectangle(legend_x, legend_y, legend_x + 14, legend_y + 14, fill=segment["color"], outline="")
            canvas.create_text(legend_x + 24, legend_y + 7, anchor="w", text=segment["label"], fill=fg, font=("Segoe UI", 10, "bold"))
            canvas.create_text(width - 18, legend_y + 7, anchor="e", text=legend_formatter(segment, percentage), fill=muted_fg, font=("Segoe UI", 10))
            legend_y += 28

    def draw_mold_chart(self, segments):
        self.draw_donut_chart(
            self.mold_chart_canvas,
            segments,
            "No mold data yet",
            str(sum(segment["value"] for segment in segments)),
            "Total molds",
            lambda segment, percentage: f"{segment['value']} ({percentage:.0f}%)",
        )

    def draw_time_chart(self, segments):
        self.draw_donut_chart(
            self.time_chart_canvas,
            segments,
            "No tracked time yet",
            str(sum(segment["value"] for segment in segments)),
            "Tracked min",
            lambda segment, percentage: f"{segment['value']} min ({percentage:.0f}%)",
        )

    def prepare_chart_canvas(self, canvas):
        canvas.delete("all")
        canvas.configure(background=self.summary_theme_tokens.get("surface_bg", "#ffffff"))

    def draw_empty_chart_state(self, canvas, width, height, message):
        fg = self.summary_theme_tokens.get("surface_fg", "#152129")
        muted_fg = self.summary_theme_tokens.get("muted_fg", "#637782")
        accent_soft = self.summary_theme_tokens.get("accent_soft", "#d6eef2")
        canvas.create_oval(width / 2 - 42, height / 2 - 56, width / 2 + 42, height / 2 + 28, outline="", fill=accent_soft)
        canvas.create_text(width / 2, height / 2 - 4, text=message, fill=fg, font=("Segoe UI", 12, "bold"))
        canvas.create_text(width / 2, height / 2 + 22, text="The chart will update as soon as the form has data.", fill=muted_fg, font=("Segoe UI", 10))

    def add_production_row(self):
        row_frame = tb.Frame(self.production_container)
        row_frame.pack(fill=X, pady=2)
        row = {
            "shop_order": tb.Entry(row_frame, width=15),
            "part_number": tb.Entry(row_frame, width=15),
            "rate_lookup": tb.Entry(row_frame, width=12),
            "molds": tb.Entry(row_frame, width=10),
            "time_calc": tb.Label(row_frame, text="0 min", width=10, font=("", 10, "bold")),
        }
        row["rate_override_enabled_var"] = tk.BooleanVar(value=False)
        row["rate_override_enabled"] = tb.Checkbutton(
            row_frame,
            variable=row["rate_override_enabled_var"],
            command=lambda current_row=row: self.controller.on_rate_override_toggled(current_row),
        )
        row["delete_btn"] = tb.Button(
            row_frame,
            text="X",
            width=3,
            bootstyle=DANGER,
            command=lambda current_row=row: self.controller.remove_production_row(current_row),
        )
        row["rate_lookup"].config(state="readonly")
        row["delete_btn"].pack(side=LEFT, padx=5)
        for key in ("shop_order", "part_number", "rate_lookup", "rate_override_enabled", "molds"):
            row[key].pack(side=LEFT, padx=5)
        row["time_calc"].pack(side=RIGHT, padx=10)
        row["part_number"].bind("<KeyRelease>", lambda _event: self.controller.update_row_math(), add="+")
        row["rate_lookup"].bind("<KeyRelease>", lambda _event: self.controller.update_row_math(), add="+")
        row["molds"].bind("<KeyRelease>", lambda _event: self.controller.update_row_math(), add="+")
        row["shop_order"].bind("<KeyRelease>", self.on_production_row_edited, add="+")
        self.bind_dirty_tracking(row["shop_order"], ("<KeyRelease>",))
        self.bind_dirty_tracking(row["part_number"], ("<KeyRelease>",))
        self.bind_dirty_tracking(row["rate_lookup"], ("<KeyRelease>",))
        self.bind_dirty_tracking(row["molds"], ("<KeyRelease>",))
        self.production_rows.append(row)
        self.update_ghost_total_display()
        return row

    def add_downtime_row(self):
        row_frame = tb.Frame(self.downtime_container)
        row_frame.pack(fill=X, pady=2)
        row = {
            "start": tb.Entry(row_frame, width=8),
            "stop": tb.Entry(row_frame, width=8),
            "code": tb.Combobox(row_frame, values=self.dt_codes, width=18, state="readonly"),
            "cause": tb.Entry(row_frame),
            "time_calc": tb.Label(row_frame, text="0 min", width=10, foreground="red", font=("", 10, "bold")),
        }
        row["delete_btn"] = tb.Button(
            row_frame,
            text="X",
            width=3,
            bootstyle=DANGER,
            command=lambda current_row=row: self.controller.remove_downtime_row(current_row),
        )
        row["delete_btn"].pack(side=LEFT, padx=5)
        row["start"].pack(side=LEFT, padx=5)
        row["stop"].pack(side=LEFT, padx=5)
        row["code"].pack(side=LEFT, padx=5)
        row["time_calc"].pack(side=RIGHT, padx=10)
        row["cause"].pack(side=LEFT, fill=X, expand=True, padx=5)
        row["start"].bind("<KeyRelease>", lambda _event: self.controller.update_row_math(), add="+")
        row["stop"].bind("<KeyRelease>", lambda _event: self.controller.update_row_math(), add="+")
        row["start"].bind("<KeyRelease>", self.on_downtime_row_value_changed, add="+")
        row["stop"].bind("<KeyRelease>", self.on_downtime_row_value_changed, add="+")
        row["code"].bind("<<ComboboxSelected>>", self.mark_dirty, add="+")
        row["code"].bind("<<ComboboxSelected>>", self.on_downtime_row_edited, add="+")
        row["cause"].bind("<KeyRelease>", self.on_downtime_row_edited, add="+")
        self.bind_dirty_tracking(row["start"], ("<KeyRelease>",))
        self.bind_dirty_tracking(row["stop"], ("<KeyRelease>",))
        self.bind_dirty_tracking(row["cause"], ("<KeyRelease>",))
        self.downtime_rows.append(row)
        return row

    def delete_production_row_with_save_reload(self, row):
        return self.controller.delete_production_row_with_save_reload(row)


    def delete_downtime_row_with_save_reload(self, row):
        return self.controller.delete_downtime_row_with_save_reload(row)

    def refresh_downtime_codes(self):
        return self.controller.refresh_downtime_codes()

    def parse_minutes_label(self, value):
        return self.model.parse_minutes_label(value)

    def on_hours_changed(self, _event=None):
        return self.controller.on_hours_changed(_event)

    def on_goal_changed(self, _event=None):
        return self.controller.on_goal_changed(_event)

    def on_header_field_focus_out(self, _event=None):
        return self.controller.on_header_field_focus_out(_event)

    def load_rates_data(self):
        return self.model.load_rates_data()

    def get_global_goal_rate(self):
        return self.controller.get_global_goal_rate()

    def calculate_total_molds(self):
        return self.controller.calculate_total_molds()

    def format_rate_value(self, value):
        return self.model.format_rate_value(value)

    def resolve_lookup_rate(self, part_number, rates_data, global_goal):
        return self.model.resolve_lookup_rate(part_number, rates_data, global_goal)

    def set_rate_lookup_value(self, row, value, editable=False):
        rate_entry = row["rate_lookup"]
        rate_entry.config(state="normal")
        rate_entry.delete(0, END)
        rate_entry.insert(0, value)
        rate_entry.config(state=("normal" if editable else "readonly"))

    def get_row_rate(self, row, rates_data, global_goal):
        return self.controller.get_row_rate(row, rates_data, global_goal)

    def on_rate_override_toggled(self, row):
        return self.controller.on_rate_override_toggled(row)

    def update_target_time_display(self):
        target_time_entry = self.entries.get("target_time")
        if target_time_entry is None:
            return
        target_value = self.controller.get_target_time_value()
        # Only call .cget('state') if widget supports it
        original_state = None
        if hasattr(target_time_entry, 'cget'):
            try:
                original_state = target_time_entry.cget("state")
            except Exception:
                original_state = None
        if original_state == "readonly":
            target_time_entry.config(state="normal")
        if hasattr(target_time_entry, 'delete') and hasattr(target_time_entry, 'insert'):
            target_time_entry.delete(0, END)
            target_time_entry.insert(0, target_value)
        if original_state == "readonly":
            target_time_entry.config(state="readonly")

    def update_ghost_total_display(self):
        if not hasattr(self, "ghost_total_lbl"):
            return
        ghost_minutes = self.get_ghost_time_minutes()
        self.displayed_ghost_minutes = ghost_minutes
        if ghost_minutes > 0:
            message = f"Ghost Time: {ghost_minutes} min missing"
            bootstyle = DANGER
        elif ghost_minutes < 0:
            message = f"Ghost Time: {abs(ghost_minutes)} min extra"
            bootstyle = SUCCESS
        else:
            message = DEFAULT_GHOST_LABEL
            bootstyle = SECONDARY
        self.ghost_total_lbl.config(text=message, bootstyle=bootstyle)
        self.schedule_summary_refresh()

    def collect_balance_state(self):
        return self.controller.collect_balance_state()

    def apply_balance_state(self, balance_state=None):
        return self.controller.apply_balance_state(balance_state)

    def reset_balance_state(self):
        return self.controller.reset_balance_state()

    def collect_balance_reference_minutes(self):
        return self.controller.collect_balance_reference_minutes()

    def apply_balance_reference_minutes(self, reference_minutes=None):
        return self.controller.apply_balance_reference_minutes(reference_minutes)

    def invalidate_balance_reference(self, reset_mode=True):
        return self.controller.invalidate_balance_reference(reset_mode=reset_mode)

    def capture_balance_reference(self, weighted_rows):
        return self.controller.capture_balance_reference(weighted_rows)

    def remember_balance_state(self, balanced_ghost_minutes, target_downtime_total):
        return self.controller.remember_balance_state(balanced_ghost_minutes, target_downtime_total)

    def update_balance_downtime_button(self):
        return self.controller.update_balance_downtime_button()

    def on_balance_mix_changed(self, _value=None):
        return self.controller.on_balance_mix_changed(_value)

    def on_downtime_row_value_changed(self, _event=None):
        return self.controller.on_downtime_row_value_changed(_event)

    def get_balance_mix_ratio(self):
        try:
            percentage = float(self.balance_mix_var.get())
        except Exception:
            percentage = 100.0
        return max(0.0, min(1.0, percentage / 100.0))

    def update_balance_mix_display(self):
        if self.balance_mix_value_lbl is None:
            return
        weighted_percentage = int(round(self.get_balance_mix_ratio() * 100))
        if weighted_percentage <= 0:
            message = "100% even"
        elif weighted_percentage >= 100:
            message = "100% weighted"
        else:
            message = f"{weighted_percentage}% weighted"
        self.balance_mix_value_lbl.config(text=message)

    def parse_clock_value(self, value):
        return self.model.parse_clock_value(value)

    def format_clock_value(self, total_minutes):
        return self.model.format_clock_value(total_minutes)

    def get_row_duration_minutes(self, row):
        return self.controller.get_row_duration_minutes(row)

    def is_balance_downtime_row(self, row):
        return self.controller.is_balance_downtime_row(row)

    def find_balance_downtime_row(self):
        return self.controller.find_balance_downtime_row()

    def remove_production_row(self, row):
        return self.controller.remove_production_row(row)

    def remove_downtime_row(self, row):
        return self.controller.remove_downtime_row(row)

    def set_downtime_row_duration(self, row, duration_minutes, set_balance_metadata=False):
        duration_minutes = max(0, int(duration_minutes))
        start_minutes = self.parse_clock_value(row["start"].get())
        if start_minutes is None:
            start_minutes = 0
            row["start"].delete(0, END)
            row["start"].insert(0, self.format_clock_value(start_minutes))
        row["stop"].delete(0, END)
        row["stop"].insert(0, self.format_clock_value(start_minutes + duration_minutes))
        if set_balance_metadata:
            if not row["code"].get().strip() and self.dt_codes:
                row["code"].set(self.dt_codes[0])
            row["cause"].delete(0, END)
            row["cause"].insert(0, BALANCE_DOWNTIME_CAUSE)

    def get_shift_total_minutes(self):
        return self.controller.get_shift_total_minutes()

    def get_production_total_minutes(self):
        return self.controller.get_production_total_minutes()

    def get_total_downtime_minutes(self):
        return self.controller.get_total_downtime_minutes()

    def get_ghost_time_minutes(self):
        return self.controller.get_ghost_time_minutes()

    def get_weighted_downtime_rows(self):
        return self.controller.get_weighted_downtime_rows()

    def apply_weighted_downtime_balance(self, target_total_minutes):
        return self.controller.apply_weighted_downtime_balance(target_total_minutes)

    def balance_downtime_to_shift(self):
        return self.controller.balance_downtime_to_shift()

    def set_entry_value(self, field_id, value):
        if field_id not in self.entries:
            return
        entry = self.entries[field_id]
        # Only call .cget('state') if widget supports it
        original_state = None
        if hasattr(entry, 'cget'):
            try:
                original_state = entry.cget("state")
            except Exception:
                original_state = None
        if original_state == "readonly":
            entry.config(state="normal")
        if hasattr(entry, 'delete') and hasattr(entry, 'insert'):
            entry.delete(0, END)
            entry.insert(0, str(value) if value is not None else "")
        if original_state == "readonly":
            entry.config(state="readonly")

    def get_widget_value(self, widget):
        if widget is None:
            return ""
        if hasattr(widget, "get"):
            try:
                return widget.get()
            except Exception:
                pass
        if hasattr(widget, "cget"):
            for option_name in ("text", "value"):
                try:
                    return widget.cget(option_name)
                except Exception:
                    continue
        return str(widget)

    def clear_dynamic_rows(self):
        for widget in self.production_container.winfo_children():
            widget.destroy()
        self.production_rows.clear()
        for widget in self.downtime_container.winfo_children():
            widget.destroy()
        self.downtime_rows.clear()
        self.schedule_summary_refresh()

    def populate_from_data(self, data, source_path=None, mark_dirty_after_load=False):
        balance_state = data.get("balance_state", {})
        self.apply_header_data(data.get("header", {}), mark_dirty=False)
        self.clear_dynamic_rows()
        for production_data in data.get("production", []):
            current_row = self.add_production_row()
            for key, value in production_data.items():
                if key == "rate_override_enabled":
                    current_row["rate_override_enabled_var"].set(str(value).strip().lower() in {"1", "true", "yes", "on"})
                    continue
                if key == "rate_lookup":
                    self.set_rate_lookup_value(current_row, str(value) if value is not None else "", editable=True)
                    continue
                if key in current_row and hasattr(current_row[key], "insert"):
                    current_row[key].delete(0, END)
                    current_row[key].insert(0, str(value) if value is not None else "")
            if current_row["rate_override_enabled_var"].get():
                current_row["rate_lookup"].config(state="normal")
        for downtime_data in data.get("downtime", []):
            current_row = self.add_downtime_row()
            for key, value in downtime_data.items():
                if key in current_row:
                    widget = current_row[key]
                    if hasattr(widget, "set"):
                        widget.set(str(value) if value is not None else "")
                    elif hasattr(widget, "insert"):
                        widget.delete(0, END)
                        widget.insert(0, str(value) if value is not None else "")
        if not self.production_rows:
            self.add_production_row()
        if not self.downtime_rows:
            self.add_downtime_row()
        self.update_row_math()
        self.calculate_metrics()
        self.update_target_time_display()
        self.update_ghost_total_display()
        self.apply_balance_state(balance_state)
        self.current_draft_path = source_path
        if mark_dirty_after_load:
            self.mark_dirty()
        else:
            self.mark_clean(data)
        self.schedule_summary_refresh()

    def list_pending_drafts(self):
        return self.controller.list_pending_drafts()

    def list_recovery_snapshots(self):
        return self.controller.list_recovery_snapshots()

    def get_latest_pending_draft(self):
        return self.controller.get_latest_pending_draft()

    def update_recovery_ui(self):
        drafts = self.list_pending_drafts()
        recovery_snapshots = self.list_recovery_snapshots()
        latest = drafts[0] if drafts else None
        self.latest_draft_path = latest["path"] if latest else None
        current_name = os.path.basename(self.current_draft_path) if self.current_draft_path else "No active draft"
        pending_count = len(drafts)
        snapshot_count = len(recovery_snapshots)
        dirty_text = "Unsaved changes" if self.has_unsaved_changes else "Saved"
        self.recovery_status_lbl.config(
            text=self.build_recovery_status_text(latest, current_name, dirty_text, pending_count, snapshot_count)
        )
        self.resume_latest_btn.config(state=(NORMAL if latest else DISABLED))
        self.delete_current_draft_btn.config(state=(NORMAL if self.current_draft_path and os.path.exists(self.current_draft_path) else DISABLED))
        self.update_recovery_wraplength()

    def confirm_discard_unsaved_changes(self):
        if not self.has_unsaved_changes:
            return True
        return messagebox.askyesno("Unsaved Changes", "You have unsaved changes in the current session. Continue and discard them?")

    def resume_latest_draft(self):
        return self.controller.resume_latest_draft()

    def open_recovery_viewer(self):
        return self.controller.open_recovery_viewer()

    def delete_current_draft(self):
        return self.controller.delete_current_draft()

    def delete_draft_file(self, draft_path):
        return self.controller.delete_draft_file(draft_path)

    def load_draft_path(self, draft_path, window=None):
        return self.controller.load_draft_path(draft_path, window=window)

    def update_row_math(self):
        return self.controller.update_row_math()

    def calculate_metrics(self):
        return self.controller.calculate_metrics()

    def export_to_excel(self):
        return self.controller.export_to_excel()

    def get_last_export_path(self):
        return self.controller.get_last_export_path()

    def update_export_action_state(self):
        return self.controller.update_export_action_state()

    def open_last_exported_file(self, show_prompt=True):
        return self.controller.open_last_exported_file(show_prompt=show_prompt)

    def print_last_exported_file(self):
        return self.controller.print_last_exported_file()

    def show_pending(self):
        top = tb.Toplevel(title="Pending Drafts")
        top.geometry("560x420")
        drafts = self.list_pending_drafts()
        if not drafts:
            tb.Label(top, text="No pending drafts found.").pack(pady=20)
            return
        outer = tb.Frame(top, padding=10)
        outer.pack(fill=BOTH, expand=True)
        canvas = tk.Canvas(outer, highlightthickness=0)
        canvas.pack(side=LEFT, fill=BOTH, expand=True)
        scrollbar = tb.Scrollbar(outer, orient=VERTICAL, command=canvas.yview)
        scrollbar.pack(side=RIGHT, fill=Y)
        canvas.configure(yscrollcommand=scrollbar.set)
        container = tb.Frame(canvas)
        window_id = canvas.create_window((0, 0), window=container, anchor="nw")

        def sync_scroll_region(_event=None):
            canvas.configure(scrollregion=canvas.bbox("all"))

        def sync_window_width(event):
            canvas.itemconfigure(window_id, width=event.width)

        container.bind("<Configure>", sync_scroll_region)
        canvas.bind("<Configure>", sync_window_width)
        tb.Label(container, text="Pending Drafts", font=("TkDefaultFont", 10, "bold"), bootstyle=PRIMARY).pack(anchor=W, pady=(0, 6))
        for draft in drafts:
            self.add_pending_draft_card(container, draft, top)
        self.dispatcher.bind_mousewheel_to_widget_tree(canvas, canvas)
        self.dispatcher.bind_mousewheel_to_widget_tree(container, canvas)

    def add_pending_draft_card(self, container, draft_record, window):
        card = tb.Labelframe(container, text=f" {draft_record['filename']} ", padding=10, style="Martin.Card.TLabelframe")
        card.pack(fill=X, pady=5)
        tb.Label(card, text=f"Saved: {draft_record['saved_at']}", style="Martin.Muted.TLabel").pack(anchor=W)
        tb.Label(card, text=f"Date: {draft_record['date'] or '(unknown)'} | Shift: {draft_record['shift'] or '(unknown)'}", style="Martin.Muted.TLabel").pack(anchor=W)
        actions = tb.Frame(card)
        actions.pack(fill=X, pady=(8, 0))
        tb.Button(actions, text="Resume", bootstyle=SUCCESS, command=lambda path=draft_record["path"], win=window: self.load_draft_path(path, win)).pack(side=LEFT, padx=(0, 6))
        tb.Button(actions, text="Delete", bootstyle=DANGER, command=lambda path=draft_record["path"], win=window: self.delete_pending_from_window(path, win)).pack(side=LEFT)

    def delete_pending_from_window(self, draft_path, window):
        if not messagebox.askyesno("Delete Draft", f"Delete {os.path.basename(draft_path)}?"):
            return
        self.delete_draft_file(draft_path)
        window.destroy()
        self.show_pending()

    def load_from_file(self, filename, window):
        path = os.path.join(self.get_pending_dir(), filename)
        self.load_draft_path(path, window)

    def import_from_excel_ui(self):
        return self.controller.import_from_excel_ui()

    def show_error(self, title, message):
        Messagebox.show_error(message, title)

    def show_toast(self, title, message, bootstyle=SUCCESS):
        self.dispatcher.show_toast(title, message, bootstyle)

    def ask_yes_no(self, title, message):
        return messagebox.askyesno(title, message)

    def ask_import_file_path(self):
        return filedialog.askopenfilename(
            title="Select Excel File to Import",
            filetypes=[("Excel files", "*.xlsx"), ("All files", "*.*")],
        )

    def sync_julian_cast_date(self, event=None):
        try:
            self.apply_header_data(self.get_raw_header_data(), mark_dirty=True)
        except Exception:
            pass

    def on_hide(self):
        return None

    def on_unload(self):
        return None
