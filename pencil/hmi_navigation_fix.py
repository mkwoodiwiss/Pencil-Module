"""Final layout corrections for the MEU touchscreen HMI."""

from __future__ import annotations

import tkinter as tk

from .hmi_navigation_layout import HMI as _NavigationHMI


class HMI(_NavigationHMI):
    """MEU HMI with corrected benchmark text and V5 piping."""

    BENCHMARK_FONT = ("Arial", 8)
    BENCHMARK_VALUE_FONT = ("Arial", 9)

    def _finish_navigation_layout(self) -> None:
        """Finalize the layout, then make the benchmark page fit cleanly."""
        super()._finish_navigation_layout()
        self._apply_benchmark_fonts()
        self.update_idletasks()

    def _apply_benchmark_fonts(self) -> None:
        """Reduce only the benchmark lower-panel text enough to prevent clipping."""
        pfd_root = self.pfds.get("benchmark", {}).get("top_section")

        value_vars = {
            str(self.weight_var),
            str(self.backwash_weight_var),
            str(self.pressure_bw_var),
            str(self.pressure_raw_var),
            str(self.temp_var),
            str(self.cycle_step_var),
            str(self.cycle_progress_var),
            str(self.cycle_time_var),
        }

        for widget in self._walk_widgets(self.benchmark_tab):
            if pfd_root is not None and self._is_descendant(widget, pfd_root):
                continue
            try:
                if isinstance(widget, tk.LabelFrame):
                    widget.configure(font=self.BENCHMARK_FONT)
                elif isinstance(widget, tk.Label):
                    if str(widget.cget("textvariable")) in value_vars:
                        widget.configure(font=self.BENCHMARK_VALUE_FONT)
                    else:
                        widget.configure(font=self.BENCHMARK_FONT)
                elif isinstance(widget, tk.Button):
                    widget.configure(font=self.BENCHMARK_FONT)
            except Exception:
                pass

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

            # V5 must remain fully connected after the Filtrate vessel moves left:
            # membrane top -> vertical rise -> horizontal header -> vertical drop
            # -> short horizontal arrow into the vessel's left edge.
            if coords == [370.0, 38.0, 370.0, 28.0]:
                canvas.coords(item, 370, 38, 370, 28)
            elif coords == [370.0, 28.0, 585.0, 28.0]:
                canvas.coords(item, 370, 28, 555, 28)
            elif coords == [585.0, 28.0, 585.0, 45.0]:
                canvas.coords(item, 555, 28, 555, 45)
            elif coords == [555.0, 45.0, 570.0, 45.0]:
                canvas.coords(item, 555, 45, 570, 45)


__all__ = ["HMI"]
