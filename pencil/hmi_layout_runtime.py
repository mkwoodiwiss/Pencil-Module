"""Final touchscreen layout for the MEU HMI."""

from __future__ import annotations

import tkinter as tk

from .hmi_runtime import HMI as _RuntimeHMI


class HMI(_RuntimeHMI):
    """MEU HMI with a vertical membrane PFD and bottom-anchored panels."""

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._test_summary_left = tk.StringVar()
        self._test_summary_right = tk.StringVar()
        self._benchmark_summary_left = tk.StringVar()
        self._benchmark_summary_right = tk.StringVar()
        self.after_idle(self._finish_layout)

    def _finish_layout(self) -> None:
        self._install_two_column_summary(
            self.test_tab, self._test_summary_left, self._test_summary_right
        )
        self._install_two_column_summary(
            self.benchmark_tab,
            self._benchmark_summary_left,
            self._benchmark_summary_right,
        )
        self._update_test_summary()
        self._update_benchmark_summary()
        self._anchor_bottom_panels()

    def _install_two_column_summary(
        self, tab: tk.Widget, left_var: tk.StringVar, right_var: tk.StringVar
    ) -> None:
        """Replace the tall single-column summary with a compact two-column block."""
        settings = None
        for widget in self._walk_widgets(tab):
            if isinstance(widget, tk.LabelFrame):
                try:
                    if widget.cget("text") == "Settings":
                        settings = widget
                        break
                except Exception:
                    pass
        if settings is None:
            return

        summary_frame = None
        for child in settings.winfo_children():
            if isinstance(child, tk.Frame):
                summary_frame = child
                break
        if summary_frame is None:
            return

        for child in summary_frame.winfo_children():
            child.destroy()
        summary_frame.columnconfigure((0, 1), weight=1)
        tk.Label(
            summary_frame,
            textvariable=left_var,
            justify="left",
            anchor="nw",
            font=("TkDefaultFont", 10),
        ).grid(row=0, column=0, sticky="nw")
        tk.Label(
            summary_frame,
            textvariable=right_var,
            justify="left",
            anchor="nw",
            font=("TkDefaultFont", 10),
        ).grid(row=0, column=1, sticky="nw", padx=(18, 0))

    def _update_test_summary(self) -> None:
        super()._update_test_summary()
        if not hasattr(self, "_test_summary_left"):
            return
        lines = self.test_summary_var.get().splitlines()
        self._test_summary_left.set("\n".join(lines[:5]))
        self._test_summary_right.set("\n".join(lines[5:8]))

    def _update_benchmark_summary(self) -> None:
        super()._update_benchmark_summary()
        if not hasattr(self, "_benchmark_summary_left"):
            return
        lines = self.benchmark_summary_var.get().splitlines()
        self._benchmark_summary_left.set("\n".join(lines[:5]))
        self._benchmark_summary_right.set("\n".join(lines[5:8]))

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

        canvas.create_rectangle(25, 85, 105, 135, fill="lightblue")
        canvas.create_text(65, 75, text="Feed Tank")
        pi2_text = canvas.create_text(65, 125, text="-- PSI")

        canvas.create_rectangle(25, 160, 105, 210, fill="lightblue")
        canvas.create_text(65, 150, text="BW Tank")
        pi1_text = canvas.create_text(65, 200, text="-- PSI")

        membrane_left = 360
        membrane_right = 380
        membrane_top = 38
        membrane_bottom = 185
        membrane_center_x = (membrane_left + membrane_right) / 2

        canvas.create_rectangle(
            membrane_left, membrane_top, membrane_right, membrane_bottom, fill="lightgray"
        )

        v2_port_y = 150
        outlet_port_y = 75
        canvas.create_rectangle(340, v2_port_y - 7.5, membrane_left, v2_port_y + 7.5, fill="lightgray")
        canvas.create_rectangle(membrane_right, outlet_port_y - 7.5, 400, outlet_port_y + 7.5, fill="lightgray")
        canvas.create_text(membrane_center_x, 12, text="Membrane")

        canvas.create_rectangle(600, 20, 650, 70, fill="lightblue")
        canvas.create_text(625, 10, text="Filtrate")
        effluent_weight_text = canvas.create_text(625, 60, text="-- g")

        canvas.create_rectangle(600, 155, 650, 205, fill="lightblue")
        canvas.create_text(625, 145, text="BW Effluent")
        backwash_weight_text = canvas.create_text(625, 195, text="-- g")

        canvas.create_rectangle(690, 90, 740, 140, fill="lightblue")
        canvas.create_text(715, 80, text="Waste")

        lines = {}
        valve_labels = {}
        valve_to_lines = {
            0: [0, "v1_bottom"],
            1: [1, "v2_drop", "v2_approach"],
            2: [2, "outlet_header", "v3_drop"],
            3: [3, "outlet_header"],
            4: [4, "v5_rise", "v5_header", "v5_drop"],
        }

        lines[0] = canvas.create_line(105, 185, 300, 185, fill="gray", width=2)
        lines["v1_bottom"] = canvas.create_line(
            300, 185, 300, 210, membrane_center_x, 210, membrane_center_x, membrane_bottom,
            arrow="last", fill="gray", width=2,
        )
        valve_labels["V1"] = canvas.create_text(185, 185, text="V1")

        # V2 approaches the side port horizontally and terminates outside the port.
        lines[1] = canvas.create_line(105, 110, 320, 110, fill="gray", width=2)
        lines["v2_drop"] = canvas.create_line(320, 110, 320, v2_port_y, fill="gray", width=2)
        lines["v2_approach"] = canvas.create_line(
            320, v2_port_y, 340, v2_port_y, arrow="last", fill="gray", width=2
        )
        valve_labels["V2"] = canvas.create_text(185, 110, text="V2")
        canvas.create_rectangle(235, 102.5, 290, 117.5, fill="white", outline="black")
        te_text = canvas.create_text(262.5, 110, text="-- C")

        # V5 rises clear of the membrane label, crosses above it, then drops into Filtrate.
        v5_header_y = 28
        lines["v5_rise"] = canvas.create_line(
            membrane_center_x, membrane_top, membrane_center_x, v5_header_y, fill="gray", width=2
        )
        lines["v5_header"] = canvas.create_line(
            membrane_center_x, v5_header_y, 585, v5_header_y, fill="gray", width=2
        )
        lines["v5_drop"] = canvas.create_line(585, v5_header_y, 585, 45, fill="gray", width=2)
        lines[4] = canvas.create_line(585, 45, 600, 45, arrow="last", fill="gray", width=2)
        valve_labels["V5"] = canvas.create_text(500, v5_header_y, text="V5")

        lines["outlet_header"] = canvas.create_line(
            400, outlet_port_y, 455, outlet_port_y, fill="gray", width=2
        )

        # V4 runs on its own lower horizontal route and points right into Waste.
        v4_y = 115
        lines[3] = canvas.create_line(
            455, outlet_port_y, 455, v4_y, 690, v4_y,
            arrow="last", fill="gray", width=2
        )
        valve_labels["V4"] = canvas.create_text(520, v4_y, text="V4")

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

        # Prime uses open white space above-left of the membrane without covering piping.
        prime_btn = tk.Button(canvas, text="Prime", command=self.prime)
        canvas.create_window(300, 55, window=prime_btn)

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

    def _update_lines(self) -> None:
        """Color the custom PFD without relying on legacy line-key names."""
        for pfd in self.pfds.values():
            canvas = pfd["canvas"]
            lines = pfd["lines"]
            for line_key, line_id in lines.items():
                active = False
                for valve_index, line_keys in pfd["valve_to_lines"].items():
                    if line_key in line_keys and self.solenoid_states[valve_index]:
                        active = True
                        break
                canvas.itemconfig(line_id, fill="green" if active else "gray")

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