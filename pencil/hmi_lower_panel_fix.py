"""Lower-panel geometry corrections for the MEU touchscreen HMI."""

from __future__ import annotations

import tkinter as tk

from .hmi_top_navigation import HMI as _TopNavigationHMI


class HMI(_TopNavigationHMI):
    """MEU HMI with corrected lower panels and centered Prime control."""

    SENSOR_FRAME_EXTRA_HEIGHT = 16
    MEMBRANE_CENTER_X = 370
    MEMBRANE_CENTER_Y = 111.5

    def _finish_navigation_layout(self) -> None:
        """Finish the base layout, then verify lower-panel geometry after Tk settles."""
        super()._finish_navigation_layout()
        self.after_idle(self._arrange_lower_panels)
        self.after(75, self._arrange_lower_panels)

    def _create_pfd(self, parent: tk.Widget) -> dict:
        """Create the PFD and center the Prime button over the membrane body."""
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
                    canvas.coords(
                        item,
                        self.MEMBRANE_CENTER_X,
                        self.MEMBRANE_CENTER_Y,
                    )
                    canvas.tag_raise(item)
                    break
                except Exception:
                    continue

        return pfd

    def _arrange_lower_panels(self) -> None:
        """Center Settings between the PFD bottom and screen bottom.

        The previous implementation centered Settings inside the left column. That
        column does not necessarily occupy the exact visible region below the PFD,
        so equal relative placement could still produce unequal screen-space gaps.
        This implementation calculates the desired center from rendered root
        coordinates and then converts that position back into the left column.
        """
        self.update_idletasks()

        tab_data = (
            (self.test_tab, self.pfds.get("test", {})),
            (self.benchmark_tab, self.pfds.get("benchmark", {})),
            (self.clean_tab, self.pfds.get("clean", {})),
        )

        screen_bottom = self.winfo_rooty() + self.winfo_height()

        for tab, pfd in tab_data:
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

            if settings is not None:
                try:
                    left_column = settings.master
                    left_column.pack_configure(
                        fill="y",
                        expand=False,
                        pady=0,
                        anchor="n",
                    )
                    self.update_idletasks()

                    width = settings.winfo_reqwidth()
                    left_column.configure(width=width)
                    left_column.pack_propagate(False)
                    self.update_idletasks()

                    top_section = pfd.get("top_section")
                    if top_section is not None:
                        pfd_bottom = (
                            top_section.winfo_rooty() + top_section.winfo_height()
                        )
                    else:
                        pfd_bottom = left_column.winfo_rooty()

                    target_center_root = (pfd_bottom + screen_bottom) / 2.0
                    target_center_local = (
                        target_center_root - left_column.winfo_rooty()
                    )

                    settings.pack_forget()
                    settings.place(
                        x=width / 2.0,
                        y=target_center_local,
                        anchor="center",
                    )
                except Exception:
                    pass

            if sensors is not None:
                try:
                    right_column = sensors.master
                    right_column.pack_configure(
                        fill="y",
                        pady=0,
                        anchor="n",
                    )

                    natural_height = getattr(
                        sensors,
                        "_meu_natural_height",
                        None,
                    )
                    if natural_height is None:
                        natural_height = sensors.winfo_reqheight()
                        sensors._meu_natural_height = natural_height

                    sensors.configure(
                        height=natural_height + self.SENSOR_FRAME_EXTRA_HEIGHT
                    )
                    sensors.pack_propagate(False)
                    sensors.pack_configure(
                        padx=5,
                        pady=(0, 0),
                        anchor="n",
                    )
                except Exception:
                    pass

            if cycle_status is not None:
                try:
                    cycle_status.pack_configure(pady=(1, 0), anchor="n")
                except Exception:
                    pass


__all__ = ["HMI"]
