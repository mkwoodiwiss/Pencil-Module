"""Final Clean-tab settings geometry correction."""

from __future__ import annotations

import tkinter as tk

from . import hmi_final as _hmi_final_module
from .hmi_touchscreen import HMI as _TouchscreenHMI


class HMI(_TouchscreenHMI):
    """Touchscreen HMI with Clean settings matched to the Test settings panel."""

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.after(300, self._apply_clean_settings_match)
        try:
            self.notebook.bind("<<NotebookTabChanged>>", self._clean_tab_selected, add="+")
        except tk.TclError:
            pass

    def _clean_tab_selected(self, _event=None) -> None:
        try:
            selected = self.notebook.select()
            if selected and self.nametowidget(selected) is self.clean_tab:
                self.after_idle(self._apply_clean_settings_match)
        except (tk.TclError, KeyError):
            pass

    def _apply_clean_settings_match(self) -> None:
        """Match only the Clean Settings frame and buttons to the Test panel."""
        test_settings = self._find_settings_frame(self.test_tab)
        clean_settings = self._find_settings_frame(self.clean_tab)
        if test_settings is None or clean_settings is None:
            return

        try:
            self.update_idletasks()
            test_width = max(test_settings.winfo_reqwidth(), test_settings.winfo_width())
            test_height = max(test_settings.winfo_reqheight(), test_settings.winfo_height())
            test_parent_width = max(
                test_settings.master.winfo_reqwidth(),
                test_settings.master.winfo_width(),
            )

            clean_settings.master.configure(width=test_parent_width)
            clean_settings.master.pack_propagate(False)
            clean_settings.pack_configure(fill="none", anchor="sw")
            clean_settings.configure(width=test_width, height=test_height)
            clean_settings.pack_propagate(False)
            clean_settings.grid_propagate(False)
        except tk.TclError:
            return

        test_buttons = self._buttons_by_text(test_settings)
        clean_buttons = self._buttons_by_text(clean_settings)
        for text in ("Edit Settings", "Calibrate", "Tare FIL", "Tare BW EFL"):
            source = test_buttons.get(text)
            target = clean_buttons.get(text)
            if source is None or target is None:
                continue
            try:
                target.configure(
                    font=source.cget("font"),
                    width=source.cget("width"),
                    height=source.cget("height"),
                    padx=source.cget("padx"),
                    pady=source.cget("pady"),
                )
            except tk.TclError:
                pass

        try:
            self.update_idletasks()
        except tk.TclError:
            pass


_hmi_final_module.HMI = HMI

__all__ = ["HMI"]
