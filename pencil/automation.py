"""Automation logic for running filtration tests."""

from dataclasses import asdict
import csv
import os
import re
import time
from typing import Optional, Callable
import threading

from tkinter import messagebox

from .hardware import PencilModule
from .config import FiltrationConfig, CleanConfig, BenchmarkConfig


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

    def log_cycle(self, step: str) -> None:
        """Record one set of sensor readings for a given cycle step."""
        if not self.data_writer:
            return
        ts = time.time()
        effluent = self.module.read_scale(0)
        backwash = self.module.read_scale(1)
        row = [
            ts,
            self.module.read_rtd(0),
            self.module.read_pressure(2),
            self.module.read_pressure(1),
            self._parse_weight(effluent),
            self._parse_weight(backwash),
            step,
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
        proj = (self.config.project or "").strip() or "unknown"
        module = (self.config.module_id or "").strip() or "unknown"
        sample = (self.config.sample_id or "").strip() or "unknown"
        base_name = f"Test_{proj}_{module}_{sample}_{timestamp}"
        base = os.path.join(self.log_dir, base_name)

        self.data_file = open(base + "_data.csv", "w", newline="")
        self.data_writer = csv.writer(self.data_file)
        self.data_writer.writerow([
            "timestamp",
            "influent_temp",
            "backwash_pressure",
            "influent_pressure",
            "effluent_weight",
            "backwash_weight",
            "step",
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

        for cycle in range(self.config.cycle_count):
            if self.progress_callback:
                self.progress_callback("Purge", cycle + 1, self.config.cycle_count)
            self._open(self.INFLUENT_SUPPLY, self.INFLUENT_DRAIN)
            start = time.time()
            while time.time() - start < self.config.refill_time:
                if self._check_cancel():
                    return
                self.log_cycle("Purge")
                time.sleep(self.config.sample_time)
            self._close(self.INFLUENT_SUPPLY, self.INFLUENT_DRAIN)

            if self.progress_callback:
                self.progress_callback("Filter", cycle + 1, self.config.cycle_count)
            self._open(self.INFLUENT_SUPPLY, self.EFFLUENT_VALVE)
            start = time.time()
            start_w = self._parse_weight(self.module.read_scale(0))
            while True:
                if self._check_cancel():
                    return
                self.log_cycle("Filter")
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
                self.progress_callback("Backwash", cycle + 1, self.config.cycle_count)
            self._open(self.BACKWASH_SUPPLY, self.BACKWASH_EFFLUENT)
            start = time.time()
            start_w = self._parse_weight(self.module.read_scale(1))
            while True:
                if self._check_cancel():
                    return
                self.log_cycle("Backwash")
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


class CleanTestSystem:
    """Automate the cleaning cycle using a :class:`CleanConfig`."""

    BACKWASH_SUPPLY = FiltrationTestSystem.BACKWASH_SUPPLY
    INFLUENT_SUPPLY = FiltrationTestSystem.INFLUENT_SUPPLY
    BACKWASH_EFFLUENT = FiltrationTestSystem.BACKWASH_EFFLUENT
    INFLUENT_DRAIN = FiltrationTestSystem.INFLUENT_DRAIN
    EFFLUENT_VALVE = FiltrationTestSystem.EFFLUENT_VALVE

    def __init__(
        self,
        module: PencilModule,
        config: CleanConfig,
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

    # Utility helpers reused from FiltrationTestSystem
    def _check_cancel(self) -> bool:
        if self._stop_event.is_set():
            self.stop_test()
            return True
        return False

    def _parse_weight(self, text: str) -> float:
        match = re.search(r"([+-]?\d+\.\d+)", text)
        return float(match.group(1)) if match else 0.0

    def log_cycle(self, step: str) -> None:
        """Record one set of sensor readings for a given cycle step."""
        if not self.data_writer:
            return
        ts = time.time()
        effluent = self.module.read_scale(0)
        backwash = self.module.read_scale(1)
        row = [
            ts,
            self.module.read_rtd(0),
            self.module.read_pressure(2),
            self.module.read_pressure(1),
            self._parse_weight(effluent),
            self._parse_weight(backwash),
            step,
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

    # Sequence implementation
    def start_test(self) -> None:
        self._stop_event.clear()
        os.makedirs(self.log_dir, exist_ok=True)
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        proj = (self.config.project or "").strip() or "unknown"
        module = (self.config.module_id or "").strip() or "unknown"
        solution = (self.config.solution or "").strip() or "unknown"
        base_name = f"Clean_{proj}_{module}_{solution}_{timestamp}"
        base = os.path.join(self.log_dir, base_name)

        self.data_file = open(base + "_data.csv", "w", newline="")
        self.data_writer = csv.writer(self.data_file)
        self.data_writer.writerow([
            "timestamp",
            "influent_temp",
            "backwash_pressure",
            "influent_pressure",
            "effluent_weight",
            "backwash_weight",
            "step",
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

        def prompt(msg: str) -> bool:
            try:
                messagebox.showinfo("Action Required", msg)
            except Exception:
                input(msg + " Press Enter to continue")
            return not self._check_cancel()

        def purge(label: str, idx: int) -> bool:
            if self.progress_callback:
                self.progress_callback(label, idx, self.config.cycle_count)
            self._open(self.INFLUENT_SUPPLY, self.INFLUENT_DRAIN)
            start = time.time()
            while time.time() - start < self.config.rinse_time:
                if self._check_cancel():
                    return False
                self.log_cycle(label)
                time.sleep(self.config.sample_time)
            self._close(self.INFLUENT_SUPPLY, self.INFLUENT_DRAIN)
            return True

        def fwd(
            label: str,
            idx: int,
            target: Optional[float] = None,
            by_volume: Optional[bool] = None,
        ) -> bool:
            if self.progress_callback:
                self.progress_callback(label, idx, self.config.cycle_count)
            tgt = self.config.forward_target if target is None else target
            use_vol = self.config.forward_by_volume if by_volume is None else by_volume
            self._open(self.INFLUENT_SUPPLY, self.EFFLUENT_VALVE)
            start = time.time()
            start_w = self._parse_weight(self.module.read_scale(0))
            while True:
                if self._check_cancel():
                    return False
                self.log_cycle(label)
                if use_vol:
                    vol = self._parse_weight(self.module.read_scale(0)) - start_w
                    if vol >= tgt:
                        break
                else:
                    if time.time() - start >= tgt:
                        break
                time.sleep(self.config.sample_time)
            self._close(self.INFLUENT_SUPPLY, self.EFFLUENT_VALVE)
            return True

        def back(
            label: str,
            idx: int,
            target: Optional[float] = None,
            by_volume: Optional[bool] = None,
        ) -> bool:
            if self.progress_callback:
                self.progress_callback(label, idx, self.config.cycle_count)
            tgt = self.config.backwash_target if target is None else target
            use_vol = self.config.backwash_by_volume if by_volume is None else by_volume
            self._open(self.BACKWASH_SUPPLY, self.BACKWASH_EFFLUENT)
            start = time.time()
            start_w = self._parse_weight(self.module.read_scale(1))
            while True:
                if self._check_cancel():
                    return False
                self.log_cycle(label)
                if use_vol:
                    vol = self._parse_weight(self.module.read_scale(1)) - start_w
                    if vol >= tgt:
                        break
                else:
                    if time.time() - start >= tgt:
                        break
                time.sleep(self.config.sample_time)
            self._close(self.BACKWASH_SUPPLY, self.BACKWASH_EFFLUENT)
            return True

        def soak(label: str, idx: int) -> bool:
            if self.progress_callback:
                self.progress_callback(label, idx, self.config.cycle_count)
            end = time.time() + self.config.soak_time
            while time.time() < end:
                if self._check_cancel():
                    return False
                self.log_cycle(label)
                time.sleep(self.config.sample_time)
            return True

        for cycle in range(self.config.cycle_count):
            if not prompt("Fill influent supply tank with caustic solution."):
                return
            if not purge("Caustic Purge", cycle + 1):
                return
            if not fwd("Caustic Filter 1", cycle + 1):
                return
            if not back("Caustic Backwash 1", cycle + 1):
                return
            if not soak("Caustic Soak", cycle + 1):
                return
            if not fwd("Caustic Filter 2", cycle + 1):
                return
            if not back("Caustic Backwash 2", cycle + 1):
                return

            if not prompt("Refill influent supply tank with DI water."):
                return
            if not purge("DI Rinse 1 Purge", cycle + 1):
                return
            if not fwd(
                "DI Rinse 1 Filter",
                cycle + 1,
                self.config.rinse_forward_target,
                self.config.rinse_forward_by_volume,
            ):
                return
            if not back(
                "DI Rinse 1 Backwash",
                cycle + 1,
                self.config.rinse_backwash_target,
                self.config.rinse_backwash_by_volume,
            ):
                return

            if not prompt("Fill influent supply tank with acid solution."):
                return
            if not purge("Acid Purge", cycle + 1):
                return
            if not fwd("Acid Filter 1", cycle + 1):
                return
            if not back("Acid Backwash 1", cycle + 1):
                return
            if not soak("Acid Soak", cycle + 1):
                return
            if not fwd("Acid Filter 2", cycle + 1):
                return
            if not back("Acid Backwash 2", cycle + 1):
                return

            if not purge("DI Rinse 2 Purge", cycle + 1):
                return
            if not fwd(
                "DI Rinse 2 Filter",
                cycle + 1,
                self.config.rinse_forward_target,
                self.config.rinse_forward_by_volume,
            ):
                return
            if not back(
                "DI Rinse 2 Backwash",
                cycle + 1,
                self.config.rinse_backwash_target,
                self.config.rinse_backwash_by_volume,
            ):
                return

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
        self._stop_event.set()


class BenchmarkTestSystem:
    """Log sensor data without controlling valves."""

    def __init__(
        self,
        module: PencilModule,
        config: BenchmarkConfig,
        log_dir: str = "logs",
        progress_callback: Optional[Callable[[str, int, int], None]] = None,
    ) -> None:
        self.module = module
        self.config = config
        self.log_dir = log_dir
        self.progress_callback = progress_callback
        self._stop_event = threading.Event()
        self.data_file: Optional[object] = None

    def log_cycle(self) -> dict:
        """Return a dictionary of sensor readings for one sample."""
        ts = time.time()
        return {
            "time": ts,
            "influent_temp": self.module.read_rtd(0),
            "influent_pressure": self.module.read_pressure(2),
            "backwash_pressure": self.module.read_pressure(1),
            "effluent_weight": self.module.read_scale(0),
            "backwash_weight": self.module.read_scale(1),
        }

    def start_test(self) -> None:
        self._stop_event.clear()
        os.makedirs(self.log_dir, exist_ok=True)
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        proj = (self.config.project or "").strip() or "unknown"
        module = (self.config.module_id or "").strip() or "unknown"
        sample = (self.config.sample_id or "").strip() or "unknown"
        filename = (
            f"Benchmark_{proj}_{module}_{sample}_{timestamp}.txt"
        )
        path = os.path.join(self.log_dir, filename)
        self.data_file = open(path, "w")
        start = time.time()
        count = 0
        try:
            while time.time() - start < self.config.duration:
                if self._stop_event.is_set():
                    break
                row = self.log_cycle()
                self.data_file.write(str(row) + "\n")
                self.data_file.flush()
                count += 1
                if self.progress_callback:
                    self.progress_callback("Benchmark", count, 0)
                time.sleep(max(1.0, self.config.interval))
        finally:
            self.stop_test()

    def stop_test(self) -> None:
        if self.data_file:
            self.data_file.close()
            self.data_file = None

    def cancel(self) -> None:
        self._stop_event.set()
