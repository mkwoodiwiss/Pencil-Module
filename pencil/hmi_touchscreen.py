"""Touchscreen sizing refinements for the final MEU HMI."""

from __future__ import annotations

import tkinter as tk

from . import hmi_final as _hmi_final_module
from .hmi_final import HMI as _FinalHMI


class HMI(_FinalHMI):
    """Final HMI with moderately enlarged touchscreen settings fields."""

    SETTINGS_MIN_WIDTH = 700
    SETTINGS_MIN_HEIGHT = 500

    def _style_settings_window(self, window: tk.Toplevel) -> None:
        """Make settings fields easier to tap without filling the whole display."""
        # This is the final styling layer. Do not call the historical styling
        # chain because the oldest runtime layer has no parent implementation.
        def enlarge(parent: tk.Widget) -> None:
            for child in parent.winfo_children():
                try:
                    if isinstance(child, tk.Entry):
                        child.configure(
                            font=("Arial", 17),
                            width=max(10, int(child.cget("width"))),
                        )
                    elif isinstance(child, tk.Checkbutton):
                        child.configure(font=("Arial", 16), padx=8, pady=4)
                    elif isinstance(child, tk.Label):
                        child.configure(font=("Arial", 16))
                    elif isinstance(child, tk.Button):
                        child.configure(
                            font=("Arial", 17, "bold"),
                            height=1,
                            padx=18,
                            pady=7,
                        )
                except (tk.TclError, ValueError):
                    pass

                try:
                    manager = child.winfo_manager()
                    if manager == "grid":
                        info = child.grid_info()
                        options = {
                            "padx": max(7, int(info.get("padx", 0) or 0)),
                            "pady": max(3, int(info.get("pady", 0) or 0)),
                        }
                        if isinstance(child, tk.Entry):
                            options["ipady"] = 4
                            options["ipadx"] = 5
                        elif isinstance(child, tk.Checkbutton):
                            options["ipady"] = 2
                            options["ipadx"] = 2
                        child.grid_configure(**options)
                    elif manager == "pack":
                        info = child.pack_info()
                        child.pack_configure(
                            padx=max(7, int(info.get("padx", 0) or 0)),
                            pady=max(4, int(info.get("pady", 0) or 0)),
                        )
                except (tk.TclError, ValueError):
                    pass

                enlarge(child)

        enlarge(window)

        try:
            window.grid_anchor("center")
            window.update_idletasks()
            screen_width = self.winfo_screenwidth()
            screen_height = self.winfo_screenheight()
            width = min(
                screen_width - 40,
                max(self.SETTINGS_MIN_WIDTH, window.winfo_reqwidth() + 60),
            )
            height = min(
                screen_height - 60,
                max(self.SETTINGS_MIN_HEIGHT, window.winfo_reqheight() + 30),
            )
            x = max(0, self.winfo_rootx() + (self.winfo_width() - width) // 2)
            y = max(0, self.winfo_rooty() + (self.winfo_height() - height) // 2)
            window.geometry(f"{width}x{height}+{x}+{y}")
            window.lift()
            window.focus_force()
        except tk.TclError:
            pass


# Preserve the historical module-level final HMI identity used by tests and imports.
_hmi_final_module.HMI = HMI

__all__ = ["HMI"]
