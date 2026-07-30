"""Final Clean-tab settings geometry correction."""

from __future__ import annotations

import tkinter as tk

from . import hmi_final as _hmi_final_module
from .hmi_touchscreen import HMI as _TouchscreenHMI


class HMI(_TouchscreenHMI):
    """Touchscreen HMI with a compact, slightly taller Clean settings panel."""

    CLEAN_EXTRA_HEIGHT = 24
    CLEAN_BUTTON_FONT = ("Arial", 12)
    CLEAN_BUTTON_WIDTH = 12
    CLEAN_BUTTON_HEIGHT = 1
    CLEAN_BUTTON_PADX = 4
    CLEAN_BUTTON_PADY = 2
    COMPACT_SUMMARY_LINE_WIDTH = 16

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.after(300, self._apply_clean_settings_layout)
        try:
            self.notebook.bind("<<NotebookTabChanged>>", self._clean_tab_selected, add="+")
        except tk.TclError:
            pass

    @classmethod
    def _truncate_summary_text(cls, text: str) -> str:
        """Retain the established value-based truncation helper behavior."""
        prefixes = ("Project: ", "Module: ", "Sample: ", "Solution: ")
        output = []
        for line in str(text).splitlines():
            for prefix in prefixes:
                if line.startswith(prefix):
                    value = line[len(prefix) :]
                    if len(value) > cls.SUMMARY_VALUE_WIDTH:
                        value = f"{value[: cls.SUMMARY_VALUE_WIDTH - 3]}..."
                    line = prefix + value
                    break
            output.append(line)
        return "\n".join(output)

    @classmethod
    def _compact_summary_text(cls, text: str) -> str:
        """Fit visible identifier lines inside the fixed summary columns."""
        prefixes = (
            "Project: ",
            "Module: ",
            "Module ID: ",
            "Sample: ",
            "Sample ID: ",
            "Solution: ",
        )
        output = []
        for line in str(text).splitlines():
            for prefix in prefixes:
                if not line.startswith(prefix):
                    continue
                value = line[len(prefix) :]
                available = max(4, cls.COMPACT_SUMMARY_LINE_WIDTH - len(prefix))
                if len(value) > available:
                    value = f"{value[: available - 3]}..."
                line = prefix + value
                break
            output.append(line)
        return "\n".join(output)

    def _compact_summary_variables(self, *names: str) -> None:
        for name in names:
            variable = getattr(self, name, None)
            if variable is not None:
                variable.set(self._compact_summary_text(variable.get()))

    def _update_test_summary(self) -> None:
        super()._update_test_summary()
        self._compact_summary_variables("test_summary_var", "_test_summary_left", "_test_summary_right")

    def _update_benchmark_summary(self) -> None:
        super()._update_benchmark_summary()
        self._compact_summary_variables(
            "benchmark_summary_var",
            "_benchmark_summary_left",
            "_benchmark_summary_right",
        )

    def _update_clean_summary(self) -> None:
        super()._update_clean_summary()
        self._compact_summary_variables("clean_summary_left_var", "clean_summary_right_var")

    def _clean_tab_selected(self, _event=None) -> None:
        try:
            selected = self.notebook.select()
            if selected and self.nametowidget(selected) is self.clean_tab:
                self.after_idle(self._apply_clean_settings_layout)
        except (tk.TclError, KeyError):
            pass

    def _apply_clean_settings_layout(self) -> None:
        """Size only the Clean Settings panel after the final layout has settled."""
        test_settings = self._find_settings_frame(self.test_tab)
        clean_settings = self._find_settings_frame(self.clean_tab)
        if test_settings is None or clean_settings is None:
            return

        try:
            self.update_idletasks()
            test_width = test_settings.winfo_width()
            test_height = test_settings.winfo_height()
            if test_width <= 1 or test_height <= 1:
                self.after(100, self._apply_clean_settings_layout)
                return

            clean_width = test_width
            clean_height = test_height + self.CLEAN_EXTRA_HEIGHT

            clean_settings.master.configure(width=clean_width)
            clean_settings.master.pack_propagate(False)
            clean_settings.pack_configure(fill="none", anchor="sw")
            clean_settings.configure(width=clean_width, height=clean_height)
            clean_settings.pack_propagate(False)
            clean_settings.grid_propagate(False)
        except tk.TclError:
            return

        clean_buttons = self._buttons_by_text(clean_settings)
        for text in ("Edit Settings", "Calibrate", "Tare FIL", "Tare BW EFL"):
            button = clean_buttons.get(text)
            if button is None:
                continue
            try:
                button.configure(
                    font=self.CLEAN_BUTTON_FONT,
                    width=self.CLEAN_BUTTON_WIDTH,
                    height=self.CLEAN_BUTTON_HEIGHT,
                    padx=self.CLEAN_BUTTON_PADX,
                    pady=self.CLEAN_BUTTON_PADY,
                )
                if button.winfo_manager() == "grid":
                    button.grid_configure(padx=4, pady=2, sticky="ew")
            except tk.TclError:
                pass

        try:
            self.update_idletasks()
        except tk.TclError:
            pass


_hmi_final_module.HMI = HMI

__all__ = ["HMI"]
