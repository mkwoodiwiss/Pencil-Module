"""Lower-panel geometry corrections for the MEU touchscreen HMI."""

from __future__ import annotations

import tkinter as tk

from .hmi_top_navigation import HMI as _TopNavigationHMI


class HMI(_TopNavigationHMI):
    """MEU HMI with measured lower-panel placement and centered Prime control."""

    SENSOR_FRAME_EXTRA_HEIGHT = 24
    LOWER_PANEL_TOP_GAP = 3
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
        """Align Settings and Sensors at the same rendered top position."""
        self.update_idletasks()

        tab_data = (
            (self.test_tab, self.pfds.get("test", {})),
            (self.benchmark_tab, self.pfds.get("benchmark", {})),
            (self.clean_tab, self.pfds.get("clean", {})),
        )

        for tab, _pfd in tab_data:
            settings, sensors, cycle_status = self._find_lower_frames(tab)

            # Establish the right-side stack first. Its rendered top becomes the
            # reference used to position Settings, so both frames start at exactly
            # the same screen height regardless of differing parent geometry.
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
                    sensors.pack_forget()
                    if cycle_status is not None:
                        cycle_status.pack_forget()

                    sensors.pack(
                        side="top",
                        padx=5,
                        pady=(self.LOWER_PANEL_TOP_GAP, 0),
                        anchor="n",
                    )
                    if cycle_status is not None:
                        cycle_status.pack(
                            side="top",
                            pady=(0, 0),
                            anchor="n",
                        )
                except Exception:
                    pass

            self.update_idletasks()

            if settings is not None:
                try:
                    left_column = settings.master
                    lower_area = left_column.master
                    left_column.pack_configure(fill="y", expand=False, pady=0, anchor="n")
                    lower_area.pack_configure(pady=0)
                    self.update_idletasks()

                    settings_width = settings.winfo_reqwidth()
                    left_column.configure(width=settings_width)
                    left_column.pack_propagate(False)
                    self.update_idletasks()

                    if sensors is not None:
                        target_top_root = sensors.winfo_rooty()
                    else:
                        target_top_root = lower_area.winfo_rooty() + self.LOWER_PANEL_TOP_GAP

                    target_top_local = target_top_root - left_column.winfo_rooty()
                    settings.pack_forget()
                    settings.place(
                        x=settings_width / 2.0,
                        y=target_top_local,
                        anchor="n",
                    )
                    self.update_idletasks()

                    # Correct any one-pixel theme rounding after placement.
                    if sensors is not None:
                        delta = settings.winfo_rooty() - sensors.winfo_rooty()
                        if delta:
                            current_y = float(settings.place_info().get("y", target_top_local))
                            settings.place_configure(y=current_y - delta)
                except Exception:
                    pass


__all__ = ["HMI"]
