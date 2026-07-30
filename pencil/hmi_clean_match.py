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

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.after(300, self._apply_clean_settings_layout)
        try:
            self.notebook.bind("<<NotebookTabChanged>>", self._clean_tab_selected, add="+")
        except tk.TclError:
            pass

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
