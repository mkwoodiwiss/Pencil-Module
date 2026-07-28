"""Runtime fixes for the MEU touchscreen HMI."""

from __future__ import annotations

import os
import tkinter as tk
from tkinter import messagebox

from .hmi_meu import HMI as _MEUHMI


class HMI(_MEUHMI):
    """MEU HMI with reliable callbacks and touchscreen run-state behavior."""

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._bind_settings_action_buttons()
        self._run_started = False

    @staticmethod
    def _is_descendant(widget: tk.Widget, ancestor: tk.Widget) -> bool:
        current = widget
        while current is not None:
            if current is ancestor:
                return True
            try:
                parent_name = current.winfo_parent()
                if not parent_name:
                    break
                current = current.nametowidget(parent_name)
            except Exception:
                break
        return False

    def _bind_settings_action_buttons(self) -> None:
        """Bind Python callables after the settings buttons are rearranged."""
        for widget in self._walk_widgets(self):
            if not isinstance(widget, tk.Button):
                continue

            try:
                text = widget.cget("text")
            except Exception:
                continue

            if self._is_descendant(widget, self.test_tab):
                edit_command = self._edit_test_settings
            elif self._is_descendant(widget, self.benchmark_tab):
                edit_command = self._edit_benchmark_settings
            elif self._is_descendant(widget, self.clean_tab):
                edit_command = self._edit_clean_settings
            else:
                continue

            if text == "Edit Settings":
                widget.config(command=edit_command)
            elif text == "Calibrate":
                widget.config(command=self.calibrate)
            elif text == "Tare FIL":
                widget.config(command=lambda: self.module.zero_scale(0))
            elif text == "Tare BW EFL":
                widget.config(command=lambda: self.module.zero_scale(1))

    def _style_settings_window(self, window: tk.Toplevel) -> None:
        """Use a slightly larger centered settings dialog."""
        super()._style_settings_window(window)
        try:
            window.update_idletasks()
            width = min(self.winfo_screenwidth() - 30, window.winfo_reqwidth() + 70)
            height = min(self.winfo_screenheight() - 50, window.winfo_reqheight() + 55)
            x = self.winfo_rootx() + max(0, (self.winfo_width() - width) // 2)
            y = self.winfo_rooty() + max(0, (self.winfo_height() - height) // 2)
            window.geometry(f"{width}x{height}+{x}+{y}")
        except Exception:
            pass

    def _disable_manual_controls(self) -> None:
        """Disable every HMI button except Cancel, help, and close during a run."""
        for widget in self._walk_widgets(self):
            if not isinstance(widget, tk.Button):
                continue
            try:
                text = widget.cget("text")
                if text in {"Cancel", "?", "X"}:
                    widget.config(state="normal")
                else:
                    widget.config(state="disabled")
            except Exception:
                pass

    def _enable_manual_controls(self) -> None:
        """Restore all HMI buttons after a run finishes."""
        for widget in self._walk_widgets(self):
            if isinstance(widget, tk.Button):
                try:
                    widget.config(state="normal")
                except Exception:
                    pass
        self._bind_settings_action_buttons()
        self._sync_all_valve_buttons()

    def _finish_start_attempt(self) -> None:
        if getattr(self, "is_running", False):
            self._disable_manual_controls()
        else:
            self._run_started = False
            self._enable_manual_controls()

    def start_test(self) -> None:
        self._run_started = True
        super().start_test()
        self._finish_start_attempt()

    def start_benchmark(self) -> None:
        self._run_started = True
        super().start_benchmark()
        self._finish_start_attempt()

    def start_clean(self) -> None:
        self._run_started = True
        super().start_clean()
        self._finish_start_attempt()

    def _latest_saved_files(self) -> list[str]:
        """Return the newest data/settings files from the active log directory."""
        log_dir = getattr(getattr(self, "test_system", None), "log_dir", "logs")
        try:
            names = [
                name for name in os.listdir(log_dir)
                if name.endswith("_data.csv") or name.endswith("_settings.csv")
            ]
            names.sort(
                key=lambda name: os.path.getmtime(os.path.join(log_dir, name)),
                reverse=True,
            )
            if not names:
                return []

            newest = names[0]
            stem = newest.removesuffix("_data.csv").removesuffix("_settings.csv")
            matching = [name for name in names if name.startswith(stem)]
            return [os.path.abspath(os.path.join(log_dir, name)) for name in sorted(matching)]
        except Exception:
            return []

    def _test_finished(self) -> None:
        had_error = bool(getattr(self, "_automation_error", None))
        saved_files = self._latest_saved_files() if self._run_started and not had_error else []
        completed = self._run_started and not had_error

        super()._test_finished()
        self._run_started = False

        if completed:
            if saved_files:
                file_text = "\n".join(saved_files)
                message = f"Test complete. Files saved:\n\n{file_text}"
            else:
                message = "Test complete. The run files were saved in the logs folder."
            messagebox.showinfo("MEU Test Complete", message)
