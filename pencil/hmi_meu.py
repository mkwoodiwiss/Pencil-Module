"""MEU-branded HMI with corrected automation behavior and I/O-list naming."""

from __future__ import annotations

import threading
import tkinter as tk
from tkinter import messagebox

from .automation_cycle_logging import AutomationError, CleanTestSystem, FiltrationTestSystem
from .config_meu import CleanConfig, FiltrationConfig
from .hmi import HMI as _BaseHMI


EXACT_TEXT_REPLACEMENTS = {
    "BW water": "BW Tank",
    "Influent water": "Feed Tank",
    "Effluent": "Filtrate",
    "Drain": "Waste",
    "Backwash": "BW Effluent",
    "Mini-module": "Membrane",
    "Tare EFL": "Tare FIL",
    "Tare BW": "Tare BW EFL",
}

TEXT_REPLACEMENTS = (
    ("Influent Supply Pressure", "Feed Tank Pressure"),
    ("Influent Pressure", "Feed Tank Pressure"),
    ("BW Supply Pressure", "Backwash Tank Pressure"),
    ("BW Pressure", "Backwash Tank Pressure"),
    ("Backwash Supply Pressure", "Backwash Tank Pressure"),
    ("Influent Temperature", "Feed Temperature"),
    ("Temperature", "Feed Temperature"),
    ("Effluent Weight", "Filtrate Weight"),
    ("Feed Weight", "Filtrate Weight"),
    ("BW Weight", "BW Effluent Weight"),
    ("Backwash Weight", "BW Effluent Weight"),
    ("Influent Supply", "Feed"),
    ("Influent Drain", "Waste"),
    ("Effluent Valve", "Filtrate"),
)


def normalize_io_text(value: str) -> str:
    if value in EXACT_TEXT_REPLACEMENTS:
        return EXACT_TEXT_REPLACEMENTS[value]
    result = value
    for old, new in TEXT_REPLACEMENTS:
        result = result.replace(old, new)
    return result


class HMI(_BaseHMI):
    """HMI for the MF/UF Membrane Evaluation Unit."""

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.title("MF/UF Membrane Evaluation Unit (MEU)")
        self._automation_error: str | None = None
        self._normalize_visible_text(self)

    def _normalize_visible_text(self, parent) -> None:
        for child in parent.winfo_children():
            try:
                text = child.cget("text")
                normalized = normalize_io_text(text)
                if normalized != text:
                    child.config(text=normalized)
            except Exception:
                pass
            if isinstance(child, tk.Canvas):
                try:
                    for item in child.find_all():
                        if child.type(item) == "text":
                            text = child.itemcget(item, "text")
                            normalized = normalize_io_text(text)
                            if normalized != text:
                                child.itemconfigure(item, text=normalized)
                except Exception:
                    pass
            self._normalize_visible_text(child)

    def _walk_widgets(self, parent):
        for child in parent.winfo_children():
            yield child
            yield from self._walk_widgets(child)

    @staticmethod
    def _positive(value: float, label: str) -> float:
        if value <= 0:
            raise ValueError(f"{label} must be greater than zero.")
        return value

    @staticmethod
    def _positive_count(value: int, label: str) -> int:
        if value < 1:
            raise ValueError(f"{label} must be at least 1.")
        return value

    def _active_offsets(self) -> dict[str, float]:
        return {
            "feed_tank_pressure_offset": self.module.pressure_offset_in,
            "backwash_tank_pressure_offset": self.module.pressure_offset_bw,
            "feed_temperature_offset": self.module.temp_offset,
        }

    def _thread_safe_prompt(self, message: str) -> bool:
        completed = threading.Event()
        result = {"accepted": False}

        def show_prompt() -> None:
            result["accepted"] = messagebox.askokcancel("Action Required", message)
            completed.set()

        self.after(0, show_prompt)
        while not completed.wait(0.1):
            if getattr(self.test_system, "_stop_event", None) and self.test_system._stop_event.is_set():
                return False
        return result["accepted"]

    def start_test(self) -> None:
        try:
            self._disable_manual_controls()
            self._close_all_valves()
            filtration_by_weight = self.filt_use_weight_var.get()
            backwash_by_weight = self.bw_use_weight_var.get()
            config = FiltrationConfig(
                filtration_target=self._positive(self.filt_target_weight_var.get() if filtration_by_weight else self.filt_target_time_var.get(), "Filtration target"),
                filtration_by_weight=filtration_by_weight,
                backwash_target=self._positive(self.bw_target_weight_var.get() if backwash_by_weight else self.bw_target_time_var.get(), "Backwash target"),
                backwash_by_weight=backwash_by_weight,
                purge_time=self._positive(self.refill_time_var.get(), "Purge time"),
                cycle_count=self._positive_count(self.cycle_count_var.get(), "Cycle count"),
                sample_time=self._positive(self.sample_time_var.get(), "Sample time"),
                project=self.project_var.get(),
                module_id=self.module_id_var.get(),
                sample_id=self.sample_id_var.get(),
                **self._active_offsets(),
            )
            self.test_system = FiltrationTestSystem(self.module, config, valve_callback=self._automation_valve_change, progress_callback=self._automation_progress)
            self.test_thread = threading.Thread(target=self._run_test_thread, daemon=True)
            self.test_thread.start()
        except Exception as exc:
            self.is_running = False
            self._enable_manual_controls()
            self.start_btn_test.config(text="Start")
            messagebox.showerror("Invalid Test Settings", str(exc))

    def start_benchmark(self) -> None:
        try:
            self._disable_manual_controls()
            self._close_all_valves()
            filtration_by_weight = self.benchmark_filt_use_weight_var.get()
            backwash_by_weight = self.benchmark_bw_use_weight_var.get()
            config = FiltrationConfig(
                filtration_target=self._positive(self.benchmark_filt_target_weight_var.get() if filtration_by_weight else self.benchmark_filt_target_time_var.get(), "Benchmark filtration target"),
                filtration_by_weight=filtration_by_weight,
                backwash_target=self._positive(self.benchmark_bw_target_weight_var.get() if backwash_by_weight else self.benchmark_bw_target_time_var.get(), "Benchmark backwash target"),
                backwash_by_weight=backwash_by_weight,
                purge_time=self._positive(self.benchmark_refill_time_var.get(), "Benchmark purge time"),
                cycle_count=self._positive_count(self.benchmark_cycle_count_var.get(), "Benchmark cycle count"),
                sample_time=self._positive(self.benchmark_sample_time_var.get(), "Benchmark sample time"),
                project=self.benchmark_project_var.get(),
                module_id=self.benchmark_module_id_var.get(),
                sample_id=self.benchmark_sample_id_var.get(),
                file_prefix="Benchmark",
                **self._active_offsets(),
            )
            self.test_system = FiltrationTestSystem(self.module, config, valve_callback=self._automation_valve_change, progress_callback=self._automation_progress)
            self.test_thread = threading.Thread(target=self._run_test_thread, daemon=True)
            self.test_thread.start()
        except Exception as exc:
            self.is_running = False
            self._enable_manual_controls()
            self.start_btn_benchmark.config(text="Start")
            messagebox.showerror("Invalid Benchmark Settings", str(exc))

    def start_clean(self) -> None:
        try:
            self._disable_manual_controls()
            self._close_all_valves()
            clean_filter_by_weight = self.clean_fwd_use_weight_var.get()
            clean_backwash_by_weight = self.clean_bw_use_weight_var.get()
            rinse_filter_by_weight = self.rinse_fwd_use_weight_var.get()
            rinse_backwash_by_weight = self.rinse_bw_use_weight_var.get()
            config = CleanConfig(
                forward_target=self._positive(self.clean_fwd_target_weight_var.get() if clean_filter_by_weight else self.clean_fwd_target_time_var.get(), "Clean filter target"),
                forward_by_weight=clean_filter_by_weight,
                soak_time=self._positive(self.clean_soak_var.get(), "Soak time"),
                backwash_target=self._positive(self.clean_bw_target_weight_var.get() if clean_backwash_by_weight else self.clean_bw_target_time_var.get(), "Clean backwash target"),
                backwash_by_weight=clean_backwash_by_weight,
                rinse_forward_target=self._positive(self.rinse_fwd_target_weight_var.get() if rinse_filter_by_weight else self.rinse_fwd_target_time_var.get(), "Rinse filter target"),
                rinse_forward_by_weight=rinse_filter_by_weight,
                rinse_backwash_target=self._positive(self.rinse_bw_target_weight_var.get() if rinse_backwash_by_weight else self.rinse_bw_target_time_var.get(), "Rinse backwash target"),
                rinse_backwash_by_weight=rinse_backwash_by_weight,
                cycle_count=self._positive_count(self.clean_cycle_count_var.get(), "Clean cycle count"),
                sample_time=self._positive(self.clean_sample_time_var.get(), "Clean sample time"),
                purge_time=self._positive(self.clean_purge_time_var.get(), "Clean purge time"),
                project=self.clean_project_var.get(),
                module_id=self.clean_module_id_var.get(),
                solution=self.clean_solution_var.get(),
                **self._active_offsets(),
            )
            self.test_system = CleanTestSystem(self.module, config, valve_callback=self._automation_valve_change, progress_callback=self._automation_progress, prompt_callback=self._thread_safe_prompt)
            self.test_thread = threading.Thread(target=self._run_test_thread, daemon=True)
            self.test_thread.start()
        except Exception as exc:
            self.is_running = False
            self._enable_manual_controls()
            self.start_btn_clean.config(text="Start")
            messagebox.showerror("Invalid Clean Settings", str(exc))

    def _run_test_thread(self) -> None:
        try:
            self.test_system.start_test()
        except AutomationError as exc:
            self._automation_error = str(exc)
        except Exception as exc:
            self._automation_error = f"Unexpected automation error: {exc}"
        finally:
            self.after(0, self._test_finished)

    def cancel_test(self) -> None:
        if not hasattr(self, "test_system"):
            self._test_finished()
            return
        self.test_system.cancel()
        self.cycle_step_var.set("Stopping")
        for button in (self.start_btn_test, self.start_btn_clean, self.start_btn_benchmark):
            button.config(state="disabled")
        self.after(100, self._wait_for_test_thread)

    def _wait_for_test_thread(self) -> None:
        if hasattr(self, "test_thread") and self.test_thread.is_alive():
            self.after(100, self._wait_for_test_thread)
            return
        self._test_finished()

    def _test_finished(self) -> None:
        super()._test_finished()
        for button in (self.start_btn_test, self.start_btn_clean, self.start_btn_benchmark):
            button.config(state="normal")
        if self._automation_error:
            error = self._automation_error
            self._automation_error = None
            messagebox.showerror("MEU Run Stopped", error)


__all__ = ["HMI", "normalize_io_text"]
