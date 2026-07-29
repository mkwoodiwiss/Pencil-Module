"""Vertical navigation rail for the MEU touchscreen HMI."""

from __future__ import annotations

import tkinter as tk

from .hmi_layout_validated import HMI as _ValidatedHMI


class HMI(_ValidatedHMI):
    """MEU HMI with compact left-side navigation and no native tab strip."""

    NAV_WIDTH = 72
    PFD_HEIGHT = 225
    PFD_SCALE_X = 0.90
    TOP_MARGIN = 8

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._active_tab = self.test_tab
        self._remove_native_tabs()
        self.after_idle(self._finish_navigation_layout)

    def _finish_navigation_layout(self) -> None:
        """Finalize the tabless page stack after Tk calculates geometry."""
        self._remove_native_tabs()
        self._show_page(self._active_tab)
        self._remove_legacy_help_controls()
        self._refresh_navigation_rails()
        self.update_idletasks()

    def _remove_native_tabs(self) -> None:
        """Remove every page from ttk.Notebook so no native tabs exist."""
        try:
            self.notebook.pack_configure(pady=(self.TOP_MARGIN, 0))
        except Exception:
            pass

        for tab in (self.test_tab, self.benchmark_tab, self.clean_tab):
            try:
                if str(tab) in self.notebook.tabs():
                    self.notebook.forget(tab)
            except Exception:
                pass

    def _show_page(self, tab: tk.Widget) -> None:
        """Display one former notebook page using a tabless stacked layout."""
        for page in (self.test_tab, self.benchmark_tab, self.clean_tab):
            try:
                page.place_forget()
            except Exception:
                pass

        tab.place(in_=self.notebook, x=0, y=0, relwidth=1.0, relheight=1.0)
        tab.lift()
        self._active_tab = tab

    def _remove_legacy_help_controls(self) -> None:
        """Remove every legacy question-mark button, including nested buttons."""
        for pfd in self.pfds.values():
            canvas = pfd.get("canvas")
            if canvas is None:
                continue
            for widget in list(self._walk_widgets(canvas)):
                if not isinstance(widget, tk.Button):
                    continue
                try:
                    if widget.cget("text") == "?":
                        parent = widget.master
                        widget.destroy()
                        if isinstance(parent, tk.Frame) and not parent.winfo_children():
                            parent.destroy()
                except Exception:
                    pass

    def _select_tab(self, tab: tk.Widget) -> None:
        self._show_page(tab)
        self.after_idle(self._refresh_navigation_rails)

    def _create_pfd(self, parent: tk.Widget) -> dict:
        """Condense the PFD and add a narrow button rail inside its left edge."""
        pfd = super()._create_pfd(parent)
        canvas = pfd["canvas"]

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
        active_index = {
            self.test_tab: 0,
            self.benchmark_tab: 1,
            self.clean_tab: 2,
        }.get(self._active_tab)

        for pfd in self.pfds.values():
            buttons = pfd.get("navigation_buttons", [])
            for index, button in enumerate(buttons[:3]):
                is_selected = index == active_index
                button.configure(
                    relief="sunken" if is_selected else "raised",
                    bg="#cfcfcf" if is_selected else "#e8e8e8",
                    font=("Arial", 9, "bold" if is_selected else "normal"),
                )


__all__ = ["HMI"]
