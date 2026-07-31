"""Make the Post-Scrub settings dialog identical to the Test dialog."""

from __future__ import annotations

import tkinter as tk

from .hmi_v2_tk_compat import HMI as _V2TkCompatHMI
from .widgets import KeyboardEntry, NumericEntry


class HMI(_V2TkCompatHMI):
    """MEU v2 HMI with a Test-identical Post-Scrub settings dialog."""

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.post_scrub_filt_use_time_var = tk.BooleanVar(
            value=not self.post_scrub_filt_use_weight_var.get()
        )
        self.post_scrub_bw_use_time_var = tk.BooleanVar(
            value=not self.post_scrub_bw_use_weight_var.get()
        )

    def _toggle_post_scrub_filt_weight(self) -> None:
        if self.post_scrub_filt_use_weight_var.get():
            self.post_scrub_filt_use_time_var.set(False)
        elif not self.post_scrub_filt_use_time_var.get():
            self.post_scrub_filt_use_time_var.set(True)

    def _toggle_post_scrub_filt_time(self) -> None:
        if self.post_scrub_filt_use_time_var.get():
            self.post_scrub_filt_use_weight_var.set(False)
        elif not self.post_scrub_filt_use_weight_var.get():
            self.post_scrub_filt_use_weight_var.set(True)

    def _toggle_post_scrub_bw_weight(self) -> None:
        if self.post_scrub_bw_use_weight_var.get():
            self.post_scrub_bw_use_time_var.set(False)
        elif not self.post_scrub_bw_use_time_var.get():
            self.post_scrub_bw_use_time_var.set(True)

    def _toggle_post_scrub_bw_time(self) -> None:
        if self.post_scrub_bw_use_time_var.get():
            self.post_scrub_bw_use_weight_var.set(False)
        elif not self.post_scrub_bw_use_weight_var.get():
            self.post_scrub_bw_use_time_var.set(True)

    def _edit_post_scrub_settings(self) -> None:
        """Open Post-Scrub through the exact same wrapper used by Test."""
        self._open_settings_dialog(self._build_post_scrub_settings_dialog)

    def _build_post_scrub_settings_dialog(self) -> None:
        """Build the same eight-row settings form as Test with Post-Scrub variables."""
        variable_names = (
            "post_scrub_filt_target_weight_var",
            "post_scrub_filt_target_time_var",
            "post_scrub_filt_use_weight_var",
            "post_scrub_filt_use_time_var",
            "post_scrub_bw_target_weight_var",
            "post_scrub_bw_target_time_var",
            "post_scrub_bw_use_weight_var",
            "post_scrub_bw_use_time_var",
            "post_scrub_purge_time_var",
            "post_scrub_cycle_count_var",
            "post_scrub_sample_time_var",
            "post_scrub_project_var",
            "post_scrub_module_id_var",
            "post_scrub_sample_id_var",
        )
        original = {name: getattr(self, name).get() for name in variable_names}

        window = tk.Toplevel(self)
        try:
            window.transient(self)
            window.focus_set()
        except Exception:
            pass
        window.title("Edit Post-Scrub Settings")

        tk.Label(window, text="Filtration Target").grid(row=0, column=0, sticky="w")
        NumericEntry(
            window,
            textvariable=self.post_scrub_filt_target_weight_var,
            width=7,
        ).grid(row=0, column=1)
        tk.Checkbutton(
            window,
            text="g",
            variable=self.post_scrub_filt_use_weight_var,
            command=self._toggle_post_scrub_filt_weight,
        ).grid(row=0, column=2, sticky="w")
        NumericEntry(
            window,
            textvariable=self.post_scrub_filt_target_time_var,
            width=7,
        ).grid(row=0, column=3)
        tk.Checkbutton(
            window,
            text="s",
            variable=self.post_scrub_filt_use_time_var,
            command=self._toggle_post_scrub_filt_time,
        ).grid(row=0, column=4, sticky="w")

        tk.Label(window, text="Backwash Target").grid(row=1, column=0, sticky="w")
        NumericEntry(
            window,
            textvariable=self.post_scrub_bw_target_weight_var,
            width=7,
        ).grid(row=1, column=1)
        tk.Checkbutton(
            window,
            text="g",
            variable=self.post_scrub_bw_use_weight_var,
            command=self._toggle_post_scrub_bw_weight,
        ).grid(row=1, column=2, sticky="w")
        NumericEntry(
            window,
            textvariable=self.post_scrub_bw_target_time_var,
            width=7,
        ).grid(row=1, column=3)
        tk.Checkbutton(
            window,
            text="s",
            variable=self.post_scrub_bw_use_time_var,
            command=self._toggle_post_scrub_bw_time,
        ).grid(row=1, column=4, sticky="w")

        tk.Label(window, text="Purge Time").grid(row=2, column=0, sticky="w")
        NumericEntry(
            window,
            textvariable=self.post_scrub_purge_time_var,
            width=7,
        ).grid(row=2, column=1)
        tk.Label(window, text="sec").grid(row=2, column=2, sticky="w")

        tk.Label(window, text="Cycle Count").grid(row=3, column=0, sticky="w")
        NumericEntry(
            window,
            textvariable=self.post_scrub_cycle_count_var,
            width=7,
        ).grid(row=3, column=1)

        tk.Label(window, text="Sample Time").grid(row=4, column=0, sticky="w")
        NumericEntry(
            window,
            textvariable=self.post_scrub_sample_time_var,
            width=7,
        ).grid(row=4, column=1)
        tk.Label(window, text="sec").grid(row=4, column=2, sticky="w")

        tk.Label(window, text="Project").grid(row=5, column=0, sticky="w")
        KeyboardEntry(
            window,
            textvariable=self.post_scrub_project_var,
            width=7,
        ).grid(row=5, column=1)

        tk.Label(window, text="Module ID").grid(row=6, column=0, sticky="w")
        KeyboardEntry(
            window,
            textvariable=self.post_scrub_module_id_var,
            width=7,
        ).grid(row=6, column=1)

        tk.Label(window, text="Sample ID").grid(row=7, column=0, sticky="w")
        KeyboardEntry(
            window,
            textvariable=self.post_scrub_sample_id_var,
            width=7,
        ).grid(row=7, column=1)

        button_frame = tk.Frame(window)
        button_frame.grid(row=8, column=0, columnspan=5, pady=5)

        def save() -> None:
            self._update_post_scrub_summary()
            window.destroy()

        def cancel() -> None:
            for name, value in original.items():
                getattr(self, name).set(value)
            window.destroy()

        tk.Button(button_frame, text="Save", command=save).pack(side="left", padx=5)
        tk.Button(button_frame, text="Cancel", command=cancel).pack(side="left", padx=5)


__all__ = ["HMI"]
