"""Final touchscreen layout for the MEU HMI."""

from __future__ import annotations

import tkinter as tk

from .hmi_runtime import HMI as _RuntimeHMI


class HMI(_RuntimeHMI):
    """MEU HMI with a vertical membrane PFD and bottom-anchored panels."""

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.after_idle(self._anchor_bottom_panels)

    def _create_pfd(self, parent: tk.Widget) -> dict:
        """Create a vertical-membrane PFD with clear orthogonal routing."""
        canvas = tk.Canvas(parent, width=780, height=225, bg="white")
        canvas.pack(side="top", anchor="n", pady=(2, 0))

        btn_opts = {"width": 2, "height": 1}
        btn_frame = tk.Frame(canvas, bg="white")
        help_btn = tk.Button(btn_frame, text="?", command=self._show_control_narrative, **btn_opts)
        close_btn = tk.Button(btn_frame, text="X", command=self._confirm_exit, **btn_opts)
        help_btn.pack(side="left", padx=(0, 2), ipadx=4, ipady=4)
        close_btn.pack(side="left", ipadx=4, ipady=4)
        canvas.create_window(770, 10, window=btn_frame, anchor="ne")

        # Inlet tanks.
        canvas.create_rectangle(25, 85, 105, 135, fill="lightblue")
        canvas.create_text(65, 75, text="Feed Tank")
        pi2_text = canvas.create_text(65, 125, text="-- PSI")

        canvas.create_rectangle(25, 160, 105, 210, fill="lightblue")
        canvas.create_text(65, 150, text="BW Tank")
        pi1_text = canvas.create_text(65, 200, text="-- PSI")

        # Vertical membrane, rotated 90 degrees counterclockwise.
        membrane_left = 360
        membrane_right = 380
        membrane_top = 35
        membrane_bottom = 185
        membrane_center_x = (membrane_left + membrane_right) / 2
        membrane_center_y = (membrane_top + membrane_bottom) / 2

        canvas.create_rectangle(
            membrane_left, membrane_top, membrane_right, membrane_bottom, fill="lightgray"
        )

        # V2 side port near the bottom, V3/V4 side port near the top.
        v2_port_y = 150
        outlet_port_y = 75
        canvas.create_rectangle(340, v2_port_y - 7.5, membrane_left, v2_port_y + 7.5, fill="lightgray")
        canvas.create_rectangle(membrane_right, outlet_port_y - 7.5, 400, outlet_port_y + 7.5, fill="lightgray")
        canvas.create_text(membrane_center_x, 22, text="Membrane")

        # Outlet vessels.
        canvas.create_rectangle(600, 20, 650, 70, fill="lightblue")
        canvas.create_text(625, 10, text="Filtrate")
        effluent_weight_text = canvas.create_text(625, 60, text="-- g")

        canvas.create_rectangle(600, 155, 650, 205, fill="lightblue")
        canvas.create_text(625, 145, text="BW Effluent")
        backwash_weight_text = canvas.create_text(625, 195, text="-- g")

        canvas.create_rectangle(690, 75, 740, 125, fill="lightblue")
        canvas.create_text(715, 65, text="Waste")

        lines = {}
        valve_labels = {}
        valve_to_lines = {
            0: [0, "v1_bottom"],
            1: [1],
            2: [2, "outlet_header", "v3_drop"],
            3: [3, "outlet_header"],
            4: [4, "v5_rise"],
        }

        # V1 enters the bottom end of the membrane.
        lines[0] = canvas.create_line(105, 185, 300, 185, fill="gray", width=2)
        lines["v1_bottom"] = canvas.create_line(
            300, 185, 300, 210, membrane_center_x, 210, membrane_center_x, membrane_bottom,
            arrow="last", fill="gray", width=2,
        )
        valve_labels["V1"] = canvas.create_text(185, 185, text="V1")

        # V2 enters the left side near the bottom.
        lines[1] = canvas.create_line(105, 110, 340, 110, 340, v2_port_y, membrane_left, v2_port_y,
                                      arrow="last", fill="gray", width=2)
        valve_labels["V2"] = canvas.create_text(185, 110, text="V2")
        canvas.create_rectangle(235, 102.5, 290, 117.5, fill="white", outline="black")
        te_text = canvas.create_text(262.5, 110, text="-- C")

        # V5 exits from the top end of the membrane.
        lines["v5_rise"] = canvas.create_line(
            membrane_center_x, membrane_top, membrane_center_x, 20, fill="gray", width=2
        )
        lines[4] = canvas.create_line(
            membrane_center_x, 20, 600, 20, 600, 45, arrow="last", fill="gray", width=2
        )
        valve_labels["V5"] = canvas.create_text(500, 20, text="V5")

        # V3 and V4 share the right-side outlet near the top.
        lines["outlet_header"] = canvas.create_line(400, outlet_port_y, 455, outlet_port_y, fill="gray", width=2)
        lines[3] = canvas.create_line(455, outlet_port_y, 690, outlet_port_y, 690, 100,
                                      arrow="last", fill="gray", width=2)
        valve_labels["V4"] = canvas.create_text(520, outlet_port_y, text="V4")

        lines["v3_drop"] = canvas.create_line(455, outlet_port_y, 455, 180, fill="gray", width=2)
        lines[2] = canvas.create_line(455, 180, 600, 180, arrow="last", fill="gray", width=2)
        valve_labels["V3"] = canvas.create_text(520, 180, text="V3")

        solenoid_buttons = []
        valve_keys = ["V1", "V2", "V3", "V4", "V5"]
        for i in range(5):
            btn = tk.Button(
                canvas,
                text=f"V{i + 1}",
                width=3,
                bg="lightgray",
                command=lambda ch=i: self.toggle_solenoid(ch),
            )
            x, y = canvas.coords(valve_labels[valve_keys[i]])
            canvas.create_window(x, y, window=btn)
            solenoid_buttons.append(btn)

        prime_btn = tk.Button(canvas, text="Prime", command=self.prime)
        canvas.create_window(290, 150, window=prime_btn)

        return {
            "canvas": canvas,
            "pi1_text": pi1_text,
            "pi2_text": pi2_text,
            "te_text": te_text,
            "effluent_weight_text": effluent_weight_text,
            "backwash_weight_text": backwash_weight_text,
            "lines": lines,
            "valve_labels": valve_labels,
            "valve_to_lines": valve_to_lines,
            "solenoid_buttons": solenoid_buttons,
            "prime_btn": prime_btn,
        }

    def _anchor_bottom_panels(self) -> None:
        """Anchor PFDs at the top and information panels at the screen bottom."""
        outer_margin = 8
        panel_gap = 8

        for tab in (self.test_tab, self.benchmark_tab, self.clean_tab):
            settings = None
            sensors = None
            cycle_status = None

            for widget in self._walk_widgets(tab):
                if not isinstance(widget, tk.LabelFrame):
                    continue
                try:
                    title = widget.cget("text")
                except Exception:
                    continue
                if title == "Settings":
                    settings = widget
                elif title == "Sensors":
                    sensors = widget
                elif title == "Cycle Status":
                    cycle_status = widget

            if settings is not None:
                left_column = settings.master
                try:
                    left_column.pack_configure(
                        side="left", fill="y", anchor="s", padx=(0, outer_margin), pady=0
                    )
                    settings.pack_forget()
                    settings.pack(side="bottom", anchor="sw")
                except Exception:
                    pass

            if sensors is not None and cycle_status is not None:
                right_column = sensors.master
                try:
                    right_column.pack_configure(
                        side="right", fill="y", anchor="s", padx=(outer_margin, 0), pady=0
                    )
                    sensors.pack_forget()
                    cycle_status.pack_forget()
                    cycle_status.pack(side="bottom", anchor="se")
                    sensors.pack(side="bottom", anchor="se", pady=(0, panel_gap))
                except Exception:
                    pass

            # The common lower area expands between the top PFD and bottom panels.
            for child in tab.winfo_children():
                if isinstance(child, tk.Frame):
                    try:
                        info = child.pack_info()
                    except Exception:
                        continue
                    if info:
                        try:
                            child.pack_configure(
                                fill="both", expand=True, padx=outer_margin, pady=outer_margin
                            )
                        except Exception:
                            pass

        self.update_idletasks()


__all__ = ["HMI"]
