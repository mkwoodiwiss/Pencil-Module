"""Final v2 navigation and page-alignment corrections."""

from __future__ import annotations

import tkinter as tk

from .hmi_v2_startup_fix import HMI as _V2StartupHMI


class HMI(_V2StartupHMI):
    """Restore Exit and align inherited v1 pages with the new v2 pages."""

    def _show_page(self, tab: tk.Widget) -> None:
        for page in self._process_pages():
            try:
                page.place_forget()
            except Exception:
                pass

        # The inherited Benchmark, Test, and Clean pages retain the old notebook
        # client top inset from v1. Move only those pages up by that measured inset
        # so every navigation row begins at the same screen position.
        legacy_pages = (self.benchmark_tab, self.test_tab, self.clean_tab)
        y = -int(getattr(self, "TOP_MARGIN", 0)) if tab in legacy_pages else 0
        tab.place(in_=self.notebook, x=0, y=y, relwidth=1.0, relheight=1.0, height=-y)
        tab.lift()
        self._active_tab = tab

    def _populate_top_navigation(
        self, nav: tk.Frame, current_tab: tk.Widget
    ) -> list[tk.Button]:
        if not hasattr(self, "flush_tab"):
            return super()._populate_top_navigation(nav, current_tab)

        nav.columnconfigure(tuple(range(6)), weight=1, uniform="meu_nav")
        nav.rowconfigure(0, weight=1)
        items = (
            ("Flush", self.flush_tab, lambda: self._select_tab(self.flush_tab)),
            ("Benchmark", self.benchmark_tab, lambda: self._select_tab(self.benchmark_tab)),
            ("Test", self.test_tab, lambda: self._select_tab(self.test_tab)),
            ("Post-Scrub", self.post_scrub_tab, lambda: self._select_tab(self.post_scrub_tab)),
            ("Clean", self.clean_tab, lambda: self._select_tab(self.clean_tab)),
            ("Exit", None, self._confirm_exit),
        )

        buttons: list[tk.Button] = []
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
                padx=2,
                pady=3,
                cursor="hand2",
            )
            button.grid(
                row=0,
                column=column,
                sticky="nsew",
                padx=(0 if column == 0 else 2, 0),
                pady=(self.EDGE_GAP, self.EDGE_GAP),
            )
            buttons.append(button)
        return buttons

    def _refresh_navigation_rails(self) -> None:
        if not hasattr(self, "flush_tab"):
            return super()._refresh_navigation_rails()

        active_index = {
            self.flush_tab: 0,
            self.benchmark_tab: 1,
            self.test_tab: 2,
            self.post_scrub_tab: 3,
            self.clean_tab: 4,
        }.get(self._active_tab)

        for pfd in self.pfds.values():
            for index, button in enumerate(pfd.get("navigation_buttons", [])):
                selected = index == active_index and index < 5
                try:
                    button.configure(
                        relief="sunken" if selected else "raised",
                        bg="#cfcfcf" if selected else "#e8e8e8",
                        font=self.NAV_FONT_ACTIVE if selected else self.NAV_FONT,
                    )
                    if index == 5:
                        self._style_navigation_button(button, selected=False)
                except tk.TclError:
                    pass


__all__ = ["HMI"]
