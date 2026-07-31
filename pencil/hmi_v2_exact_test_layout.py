"""Build Flush and Post-Scrub lower panels from the same geometry as Test."""

from __future__ import annotations

import tkinter as tk

from .hmi_v2_layout_fix import HMI as _V2LayoutHMI


class HMI(_V2LayoutHMI):
    """MEU v2 HMI with Test-identical lower-panel construction."""

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._rebuild_v2_lower_panel(self.flush_tab, "flush")
        self._rebuild_v2_lower_panel(self.post_scrub_tab, "post_scrub")
        self.after_idle(self._normalize_v2_lower_panels)
        self.after(100, self._normalize_v2_lower_panels)

    def _destroy_existing_lower_panel(self, tab: tk.Widget, key: str) -> None:
        top_section = self.pfds.get(key, {}).get("top_section")
        for child in list(tab.winfo_children()):
            if child is top_section:
                continue
            try:
                child.destroy()
            except tk.TclError:
                pass

    def _rebuild_v2_lower_panel(self, tab: tk.Widget, key: str) -> None:
        self._destroy_existing_lower_panel(tab, key)

        area = tk.Frame(tab)
        area.pack(fill="both", expand=True, padx=5, pady=(0, 5))

        left = tk.Frame(area, width=self.LEFT_COLUMN_WIDTH)
        left.pack(side="left", padx=5, pady=5, anchor="n", fill="y")
        left.pack_propagate(False)

        middle = tk.Frame(area)
        middle.pack(side="left", padx=5, pady=5, anchor="n", expand=True, fill="both")

        right = tk.Frame(area, width=self.RIGHT_COLUMN_WIDTH)
        right.pack(side="right", fill="y", padx=5, pady=5)
        right.pack_propagate(False)

        settings = tk.LabelFrame(left, text="Settings", width=self.LEFT_COLUMN_WIDTH)
        settings.pack(fill="x", anchor="sw")
        settings.grid_columnconfigure((0, 1), weight=1, uniform="v2_settings")

        summary_var = self.flush_summary_var if key == "flush" else self.post_scrub_summary_var
        summary = tk.Label(
            settings,
            textvariable=summary_var,
            justify="left",
            anchor="nw",
            width=self.SUMMARY_COLUMN_WIDTH,
            font=("TkDefaultFont", 10),
        )
        summary.grid(row=0, column=0, columnspan=2, sticky="nw", padx=4, pady=(0, 2))

        controls = tk.Frame(settings)
        controls.grid(row=1, column=0, columnspan=2, padx=4, pady=(2, 4), sticky="ew")
        controls.grid_columnconfigure((0, 1), weight=1, uniform="v2_controls")

        edit_command = self._edit_flush_settings if key == "flush" else self._edit_post_scrub_settings
        edit = tk.Button(controls, text="Edit Settings", command=edit_command, width=11, padx=3)
        calibrate = tk.Button(controls, text="Calibrate", command=self.calibrate, width=11, padx=3)
        tare_fil = tk.Button(controls, text="Tare FIL", width=11, padx=3)
        tare_bw = tk.Button(controls, text="Tare BW EFL", width=11, padx=3)
        tare_fil.configure(command=lambda button=tare_fil: self._start_manual_tare(0, button))
        tare_bw.configure(command=lambda button=tare_bw: self._start_manual_tare(1, button))

        edit.grid(row=0, column=0, padx=4, pady=3, sticky="ew")
        calibrate.grid(row=0, column=1, padx=4, pady=3, sticky="ew")
        tare_fil.grid(row=1, column=0, padx=4, pady=3, sticky="ew")
        tare_bw.grid(row=1, column=1, padx=4, pady=3, sticky="ew")

        start_command = self._toggle_flush if key == "flush" else self._toggle_post_scrub
        start = tk.Button(
            middle,
            text="Start",
            command=start_command,
            font=self.START_FONT,
            width=9,
            height=1,
            padx=8,
            pady=5,
        )
        start.pack(pady=(0, 10))
        tk.Label(middle, image=self.logo_image, borderwidth=0).pack()

        sensors = tk.LabelFrame(right, text="Sensors", width=self.RIGHT_COLUMN_WIDTH)
        sensors.pack(fill="x", padx=5, pady=5, anchor="se")
        sensor_rows = (
            ("Filtrate Weight:", self.weight_var, "g"),
            ("BW Effluent Weight:", self.backwash_weight_var, "g"),
            ("Backwash Tank Pressure:", self.pressure_bw_var, "kPa"),
            ("Feed Tank Pressure:", self.pressure_raw_var, "kPa"),
            ("Feed Temp:", self.temp_var, "C"),
        )
        for row, (label, variable, unit) in enumerate(sensor_rows):
            tk.Label(sensors, text=label).grid(row=row, column=0, sticky="w")
            tk.Label(sensors, textvariable=variable, font=self.PANEL_VALUE_FONT).grid(
                row=row, column=1, sticky="w"
            )
            tk.Label(sensors, text=unit).grid(row=row, column=2, sticky="w")

        cycle = tk.LabelFrame(right, text="Cycle Status", width=self.RIGHT_COLUMN_WIDTH)
        cycle.pack(fill="x", anchor="se", pady=5)
        tk.Label(cycle, text="Cycle Step:").grid(row=0, column=0, sticky="w")
        tk.Label(
            cycle,
            textvariable=self.cycle_step_var,
            font=self.PANEL_VALUE_FONT,
            width=15,
            anchor="w",
        ).grid(row=0, column=1, sticky="w")
        tk.Label(cycle, text="Cycle Count:").grid(row=1, column=0, sticky="w")
        tk.Label(cycle, textvariable=self.cycle_progress_var, font=self.PANEL_VALUE_FONT).grid(
            row=1, column=1, sticky="w"
        )
        tk.Label(cycle, text="Time:").grid(row=2, column=0, sticky="w")
        tk.Label(cycle, textvariable=self.cycle_time_var, font=self.PANEL_VALUE_FONT).grid(
            row=2, column=1, sticky="w"
        )

        if key == "flush":
            self.start_btn_flush = start
        else:
            self.start_btn_post_scrub = start

    def _copy_test_frame_geometry(self, target_tab: tk.Widget) -> None:
        test_settings = self._find_settings_frame(self.test_tab)
        target_settings = self._find_settings_frame(target_tab)
        test_sensors = self._find_panel(self.test_tab, "Sensors")
        target_sensors = self._find_panel(target_tab, "Sensors")
        test_cycle = self._find_panel(self.test_tab, "Cycle Status")
        target_cycle = self._find_panel(target_tab, "Cycle Status")
        if None in (test_settings, target_settings, test_sensors, target_sensors, test_cycle, target_cycle):
            return

        self.update_idletasks()
        for source, target in (
            (test_settings, target_settings),
            (test_sensors, target_sensors),
            (test_cycle, target_cycle),
        ):
            target.configure(width=source.winfo_width(), height=source.winfo_height())
            target.pack_propagate(False)
            target.grid_propagate(False)

        target_settings.master.configure(width=test_settings.master.winfo_width())
        target_settings.master.pack_propagate(False)
        target_sensors.master.configure(width=test_sensors.master.winfo_width())
        target_sensors.master.pack_propagate(False)

        source_buttons = self._buttons_by_text(test_settings)
        target_buttons = self._buttons_by_text(target_settings)
        for text in ("Edit Settings", "Calibrate", "Tare FIL", "Tare BW EFL"):
            source = source_buttons.get(text)
            target = target_buttons.get(text)
            if source is None or target is None:
                continue
            target.configure(
                font=source.cget("font"),
                width=source.cget("width"),
                height=source.cget("height"),
                padx=source.cget("padx"),
                pady=source.cget("pady"),
                borderwidth=source.cget("borderwidth"),
                relief=source.cget("relief"),
            )
            source_grid = source.grid_info()
            target.grid_configure(
                row=source_grid.get("row", 0),
                column=source_grid.get("column", 0),
                padx=source_grid.get("padx", 0),
                pady=source_grid.get("pady", 0),
                ipadx=source_grid.get("ipadx", 0),
                ipady=source_grid.get("ipady", 0),
                sticky=source_grid.get("sticky", "ew"),
            )

    def _normalize_v2_lower_panels(self) -> None:
        try:
            self._normalize_bottom_columns()
            self._copy_test_frame_geometry(self.flush_tab)
            self._copy_test_frame_geometry(self.post_scrub_tab)
            self.update_idletasks()
        except tk.TclError:
            pass


__all__ = ["HMI"]
