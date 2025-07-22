"""Automation logic for running filtration tests."""

from dataclasses import dataclass, asdict
import csv
import os
import re
import time
from typing import Optional, Callable
import threading

from .hardware import PencilModule


@dataclass
class FiltrationConfig:
    """Configuration for an automated filtration test."""

    filtration_target: float
    filtration_by_volume: bool
    backwash_target: float
    backwash_by_volume: bool
    refill_time: float
    repeat_count: int
    sample_time: float
    project_name: str
    pressure_offset: float = 0.0
    temp_offset: float = 0.0


class FiltrationTestSystem:
    """Run automated filtration cycles based on a :class:`FiltrationConfig`."""

    BACKWASH_SUPPLY = 1
    INFLUENT_SUPPLY = 2
    BACKWASH_EFFLUENT = 3
    INFLUENT_DRAIN = 4
    EFFLUENT_VALVE = 5

    def __init__(
        self,
        module: PencilModule,
        config: FiltrationConfig,
        log_dir: str = "logs",
        valve_callback: Optional[Callable[[int, bool], None]] = None,
        progress_callback: Optional[Callable[[str, int, int], None]] = None,
    ) -> None:
        self.module = module
        self.config = config
        self.log_dir = log_dir
        self.valve_callback = valve_callback
        self.progress_callback = progress_callback
        self.data_writer: Optional[csv.writer] = None
        self.data_file: Optional[object] = None
        self._stop_event = threading.Event()

    def _check_cancel(self) -> bool:
        """Return True if cancellation requested and stop valves."""
        if self._stop_event.is_set():
            self.stop_test()
            return True
        return False

    def _parse_weight(self, text: str) -> float:
        match = re.search(r"([+-]?\d+\.\d+)", text)
        return float(match.group(1)) if match else 0.0

    def _log_row(self) -> None:
        if not self.data_writer:
            return
        row = [
            time.time(),
            self.module.read_rtd(0),
            self.module.read_pressure(2),
            self.module.read_pressure(1),
            self._parse_weight(self.module.read_scale(0)),
            self._parse_weight(self.module.read_scale(1)),
        ]
        self.data_writer.writerow(row)

    def _open(self, *valves: int) -> None:
        for v in valves:
            self.module.set_solenoid(v, True)
            if self.valve_callback:
                self.valve_callback(v, True)

    def _close(self, *valves: int) -> None:
        for v in valves:
            self.module.set_solenoid(v, False)
            if self.valve_callback:
                self.valve_callback(v, False)

    def prime(self, duration: float = 1.0) -> None:
        self._open(self.INFLUENT_SUPPLY)
        time.sleep(duration)
        self._close(self.INFLUENT_SUPPLY)

    def start_test(self) -> None:
        self._stop_event.clear()
        os.makedirs(self.log_dir, exist_ok=True)
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        base = os.path.join(self.log_dir, f"{self.config.project_name}_{timestamp}")

        self.data_file = open(base + "_data.csv", "w", newline="")
        self.data_writer = csv.writer(self.data_file)
        self.data_writer.writerow([
            "timestamp",
            "influent_temp",
            "backwash_pressure",
            "influent_pressure",
            "effluent_weight",
            "backwash_weight",
        ])

        with open(base + "_settings.csv", "w", newline="") as sfile:
            writer = csv.writer(sfile)
            for k, v in asdict(self.config).items():
                writer.writerow([k, v])

        if (
            self.config.pressure_offset != 0.0
            or self.config.temp_offset != 0.0
        ):
            self.module.apply_offsets(
                pressure_bw=self.config.pressure_offset,
                pressure_in=self.config.pressure_offset,
                temperature=self.config.temp_offset,
            )
        self.module.zero_scales()

        for cycle in range(self.config.repeat_count):
            if self.progress_callback:
                self.progress_callback("refill", cycle + 1, self.config.repeat_count)
            self._open(self.INFLUENT_SUPPLY, self.INFLUENT_DRAIN)
            start = time.time()
            while time.time() - start < self.config.refill_time:
                if self._check_cancel():
                    return
                self._log_row()
                time.sleep(self.config.sample_time)
            self._close(self.INFLUENT_SUPPLY, self.INFLUENT_DRAIN)

            if self.progress_callback:
                self.progress_callback("filter", cycle + 1, self.config.repeat_count)
            self._open(self.INFLUENT_SUPPLY, self.EFFLUENT_VALVE)
            start = time.time()
            start_w = self._parse_weight(self.module.read_scale(0))
            while True:
                if self._check_cancel():
                    return
                self._log_row()
                if self.config.filtration_by_volume:
                    vol = self._parse_weight(self.module.read_scale(0)) - start_w
                    if vol >= self.config.filtration_target:
                        break
                else:
                    if time.time() - start >= self.config.filtration_target:
                        break
                time.sleep(self.config.sample_time)
            self._close(self.INFLUENT_SUPPLY, self.EFFLUENT_VALVE)

            if self.progress_callback:
                self.progress_callback("backwash", cycle + 1, self.config.repeat_count)
            self._open(self.BACKWASH_SUPPLY, self.BACKWASH_EFFLUENT)
            start = time.time()
            start_w = self._parse_weight(self.module.read_scale(1))
            while True:
                if self._check_cancel():
                    return
                self._log_row()
                if self.config.backwash_by_volume:
                    vol = self._parse_weight(self.module.read_scale(1)) - start_w
                    if vol >= self.config.backwash_target:
                        break
                else:
                    if time.time() - start >= self.config.backwash_target:
                        break
                time.sleep(self.config.sample_time)
            self._close(self.BACKWASH_SUPPLY, self.BACKWASH_EFFLUENT)

        self.stop_test()

    def stop_test(self) -> None:
        self._close(
            self.INFLUENT_SUPPLY,
            self.BACKWASH_SUPPLY,
            self.EFFLUENT_VALVE,
            self.BACKWASH_EFFLUENT,
            self.INFLUENT_DRAIN,
        )
        if self.data_file:
            self.data_file.close()
            self.data_file = None
        self.data_writer = None

    def cancel(self) -> None:
        """Signal the running test loop to cancel."""
        self._stop_event.set()
