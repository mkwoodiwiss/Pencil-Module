"""Runtime fixes for the MEU touchscreen HMI."""

from __future__ import annotations

import tkinter as tk

from .hmi_meu import HMI as _MEUHMI


class HMI(_MEUHMI):
    """MEU HMI with reliable callbacks for rebuilt settings controls."""

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._bind_settings_action_buttons()

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
