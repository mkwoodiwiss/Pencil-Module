"""Vertical navigation rail for the MEU touchscreen HMI."""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk

from .hmi_layout_validated import HMI as _ValidatedHMI


class HMI(_ValidatedHMI):
    """MEU HMI with compact left-side navigation and full-size touch targets."""

    NAV_WIDTH = 72
    PFD_HEIGHT = 225
    PFD_SCALE_X = 0.90

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._hide_native_tabs()
        self.after_idle(self._finish_navigation_layout)

    def _finish_navigation_layout(self) -> None:
        """Reapply the hidden-tab style after Tk finishes constructing the notebook."""
        self._hide_native_tabs()
        self._refresh_navigation_rails()

    def _hide_native_tabs(self) -> None:
        """Remove the horizontal ttk tab row while preserving notebook switching."""
        style = ttk.Style(self)
        style.layout(
            "MEU.Hidden.TNotebook",
            [("Notebook.client", {"sticky": "nswe"})],
        )
        style.configure(
            "MEU.Hidden.TNotebook",
            borderwidth=0,
            tabmargins=0,
            padding=0,
        )
        self.notebook.configure(style="MEU.Hidden.TNotebook")

    def _select_tab(self, tab: tk.Widget) -> None:
        self.notebook.select(tab)
        self.after_idle(self._refresh_navigation_rails)

    def _create_pfd(self, parent: tk.Widget) -> dict:
        """Condense the PFD and add a narrow button rail inside its left edge."""
        pfd = super()._create_pfd(parent)
        canvas = pfd["canvas"]

        # Remove the former help button. Info in the side rail replaces it.
        for child in list(canvas.winfo_children()):
            if not isinstance(child, tk.Button):
                continue
            try:
                if child.cget("text") == "?":
                    child.destroy()
            except Exception:
                pass

        # Compress only enough to provide the navigation rail while keeping all
        # process labels, vessels, lines, and valve controls readable.
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
        """Create clearly defined industrial-style navigation buttons."""
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
                font=("Arial", 9, "bold" if selected else "normal"),
                relief="sunken" if selected else "raised",
                borderwidth=2,
                highlightthickness=0,
                bg="#cfcfcf" if selected else "#e8e8e8",
                activebackground="#d8d8d8",
                padx=2,
                pady=7,
                cursor="hand2",
            )
            button.pack(fill="x", padx=3, pady=(3, 2))
            buttons.append(button)

        info_button = tk.Button(
            rail,
            text="Info",
            command=self._show_control_narrative,
            font=("Arial", 9),
            relief="raised",
            borderwidth=2,
            highlightthickness=0,
            bg="#e8e8e8",
            activebackground="#d8d8d8",
            padx=2,
            pady=7,
            cursor="hand2",
        )
        info_button.pack(fill="x", padx=3, pady=(3, 2))
        buttons.append(info_button)
        return buttons

    def _refresh_navigation_rails(self) -> None:
        """Keep the selected navigation button visibly depressed."""
        current = self.notebook.select()
        index_by_key = {"test": 0, "benchmark": 1, "clean": 2}

        for key, pfd in self.pfds.items():
            buttons = pfd.get("navigation_buttons", [])
            selected_index = index_by_key.get(key)
            for index, button in enumerate(buttons[:3]):
                is_selected = selected_index == index and str(
                    (self.test_tab, self.benchmark_tab, self.clean_tab)[index]
                ) == current
                button.configure(
                    relief="sunken" if is_selected else "raised",
                    bg="#cfcfcf" if is_selected else "#e8e8e8",
                    font=("Arial", 9, "bold" if is_selected else "normal"),
                )


__all__ = ["HMI"]
