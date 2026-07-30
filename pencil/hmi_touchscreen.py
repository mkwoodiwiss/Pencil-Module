"""Touchscreen sizing refinements for the final MEU HMI."""

from __future__ import annotations

import tkinter as tk

from . import hmi_final as _hmi_final_module
from .hmi_final import HMI as _FinalHMI


class HMI(_FinalHMI):
    """Final HMI with moderately enlarged touchscreen settings fields."""

    SETTINGS_MIN_WIDTH = 700
    SETTINGS_MIN_HEIGHT = 450

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.after_idle(self._finish_touchscreen_settings_layout)

    def _finish_touchscreen_settings_layout(self) -> None:
        """Normalize Clean controls, then lock every Settings panel geometry."""
        self._normalize_clean_settings_controls()
        self.update_idletasks()
        self._normalize_settings_panels()

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

    def _normalize_settings_panels(self) -> None:
        """Use one fixed panel size so summary text cannot shift the layout."""
        frames = [
            frame
            for frame in (
                self._find_settings_frame(self.test_tab),
                self._find_settings_frame(self.benchmark_tab),
                self._find_settings_frame(self.clean_tab),
            )
            if frame is not None
        ]
        if not frames:
            return

        # Fixed-width summary labels prevent long identifiers from changing the
        # requested width. The final HMI already ellipsizes the displayed value.
        for frame in frames:
            for widget in self._walk_widgets(frame):
                if not isinstance(widget, tk.Label):
                    continue
                try:
                    if widget.cget("textvariable"):
                        widget.configure(width=20, anchor="nw", justify="left")
                except tk.TclError:
                    pass

        self.update_idletasks()
        panel_width = min(480, max(380, int(self.winfo_width() * 0.39)))
        available_heights = []
        for frame in frames:
            try:
                relative_top = frame.winfo_rooty() - self.winfo_rooty()
                available_heights.append(max(250, self.winfo_height() - relative_top - 8))
            except tk.TclError:
                pass
        panel_height = min(available_heights) if available_heights else 315

        for frame in frames:
            try:
                frame.configure(width=panel_width, height=panel_height)
                frame.pack_propagate(False)
                frame.grid_propagate(False)
            except tk.TclError:
                pass

    def _normalize_clean_settings_controls(self) -> None:
        """Match the Clean settings button layout to Test and Benchmark."""
        if getattr(self, "_clean_settings_controls_normalized", False):
            return

        settings = self._find_settings_frame(self.clean_tab)
        if settings is None:
            return

        # Hide the historical Clean controls and replace them with the same
        # two-by-two arrangement used on the Test and Benchmark tabs.
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
        controls.grid(row=1, column=0, columnspan=5, padx=5, pady=(2, 6), sticky="ew")
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

        edit_button.grid(row=0, column=0, padx=5, pady=4, sticky="ew")
        calibrate_button.grid(row=0, column=1, padx=5, pady=4, sticky="ew")
        tare_fil_button.grid(row=1, column=0, padx=5, pady=4, sticky="ew")
        tare_bw_button.grid(row=1, column=1, padx=5, pady=4, sticky="ew")

        self._clean_settings_controls_normalized = True

    def _style_settings_window(self, window: tk.Toplevel) -> None:
        """Make settings fields easier to tap without filling the whole display."""
        # This is the final styling layer. Do not call the historical styling
        # chain because the oldest runtime layer has no parent implementation.
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
