"""Top-button navigation layout for the MEU touchscreen HMI."""

from __future__ import annotations

import tkinter as tk

from .hmi_layout_validated import HMI as _ValidatedHMI
from .hmi_navigation_fix import HMI as _PreviousHMI


class HMI(_PreviousHMI):
    """MEU HMI with uniform top navigation and a centered PFD."""

    TOP_MARGIN = 8
    NAV_HEIGHT = 34
    PFD_HEIGHT = 217
    PFD_WIDTH = 780
    PFD_SCALE_X = 1.0
    NAV_FONT = ("Arial", 9)
    NAV_FONT_ACTIVE = ("Arial", 9, "bold")
    START_FONT = ("Arial", 15, "bold")

    def _finish_navigation_layout(self) -> None:
        """Finalize the tabless page stack and operator control sizing."""
        super()._finish_navigation_layout()
        self._enlarge_start_buttons()
        self._refresh_navigation_rails()
        self.update_idletasks()

    def _create_pfd(self, parent: tk.Widget) -> dict:
        """Create a centered PFD with a separate uniform top button row."""
        section = tk.Frame(
            parent,
            width=self.PFD_WIDTH,
            height=self.NAV_HEIGHT + self.PFD_HEIGHT,
            bg=parent.cget("bg"),
            bd=0,
            highlightthickness=0,
        )
        section.pack(side="top", anchor="n", padx=10, pady=(2, 0))
        section.pack_propagate(False)

        nav = tk.Frame(
            section,
            width=self.PFD_WIDTH,
            height=self.NAV_HEIGHT,
            bg=parent.cget("bg"),
            bd=0,
            highlightthickness=0,
        )
        nav.pack(side="top", fill="x")
        nav.pack_propagate(False)

        pfd_holder = tk.Frame(
            section,
            width=self.PFD_WIDTH,
            height=self.PFD_HEIGHT,
            bg="white",
            bd=1,
            relief="solid",
            highlightthickness=0,
        )
        pfd_holder.pack(side="top", anchor="n")
        pfd_holder.pack_propagate(False)

        # Build the diagram directly in its final parent. This avoids reparenting,
        # overlap, clipping, and geometry-manager conflicts.
        pfd = _ValidatedHMI._create_pfd(self, pfd_holder)
        canvas = pfd["canvas"]

        # Remove the legacy help button. Info is provided in the top navigation.
        for widget in list(self._walk_widgets(canvas)):
            if not isinstance(widget, tk.Button):
                continue
            try:
                if widget.cget("text") == "?":
                    owner = widget.master
                    widget.destroy()
                    if isinstance(owner, tk.Frame) and not owner.winfo_children():
                        owner.destroy()
            except Exception:
                pass

        # Retain the corrected equal-width outlet vessels and connected V5 route.
        self._resize_pfd_vessels_and_routes(canvas)
        canvas.configure(width=self.PFD_WIDTH - 2, height=self.PFD_HEIGHT - 2)
        canvas.pack_configure(side="top", anchor="n", pady=0)

        pfd["top_section"] = section
        pfd["navigation_rail"] = nav
        pfd["navigation_buttons"] = self._populate_top_navigation(nav, parent)
        return pfd

    def _populate_top_navigation(
        self, nav: tk.Frame, current_tab: tk.Widget
    ) -> list[tk.Button]:
        """Create four equal-size top navigation buttons."""
        nav.columnconfigure((0, 1, 2, 3), weight=1, uniform="meu_nav")
        buttons: list[tk.Button] = []
        items = (
            ("Test", self.test_tab, lambda: self._select_tab(self.test_tab)),
            (
                "Benchmark",
                self.benchmark_tab,
                lambda: self._select_tab(self.benchmark_tab),
            ),
            ("Clean", self.clean_tab, lambda: self._select_tab(self.clean_tab)),
            ("Info", None, self._show_control_narrative),
        )

        for column, (label, tab, command) in enumerate(items):
            selected = tab is not None and tab is current_tab
            button = tk.Button(
                nav,
                text=label,
                command=command,
                font=self.NAV_FONT_ACTIVE if selected else self.NAV_FONT,
                relief="sunken" if selected else "raised",
                borderwidth=2,
                highlightthickness=0,
                bg="#cfcfcf" if selected else "#e8e8e8",
                activebackground="#d8d8d8",
                padx=4,
                pady=3,
                cursor="hand2",
            )
            button.grid(
                row=0,
                column=column,
                sticky="nsew",
                padx=(0 if column == 0 else 2, 0),
                pady=(0, 3),
            )
            buttons.append(button)
        return buttons

    def _refresh_navigation_rails(self) -> None:
        """Show one consistent active state across every top navigation row."""
        active_index = {
            self.test_tab: 0,
            self.benchmark_tab: 1,
            self.clean_tab: 2,
        }.get(self._active_tab)

        for pfd in self.pfds.values():
            buttons = pfd.get("navigation_buttons", [])
            for index, button in enumerate(buttons):
                selected = index == active_index and index < 3
                try:
                    button.configure(
                        relief="sunken" if selected else "raised",
                        bg="#cfcfcf" if selected else "#e8e8e8",
                        font=self.NAV_FONT_ACTIVE if selected else self.NAV_FONT,
                    )
                except Exception:
                    pass

    def _enlarge_start_buttons(self) -> None:
        """Increase every Start/Stop control without affecting other buttons."""
        for tab in (self.test_tab, self.benchmark_tab, self.clean_tab):
            for widget in self._walk_widgets(tab):
                if not isinstance(widget, tk.Button):
                    continue
                try:
                    if str(widget.cget("text")) not in {"Start", "Stop"}:
                        continue
                    widget.configure(
                        font=self.START_FONT,
                        width=9,
                        height=1,
                        padx=8,
                        pady=5,
                    )
                except Exception:
                    pass


__all__ = ["HMI"]
