"""Lower-panel geometry corrections for the MEU touchscreen HMI."""

from __future__ import annotations

import tkinter as tk

from .hmi_top_navigation import HMI as _TopNavigationHMI


class HMI(_TopNavigationHMI):
    """MEU HMI with measured lower-panel placement and centered Prime control."""

    SENSOR_FRAME_EXTRA_HEIGHT = 24
    MEMBRANE_CENTER_X = 370
    MEMBRANE_CENTER_Y = 111.5

    def _finish_navigation_layout(self) -> None:
        super()._finish_navigation_layout()
        self.after_idle(self._arrange_lower_panels)
        self.after(75, self._arrange_lower_panels)
        self.after(200, self._arrange_lower_panels)

    def _create_pfd(self, parent: tk.Widget) -> dict:
        pfd = super()._create_pfd(parent)
        canvas = pfd.get("canvas")
        prime_btn = pfd.get("prime_btn")

        if canvas is not None and prime_btn is not None:
            prime_path = str(prime_btn)
            for item in canvas.find_all():
                try:
                    if canvas.type(item) != "window":
                        continue
                    if str(canvas.itemcget(item, "window")) != prime_path:
                        continue
                    canvas.coords(item, self.MEMBRANE_CENTER_X, self.MEMBRANE_CENTER_Y)
                    canvas.tag_raise(item)
                    break
                except Exception:
                    continue
        return pfd

    def _find_lower_frames(self, tab: tk.Widget):
        settings = None
        sensors = None
        cycle_status = None
        for widget in self._walk_widgets(tab):
            if not isinstance(widget, tk.LabelFrame):
                continue
            try:
                title = str(widget.cget("text"))
            except Exception:
                continue
            if title == "Settings":
                settings = widget
            elif title == "Sensors":
                sensors = widget
            elif title == "Cycle Status":
                cycle_status = widget
        return settings, sensors, cycle_status

    def _arrange_lower_panels(self) -> None:
        """Use rendered boundaries so Settings has equal visible gaps above and below."""
        self.update_idletasks()

        tab_data = (
            (self.test_tab, self.pfds.get("test", {})),
            (self.benchmark_tab, self.pfds.get("benchmark", {})),
            (self.clean_tab, self.pfds.get("clean", {})),
        )
        window_bottom = self.winfo_rooty() + self.winfo_height()

        for tab, pfd in tab_data:
            settings, sensors, cycle_status = self._find_lower_frames(tab)

            if settings is not None:
                try:
                    left_column = settings.master
                    lower_area = left_column.master
                    left_column.pack_configure(fill="y", expand=False, pady=0, anchor="n")
                    lower_area.pack_configure(pady=0)
                    self.update_idletasks()

                    settings_width = settings.winfo_reqwidth()
                    settings_height = settings.winfo_reqheight()
                    left_column.configure(width=settings_width)
                    left_column.pack_propagate(False)
                    self.update_idletasks()

                    top_section = pfd.get("top_section")
                    pfd_bottom = (
                        top_section.winfo_rooty() + top_section.winfo_height()
                        if top_section is not None
                        else lower_area.winfo_rooty()
                    )
                    area_top = lower_area.winfo_rooty()
                    area_bottom = area_top + lower_area.winfo_height()
                    visible_top = max(pfd_bottom, area_top)
                    visible_bottom = min(window_bottom, area_bottom)

                    available_height = max(0, visible_bottom - visible_top)
                    target_top_root = visible_top + max(
                        0,
                        (available_height - settings_height) / 2.0,
                    )
                    target_top_local = target_top_root - left_column.winfo_rooty()

                    settings.pack_forget()
                    settings.place(
                        x=settings_width / 2.0,
                        y=target_top_local,
                        anchor="n",
                    )
                    self.update_idletasks()

                    # Correct the actual rendered result, including LabelFrame borders,
                    # font metrics, and any remaining theme geometry.
                    actual_top_gap = settings.winfo_rooty() - visible_top
                    actual_bottom_gap = visible_bottom - (
                        settings.winfo_rooty() + settings.winfo_height()
                    )
                    correction = (actual_top_gap - actual_bottom_gap) / 2.0
                    if abs(correction) >= 0.5:
                        current_y = float(settings.place_info().get("y", target_top_local))
                        settings.place_configure(y=current_y - correction)
                except Exception:
                    pass

            if sensors is not None:
                try:
                    right_column = sensors.master
                    right_column.pack_configure(fill="y", pady=0, anchor="n")
                    natural_height = getattr(sensors, "_meu_natural_height", None)
                    if natural_height is None:
                        natural_height = sensors.winfo_reqheight()
                        sensors._meu_natural_height = natural_height

                    sensors.configure(height=natural_height + self.SENSOR_FRAME_EXTRA_HEIGHT)
                    sensors.pack_propagate(False)
                    sensors.pack_configure(padx=5, pady=(0, 0), anchor="n")
                except Exception:
                    pass

            if cycle_status is not None:
                try:
                    cycle_status.pack_configure(pady=(0, 0), anchor="n")
                except Exception:
                    pass


__all__ = ["HMI"]
