"""Shared identifier coordination for the MEU v2 process tabs."""

from __future__ import annotations

import tkinter as tk


class IdentifierStateMixin:
    """Synchronize project, module, and sample identifiers across process tabs."""

    _v2_identifier_sync_active: bool
    _v2_identifier_trace_ids: list[tuple[tk.Variable, str]]

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

    def _initialize_v2_identifier_state(self) -> None:
        """Install traces after every v2 process tab has created its variables."""
        self._v2_identifier_sync_active = False
        self._v2_identifier_trace_ids = []
        self._install_v2_identifier_sync()
        self._synchronize_all_v2_identifiers()
        self._refresh_v2_identifier_summaries()

    def _install_v2_identifier_sync(self) -> None:
        for group in self._v2_identifier_groups():
            for variable_name in group:
                variable = getattr(self, variable_name, None)
                if variable is None:
                    continue
                trace_id = variable.trace_add(
                    "write",
                    lambda *_args, source=variable_name, members=group: self._sync_v2_identifier_group(
                        source, members
                    ),
                )
                self._v2_identifier_trace_ids.append((variable, trace_id))

    def _synchronize_all_v2_identifiers(self) -> None:
        for group in self._v2_identifier_groups():
            variables = self._available_v2_identifier_variables(group)
            if not variables:
                continue
            value = next(
                (str(variable.get()) for variable in variables if str(variable.get())),
                "",
            )
            self._set_v2_identifier_group(variables, value)

    def _sync_v2_identifier_group(
        self,
        source_name: str,
        group: tuple[str, ...],
    ) -> None:
        if self._v2_identifier_sync_active:
            return
        source = getattr(self, source_name, None)
        if source is None:
            return
        self._set_v2_identifier_group(
            self._available_v2_identifier_variables(group),
            str(source.get()),
        )
        self._refresh_v2_identifier_summaries()

    def _available_v2_identifier_variables(
        self,
        group: tuple[str, ...],
    ) -> list[tk.Variable]:
        return [
            variable
            for variable in (getattr(self, name, None) for name in group)
            if variable is not None
        ]

    def _set_v2_identifier_group(
        self,
        variables: list[tk.Variable],
        value: str,
    ) -> None:
        self._v2_identifier_sync_active = True
        try:
            for variable in variables:
                if str(variable.get()) != value:
                    variable.set(value)
        finally:
            self._v2_identifier_sync_active = False

    def _refresh_v2_identifier_summaries(self) -> None:
        for updater_name in (
            "_update_test_summary",
            "_update_benchmark_summary",
            "_update_post_scrub_summary",
            "_update_clean_summary",
        ):
            updater = getattr(self, updater_name, None)
            if callable(updater):
                updater()


__all__ = ["IdentifierStateMixin"]
