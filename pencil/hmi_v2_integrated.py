"""Coherent v2 dialog and shared-identifier integration.

Test and Post-Scrub use one settings-dialog builder. Shared identifiers are
synchronized only after every v2 variable has been created.
"""

from __future__ import annotations

import tkinter as tk
from collections.abc import Callable

from .hmi_v2_summary_text import HMI as _V2SummaryHMI
from .widgets import KeyboardEntry, NumericEntry


class HMI(_V2SummaryHMI):
    """Final v2 HMI with shared dialog construction and identifier state."""

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._v2_identifier_sync_active = False
        self._install_v2_identifier_sync()
        self._synchronize_all_identifiers()
        self._refresh_v2_summaries()

    # ------------------------------------------------------------------
    # Shared identifier state
    # ------------------------------------------------------------------
    @staticmethod
    def _v2_identifier_groups() -> tuple[tuple[str, ...], ...]:
        return (
            (
                "project_var",
                "benchmark_project_var",
                "post_scrub_project_var",
                "clean_project_var",
            ),
            (
                "module_id_var",
                "benchmark_module_id_var",
                "post_scrub_module_id_var",
                "clean_module_id_var",
            ),
            (
                "sample_id_var",
                "benchmark_sample_id_var",
                "post_scrub_sample_id_var",
            ),
        )

    def _install_v2_identifier_sync(self) -> None:
        """Attach traces after all Test, Benchmark, Post-Scrub, and Clean vars exist."""
        self._v2_identifier_trace_ids: list[tuple[tk.Variable, str]] = []
        for group in self._v2_identifier_groups():
            for name in group:
                variable = getattr(self, name, None)
                if variable is None:
                    continue
                trace_id = variable.trace_add(
                    "write",
                    lambda *_args, source=name, members=group: self._sync_v2_identifier_group(
                        source, members
                    ),
                )
                self._v2_identifier_trace_ids.append((variable, trace_id))

    def _synchronize_all_identifiers(self) -> None:
        """Initialize each group from the first non-empty value, then share it."""
        for group in self._v2_identifier_groups():
            available = [getattr(self, name, None) for name in group]
            variables = [variable for variable in available if variable is not None]
            if not variables:
                continue
            value = next((str(variable.get()) for variable in variables if str(variable.get())), "")
            self._set_identifier_group(variables, value)

    def _sync_v2_identifier_group(self, source_name: str, group: tuple[str, ...]) -> None:
        if self._v2_identifier_sync_active:
            return
        source = getattr(self, source_name, None)
        if source is None:
            return
        variables = [
            variable
            for variable in (getattr(self, name, None) for name in group)
            if variable is not None
        ]
        self._set_identifier_group(variables, str(source.get()))
        self._refresh_v2_summaries()

    def _set_identifier_group(self, variables: list[tk.Variable], value: str) -> None:
        self._v2_identifier_sync_active = True
        try:
            for variable in variables:
                if str(variable.get()) != value:
                    variable.set(value)
        finally:
            self._v2_identifier_sync_active = False

    def _refresh_v2_summaries(self) -> None:
        for updater_name in (
            "_update_test_summary",
            "_update_benchmark_summary",
            "_update_post_scrub_summary",
            "_update_clean_summary",
        ):
            updater = getattr(self, updater_name, None)
            if callable(updater):
                updater()

    # ------------------------------------------------------------------
    # Summary terminology
    # ------------------------------------------------------------------
    @staticmethod
    def _rename_identifier_sample_line(text: str) -> str:
        """Rename only the final identifier line, not the Sample Time line."""
        lines = str(text).splitlines()
        for index in range(len(lines) - 1, -1, -1):
            if lines[index].startswith("Sample: "):
                lines[index] = "Sample ID: " + lines[index][len("Sample: ") :]
                break
        return "\n".join(lines)

    def _update_test_summary(self) -> None:
        super()._update_test_summary()
        for name in ("test_summary_var", "_test_summary_left", "_test_summary_right"):
            variable = getattr(self, name, None)
            if variable is not None:
                variable.set(self._rename_identifier_sample_line(variable.get()))

    def _update_benchmark_summary(self) -> None:
        super()._update_benchmark_summary()
        for name in (
            "benchmark_summary_var",
            "_benchmark_summary_left",
            "_benchmark_summary_right",
        ):
            variable = getattr(self, name, None)
            if variable is not None:
                variable.set(self._rename_identifier_sample_line(variable.get()))

    # ------------------------------------------------------------------
    # One dialog builder for Test and Post-Scrub
    # ------------------------------------------------------------------
    def _build_filtration_settings_dialog(
        self,
        *,
        title: str,
        prefix: str,
        update_summary: Callable[[], None],
        filter_weight_toggle: Callable[[], None],
        filter_time_toggle: Callable[[], None],
        backwash_weight_toggle: Callable[[], None],
        backwash_time_toggle: Callable[[], None],
    ) -> None:
        names = (
            f"{prefix}filt_target_weight_var",
            f"{prefix}filt_target_time_var",
            f"{prefix}filt_use_weight_var",
            f"{prefix}filt_use_time_var",
            f"{prefix}bw_target_weight_var",
            f"{prefix}bw_target_time_var",
            f"{prefix}bw_use_weight_var",
            f"{prefix}bw_use_time_var",
            f"{prefix}purge_time_var" if prefix else "refill_time_var",
            f"{prefix}cycle_count_var",
            f"{prefix}sample_time_var",
            f"{prefix}project_var",
            f"{prefix}module_id_var",
            f"{prefix}sample_id_var",
        )
        original = {name: getattr(self, name).get() for name in names}

        window = tk.Toplevel(self)
        try:
            window.transient(self)
            window.focus_set()
        except Exception:
            pass
        window.title(title)

        filter_weight = getattr(self, f"{prefix}filt_target_weight_var")
        filter_time = getattr(self, f"{prefix}filt_target_time_var")
        filter_use_weight = getattr(self, f"{prefix}filt_use_weight_var")
        filter_use_time = getattr(self, f"{prefix}filt_use_time_var")
        backwash_weight = getattr(self, f"{prefix}bw_target_weight_var")
        backwash_time = getattr(self, f"{prefix}bw_target_time_var")
        backwash_use_weight = getattr(self, f"{prefix}bw_use_weight_var")
        backwash_use_time = getattr(self, f"{prefix}bw_use_time_var")
        purge_time = getattr(self, f"{prefix}purge_time_var") if prefix else self.refill_time_var
        cycle_count = getattr(self, f"{prefix}cycle_count_var")
        sample_time = getattr(self, f"{prefix}sample_time_var")
        project = getattr(self, f"{prefix}project_var")
        module_id = getattr(self, f"{prefix}module_id_var")
        sample_id = getattr(self, f"{prefix}sample_id_var")

        tk.Label(window, text="Filtration Target").grid(row=0, column=0, sticky="w")
        NumericEntry(window, textvariable=filter_weight, width=7).grid(row=0, column=1)
        tk.Checkbutton(
            window,
            text="g",
            variable=filter_use_weight,
            command=filter_weight_toggle,
        ).grid(row=0, column=2, sticky="w")
        NumericEntry(window, textvariable=filter_time, width=7).grid(row=0, column=3)
        tk.Checkbutton(
            window,
            text="s",
            variable=filter_use_time,
            command=filter_time_toggle,
        ).grid(row=0, column=4, sticky="w")

        tk.Label(window, text="Backwash Target").grid(row=1, column=0, sticky="w")
        NumericEntry(window, textvariable=backwash_weight, width=7).grid(row=1, column=1)
        tk.Checkbutton(
            window,
            text="g",
            variable=backwash_use_weight,
            command=backwash_weight_toggle,
        ).grid(row=1, column=2, sticky="w")
        NumericEntry(window, textvariable=backwash_time, width=7).grid(row=1, column=3)
        tk.Checkbutton(
            window,
            text="s",
            variable=backwash_use_time,
            command=backwash_time_toggle,
        ).grid(row=1, column=4, sticky="w")

        tk.Label(window, text="Purge Time").grid(row=2, column=0, sticky="w")
        NumericEntry(window, textvariable=purge_time, width=7).grid(row=2, column=1)
        tk.Label(window, text="sec").grid(row=2, column=2, sticky="w")

        tk.Label(window, text="Cycle Count").grid(row=3, column=0, sticky="w")
        NumericEntry(window, textvariable=cycle_count, width=7).grid(row=3, column=1)

        tk.Label(window, text="Sample Time").grid(row=4, column=0, sticky="w")
        NumericEntry(window, textvariable=sample_time, width=7).grid(row=4, column=1)
        tk.Label(window, text="sec").grid(row=4, column=2, sticky="w")

        tk.Label(window, text="Project").grid(row=5, column=0, sticky="w")
        KeyboardEntry(window, textvariable=project, width=7).grid(row=5, column=1)

        tk.Label(window, text="Module ID").grid(row=6, column=0, sticky="w")
        KeyboardEntry(window, textvariable=module_id, width=7).grid(row=6, column=1)

        tk.Label(window, text="Sample ID").grid(row=7, column=0, sticky="w")
        KeyboardEntry(window, textvariable=sample_id, width=7).grid(row=7, column=1)

        button_frame = tk.Frame(window)
        button_frame.grid(row=8, column=0, columnspan=5, pady=5)

        def save() -> None:
            update_summary()
            window.destroy()

        def cancel() -> None:
            for name, value in original.items():
                getattr(self, name).set(value)
            window.destroy()

        tk.Button(button_frame, text="Save", command=save).pack(side="left", padx=5)
        tk.Button(button_frame, text="Cancel", command=cancel).pack(side="left", padx=5)

    def _edit_test_settings(self) -> None:
        self._open_settings_dialog(
            lambda: self._build_filtration_settings_dialog(
                title="Edit Test Settings",
                prefix="",
                update_summary=self._update_test_summary,
                filter_weight_toggle=self._toggle_filt_weight,
                filter_time_toggle=self._toggle_filt_time,
                backwash_weight_toggle=self._toggle_bw_weight,
                backwash_time_toggle=self._toggle_bw_time,
            )
        )

    def _edit_post_scrub_settings(self) -> None:
        self._open_settings_dialog(
            lambda: self._build_filtration_settings_dialog(
                title="Edit Post-Scrub Settings",
                prefix="post_scrub_",
                update_summary=self._update_post_scrub_summary,
                filter_weight_toggle=self._toggle_post_scrub_filt_weight,
                filter_time_toggle=self._toggle_post_scrub_filt_time,
                backwash_weight_toggle=self._toggle_post_scrub_bw_weight,
                backwash_time_toggle=self._toggle_post_scrub_bw_time,
            )
        )


__all__ = ["HMI"]
