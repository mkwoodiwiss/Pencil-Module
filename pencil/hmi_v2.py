"""Version 2 staging HMI with Flush and Post-Scrub operating modes."""

from __future__ import annotations

import threading
import tkinter as tk
from tkinter import messagebox

from .automation_cycle_logging import FiltrationTestSystem
from .config_meu import FiltrationConfig
from .hmi_modal_safety import HMI as _V1HMI


class _FlushTestSystem(FiltrationTestSystem):
    """Run the filtration sequence without creating data or settings files."""

    def _open_logs(self, prefix, project, module_id, final_id, config) -> None:
        self.current_cycle = 0
        self.data_file = None
        self.data_writer = None


class HMI(_V1HMI):
    """MEU v2 HMI with five process tabs in the required operating order."""

    PROCESS_TABS = ("flush", "benchmark", "test", "post_scrub", "clean")

    def __init__(self, *args, **kwargs) -> None:
        defaults = dict(kwargs.get("defaults") or {})
        super().__init__(*args, **kwargs)

        self.flush_tab = tk.Frame(self.notebook)
        self.post_scrub_tab = tk.Frame(self.notebook)

        self.flush_filt_target_weight_var = tk.DoubleVar(
            value=defaults.get("flush_filt_target_weight", 250.0)
        )
        self.flush_bw_target_weight_var = tk.DoubleVar(
            value=defaults.get("flush_bw_target_weight", 250.0)
        )
        self.flush_purge_time_var = tk.DoubleVar(
            value=defaults.get("flush_purge_time", 3.0)
        )
        self.flush_cycle_count_var = tk.IntVar(
            value=defaults.get("flush_cycle_count", 1)
        )
        self.flush_summary_var = tk.StringVar()

        self.post_scrub_filt_target_weight_var = tk.DoubleVar(
            value=defaults.get("post_scrub_filt_target_weight", self.filt_target_weight_var.get())
        )
        self.post_scrub_filt_target_time_var = tk.DoubleVar(
            value=defaults.get("post_scrub_filt_target_time", self.filt_target_time_var.get())
        )
        self.post_scrub_filt_use_weight_var = tk.BooleanVar(
            value=defaults.get("post_scrub_filt_use_weight", self.filt_use_weight_var.get())
        )
        self.post_scrub_bw_target_weight_var = tk.DoubleVar(
            value=defaults.get("post_scrub_bw_target_weight", self.bw_target_weight_var.get())
        )
        self.post_scrub_bw_target_time_var = tk.DoubleVar(
            value=defaults.get("post_scrub_bw_target_time", self.bw_target_time_var.get())
        )
        self.post_scrub_bw_use_weight_var = tk.BooleanVar(
            value=defaults.get("post_scrub_bw_use_weight", self.bw_use_weight_var.get())
        )
        self.post_scrub_purge_time_var = tk.DoubleVar(
            value=defaults.get("post_scrub_purge_time", self.refill_time_var.get())
        )
        self.post_scrub_cycle_count_var = tk.IntVar(
            value=defaults.get("post_scrub_cycle_count", self.cycle_count_var.get())
        )
        self.post_scrub_sample_time_var = tk.DoubleVar(
            value=defaults.get("post_scrub_sample_time", self.sample_time_var.get())
        )
        self.post_scrub_project_var = tk.StringVar(
            value=defaults.get("post_scrub_project", "")
        )
        self.post_scrub_module_id_var = tk.StringVar(
            value=defaults.get("post_scrub_module_id", "")
        )
        self.post_scrub_sample_id_var = tk.StringVar(
            value=defaults.get("post_scrub_sample_id", "")
        )
        self.post_scrub_summary_var = tk.StringVar()

        self.notebook.add(self.flush_tab, text="Flush")
        self.notebook.add(self.post_scrub_tab, text="Post-Scrub")
        self.notebook.insert(0, self.flush_tab)
        self.notebook.insert(1, self.benchmark_tab)
        self.notebook.insert(2, self.test_tab)
        self.notebook.insert(3, self.post_scrub_tab)
        self.notebook.insert(4, self.clean_tab)

        self._build_v2_tab(
            self.flush_tab,
            "flush",
            self.flush_summary_var,
            self._edit_flush_settings,
            self._toggle_flush,
        )
        self._build_v2_tab(
            self.post_scrub_tab,
            "post_scrub",
            self.post_scrub_summary_var,
            self._edit_post_scrub_settings,
            self._toggle_post_scrub,
        )

        self._update_flush_summary()
        self._update_post_scrub_summary()
        self._select_tab(self.flush_tab)
        self.after_idle(self._finish_v2_layout)

    def _finish_v2_layout(self) -> None:
        self._rebuild_navigation_rails()
        self._arrange_lower_panels()
        self._enlarge_start_buttons()
        self._refresh_navigation_rails()
        self._apply_selected_accents(self)

    def _build_v2_tab(
        self,
        tab: tk.Frame,
        key: str,
        summary_var: tk.StringVar,
        edit_command,
        start_command,
    ) -> None:
        self.pfds[key] = self._create_pfd(tab)
        area = tk.Frame(tab)
        area.pack(fill="both", expand=True, padx=5, pady=(0, 5))

        left = tk.Frame(area)
        left.pack(side="left", padx=5, pady=0, anchor="n", fill="y")
        settings = tk.LabelFrame(left, text="Settings")
        settings.pack(anchor="n")
        tk.Label(
            settings,
            textvariable=summary_var,
            justify="left",
            font=("TkDefaultFont", 10),
        ).grid(row=0, column=0, columnspan=5, sticky="w", pady=(0, 2))
        tk.Button(settings, text="Edit Settings", command=edit_command).grid(
            row=1, column=0, columnspan=5, pady=(2, 5)
        )
        controls = tk.Frame(settings)
        controls.grid(row=2, column=0, columnspan=5, pady=8, sticky="ew")
        controls.columnconfigure((0, 1, 2), weight=1)
        tk.Button(controls, text="Calibrate", command=self.calibrate).grid(
            row=0, column=0, padx=5, sticky="ew"
        )
        tk.Button(controls, text="Tare FIL", command=lambda: self.module.zero_scale(0)).grid(
            row=0, column=1, padx=5, sticky="ew"
        )
        tk.Button(controls, text="Tare BW EFL", command=lambda: self.module.zero_scale(1)).grid(
            row=0, column=2, padx=5, sticky="ew"
        )

        middle = tk.Frame(area)
        middle.pack(side="left", padx=5, pady=0, anchor="n", expand=True, fill="both")
        start_button = tk.Button(
            middle, text="Start", command=start_command, font=("Arial", 12), width=7, height=1
        )
        start_button.pack(pady=(0, 10))
        tk.Label(middle, image=self.logo_image, borderwidth=0).pack()

        right = tk.Frame(area)
        right.pack(side="right", fill="y", padx=5, pady=0)
        sensors = tk.LabelFrame(right, text="Sensors")
        sensors.pack(padx=5, pady=0, anchor="n")
        rows = (
            ("Filtrate Weight:", self.weight_var, "g"),
            ("BW Effluent Weight:", self.backwash_weight_var, "g"),
            ("Backwash Tank Pressure:", self.pressure_bw_var, "PSI"),
            ("Feed Tank Pressure:", self.pressure_raw_var, "PSI"),
            ("Feed Temperature:", self.temp_var, "C"),
        )
        for row, (label, variable, unit) in enumerate(rows):
            tk.Label(sensors, text=label).grid(row=row, column=0, sticky="w")
            tk.Label(sensors, textvariable=variable, font=("Arial", 12)).grid(
                row=row, column=1, sticky="w"
            )
            tk.Label(sensors, text=unit).grid(row=row, column=2, sticky="w")

        cycle = tk.LabelFrame(right, text="Cycle Status")
        cycle.pack(anchor="n", pady=(2, 0))
        tk.Label(cycle, text="Cycle Step:").grid(row=0, column=0, sticky="w")
        tk.Label(cycle, textvariable=self.cycle_step_var, font=("Arial", 12), width=15, anchor="w").grid(
            row=0, column=1, sticky="w"
        )
        tk.Label(cycle, text="Cycle Count:").grid(row=1, column=0, sticky="w")
        tk.Label(cycle, textvariable=self.cycle_progress_var, font=("Arial", 12)).grid(
            row=1, column=1, sticky="w"
        )
        tk.Label(cycle, text="Time:").grid(row=2, column=0, sticky="w")
        tk.Label(cycle, textvariable=self.cycle_time_var, font=("Arial", 12)).grid(
            row=2, column=1, sticky="w"
        )

        if key == "flush":
            self.start_btn_flush = start_button
        else:
            self.start_btn_post_scrub = start_button

    def _rebuild_navigation_rails(self) -> None:
        for key, tab in (
            ("test", self.test_tab),
            ("benchmark", self.benchmark_tab),
            ("clean", self.clean_tab),
            ("flush", self.flush_tab),
            ("post_scrub", self.post_scrub_tab),
        ):
            pfd = self.pfds.get(key, {})
            nav = pfd.get("navigation_rail")
            if nav is None:
                continue
            for child in nav.winfo_children():
                child.destroy()
            pfd["navigation_buttons"] = self._populate_top_navigation(nav, tab)

    def _populate_top_navigation(self, nav: tk.Frame, current_tab: tk.Widget) -> list[tk.Button]:
        if not hasattr(self, "flush_tab"):
            return super()._populate_top_navigation(nav, current_tab)
        nav.columnconfigure(tuple(range(5)), weight=1, uniform="meu_nav")
        nav.rowconfigure(0, weight=1)
        items = (
            ("Flush", self.flush_tab, lambda: self._select_tab(self.flush_tab)),
            ("Benchmark", self.benchmark_tab, lambda: self._select_tab(self.benchmark_tab)),
            ("Test", self.test_tab, lambda: self._select_tab(self.test_tab)),
            ("Post-Scrub", self.post_scrub_tab, lambda: self._select_tab(self.post_scrub_tab)),
            ("Clean", self.clean_tab, lambda: self._select_tab(self.clean_tab)),
        )
        buttons = []
        for column, (label, tab, command) in enumerate(items):
            selected = tab is current_tab
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
                row=0, column=column, sticky="nsew",
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
                selected = index == active_index
                try:
                    button.configure(
                        relief="sunken" if selected else "raised",
                        bg="#cfcfcf" if selected else "#e8e8e8",
                        font=self.NAV_FONT_ACTIVE if selected else self.NAV_FONT,
                    )
                except tk.TclError:
                    pass

    def _arrange_lower_panels(self) -> None:
        super()._arrange_lower_panels()
        if not hasattr(self, "flush_tab"):
            return
        for tab in (self.flush_tab, self.post_scrub_tab):
            settings, sensors, cycle = self._find_lower_frames(tab)
            if sensors is not None:
                try:
                    natural = sensors.winfo_reqheight()
                    sensors.configure(height=natural + self.SENSOR_FRAME_EXTRA_HEIGHT)
                    sensors.pack_propagate(False)
                except tk.TclError:
                    pass
            if settings is not None and sensors is not None:
                try:
                    left = settings.master
                    left.configure(width=settings.winfo_reqwidth())
                    left.pack_propagate(False)
                    self.update_idletasks()
                    settings.pack_forget()
                    settings.place(
                        x=settings.winfo_reqwidth() / 2,
                        y=sensors.winfo_rooty() - left.winfo_rooty(),
                        anchor="n",
                    )
                except tk.TclError:
                    pass

    def _enlarge_start_buttons(self) -> None:
        super()._enlarge_start_buttons()
        for name in ("start_btn_flush", "start_btn_post_scrub"):
            button = getattr(self, name, None)
            if button is not None:
                button.configure(font=self.START_FONT, width=9, height=1, padx=8, pady=5)

    def _update_flush_summary(self) -> None:
        self.flush_summary_var.set(
            f"Filter: {self.flush_filt_target_weight_var.get():g} g\n"
            f"Backwash: {self.flush_bw_target_weight_var.get():g} g\n"
            f"Purge: {self.flush_purge_time_var.get():g} s\n"
            f"Cycles: {self.flush_cycle_count_var.get()}\n"
            "Data logging: Off"
        )

    def _update_post_scrub_summary(self) -> None:
        filt_unit = "g" if self.post_scrub_filt_use_weight_var.get() else "s"
        bw_unit = "g" if self.post_scrub_bw_use_weight_var.get() else "s"
        filt_value = (
            self.post_scrub_filt_target_weight_var.get()
            if self.post_scrub_filt_use_weight_var.get()
            else self.post_scrub_filt_target_time_var.get()
        )
        bw_value = (
            self.post_scrub_bw_target_weight_var.get()
            if self.post_scrub_bw_use_weight_var.get()
            else self.post_scrub_bw_target_time_var.get()
        )
        self.post_scrub_summary_var.set(
            f"Filter: {filt_value:g} {filt_unit}\n"
            f"Backwash: {bw_value:g} {bw_unit}\n"
            f"Purge: {self.post_scrub_purge_time_var.get():g} s\n"
            f"Cycles: {self.post_scrub_cycle_count_var.get()}\n"
            f"Sample: {self.post_scrub_sample_time_var.get():g} s"
        )

    def _settings_window(self, title: str) -> tuple[tk.Toplevel, tk.Frame]:
        window = tk.Toplevel(self)
        window.title(title)
        window.transient(self)
        window.resizable(False, False)
        body = tk.Frame(window, padx=20, pady=16)
        body.pack(fill="both", expand=True)
        return window, body

    @staticmethod
    def _entry(body: tk.Frame, row: int, label: str, variable: tk.Variable) -> None:
        tk.Label(body, text=label).grid(row=row, column=0, sticky="e", padx=6, pady=4)
        tk.Entry(body, textvariable=variable, width=16).grid(
            row=row, column=1, sticky="w", padx=6, pady=4
        )

    def _edit_flush_settings(self) -> None:
        window, body = self._settings_window("Flush Settings")
        self._entry(body, 0, "Filter target (g)", self.flush_filt_target_weight_var)
        self._entry(body, 1, "Backwash target (g)", self.flush_bw_target_weight_var)
        self._entry(body, 2, "Purge time (s)", self.flush_purge_time_var)
        self._entry(body, 3, "Cycle count", self.flush_cycle_count_var)

        def save() -> None:
            try:
                self._positive(self.flush_filt_target_weight_var.get(), "Filter target")
                self._positive(self.flush_bw_target_weight_var.get(), "Backwash target")
                self._positive(self.flush_purge_time_var.get(), "Purge time")
                self._positive_count(self.flush_cycle_count_var.get(), "Cycle count")
            except Exception as exc:
                messagebox.showerror("Invalid Flush Settings", str(exc), parent=window)
                return
            self._update_flush_summary()
            window.destroy()

        tk.Button(body, text="Cancel", command=window.destroy).grid(row=4, column=0, pady=(12, 0))
        tk.Button(body, text="Save", command=save).grid(row=4, column=1, pady=(12, 0))
        self._style_settings_window(window)

    def _edit_post_scrub_settings(self) -> None:
        window, body = self._settings_window("Post-Scrub Settings")
        self._entry(body, 0, "Filter target (g)", self.post_scrub_filt_target_weight_var)
        self._entry(body, 1, "Filter target (s)", self.post_scrub_filt_target_time_var)
        tk.Checkbutton(
            body, text="Stop filter by weight", variable=self.post_scrub_filt_use_weight_var
        ).grid(row=2, column=0, columnspan=2, sticky="w")
        self._entry(body, 3, "Backwash target (g)", self.post_scrub_bw_target_weight_var)
        self._entry(body, 4, "Backwash target (s)", self.post_scrub_bw_target_time_var)
        tk.Checkbutton(
            body, text="Stop backwash by weight", variable=self.post_scrub_bw_use_weight_var
        ).grid(row=5, column=0, columnspan=2, sticky="w")
        self._entry(body, 6, "Purge time (s)", self.post_scrub_purge_time_var)
        self._entry(body, 7, "Cycle count", self.post_scrub_cycle_count_var)
        self._entry(body, 8, "Sample rate (s)", self.post_scrub_sample_time_var)
        self._entry(body, 9, "Project", self.post_scrub_project_var)
        self._entry(body, 10, "Module ID", self.post_scrub_module_id_var)
        self._entry(body, 11, "Sample ID", self.post_scrub_sample_id_var)

        def save() -> None:
            try:
                filt = (
                    self.post_scrub_filt_target_weight_var.get()
                    if self.post_scrub_filt_use_weight_var.get()
                    else self.post_scrub_filt_target_time_var.get()
                )
                bw = (
                    self.post_scrub_bw_target_weight_var.get()
                    if self.post_scrub_bw_use_weight_var.get()
                    else self.post_scrub_bw_target_time_var.get()
                )
                self._positive(filt, "Filter target")
                self._positive(bw, "Backwash target")
                self._positive(self.post_scrub_purge_time_var.get(), "Purge time")
                self._positive_count(self.post_scrub_cycle_count_var.get(), "Cycle count")
                self._positive(self.post_scrub_sample_time_var.get(), "Sample rate")
            except Exception as exc:
                messagebox.showerror("Invalid Post-Scrub Settings", str(exc), parent=window)
                return
            self._update_post_scrub_summary()
            window.destroy()

        tk.Button(body, text="Cancel", command=window.destroy).grid(row=12, column=0, pady=(12, 0))
        tk.Button(body, text="Save", command=save).grid(row=12, column=1, pady=(12, 0))
        self._style_settings_window(window)

    def _toggle_flush(self) -> None:
        if self.is_running:
            self.cancel_test()
            return
        self.is_running = True
        self.start_btn_flush.config(text="Stop")
        self.start_flush()

    def _toggle_post_scrub(self) -> None:
        if self.is_running:
            self.cancel_test()
            return
        self.is_running = True
        self.start_btn_post_scrub.config(text="Stop")
        self.start_post_scrub()

    def start_flush(self) -> None:
        try:
            self._mark_run_start()
            self._run_started = True
            self._disable_manual_controls()
            self._close_all_valves()
            config = FiltrationConfig(
                filtration_target=self._positive(
                    self.flush_filt_target_weight_var.get(), "Flush filter target"
                ),
                filtration_by_weight=True,
                backwash_target=self._positive(
                    self.flush_bw_target_weight_var.get(), "Flush backwash target"
                ),
                backwash_by_weight=True,
                purge_time=self._positive(self.flush_purge_time_var.get(), "Flush purge time"),
                cycle_count=self._positive_count(
                    self.flush_cycle_count_var.get(), "Flush cycle count"
                ),
                sample_time=1.0,
                project="",
                module_id="",
                sample_id="",
                file_prefix="Flush",
                **self._active_offsets(),
            )
            self.test_system = _FlushTestSystem(
                self.module,
                config,
                valve_callback=self._automation_valve_change,
                progress_callback=self._automation_progress,
            )
            self.test_thread = threading.Thread(target=self._run_test_thread, daemon=True)
            self.test_thread.start()
        except Exception as exc:
            self.is_running = False
            self._run_started = False
            self.start_btn_flush.config(text="Start")
            self._enable_manual_controls()
            messagebox.showerror("Invalid Flush Settings", str(exc))

    def start_post_scrub(self) -> None:
        try:
            self._mark_run_start()
            self._run_started = True
            self._disable_manual_controls()
            self._close_all_valves()
            filt_by_weight = self.post_scrub_filt_use_weight_var.get()
            bw_by_weight = self.post_scrub_bw_use_weight_var.get()
            config = FiltrationConfig(
                filtration_target=self._positive(
                    self.post_scrub_filt_target_weight_var.get()
                    if filt_by_weight else self.post_scrub_filt_target_time_var.get(),
                    "Post-Scrub filter target",
                ),
                filtration_by_weight=filt_by_weight,
                backwash_target=self._positive(
                    self.post_scrub_bw_target_weight_var.get()
                    if bw_by_weight else self.post_scrub_bw_target_time_var.get(),
                    "Post-Scrub backwash target",
                ),
                backwash_by_weight=bw_by_weight,
                purge_time=self._positive(
                    self.post_scrub_purge_time_var.get(), "Post-Scrub purge time"
                ),
                cycle_count=self._positive_count(
                    self.post_scrub_cycle_count_var.get(), "Post-Scrub cycle count"
                ),
                sample_time=self._positive(
                    self.post_scrub_sample_time_var.get(), "Post-Scrub sample rate"
                ),
                project=self.post_scrub_project_var.get(),
                module_id=self.post_scrub_module_id_var.get(),
                sample_id=self.post_scrub_sample_id_var.get(),
                file_prefix="Post Scrub",
                **self._active_offsets(),
            )
            self.test_system = FiltrationTestSystem(
                self.module,
                config,
                valve_callback=self._automation_valve_change,
                progress_callback=self._automation_progress,
            )
            self.test_thread = threading.Thread(target=self._run_test_thread, daemon=True)
            self.test_thread.start()
        except Exception as exc:
            self.is_running = False
            self._run_started = False
            self.start_btn_post_scrub.config(text="Start")
            self._enable_manual_controls()
            messagebox.showerror("Invalid Post-Scrub Settings", str(exc))

    def cancel_test(self) -> None:
        super().cancel_test()
        for button in (self.start_btn_flush, self.start_btn_post_scrub):
            try:
                button.config(state="disabled")
            except tk.TclError:
                pass

    def _test_finished(self) -> None:
        flush_run = self._active_tab is self.flush_tab
        if flush_run:
            self._run_started = False
        super()._test_finished()
        self.start_btn_flush.config(text="Start", state="normal")
        self.start_btn_post_scrub.config(text="Start", state="normal")
        if flush_run:
            self._run_log_snapshot = self._csv_snapshot(self._current_log_dir())


__all__ = ["HMI"]
