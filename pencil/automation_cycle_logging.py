"""Automation variants that add the active cycle number to every data row."""

from __future__ import annotations

import time
from typing import Callable, Optional

from .automation_meu import (
    AutomationError,
    BenchmarkTestSystem as _BenchmarkTestSystem,
    CleanTestSystem as _CleanTestSystem,
    FiltrationTestSystem as _FiltrationTestSystem,
)
from .config_meu import BenchmarkConfig, CleanConfig, FiltrationConfig
from .hardware import MEU


PSI_TO_KPA = 6.894757293168


class _CycleLoggingMixin:
    """Insert a one-based cycle number immediately before the step column."""

    def _open_logs(self, prefix: str, project: str, module_id: str, final_id: str, config) -> None:
        super()._open_logs(prefix, project, module_id, final_id, config)
        self.current_cycle = 0

        # The base class has already written its header. Rewrite the new file once so
        # the column order remains explicit and every following row has the same width.
        self.data_file.seek(0)
        self.data_file.truncate()
        self.data_writer.writerow([
            "timestamp",
            "feed_temperature",
            "feed_tank_pressure_kpa",
            "backwash_tank_pressure_kpa",
            "feed_weight",
            "backwash_weight",
            "cycle",
            "step",
        ])
        self.data_file.flush()

    def log_cycle(self, step: str) -> None:
        if not self.data_writer or not self.data_file:
            return
        self.data_writer.writerow([
            time.strftime("%H:%M:%S"),
            self.module.read_rtd(0),
            self.module.read_pressure(2) * PSI_TO_KPA,
            self.module.read_pressure(1) * PSI_TO_KPA,
            self._read_weight(0),
            self._read_weight(1),
            self.current_cycle,
            step,
        ])
        self.data_file.flush()


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

    def start_test(self) -> None:
        self._stop_event.clear()
        self.close_all_valves()
        try:
            self._open_logs(
                self.config.file_prefix,
                self.config.project,
                self.config.module_id,
                self.config.sample_id,
                self.config,
            )
            self._apply_offsets(self.config)
            self.module.zero_scales()
            time.sleep(1.0)
            for cycle in range(self.config.cycle_count):
                self.current_cycle = cycle + 1
                if self.progress_callback:
                    self.progress_callback("Purge", self.current_cycle, self.config.cycle_count)
                self._timed_phase(
                    "Purge",
                    self.config.purge_time,
                    (self.FEED, self.WASTE),
                    self.config.sample_time,
                )
                if self.progress_callback:
                    self.progress_callback("Filter", self.current_cycle, self.config.cycle_count)
                if self.config.filtration_by_weight:
                    self._weight_phase(
                        "Filter",
                        self.config.filtration_target,
                        0,
                        (self.FEED, self.FILTRATE),
                        self.config.sample_time,
                        self.config.max_weight_phase_time,
                    )
                else:
                    self._timed_phase(
                        "Filter",
                        self.config.filtration_target,
                        (self.FEED, self.FILTRATE),
                        self.config.sample_time,
                    )
                if self.progress_callback:
                    self.progress_callback("Backwash", self.current_cycle, self.config.cycle_count)
                if self.config.backwash_by_weight:
                    self._weight_phase(
                        "Backwash",
                        self.config.backwash_target,
                        1,
                        (self.BACKWASH, self.BACKWASH_EFFLUENT),
                        self.config.sample_time,
                        self.config.max_weight_phase_time,
                    )
                else:
                    self._timed_phase(
                        "Backwash",
                        self.config.backwash_target,
                        (self.BACKWASH, self.BACKWASH_EFFLUENT),
                        self.config.sample_time,
                    )
        finally:
            self.stop_test()


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

    def start_test(self) -> None:
        self._stop_event.clear()
        self.close_all_valves()
        try:
            self._open_logs(
                "Clean",
                self.config.project,
                self.config.module_id,
                self.config.solution,
                self.config,
            )
            self._apply_offsets(self.config)
            self.module.zero_scales()
            time.sleep(1.0)
            for cycle in range(self.config.cycle_count):
                self.current_cycle = cycle + 1
                self._prompt("Fill the Feed tank with caustic solution, then confirm to continue.")
                self._timed_phase("Caustic Purge", self.config.purge_time, (self.FEED, self.WASTE), self.config.sample_time)
                self._process_phase("Caustic Filter 1", self.config.forward_target, self.config.forward_by_weight, 0, (self.FEED, self.FILTRATE))
                self._process_phase("Caustic Backwash 1", self.config.backwash_target, self.config.backwash_by_weight, 1, (self.BACKWASH, self.BACKWASH_EFFLUENT))
                self._timed_phase("Caustic Soak", self.config.soak_time, tuple(), self.config.sample_time)
                self._process_phase("Caustic Filter 2", self.config.forward_target, self.config.forward_by_weight, 0, (self.FEED, self.FILTRATE))
                self._process_phase("Caustic Backwash 2", self.config.backwash_target, self.config.backwash_by_weight, 1, (self.BACKWASH, self.BACKWASH_EFFLUENT))
                self._prompt("Replace the Feed tank contents with DI water, then confirm to continue.")
                self._timed_phase("DI Rinse 1 Purge", self.config.purge_time, (self.FEED, self.WASTE), self.config.sample_time)
                self._process_phase("DI Rinse 1 Filter", self.config.rinse_forward_target, self.config.rinse_forward_by_weight, 0, (self.FEED, self.FILTRATE))
                self._process_phase("DI Rinse 1 Backwash", self.config.rinse_backwash_target, self.config.rinse_backwash_by_weight, 1, (self.BACKWASH, self.BACKWASH_EFFLUENT))
                self._prompt("Fill the Feed tank with acid solution, then confirm to continue.")
                self._timed_phase("Acid Purge", self.config.purge_time, (self.FEED, self.WASTE), self.config.sample_time)
                self._process_phase("Acid Filter 1", self.config.forward_target, self.config.forward_by_weight, 0, (self.FEED, self.FILTRATE))
                self._process_phase("Acid Backwash 1", self.config.backwash_target, self.config.backwash_by_weight, 1, (self.BACKWASH, self.BACKWASH_EFFLUENT))
                self._timed_phase("Acid Soak", self.config.soak_time, tuple(), self.config.sample_time)
                self._process_phase("Acid Filter 2", self.config.forward_target, self.config.forward_by_weight, 0, (self.FEED, self.FILTRATE))
                self._process_phase("Acid Backwash 2", self.config.backwash_target, self.config.backwash_by_weight, 1, (self.BACKWASH, self.BACKWASH_EFFLUENT))
                self._prompt("Replace the acid in the Feed tank with DI water, then confirm before DI Rinse 2.")
                self._timed_phase("DI Rinse 2 Purge", self.config.purge_time, (self.FEED, self.WASTE), self.config.sample_time)
                self._process_phase("DI Rinse 2 Filter", self.config.rinse_forward_target, self.config.rinse_forward_by_weight, 0, (self.FEED, self.FILTRATE))
                self._process_phase("DI Rinse 2 Backwash", self.config.rinse_backwash_target, self.config.rinse_backwash_by_weight, 1, (self.BACKWASH, self.BACKWASH_EFFLUENT))
        finally:
            self.stop_test()


class BenchmarkTestSystem(_CycleLoggingMixin, _BenchmarkTestSystem):
    def __init__(
        self,
        module: MEU,
        config: BenchmarkConfig,
        log_dir: str = "logs",
        progress_callback=None,
    ) -> None:
        super().__init__(module, config, log_dir, progress_callback)

    def start_test(self) -> None:
        self._stop_event.clear()
        try:
            self._open_logs(
                "BenchmarkPassive",
                self.config.project,
                self.config.module_id,
                self.config.sample_id,
                self.config,
            )
            self._apply_offsets(self.config)
            started = time.monotonic()
            count = 0
            while time.monotonic() - started < self.config.duration:
                self._check_cancel()
                count += 1
                self.current_cycle = count
                if self.progress_callback:
                    self.progress_callback("Benchmark Passive", count, 0)
                self.log_cycle("Benchmark Passive")
                time.sleep(max(1.0, self.config.interval))
        finally:
            self.stop_test()


__all__ = [
    "AutomationError",
    "FiltrationTestSystem",
    "CleanTestSystem",
    "BenchmarkTestSystem",
]
