"""Vertical navigation rail for the MEU touchscreen HMI."""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk

from .hmi_layout_validated import HMI as _ValidatedHMI


class HMI(_ValidatedHMI):
    """MEU HMI with compact left-side navigation and full-size touch targets."""

    NAV_WIDTH = 64
    PFD_HEIGHT = 225
    PFD_SCALE_X = 0.91

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._hide_native_tabs()
        self.after_idle(self._refresh_navigation_rails)

    def _hide_native_tabs(self) -> None:
        """Hide the horizontal ttk tab row without changing notebook behavior."""
        style = ttk.Style(self)
        style.layout("MEU.Hidden.TNotebook", [("Notebook.client", {"sticky": "nswe"})])
        style.configure("MEU.Hidden.TNotebook", borderwidth=0, tabmargins=0)
        self.notebook.configure(style="MEU.Hidden.TNotebook")

    def _select_tab(self, tab: tk.Widget) -> None:
        self.notebook.select(tab)
        self.after_idle(self._refresh_navigation_rails)

    def _create_pfd(self, parent: tk.Widget) -> dict:
        """Condense the PFD and add a narrow navigation rail inside its left edge."""
        pfd = super()._create_pfd(parent)
        canvas = pfd["canvas"]

        # Remove any legacy help button. Info is now part of the navigation rail.
        for child in list(canvas.winfo_children()):
            if isinstance(child, tk.Button):
                try:
                    if child.cget("text") == "?":
                        child.destroy()
                except Exception:
                    pass

        # Compress the complete PFD just enough to create a dedicated navigation
        # rail while preserving readable text, valve buttons, and vessel sizes.
        canvas.scale("all", 0, 0, self.PFD_SCALE_X, 1.0)
        canvas.move("all", self.NAV_WIDTH, 0)

        rail = tk.Frame(
            canvas,
            width=self.NAV_WIDTH,
            height=self.PFD_HEIGHT,
            bg="white",
            bd=0,
            highlightthickness=0,
        )
        rail.pack_propagate(False)
        canvas.create_window(0, 0, window=rail, anchor="nw")
        pfd["navigation_rail"] = rail
        pfd["navigation_buttons"] = self._populate_navigation_rail(rail, parent)
        return pfd

    def _populate_navigation_rail(
        self, rail: tk.Frame, current_tab: tk.Widget
    ) -> list[tk.Button]:
        """Use flat labels with a larger invisible rectangular touch area."""
        buttons: list[tk.Button] = []
        destinations = (
            ("Test", self.test_tab),
            ("Benchmark", self.benchmark_tab),
            ("Clean", self.clean_tab),
        )

        for label, tab in destinations:
            selected = tab is current_tab
            button = tk.Button(
                rail,
                text=label,
                command=lambda target=tab: self._select_tab(target),
                width=8,
                height=2,
                font=("Arial", 9),
                relief="flat",
                borderwidth=0,
                highlightthickness=0,
                bg="#d9d9d9" if selected else "white",
                activebackground="#d9d9d9",
                padx=2,
                pady=2,
                cursor="hand2",
            )
            button.pack(fill="x", pady=(2, 1))
            buttons.append(button)

        info_button = tk.Button(
            rail,
            text="Info",
            command=self._show_control_narrative,
            width=8,
            height=2,
            font=("Arial", 9),
            relief="flat",
            borderwidth=0,
            highlightthickness=0,
            bg="white",
            activebackground="#d9d9d9",
            padx=2,
            pady=2,
            cursor="hand2",
        )
        info_button.pack(fill="x", pady=(2, 1))
        buttons.append(info_button)
        return buttons

    def _refresh_navigation_rails(self) -> None:
        """Keep the selected tab visibly distinct on every PFD rail."""
        current = self.notebook.select()
        for key, pfd in self.pfds.items():
            buttons = pfd.get("navigation_buttons", [])
            tab = {
                "test": self.test_tab,
                "benchmark": self.benchmark_tab,
                "clean": self.clean_tab,
            }.get(key)
            selected = tab is not None and str(tab) == current
            for index, button in enumerate(buttons[:3]):
                button.configure(bg="#d9d9d9" if selected and index == (0 if key == "test" else 1 if key == "benchmark" else 2) else "white")


__all__ = ["HMI"]
