"""Production composition point for the MEU v2 HMI."""

from __future__ import annotations

from .hmi_filtration_dialogs import FiltrationSettingsDialogMixin
from .hmi_identifier_state import IdentifierStateMixin
from .hmi_v2_summary_text import HMI as _V2SummaryHMI


class HMI(
    FiltrationSettingsDialogMixin,
    IdentifierStateMixin,
    _V2SummaryHMI,
):
    """Final v2 HMI assembled from focused behavior components."""

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._initialize_v2_identifier_state()

    @staticmethod
    def _rename_identifier_sample_line(text: str) -> str:
        """Rename only the identifier line, leaving Sample Time unchanged."""
        lines = str(text).splitlines()
        for index in range(len(lines) - 1, -1, -1):
            if lines[index].startswith("Sample: "):
                lines[index] = "Sample ID: " + lines[index][len("Sample: ") :]
                break
        return "\n".join(lines)

    def _update_test_summary(self) -> None:
        super()._update_test_summary()
        self._rename_summary_sample_fields(
            "test_summary_var",
            "_test_summary_left",
            "_test_summary_right",
        )

    def _update_benchmark_summary(self) -> None:
        super()._update_benchmark_summary()
        self._rename_summary_sample_fields(
            "benchmark_summary_var",
            "_benchmark_summary_left",
            "_benchmark_summary_right",
        )

    def _rename_summary_sample_fields(self, *variable_names: str) -> None:
        for variable_name in variable_names:
            variable = getattr(self, variable_name, None)
            if variable is not None:
                variable.set(self._rename_identifier_sample_line(variable.get()))


__all__ = ["HMI"]
