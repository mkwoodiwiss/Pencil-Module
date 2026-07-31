"""Automation variants that add the active cycle number to every data row."""

from __future__ import annotations

import time

from .automation_meu import (
    AutomationError,
    BenchmarkTestSystem as _BenchmarkTestSystem,
    CleanTestSystem as _CleanTestSystem,
    FiltrationTestSystem as _FiltrationTestSystem,
)
from .data_logging import PSI_TO_KPA, build_data_row, write_header


class _CycleLoggingMixin:
    """Replace base logging with the cycle-aware MEU CSV schema."""

    def _open_logs(
        self,
        prefix: str,
        project: str,
        module_id: str,
        final_id: str,
        config,
    ) -> None:
        super()._open_logs(prefix, project, module_id, final_id, config)
        self.current_cycle = 0
        self.data_file.seek(0)
        self.data_file.truncate()
        write_header(self.data_writer)
        self.data_file.flush()

    def log_cycle(self, step: str) -> None:
        if not self.data_writer or not self.data_file:
            return
        self.data_writer.writerow(
            build_data_row(
                self.module,
                self._read_weight,
                self.current_cycle,
                step,
            )
        )
        self.data_file.flush()


class FiltrationTestSystem(_CycleLoggingMixin, _FiltrationTestSystem):
    def _run_cycles(self) -> None:
        config = self.config
        for cycle in range(config.cycle_count):
            self.current_cycle = cycle + 1
            self._report_progress("Purge", self.current_cycle, config.cycle_count)
            self._timed_phase(
                "Purge",
                config.purge_time,
                (self.FEED, self.WASTE),
                config.sample_time,
            )
            self._report_progress("Filter", self.current_cycle, config.cycle_count)
            self._run_filter_phase()
            self._report_progress("Backwash", self.current_cycle, config.cycle_count)
            self._run_backwash_phase()


class CleanTestSystem(_CycleLoggingMixin, _CleanTestSystem):
    def _run_cycles(self) -> None:
        for cycle in range(self.config.cycle_count):
            self.current_cycle = cycle + 1
            self._run_clean_cycle()


class BenchmarkTestSystem(_CycleLoggingMixin, _BenchmarkTestSystem):
    def _run_samples(self) -> None:
        started = time.monotonic()
        count = 0
        while time.monotonic() - started < self.config.duration:
            self._check_cancel()
            count += 1
            self.current_cycle = count
            self._report_progress("Benchmark Passive", count, 0)
            self.log_cycle("Benchmark Passive")
            time.sleep(max(1.0, self.config.interval))


__all__ = [
    "AutomationError",
    "PSI_TO_KPA",
    "FiltrationTestSystem",
    "CleanTestSystem",
    "BenchmarkTestSystem",
]
