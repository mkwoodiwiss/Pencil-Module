"""Final layout corrections for the MEU touchscreen HMI."""

from __future__ import annotations

import tkinter as tk

from .hmi_navigation_layout import HMI as _NavigationHMI


class HMI(_NavigationHMI):
    """MEU HMI with corrected V5 piping and readable navigation labels."""

    BENCHMARK_NAV_FONT = ("Arial", 7)
    BENCHMARK_NAV_FONT_ACTIVE = ("Arial", 7, "bold")

    def _finish_navigation_layout(self) -> None:
        """Finalize the normal panel layout and then refine the navigation label."""
        super()._finish_navigation_layout()
        self._apply_benchmark_nav_font()
        self.update_idletasks()

    def _apply_benchmark_nav_font(self) -> None:
        """Reduce only the Benchmark side-button font so its text fits."""
        active = self._active_tab is self.benchmark_tab
        font = self.BENCHMARK_NAV_FONT_ACTIVE if active else self.BENCHMARK_NAV_FONT
        for pfd in self.pfds.values():
            buttons = pfd.get("navigation_buttons", [])
            if len(buttons) > 1:
                try:
                    buttons[1].configure(font=font)
                except Exception:
                    pass

    def _refresh_navigation_rails(self) -> None:
        """Refresh selected states without enlarging the Benchmark label again."""
        super()._refresh_navigation_rails()
        self._apply_benchmark_nav_font()

    @staticmethod
    def _resize_pfd_vessels_and_routes(canvas: tk.Canvas) -> None:
        """Resize vessels and rebuild V5 as one connected orthogonal route."""
        _NavigationHMI._resize_pfd_vessels_and_routes(canvas)

        for item in canvas.find_all():
            try:
                if canvas.type(item) != "line":
                    continue
                coords = canvas.coords(item)
            except Exception:
                continue

            # V5 remains one continuous path after the Filtrate vessel moves left:
            # membrane top -> rise -> header -> drop -> arrow into vessel edge.
            if coords == [370.0, 38.0, 370.0, 28.0]:
                canvas.coords(item, 370, 38, 370, 28)
            elif coords == [370.0, 28.0, 585.0, 28.0]:
                canvas.coords(item, 370, 28, 555, 28)
            elif coords == [585.0, 28.0, 585.0, 45.0]:
                canvas.coords(item, 555, 28, 555, 45)
            elif coords == [555.0, 45.0, 570.0, 45.0]:
                canvas.coords(item, 555, 45, 570, 45)


__all__ = ["HMI"]
