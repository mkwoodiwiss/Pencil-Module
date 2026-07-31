"""Core automation for the MF/UF Membrane Evaluation Unit."""

from __future__ import annotations

from dataclasses import asdict
import csv
import os
import re
import threading
import time
from typing import Callable, Optional

from .clean_sequence import CleanSequenceMixin
from .config_meu import BenchmarkConfig, CleanConfig, FiltrationConfig
from .hardware import MEU


DATA_HEADER = [
    "timestamp",
    "feed_temperature",
    "feed_tank_pressure",
    "backwash_tank_pressure",
    "feed_weight",
    "backwash_weight",
    "step",
]


def _safe_name(value: str) -> str:
    text = (value or "").strip() or "unknown"
    return re.sub(r"[^A-Za-z0-9._-]+", "_", text)


class AutomationError(RuntimeError):
    """Raised when an MEU process cannot continue safely."""


class _AutomationBase:
    BACKWASH = 1
    FEED = 2
    BACKWASH_EFFLUENT = 3
    WASTE = 4
    FILTRATE = 5

    BACKWASH_SUPPLY = BACKWASH
    INFLUENT_SUPPLY = FEED
    INFLUENT_DRAIN = WASTE
    EFFLUENT_VALVE = FILTRATE

    def __init__(
        self,
        meu: MEU,
        log_dir: str,
        valve_callback: Optional[Callable[[int, bool], None]] = None,
        progress_callback: Optional[Callable[[str, int, int], None]] = None,
    ) -> None:
        self.module = meu
        self.log_dir = log_dir
        self.valve_callback = valve_callback
        self.progress_callback = progress_callback
        self._stop_event = threading.Event()
        self.data_file = None
        self.data_writer = None

    def _set_valve(self, relay: int, state: bool) -> None:
        self.module.set_solenoid(relay, state)
        if self.valve_callback:
            self.valve_callback(relay, state)

    def _open(self, *relays: int) -> None:
        for relay in relays:
            self._set_valve(relay, True)

    def _close(self, *relays: int) -> None:
        for relay in relays:
            self._set_valve(relay, False)

    def close_all_valves(self) -> None:
        self._close(
            self.BACKWASH,
            self.FEED,
            self.BACKWASH_EFFLUENT,
            self.WASTE,
            self.FILTRATE,
        )

    def cancel(self) -> None:
        self._stop_event.set()

    def _check_cancel(self) -> None:
        if self._stop_event.is_set():
            raise AutomationError("Run cancelled")

    @staticmethod
    def _parse_weight(text: str) -> float:
        if not text or text.strip() == "--":
            raise AutomationError("Scale response unavailable")
        match = re.search(r"([+-]?\d+(?:\.\d+)?)", text)
        if not match:
            raise AutomationError(f"Invalid scale response: {text!r}")
        return float(match.group(1))

    def _read_weight(self, scale_index: int, attempts: int = 5) -> float:
        last_response = "--"
        for attempt in range(attempts):
            self._check_cancel()
            last_response = self.module.read_scale(scale_index)
            try:
                return self._parse_weight(last_response)
            except AutomationError:
                if attempt < attempts - 1:
                    time.sleep(0.25)
        raise AutomationError(
            f"Scale {scale_index + 1} response unavailable after "
            f"{attempts} attempts. Last response: {last_response!r}"
        )

    def _apply_offsets(self, config) -> None:
        self.module.apply_offsets(
            pressure_in=config.feed_tank_pressure_offset,
            pressure_bw=config.backwash_tank_pressure_offset,
            temperature=config.feed_temperature_offset,
        )

    def _open_logs(
        self,
        prefix: str,
        project: str,
        module_id: str,
        final_id: str,
        config,
    ) -> None:
        os.makedirs(self.log_dir, exist_ok=True)
        stamp = time.strftime("%Y%m%d_%H%M%S")
        test_date = time.strftime("%Y-%m-%d")
        base = os.path.join(
            self.log_dir,
            f"{_safe_name(prefix)}_{_safe_name(project)}_"
            f"{_safe_name(module_id)}_{_safe_name(final_id)}_{stamp}",
        )
        self.data_file = open(base + "_data.csv", "w", newline="", encoding="utf-8")
        self.data_writer = csv.writer(self.data_file)
        self.data_writer.writerow(DATA_HEADER)
        self.data_file.flush()
        with open(base + "_settings.csv", "w", newline="", encoding="utf-8") as settings:
            writer = csv.writer(settings)
            writer.writerow(["test_date", test_date])
            for key, value in asdict(config).items():
                writer.writerow([key, value])

    def log_cycle(self, step: str) -> None:
        if not self.data_writer or not self.data_file:
            return
        self.data_writer.writerow(
            [
                time.strftime("%H:%M:%S"),
                self.module.read_rtd(0),
                self.module.read_pressure(2),
                self.module.read_pressure(1),
                self._read_weight(0),
                self._read_weight(1),
                step,
            ]
        )
        self.data_file.flush()

    def _timed_phase(
        self,
        step: str,
        duration: float,
        relays: tuple[int, ...],
        sample_time: float,
    ) -> None:
        if duration <= 0:
            raise AutomationError(f"{step} duration must be greater than zero")
        self._open(*relays)
        try:
            end = time.monotonic() + duration
            while time.monotonic() < end:
                self._check_cancel()
                self.log_cycle(step)
                time.sleep(max(0.01, sample_time))
        finally:
            self._close(*relays)

    def _weight_phase(
        self,
        step: str,
        target: float,
        scale_index: int,
        relays: tuple[int, ...],
        sample_time: float,
        max_duration: float,
    ) -> None:
        if target <= 0 or max_duration <= 0:
            raise AutomationError(
                f"{step} target and maximum duration must be greater than zero"
            )
        start_weight = self._read_weight(scale_index)
        last_weight = start_weight
        last_change = time.monotonic()
        started = time.monotonic()
        self._open(*relays)
        try:
            while True:
                self._check_cancel()
                current = self._read_weight(scale_index)
                if current < start_weight - 0.1:
                    raise AutomationError(
                        f"{step} scale decreased more than 0.1 g below its starting value"
                    )
                if current > last_weight + 0.01:
                    last_change = time.monotonic()
                    last_weight = current
                if current - start_weight >= target:
                    break
                if time.monotonic() - last_change > 60:
                    raise AutomationError(
                        f"{step} scale failed to increase by more than 0.01 g for 60 seconds"
                    )
                if time.monotonic() - started > max_duration:
                    raise AutomationError(f"{step} exceeded its maximum duration")
                self.log_cycle(step)
                time.sleep(max(0.01, sample_time))
        finally:
            self._close(*relays)

    def stop_test(self) -> None:
        self.close_all_valves()
        if self.data_file:
            self.data_file.close()
            self.data_file = None
        self.data_writer = None


class FiltrationTestSystem(_AutomationBase):
    def __init__(
        self,
        module: MEU,
        config: FiltrationConfig,
        log_dir: str = "logs",
        valve_callback=None,
        progress_callback=None,
    ) -> None:
        super().__init__(module, log_dir, valve_callback, progress_callback)
        self.config = config

    def start_test(self) -> None:
        self._stop_event.clear()
        self.close_all_valves()
        try:
            config = self.config
            self._open_logs(
                config.file_prefix,
                config.project,
                config.module_id,
                config.sample_id,
                config,
            )
            self._apply_offsets(config)
            self.module.zero_scales()
            time.sleep(1.0)
            for cycle in range(config.cycle_count):
                current_cycle = cycle + 1
                if self.progress_callback:
                    self.progress_callback("Purge", current_cycle, config.cycle_count)
                self._timed_phase(
                    "Purge",
                    config.purge_time,
                    (self.FEED, self.WASTE),
                    config.sample_time,
                )
                if self.progress_callback:
                    self.progress_callback("Filter", current_cycle, config.cycle_count)
                if config.filtration_by_weight:
                    self._weight_phase(
                        "Filter",
                        config.filtration_target,
                        0,
                        (self.FEED, self.FILTRATE),
                        config.sample_time,
                        config.max_weight_phase_time,
                    )
                else:
                    self._timed_phase(
                        "Filter",
                        config.filtration_target,
                        (self.FEED, self.FILTRATE),
                        config.sample_time,
                    )
                if self.progress_callback:
                    self.progress_callback("Backwash", current_cycle, config.cycle_count)
                if config.backwash_by_weight:
                    self._weight_phase(
                        "Backwash",
                        config.backwash_target,
                        1,
                        (self.BACKWASH, self.BACKWASH_EFFLUENT),
                        config.sample_time,
                        config.max_weight_phase_time,
                    )
                else:
                    self._timed_phase(
                        "Backwash",
                        config.backwash_target,
                        (self.BACKWASH, self.BACKWASH_EFFLUENT),
                        config.sample_time,
                    )
        finally:
            self.stop_test()

    def prime(self, duration: float = 1.0) -> None:
        self._timed_phase("Prime", duration, (self.FEED,), 0.1)


class CleanTestSystem(CleanSequenceMixin, _AutomationBase):
    def __init__(
        self,
        module: MEU,
        config: CleanConfig,
        log_dir: str = "logs",
        valve_callback=None,
        progress_callback=None,
        prompt_callback: Optional[Callable[[str], bool]] = None,
    ) -> None:
        super().__init__(module, log_dir, valve_callback, progress_callback)
        self.config = config
        self.prompt_callback = prompt_callback or (lambda _message: True)

    def _prompt(self, message: str) -> None:
        self._check_cancel()
        if not self.prompt_callback(message):
            raise AutomationError("Operator cancelled at confirmation prompt")

    def _process_phase(
        self,
        step: str,
        target: float,
        by_weight: bool,
        scale_index: int,
        relays: tuple[int, ...],
    ) -> None:
        if by_weight:
            self._weight_phase(
                step,
                target,
                scale_index,
                relays,
                self.config.sample_time,
                self.config.max_weight_phase_time,
            )
            return
        self._timed_phase(step, target, relays, self.config.sample_time)

    def start_test(self) -> None:
        self._stop_event.clear()
        self.close_all_valves()
        try:
            config = self.config
            self._open_logs(
                "Clean",
                config.project,
                config.module_id,
                config.solution,
                config,
            )
            self._apply_offsets(config)
            self.module.zero_scales()
            time.sleep(1.0)
            for _cycle in range(config.cycle_count):
                self._run_clean_cycle()
        finally:
            self.stop_test()


class BenchmarkTestSystem(_AutomationBase):
    """Passive benchmark logger retained for maintenance and diagnostics."""

    def __init__(
        self,
        module: MEU,
        config: BenchmarkConfig,
        log_dir: str = "logs",
        progress_callback=None,
    ) -> None:
        super().__init__(module, log_dir, progress_callback=progress_callback)
        self.config = config

    def start_test(self) -> None:
        self._stop_event.clear()
        try:
            config = self.config
            self._open_logs(
                "BenchmarkPassive",
                config.project,
                config.module_id,
                config.sample_id,
                config,
            )
            self._apply_offsets(config)
            started = time.monotonic()
            count = 0
            while time.monotonic() - started < config.duration:
                self._check_cancel()
                count += 1
                if self.progress_callback:
                    self.progress_callback("Benchmark Passive", count, 0)
                self.log_cycle("Benchmark Passive")
                time.sleep(max(1.0, config.interval))
        finally:
            self.stop_test()


__all__ = [
    "AutomationError",
    "BenchmarkTestSystem",
    "CleanTestSystem",
    "DATA_HEADER",
    "FiltrationTestSystem",
    "_AutomationBase",
    "_safe_name",
]
