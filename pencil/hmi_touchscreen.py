"""Touchscreen sizing refinements for the final MEU HMI."""

from __future__ import annotations

import tkinter as tk

from .hmi_final import HMI as _FinalHMI


class HMI(_FinalHMI):
    """Final HMI with larger, well-spaced touchscreen settings fields."""

    SETTINGS_MIN_WIDTH = 900
    SETTINGS_MIN_HEIGHT = 680

    def _style_settings_window(self, window: tk.Toplevel) -> None:
        """Enlarge settings controls so each field is an easy touch target."""
        super()._style_settings_window(window)

        def enlarge(parent: tk.Widget) -> None:
            for child in parent.winfo_children():
                try:
                    if isinstance(child, tk.Entry):
                        child.configure(font=("Arial", 22), width=max(12, int(child.cget("width"))))
                    elif isinstance(child, tk.Checkbutton):
                        child.configure(font=("Arial", 19), padx=14, pady=9)
                    elif isinstance(child, tk.Label):
                        child.configure(font=("Arial", 19))
                    elif isinstance(child, tk.Button):
                        child.configure(font=("Arial", 20, "bold"), height=2, padx=26, pady=12)
                except (tk.TclError, ValueError):
                    pass

                try:
                    manager = child.winfo_manager()
                    if manager == "grid":
                        info = child.grid_info()
                        options = {
                            "padx": max(10, int(info.get("padx", 0) or 0)),
                            "pady": max(7, int(info.get("pady", 0) or 0)),
                        }
                        if isinstance(child, tk.Entry):
                            options["ipady"] = 9
                            options["ipadx"] = 8
                        elif isinstance(child, tk.Checkbutton):
                            options["ipady"] = 5
                            options["ipadx"] = 5
                        child.grid_configure(**options)
                    elif manager == "pack":
                        info = child.pack_info()
                        child.pack_configure(
                            padx=max(10, int(info.get("padx", 0) or 0)),
                            pady=max(7, int(info.get("pady", 0) or 0)),
                        )
                except (tk.TclError, ValueError):
                    pass

                enlarge(child)

        enlarge(window)

        try:
            window.update_idletasks()
            screen_width = self.winfo_screenwidth()
            screen_height = self.winfo_screenheight()
            width = min(screen_width - 20, max(self.SETTINGS_MIN_WIDTH, window.winfo_reqwidth() + 120))
            height = min(screen_height - 24, max(self.SETTINGS_MIN_HEIGHT, window.winfo_reqheight() + 70))
            x = max(0, self.winfo_rootx() + (self.winfo_width() - width) // 2)
            y = max(0, self.winfo_rooty() + (self.winfo_height() - height) // 2)
            window.geometry(f"{width}x{height}+{x}+{y}")
            window.lift()
            window.focus_force()
        except tk.TclError:
            pass


__all__ = ["HMI"]
