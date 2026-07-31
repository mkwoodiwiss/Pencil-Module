"""Reusable settings dialogs for filtration-style MEU processes."""

from __future__ import annotations

import tkinter as tk
from collections.abc import Callable
from dataclasses import dataclass

from .widgets import KeyboardEntry, NumericEntry


@dataclass(frozen=True)
class FiltrationDialogSpec:
    """Bindings and callbacks required to construct one filtration dialog."""

    title: str
    prefix: str
    update_summary: Callable[[], None]
    filter_weight_toggle: Callable[[], None]
    filter_time_toggle: Callable[[], None]
    backwash_weight_toggle: Callable[[], None]
    backwash_time_toggle: Callable[[], None]


class FiltrationSettingsDialogMixin:
    """Build identical Test and Post-Scrub settings dialogs."""

    def _build_filtration_settings_dialog(self, spec: FiltrationDialogSpec) -> None:
        variable_names = self._filtration_dialog_variable_names(spec.prefix)
        original_values = {
            name: getattr(self, name).get()
            for name in variable_names
        }

        window = tk.Toplevel(self)
        try:
            window.transient(self)
            window.focus_set()
        except tk.TclError:
            pass
        window.title(spec.title)

        variables = {
            name: getattr(self, variable_name)
            for name, variable_name in self._filtration_dialog_bindings(spec.prefix).items()
        }

        self._add_target_row(
            window,
            row=0,
            label="Filtration Target",
            weight_variable=variables["filter_weight"],
            time_variable=variables["filter_time"],
            use_weight_variable=variables["filter_use_weight"],
            use_time_variable=variables["filter_use_time"],
            weight_toggle=spec.filter_weight_toggle,
            time_toggle=spec.filter_time_toggle,
        )
        self._add_target_row(
            window,
            row=1,
            label="Backwash Target",
            weight_variable=variables["backwash_weight"],
            time_variable=variables["backwash_time"],
            use_weight_variable=variables["backwash_use_weight"],
            use_time_variable=variables["backwash_use_time"],
            weight_toggle=spec.backwash_weight_toggle,
            time_toggle=spec.backwash_time_toggle,
        )
        self._add_numeric_row(window, 2, "Purge Time", variables["purge_time"], "sec")
        self._add_numeric_row(window, 3, "Cycle Count", variables["cycle_count"])
        self._add_numeric_row(window, 4, "Sample Time", variables["sample_time"], "sec")
        self._add_text_row(window, 5, "Project", variables["project"])
        self._add_text_row(window, 6, "Module ID", variables["module_id"])
        self._add_text_row(window, 7, "Sample ID", variables["sample_id"])

        button_frame = tk.Frame(window)
        button_frame.grid(row=8, column=0, columnspan=5, pady=5)

        def save() -> None:
            spec.update_summary()
            window.destroy()

        def cancel() -> None:
            for name, value in original_values.items():
                getattr(self, name).set(value)
            window.destroy()

        tk.Button(button_frame, text="Save", command=save).pack(side="left", padx=5)
        tk.Button(button_frame, text="Cancel", command=cancel).pack(side="left", padx=5)

    @staticmethod
    def _filtration_dialog_variable_names(prefix: str) -> tuple[str, ...]:
        return tuple(FiltrationSettingsDialogMixin._filtration_dialog_bindings(prefix).values())

    @staticmethod
    def _filtration_dialog_bindings(prefix: str) -> dict[str, str]:
        return {
            "filter_weight": f"{prefix}filt_target_weight_var",
            "filter_time": f"{prefix}filt_target_time_var",
            "filter_use_weight": f"{prefix}filt_use_weight_var",
            "filter_use_time": f"{prefix}filt_use_time_var",
            "backwash_weight": f"{prefix}bw_target_weight_var",
            "backwash_time": f"{prefix}bw_target_time_var",
            "backwash_use_weight": f"{prefix}bw_use_weight_var",
            "backwash_use_time": f"{prefix}bw_use_time_var",
            "purge_time": f"{prefix}purge_time_var" if prefix else "refill_time_var",
            "cycle_count": f"{prefix}cycle_count_var",
            "sample_time": f"{prefix}sample_time_var",
            "project": f"{prefix}project_var",
            "module_id": f"{prefix}module_id_var",
            "sample_id": f"{prefix}sample_id_var",
        }

    @staticmethod
    def _add_target_row(
        window: tk.Misc,
        *,
        row: int,
        label: str,
        weight_variable: tk.Variable,
        time_variable: tk.Variable,
        use_weight_variable: tk.Variable,
        use_time_variable: tk.Variable,
        weight_toggle: Callable[[], None],
        time_toggle: Callable[[], None],
    ) -> None:
        tk.Label(window, text=label).grid(row=row, column=0, sticky="w")
        NumericEntry(window, textvariable=weight_variable, width=7).grid(row=row, column=1)
        tk.Checkbutton(
            window,
            text="g",
            variable=use_weight_variable,
            command=weight_toggle,
        ).grid(row=row, column=2, sticky="w")
        NumericEntry(window, textvariable=time_variable, width=7).grid(row=row, column=3)
        tk.Checkbutton(
            window,
            text="s",
            variable=use_time_variable,
            command=time_toggle,
        ).grid(row=row, column=4, sticky="w")

    @staticmethod
    def _add_numeric_row(
        window: tk.Misc,
        row: int,
        label: str,
        variable: tk.Variable,
        unit: str = "",
    ) -> None:
        tk.Label(window, text=label).grid(row=row, column=0, sticky="w")
        NumericEntry(window, textvariable=variable, width=7).grid(row=row, column=1)
        if unit:
            tk.Label(window, text=unit).grid(row=row, column=2, sticky="w")

    @staticmethod
    def _add_text_row(
        window: tk.Misc,
        row: int,
        label: str,
        variable: tk.Variable,
    ) -> None:
        tk.Label(window, text=label).grid(row=row, column=0, sticky="w")
        KeyboardEntry(window, textvariable=variable, width=7).grid(row=row, column=1)

    def _edit_test_settings(self) -> None:
        self._open_settings_dialog(
            lambda: self._build_filtration_settings_dialog(
                FiltrationDialogSpec(
                    title="Edit Test Settings",
                    prefix="",
                    update_summary=self._update_test_summary,
                    filter_weight_toggle=self._toggle_filt_weight,
                    filter_time_toggle=self._toggle_filt_time,
                    backwash_weight_toggle=self._toggle_bw_weight,
                    backwash_time_toggle=self._toggle_bw_time,
                )
            )
        )

    def _edit_post_scrub_settings(self) -> None:
        self._open_settings_dialog(
            lambda: self._build_filtration_settings_dialog(
                FiltrationDialogSpec(
                    title="Edit Post-Scrub Settings",
                    prefix="post_scrub_",
                    update_summary=self._update_post_scrub_summary,
                    filter_weight_toggle=self._toggle_post_scrub_filt_weight,
                    filter_time_toggle=self._toggle_post_scrub_filt_time,
                    backwash_weight_toggle=self._toggle_post_scrub_bw_weight,
                    backwash_time_toggle=self._toggle_post_scrub_bw_time,
                )
            )
        )


__all__ = ["FiltrationDialogSpec", "FiltrationSettingsDialogMixin"]
