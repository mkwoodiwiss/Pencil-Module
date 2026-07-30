"""Touchscreen-safe sizing and centering for MEU settings dialogs."""

from __future__ import annotations

import tkinter as tk

from .hmi_clean_match import HMI as _CleanMatchHMI


class HMI(_CleanMatchHMI):
    """MEU HMI with compact settings dialogs centered on the display."""

    SETTINGS_SCREEN_MARGIN_X = 12
    SETTINGS_SCREEN_MARGIN_Y = 12

    def _style_settings_window(self, window: tk.Toplevel) -> None:
        """Shrink the inherited dialog styling and center it on the screen."""
        super()._style_settings_window(window)

        self._compact_settings_widgets(window)

        # Tk may not have calculated the final requested size until the dialog is
        # mapped. Reapply the geometry after idle and once more shortly afterward.
        self._fit_and_center_settings_window(window)
        window.after_idle(lambda: self._fit_and_center_settings_window(window))
        window.after(40, lambda: self._fit_and_center_settings_window(window))

    def _compact_settings_widgets(self, parent: tk.Widget) -> None:
        """Reduce only the popup controls enough to fit the 800x480 display."""
        for child in parent.winfo_children():
            try:
                if isinstance(child, tk.Button):
                    child.configure(font=("Arial", 13), height=1, padx=10, pady=3)
                elif isinstance(child, tk.Checkbutton):
                    child.configure(font=("Arial", 12), padx=5, pady=2)
                elif isinstance(child, tk.Entry):
                    child.configure(
                        font=("Arial", 13),
                        width=max(8, min(18, int(child.cget("width")))),
                    )
                elif isinstance(child, tk.Label):
                    child.configure(font=("Arial", 12))
            except (tk.TclError, ValueError, TypeError):
                pass

            try:
                manager = child.winfo_manager()
                if manager == "grid":
                    info = child.grid_info()
                    child.grid_configure(
                        padx=min(5, int(info.get("padx", 0) or 0)),
                        pady=min(3, int(info.get("pady", 0) or 0)),
                    )
                elif manager == "pack":
                    info = child.pack_info()
                    child.pack_configure(
                        padx=min(5, int(info.get("padx", 0) or 0)),
                        pady=min(3, int(info.get("pady", 0) or 0)),
                    )
            except (tk.TclError, ValueError, TypeError):
                pass

            self._compact_settings_widgets(child)

    def _fit_and_center_settings_window(self, window: tk.Toplevel) -> None:
        """Use the dialog's natural size, constrained to the visible screen."""
        try:
            if not window.winfo_exists():
                return

            window.update_idletasks()
            screen_width = window.winfo_screenwidth()
            screen_height = window.winfo_screenheight()
            max_width = max(1, screen_width - (2 * self.SETTINGS_SCREEN_MARGIN_X))
            max_height = max(1, screen_height - (2 * self.SETTINGS_SCREEN_MARGIN_Y))

            width = min(max_width, window.winfo_reqwidth())
            height = min(max_height, window.winfo_reqheight())
            x = max(0, (screen_width - width) // 2)
            y = max(0, (screen_height - height) // 2)

            window.geometry(f"{width}x{height}+{x}+{y}")
            window.lift()
        except tk.TclError:
            pass


__all__ = ["HMI"]
