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
    """Replace legacy public-facing names with approved MEU terminology."""
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
        self._normalize_visible_text(self)

    def _normalize_visible_text(self, root: tk.Misc) -> None:
        for widget in self._walk_widgets(root):
            try:
                text = widget.cget("text")
            except Exception:
                continue
            if not isinstance(text, str) or not text:
                continue
            normalized = normalize_io_text(text)
            if normalized != text:
                try:
                    widget.configure(text=normalized)
                except Exception:
                    pass

    def _toggle_test(self) -> None:
        if self.is_running:
            self._stop_current_test()
            return

        try:
            config = self._build_filtration_config()
        except Exception as exc:
            messagebox.showerror("Invalid Configuration", str(exc))
            return

        self.is_running = True
        self.start_btn_test.configure(text="Stop")
        self.test_system = FiltrationTestSystem(
            self.module,
            config,
            valve_callback=self._set_solenoid_state,
            progress_callback=self._update_progress,
        )
        threading.Thread(target=self._run_test_system, args=(self.test_system,), daemon=True).start()

    def _toggle_clean(self) -> None:
        if self.is_running:
            self._stop_current_test()
            return

        try:
            config = self._build_clean_config()
        except Exception as exc:
            messagebox.showerror("Invalid Configuration", str(exc))
            return

        self.is_running = True
        self.start_btn_clean.configure(text="Stop")
        self.clean_system = CleanTestSystem(
            self.module,
            config,
            valve_callback=self._set_solenoid_state,
            progress_callback=self._update_progress,
            prompt_callback=self._operator_prompt,
        )
        threading.Thread(target=self._run_test_system, args=(self.clean_system,), daemon=True).start()

    def _run_test_system(self, system) -> None:
        try:
            system.start_test()
        except AutomationError as exc:
            self.after(0, lambda: messagebox.showerror("Automation Error", str(exc)))
        except Exception as exc:
            self.after(0, lambda: messagebox.showerror("Unexpected Error", str(exc)))
        finally:
            self.after(0, self._reset_run_state)

    def _stop_current_test(self) -> None:
        for name in ("test_system", "clean_system", "benchmark_system"):
            system = getattr(self, name, None)
            if system is not None:
                try:
                    system.cancel()
                except Exception:
                    pass

    def _reset_run_state(self) -> None:
        self.is_running = False
        for name in ("start_btn_test", "start_btn_clean", "start_btn_benchmark"):
            button = getattr(self, name, None)
            if button is not None:
                try:
                    button.configure(text="Start")
                except Exception:
                    pass


__all__ = ["HMI", "normalize_io_text"]
