"""Navigation corrections for the five-page MEU v2 HMI."""

from __future__ import annotations

import tkinter as tk

from .hmi_v2 import HMI as _V2HMI


class HMI(_V2HMI):
    """Ensure all five v2 pages participate in the tabless page stack."""

    def _process_pages(self) -> tuple[tk.Widget, ...]:
        if not hasattr(self, "flush_tab"):
            return (self.test_tab, self.benchmark_tab, self.clean_tab)
        return (
            self.flush_tab,
            self.benchmark_tab,
            self.test_tab,
            self.post_scrub_tab,
            self.clean_tab,
        )

    def _remove_native_tabs(self) -> None:
        try:
            self.notebook.pack_configure(pady=(self.TOP_MARGIN, 0))
        except Exception:
            pass
        for tab in self._process_pages():
            try:
                if str(tab) in self.notebook.tabs():
                    self.notebook.forget(tab)
            except Exception:
                pass

    def _show_page(self, tab: tk.Widget) -> None:
        for page in self._process_pages():
            try:
                page.place_forget()
            except Exception:
                pass
        tab.place(in_=self.notebook, x=0, y=0, relwidth=1.0, relheight=1.0)
        tab.lift()
        self._active_tab = tab


__all__ = ["HMI"]
