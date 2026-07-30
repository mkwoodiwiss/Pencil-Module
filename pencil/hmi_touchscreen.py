"""Touchscreen sizing refinements for the final MEU HMI."""

from __future__ import annotations

import tkinter as tk

from . import hmi_final as _hmi_final_module
from .hmi_final import HMI as _FinalHMI


class HMI(_FinalHMI):
    """Final HMI with moderately enlarged touchscreen settings fields."""

    SETTINGS_MIN_WIDTH = 700
    SETTINGS_MIN_HEIGHT = 450
    LEFT_COLUMN_WIDTH = 405
    RIGHT_COLUMN_WIDTH = 330
    SUMMARY_COLUMN_WIDTH = 16

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.after_idle(self._finish_touchscreen_settings_layout)

    def _finish_touchscreen_settings_layout(self) -> None:
        """Normalize controls and constrain the columns that own the panels."""
        self._normalize_clean_settings_controls()
        self.update_idletasks()
        self._normalize_bottom_columns()

    def _find_settings_frame(self, tab: tk.Widget):
        for widget in self._walk_widgets(tab):
            if not isinstance(widget, tk.LabelFrame):
                continue
            try:
                if widget.cget("text") == "Settings":
                    return widget
            except tk.TclError:
                pass
        return None

    def _find_panel(self, tab: tk.Widget, title: str):
        for widget in self._walk_widgets(tab):
            if not isinstance(widget, tk.LabelFrame):
                continue
            try:
                if widget.cget("text") == title:
                    return widget
            except tk.TclError:
                pass
        return None

    def _normalize_bottom_columns(self) -> None:
        """Constrain parent columns while allowing panels to keep natural height."""
        for tab in (self.test_tab, self.benchmark_tab, self.clean_tab):
            settings = self._find_settings_frame(tab)
            sensors = self._find_panel(tab, "Sensors")
            cycle = self._find_panel(tab, "Cycle Status")
            if settings is None:
                continue

            # The parent columns, not the LabelFrames, control the packed width.
            left_column = settings.master
            try:
                left_column.configure(width=self.LEFT_COLUMN_WIDTH)
                left_column.pack_propagate(False)
                settings.pack_configure(fill="x", anchor="sw")
                settings.configure(width=self.LEFT_COLUMN_WIDTH)
                settings.pack_propagate(True)
                settings.grid_propagate(True)
            except tk.TclError:
                pass

            # Keep summary text content-driven only vertically. Horizontal size is
            # fixed and the final HMI already ellipsizes long identifiers.
            for widget in self._walk_widgets(settings):
                try:
                    if isinstance(widget, tk.Label) and widget.cget("textvariable"):
                        widget.configure(
                            width=self.SUMMARY_COLUMN_WIDTH,
                            anchor="nw",
                            justify="left",
                        )
                    elif isinstance(widget, tk.Button):
                        widget.configure(width=11, padx=3)
                except tk.TclError:
                    pass

            if sensors is not None:
                right_column = sensors.master
                try:
                    right_column.configure(width=self.RIGHT_COLUMN_WIDTH)
                    right_column.pack_propagate(False)
                    sensors.pack_configure(fill="x", anchor="se")
                    sensors.configure(width=self.RIGHT_COLUMN_WIDTH)
                    sensors.grid_propagate(True)
                    if cycle is not None:
                        cycle.pack_configure(fill="x", anchor="se")
                        cycle.configure(width=self.RIGHT_COLUMN_WIDTH)
                        cycle.grid_propagate(True)
                except tk.TclError:
                    pass

        self.update_idletasks()

    def _normalize_clean_settings_controls(self) -> None:
        """Match the Clean settings button layout to Test and Benchmark."""
        if getattr(self, "_clean_settings_controls_normalized", False):
            return

        settings = self._find_settings_frame(self.clean_tab)
        if settings is None:
            return

        for widget in self._walk_widgets(settings):
            if not isinstance(widget, tk.Button):
                continue
            try:
                if widget.cget("text") in {
                    "Edit Settings",
                    "Calibrate",
                    "Tare FIL",
                    "Tare BW EFL",
                }:
                    manager = widget.winfo_manager()
                    if manager == "grid":
                        widget.grid_remove()
                    elif manager == "pack":
                        widget.pack_forget()
            except tk.TclError:
                pass

        controls = tk.Frame(settings)
        controls.grid(row=1, column=0, columnspan=5, padx=4, pady=(2, 4), sticky="ew")
        controls.columnconfigure((0, 1), weight=1)

        edit_button = tk.Button(
            controls,
            text="Edit Settings",
            command=self._edit_clean_settings,
        )
        calibrate_button = tk.Button(
            controls,
            text="Calibrate",
            command=self.calibrate,
        )
        tare_fil_button = tk.Button(controls, text="Tare FIL")
        tare_bw_button = tk.Button(controls, text="Tare BW EFL")
        tare_fil_button.configure(
            command=lambda button=tare_fil_button: self._start_manual_tare(0, button)
        )
        tare_bw_button.configure(
            command=lambda button=tare_bw_button: self._start_manual_tare(1, button)
        )

        edit_button.grid(row=0, column=0, padx=4, pady=3, sticky="ew")
        calibrate_button.grid(row=0, column=1, padx=4, pady=3, sticky="ew")
        tare_fil_button.grid(row=1, column=0, padx=4, pady=3, sticky="ew")
        tare_bw_button.grid(row=1, column=1, padx=4, pady=3, sticky="ew")

        self._clean_settings_controls_normalized = True

    def _style_settings_window(self, window: tk.Toplevel) -> None:
        """Make settings fields easier to tap without filling the whole display."""

        def enlarge(parent: tk.Widget) -> None:
            for child in parent.winfo_children():
                try:
                    if isinstance(child, tk.Entry):
                        child.configure(
                            font=("Arial", 16),
                            width=max(10, int(child.cget("width"))),
                        )
                    elif isinstance(child, tk.Checkbutton):
                        child.configure(font=("Arial", 15), padx=7, pady=3)
                    elif isinstance(child, tk.Label):
                        child.configure(font=("Arial", 15))
                    elif isinstance(child, tk.Button):
                        child.configure(
                            font=("Arial", 16, "bold"),
                            height=1,
                            padx=16,
                            pady=5,
                        )
                except (tk.TclError, ValueError):
                    pass

                try:
                    manager = child.winfo_manager()
                    if manager == "grid":
                        info = child.grid_info()
                        options = {
                            "padx": max(6, int(info.get("padx", 0) or 0)),
                            "pady": max(2, int(info.get("pady", 0) or 0)),
                        }
                        if isinstance(child, tk.Entry):
                            options["ipady"] = 3
                            options["ipadx"] = 5
                        elif isinstance(child, tk.Checkbutton):
                            options["ipady"] = 1
                            options["ipadx"] = 2
                        child.grid_configure(**options)
                    elif manager == "pack":
                        info = child.pack_info()
                        child.pack_configure(
                            padx=max(6, int(info.get("padx", 0) or 0)),
                            pady=max(3, int(info.get("pady", 0) or 0)),
                        )
                except (tk.TclError, ValueError):
                    pass

                enlarge(child)

        enlarge(window)

        try:
            window.grid_anchor("center")
            window.update_idletasks()
            screen_width = self.winfo_screenwidth()
            screen_height = self.winfo_screenheight()
            width = min(
                screen_width - 40,
                max(self.SETTINGS_MIN_WIDTH, window.winfo_reqwidth() + 50),
            )
            height = min(
                screen_height - 90,
                max(self.SETTINGS_MIN_HEIGHT, window.winfo_reqheight() + 12),
            )
            x = max(0, self.winfo_rootx() + (self.winfo_width() - width) // 2)
            y = max(0, self.winfo_rooty() + (self.winfo_height() - height) // 2)
            window.geometry(f"{width}x{height}+{x}+{y}")
            window.lift()
            window.focus_force()
        except tk.TclError:
            pass


# Preserve the historical module-level final HMI identity used by tests and imports.
_hmi_final_module.HMI = HMI

__all__ = ["HMI"]
