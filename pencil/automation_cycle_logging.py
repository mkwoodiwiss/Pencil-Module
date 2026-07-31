"""Automation variants that add the active cycle number to every data row."""

from __future__ import annotations

import time
from typing import Callable, Optional

from .automation_lifecycle import AutomationLifecycleMixin
from .automation_meu import (
    AutomationError,
    BenchmarkTestSystem as _BenchmarkTestSystem,
    CleanTestSystem as _CleanTestSystem,
    FiltrationTestSystem as _FiltrationTestSystem,
)
from .config_meu import BenchmarkConfig, CleanConfig, FiltrationConfig
from .data_logging import PSI_TO_KPA, build_data_row, write_header
from .hardware import MEU


class _CycleLoggingMixin(AutomationLifecycleMixin):
    """Add cycle-aware logging and shared lifecycle behavior."""

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

    def _report_progress(self, step: str, current: int, total: int) -> None:
        if self.progress_callback:
            self.progress_callback(step, current, total)


class FiltrationTestSystem(_CycleLoggingMixin, _FiltrationTestSystem):
    def __init__(
        self,
        module: MEU,
        config: FiltrationConfig,
        log_dir: str = "logs",
        valve_callback=None,
        progress_callback=None,
    ) -> None:
        super().__init__(module, config, log_dir, valve_callback, progress_callback)

    def _run_filter_phase(self) -> None:
        config = self.config
        if config.filtration_by_weight:
            self._weight_phase(
                "Filter",
                config.filtration_target,
                0,
                (self.FEED, self.FILTRATE),
                config.sample_time,
                config.max_weight_phase_time,
            )
            return
        self._timed_phase(
            "Filter",
            config.filtration_target,
            (self.FEED, self.FILTRATE),
            config.sample_time,
        )

    def _run_backwash_phase(self) -> None:
        config = self.config
        if config.backwash_by_weight:
            self._weight_phase(
                "Backwash",
                config.backwash_target,
                1,
                (self.BACKWASH, self.BACKWASH_EFFLUENT),
                config.sample_time,
                config.max_weight_phase_time,
            )
            return
        self._timed_phase(
            "Backwash",
            config.backwash_target,
            (self.BACKWASH, self.BACKWASH_EFFLUENT),
            config.sample_time,
        )

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

    def start_test(self) -> None:
        self._run_managed(
            self._run_cycles,
            prefix=self.config.file_prefix,
            final_id=self.config.sample_id,
        )


class CleanTestSystem(_CycleLoggingMixin, _CleanTestSystem):
    def __init__(
        self,
        module: MEU,
        config: CleanConfig,
        log_dir: str = "logs",
        valve_callback=None,
        progress_callback=None,
        prompt_callback: Optional[Callable[[str], bool]] = None,
    ) -> None:
        super().__init__(
            module,
            config,
            log_dir,
            valve_callback,
            progress_callback,
            prompt_callback,
        )

    def _run_cycles(self) -> None:
        for cycle in range(self.config.cycle_count):
            self.current_cycle = cycle + 1
            self._run_clean_cycle()

    def start_test(self) -> None:
        self._run_managed(
            self._run_cycles,
            prefix="Clean",
            final_id=self.config.solution,
        )


class BenchmarkTestSystem(_CycleLoggingMixin, _BenchmarkTestSystem):
    def __init__(
        self,
        module: MEU,
        config: BenchmarkConfig,
        log_dir: str = "logs",
        progress_callback=None,
    ) -> None:
        super().__init__(module, config, log_dir, progress_callback)

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

    def start_test(self) -> None:
        self._run_managed(
            self._run_samples,
            prefix="BenchmarkPassive",
            final_id=self.config.sample_id,
            close_valves=False,
            tare_scales=False,
        )


__all__ = [
    "AutomationError",
    "PSI_TO_KPA",
    "FiltrationTestSystem",
    "CleanTestSystem",
    "BenchmarkTestSystem",
]
