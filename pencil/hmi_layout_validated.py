"""Validated final layout corrections for the MEU touchscreen HMI."""

from __future__ import annotations

import tkinter as tk

from .hmi_layout_runtime import HMI as _LayoutHMI


class HMI(_LayoutHMI):
    """MEU HMI with compact, non-duplicated settings summaries."""

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        # The parent installs its layout on idle. Run this immediately afterward
        # so the finished interface contains one summary and one action area.
        self.after_idle(self._repair_settings_layouts)

    def _find_settings_frame(self, tab: tk.Widget) -> tk.LabelFrame | None:
        for widget in self._walk_widgets(tab):
            if not isinstance(widget, tk.LabelFrame):
                continue
            try:
                if widget.cget("text") == "Settings":
                    return widget
            except Exception:
                pass
        return None

    @staticmethod
    def _textvariable_name(widget: tk.Widget) -> str:
        try:
            return str(widget.cget("textvariable"))
        except Exception:
            return ""

    def _repair_settings_layouts(self) -> None:
        """Remove legacy summaries and build one compact two-column block."""
        self._repair_one_settings_layout(
            self.test_tab,
            self.test_summary_var,
            self._test_summary_left,
            self._test_summary_right,
            self._edit_test_settings,
        )
        self._repair_one_settings_layout(
            self.benchmark_tab,
            self.benchmark_summary_var,
            self._benchmark_summary_left,
            self._benchmark_summary_right,
            self._edit_benchmark_settings,
        )
        self._anchor_bottom_panels()
        self._bind_settings_action_buttons()
        self.update_idletasks()

    def _repair_one_settings_layout(
        self,
        tab: tk.Widget,
        legacy_var: tk.StringVar,
        left_var: tk.StringVar,
        right_var: tk.StringVar,
        edit_command,
    ) -> None:
        settings = self._find_settings_frame(tab)
        if settings is None:
            return

        variable_names = {str(legacy_var), str(left_var), str(right_var)}

        # Remove the original tall summary and the accidentally repurposed
        # action frame. Leave unrelated settings widgets untouched.
        for child in list(settings.winfo_children()):
            if isinstance(child, tk.Label) and self._textvariable_name(child) in variable_names:
                child.destroy()
                continue
            if isinstance(child, tk.Frame):
                contains_summary = any(
                    isinstance(grandchild, tk.Label)
                    and self._textvariable_name(grandchild) in variable_names
                    for grandchild in child.winfo_children()
                )
                if contains_summary:
                    child.destroy()

        summary_frame = tk.Frame(settings)
        summary_frame.grid(row=0, column=0, columnspan=5, sticky="ew", padx=6, pady=(2, 4))
        summary_frame.columnconfigure(0, weight=1)
        summary_frame.columnconfigure(1, weight=1)

        tk.Label(
            summary_frame,
            textvariable=left_var,
            justify="left",
            anchor="nw",
            font=("TkDefaultFont", 10),
        ).grid(row=0, column=0, sticky="nw")
        tk.Label(
            summary_frame,
            textvariable=right_var,
            justify="left",
            anchor="nw",
            font=("TkDefaultFont", 10),
        ).grid(row=0, column=1, sticky="nw", padx=(18, 0))

        action_frame = tk.Frame(settings)
        action_frame.grid(row=1, column=0, columnspan=5, sticky="ew", padx=5, pady=(2, 6))
        action_frame.columnconfigure((0, 1), weight=1)

        tk.Button(
            action_frame,
            text="Edit Settings",
            command=edit_command,
            width=13,
        ).grid(row=0, column=0, padx=4, pady=(0, 4), sticky="ew")
        tk.Button(
            action_frame,
            text="Calibrate",
            command=self.calibrate,
            width=13,
        ).grid(row=0, column=1, padx=4, pady=(0, 4), sticky="ew")

        tare_fil = tk.Button(action_frame, text="Tare FIL", width=13)
        tare_fil.grid(row=1, column=0, padx=4, sticky="ew")
        tare_fil.config(command=lambda button=tare_fil: self._start_manual_tare(0, button))

        tare_bw = tk.Button(action_frame, text="Tare BW EFL", width=13)
        tare_bw.grid(row=1, column=1, padx=4, sticky="ew")
        tare_bw.config(command=lambda button=tare_bw: self._start_manual_tare(1, button))


__all__ = ["HMI"]
