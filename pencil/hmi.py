"""Tkinter based HMI for the Pencil Module."""

import os
import re
import tkinter as tk
from tkinter import ttk
import threading
import time
from tkinter import scrolledtext

from .automation import (
    FiltrationConfig,
    FiltrationTestSystem,
    CleanConfig,
    CleanTestSystem,
)
from .hardware import PencilModule
from .widgets import NumericEntry, NumericKeypad, OnScreenKeyboard, KeyboardEntry
from tkinter import messagebox




class HMI(tk.Tk):
    """Simple Tkinter graphical interface with a process diagram."""

    def __init__(self, module: PencilModule, fullscreen: bool = False) -> None:
        super().__init__()
        self.module = module
        self.title("Pencil Module")
        self.geometry("800x480")
        self.update_idletasks()
        self.protocol("WM_DELETE_WINDOW", self._confirm_exit)
        # Close button will be created in the PFD canvas
        if fullscreen:
            try:
                self.attributes("-fullscreen", True)
            except Exception:
                pass

        self.weight_var = tk.StringVar()
        self.backwash_weight_var = tk.StringVar()
        self.pressure_bw_var = tk.StringVar()
        self.pressure_raw_var = tk.StringVar()
        self.temp_var = tk.StringVar()
        self.cycle_step_var = tk.StringVar(value="Idle")
        self.cycle_count_var = tk.StringVar(value="")

        self.filt_target_weight_var = tk.DoubleVar(value=1.0)
        self.filt_target_time_var = tk.DoubleVar(value=1.0)
        self.filt_use_weight_var = tk.BooleanVar(value=False)
        self.filt_use_time_var = tk.BooleanVar(value=True)
        self.bw_target_weight_var = tk.DoubleVar(value=1.0)
        self.bw_target_time_var = tk.DoubleVar(value=1.0)
        self.bw_use_weight_var = tk.BooleanVar(value=False)
        self.bw_use_time_var = tk.BooleanVar(value=True)
        self.refill_time_var = tk.DoubleVar(value=0.5)
        self.repeat_count_var = tk.IntVar(value=1)
        self.sample_time_var = tk.DoubleVar(value=0.1)
        self.project_name_var = tk.StringVar(value="demo")

        # Clean mode variables
        self.clean_fwd_target_weight_var = tk.DoubleVar(value=1.0)
        self.clean_fwd_target_time_var = tk.DoubleVar(value=1.0)
        self.clean_fwd_use_weight_var = tk.BooleanVar(value=False)
        self.clean_fwd_use_time_var = tk.BooleanVar(value=True)
        self.clean_bw_target_weight_var = tk.DoubleVar(value=1.0)
        self.clean_bw_target_time_var = tk.DoubleVar(value=1.0)
        self.clean_bw_use_weight_var = tk.BooleanVar(value=False)
        self.clean_bw_use_time_var = tk.BooleanVar(value=True)
        self.clean_fwd_soak_var = tk.DoubleVar(value=0.5)
        self.clean_bw_soak_var = tk.DoubleVar(value=0.5)
        self.clean_cycle_count_var = tk.IntVar(value=1)
        self.clean_sample_time_var = tk.DoubleVar(value=0.1)
        self.clean_rinse_time_var = tk.DoubleVar(value=1.0)
        self.clean_project_name_var = tk.StringVar(value="clean")
        self.is_running = False
        self.solenoid_states = [False] * 5
        self.prime_frame = None
        self.prime_stage = 0

        # Thread-safe storage for sensor readings
        self._sensor_lock = threading.Lock()
        self._stop_event = threading.Event()
        self.latest_weight = "--"
        self.latest_bw_weight = "--"
        self.latest_pressure_bw = 0.0
        self.latest_pressure_raw = 0.0
        self.latest_temp = 0.0

        # Read once before starting the background thread
        self._read_sensors()
        self._worker = threading.Thread(target=self._sensor_worker, daemon=True)
        self._worker.start()

        # Create tabbed interface
        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill="both", expand=True)

        self.pfds = {}

        self.test_tab = tk.Frame(self.notebook)
        self.clean_tab = tk.Frame(self.notebook)
        self.notebook.add(self.test_tab, text="Test")
        self.notebook.add(self.clean_tab, text="Clean")

        # Build Test tab
        self.pfds["test"] = self._create_pfd(self.test_tab)
        self.area = tk.Frame(self.test_tab)
        self.area.pack(fill="both", expand=True, padx=5, pady=(0, 5))

        left_col = tk.Frame(self.area)
        left_col.pack(side="left", padx=5, pady=5, anchor="n")

        middle_col = tk.Frame(self.area)
        middle_col.pack(side="left", padx=5, pady=5, anchor="n")

        self.start_btn_test = tk.Button(
            middle_col,
            text="Start",
            command=self._toggle_test,
            font=("Arial", 12),
            width=7,
            height=1,
        )
        self.start_btn_test.pack()

        settings = tk.LabelFrame(left_col, text="Settings")
        settings.pack(anchor="n")
        self.settings_frame = settings

        right_col = tk.Frame(self.area)
        right_col.pack(side="right", fill="y", padx=5, pady=5)

        logo_path = os.path.join(os.path.dirname(__file__), "..", "resources", "WaterARC Logo-Carollo-01.png")
        self.logo_image = tk.PhotoImage(file=logo_path)
        self.logo_image = self.logo_image.subsample(8, 8)
        logo_label = tk.Label(self.area, image=self.logo_image, borderwidth=0)
        logo_label.place(relx=0.5, rely=0.5, x=40, anchor="center")
        logo_label.lower()

        info = tk.LabelFrame(right_col, text="Sensors")
        info.pack(padx=5, pady=5, anchor="n")
        tk.Label(info, text="Effluent Weight:").grid(row=0, column=0, sticky="w")
        tk.Label(info, textvariable=self.weight_var, font=("Arial", 12)).grid(row=0, column=1, sticky="w")
        tk.Label(info, text="g").grid(row=0, column=2, sticky="w")
        tk.Label(info, text="BW Weight:").grid(row=1, column=0, sticky="w")
        tk.Label(info, textvariable=self.backwash_weight_var, font=("Arial", 12)).grid(row=1, column=1, sticky="w")
        tk.Label(info, text="g").grid(row=1, column=2, sticky="w")
        tk.Label(info, text="BW Pressure:").grid(row=2, column=0, sticky="w")
        tk.Label(info, textvariable=self.pressure_bw_var, font=("Arial", 12)).grid(row=2, column=1, sticky="w")
        tk.Label(info, text="PSI").grid(row=2, column=2, sticky="w")
        tk.Label(info, text="Influent Pressure:").grid(row=3, column=0, sticky="w")
        tk.Label(info, textvariable=self.pressure_raw_var, font=("Arial", 12)).grid(row=3, column=1, sticky="w")
        tk.Label(info, text="PSI").grid(row=3, column=2, sticky="w")
        tk.Label(info, text="Temperature:").grid(row=4, column=0, sticky="w")
        tk.Label(info, textvariable=self.temp_var, font=("Arial", 12)).grid(row=4, column=1, sticky="w")
        tk.Label(info, text="C").grid(row=4, column=2, sticky="w")

        cycle_frame = tk.LabelFrame(right_col, text="Cycle Status")
        cycle_frame.pack(anchor="n", pady=5)
        tk.Label(cycle_frame, text="Cycle Step:").grid(row=0, column=0, sticky="w")
        tk.Label(cycle_frame, textvariable=self.cycle_step_var, font=("Arial", 12)).grid(row=0, column=1, sticky="w")
        tk.Label(cycle_frame, text="Cycle Count:").grid(row=1, column=0, sticky="w")
        tk.Label(cycle_frame, textvariable=self.cycle_count_var, font=("Arial", 12)).grid(row=1, column=1, sticky="w")

        tk.Label(settings, text="Filtration Target").grid(row=0, column=0, sticky="w")
        NumericEntry(settings, textvariable=self.filt_target_weight_var, width=7).grid(row=0, column=1)
        tk.Checkbutton(settings, text="g", variable=self.filt_use_weight_var, command=self._toggle_filt_weight).grid(row=0, column=2, sticky="w")
        NumericEntry(settings, textvariable=self.filt_target_time_var, width=7).grid(row=0, column=3)
        tk.Checkbutton(settings, text="s", variable=self.filt_use_time_var, command=self._toggle_filt_time).grid(row=0, column=4, sticky="w")

        tk.Label(settings, text="Backwash Target").grid(row=1, column=0, sticky="w")
        NumericEntry(settings, textvariable=self.bw_target_weight_var, width=7).grid(row=1, column=1)
        tk.Checkbutton(settings, text="g", variable=self.bw_use_weight_var, command=self._toggle_bw_weight).grid(row=1, column=2, sticky="w")
        NumericEntry(settings, textvariable=self.bw_target_time_var, width=7).grid(row=1, column=3)
        tk.Checkbutton(settings, text="s", variable=self.bw_use_time_var, command=self._toggle_bw_time).grid(row=1, column=4, sticky="w")

        tk.Label(settings, text="Purge Time").grid(row=2, column=0, sticky="w")
        NumericEntry(settings, textvariable=self.refill_time_var, width=7).grid(row=2, column=1)
        tk.Label(settings, text="sec").grid(row=2, column=2, sticky="w")

        tk.Label(settings, text="Cycle Count").grid(row=3, column=0, sticky="w")
        NumericEntry(settings, textvariable=self.repeat_count_var, width=7).grid(row=3, column=1)

        tk.Label(settings, text="Sample Time").grid(row=4, column=0, sticky="w")
        NumericEntry(settings, textvariable=self.sample_time_var, width=7).grid(row=4, column=1)
        tk.Label(settings, text="sec").grid(row=4, column=2, sticky="w")

        tk.Label(settings, text="Project Name").grid(row=5, column=0, sticky="w")
        KeyboardEntry(settings, textvariable=self.project_name_var, width=7).grid(row=5, column=1)

        btn_frame = tk.Frame(settings)
        btn_frame.grid(row=6, column=0, columnspan=5, pady=8, sticky="ew")
        btn_frame.columnconfigure((0, 1, 2), weight=1)

        tk.Button(btn_frame, text="Calibrate", command=self.calibrate).grid(row=0, column=0, padx=5, sticky="ew")
        tk.Button(btn_frame, text="Tare EFL", command=lambda: self.module.zero_scale(0)).grid(row=0, column=1, padx=5, sticky="ew")
        tk.Button(btn_frame, text="Tare BW", command=lambda: self.module.zero_scale(1)).grid(row=0, column=2, padx=5, sticky="ew")

        # Clean tab
        self.pfds["clean"] = self._create_pfd(self.clean_tab)
        clean_area = tk.Frame(self.clean_tab)
        clean_area.pack(fill="both", expand=True, padx=5, pady=(0, 5))

        clean_left = tk.Frame(clean_area)
        clean_left.pack(side="left", padx=5, pady=5, anchor="n")
        clean_settings = tk.LabelFrame(clean_left, text="Settings")
        clean_settings.pack(anchor="n")

        clean_middle = tk.Frame(clean_area)
        clean_middle.pack(side="left", padx=5, pady=5, anchor="n")

        self.start_btn_clean = tk.Button(
            clean_middle,
            text="Start",
            command=self._toggle_clean,
            font=("Arial", 12),
            width=7,
            height=1,
        )
        self.start_btn_clean.pack()

        clean_right = tk.Frame(clean_area)
        clean_right.pack(side="right", fill="y", padx=5, pady=5)

        logo_label2 = tk.Label(clean_area, image=self.logo_image, borderwidth=0)
        logo_label2.place(relx=0.5, rely=0.5, x=40, anchor="center")
        logo_label2.lower()

        info2 = tk.LabelFrame(clean_right, text="Sensors")
        info2.pack(padx=5, pady=5, anchor="n")
        tk.Label(info2, text="Effluent Weight:").grid(row=0, column=0, sticky="w")
        tk.Label(info2, textvariable=self.weight_var, font=("Arial", 12)).grid(row=0, column=1, sticky="w")
        tk.Label(info2, text="g").grid(row=0, column=2, sticky="w")
        tk.Label(info2, text="BW Weight:").grid(row=1, column=0, sticky="w")
        tk.Label(info2, textvariable=self.backwash_weight_var, font=("Arial", 12)).grid(row=1, column=1, sticky="w")
        tk.Label(info2, text="g").grid(row=1, column=2, sticky="w")
        tk.Label(info2, text="BW Pressure:").grid(row=2, column=0, sticky="w")
        tk.Label(info2, textvariable=self.pressure_bw_var, font=("Arial", 12)).grid(row=2, column=1, sticky="w")
        tk.Label(info2, text="PSI").grid(row=2, column=2, sticky="w")
        tk.Label(info2, text="Influent Pressure:").grid(row=3, column=0, sticky="w")
        tk.Label(info2, textvariable=self.pressure_raw_var, font=("Arial", 12)).grid(row=3, column=1, sticky="w")
        tk.Label(info2, text="PSI").grid(row=3, column=2, sticky="w")
        tk.Label(info2, text="Temperature:").grid(row=4, column=0, sticky="w")
        tk.Label(info2, textvariable=self.temp_var, font=("Arial", 12)).grid(row=4, column=1, sticky="w")
        tk.Label(info2, text="C").grid(row=4, column=2, sticky="w")

        cycle_frame2 = tk.LabelFrame(clean_right, text="Cycle Status")
        cycle_frame2.pack(anchor="n", pady=5)
        tk.Label(cycle_frame2, text="Cycle Step:").grid(row=0, column=0, sticky="w")
        tk.Label(cycle_frame2, textvariable=self.cycle_step_var, font=("Arial", 12)).grid(row=0, column=1, sticky="w")
        tk.Label(cycle_frame2, text="Cycle Count:").grid(row=1, column=0, sticky="w")
        tk.Label(cycle_frame2, textvariable=self.cycle_count_var, font=("Arial", 12)).grid(row=1, column=1, sticky="w")

        tk.Label(clean_settings, text="Forward Target").grid(row=0, column=0, sticky="w")
        NumericEntry(clean_settings, textvariable=self.clean_fwd_target_weight_var, width=7).grid(row=0, column=1)
        tk.Checkbutton(clean_settings, text="g", variable=self.clean_fwd_use_weight_var).grid(row=0, column=2, sticky="w")
        NumericEntry(clean_settings, textvariable=self.clean_fwd_target_time_var, width=7).grid(row=0, column=3)
        tk.Checkbutton(clean_settings, text="s", variable=self.clean_fwd_use_time_var).grid(row=0, column=4, sticky="w")

        tk.Label(clean_settings, text="Forward Soak").grid(row=1, column=0, sticky="w")
        NumericEntry(clean_settings, textvariable=self.clean_fwd_soak_var, width=7).grid(row=1, column=1)
        tk.Label(clean_settings, text="s").grid(row=1, column=2, sticky="w")

        tk.Label(clean_settings, text="Backwash Target").grid(row=2, column=0, sticky="w")
        NumericEntry(clean_settings, textvariable=self.clean_bw_target_weight_var, width=7).grid(row=2, column=1)
        tk.Checkbutton(clean_settings, text="g", variable=self.clean_bw_use_weight_var).grid(row=2, column=2, sticky="w")
        NumericEntry(clean_settings, textvariable=self.clean_bw_target_time_var, width=7).grid(row=2, column=3)
        tk.Checkbutton(clean_settings, text="s", variable=self.clean_bw_use_time_var).grid(row=2, column=4, sticky="w")

        tk.Label(clean_settings, text="Backwash Soak").grid(row=3, column=0, sticky="w")
        NumericEntry(clean_settings, textvariable=self.clean_bw_soak_var, width=7).grid(row=3, column=1)
        tk.Label(clean_settings, text="s").grid(row=3, column=2, sticky="w")

        tk.Label(clean_settings, text="Cycle Count").grid(row=4, column=0, sticky="w")
        NumericEntry(clean_settings, textvariable=self.clean_cycle_count_var, width=7).grid(row=4, column=1)

        tk.Label(clean_settings, text="Sample Time").grid(row=5, column=0, sticky="w")
        NumericEntry(clean_settings, textvariable=self.clean_sample_time_var, width=7).grid(row=5, column=1)
        tk.Label(clean_settings, text="sec").grid(row=5, column=2, sticky="w")

        tk.Label(clean_settings, text="Rinse Time").grid(row=6, column=0, sticky="w")
        NumericEntry(clean_settings, textvariable=self.clean_rinse_time_var, width=7).grid(row=6, column=1)
        tk.Label(clean_settings, text="sec").grid(row=6, column=2, sticky="w")

        tk.Label(clean_settings, text="Project Name").grid(row=7, column=0, sticky="w")
        KeyboardEntry(clean_settings, textvariable=self.clean_project_name_var, width=7).grid(row=7, column=1)

        btn_frame2 = tk.Frame(clean_settings)
        btn_frame2.grid(row=8, column=0, columnspan=5, pady=8, sticky="ew")
        btn_frame2.columnconfigure((0, 1, 2), weight=1)
        tk.Button(btn_frame2, text="Calibrate", command=self.calibrate).grid(row=0, column=0, padx=5, sticky="ew")
        tk.Button(btn_frame2, text="Tare EFL", command=lambda: self.module.zero_scale(0)).grid(row=0, column=1, padx=5, sticky="ew")
        tk.Button(btn_frame2, text="Tare BW", command=lambda: self.module.zero_scale(1)).grid(row=0, column=2, padx=5, sticky="ew")

        self.update_data()

    def _create_pfd(self, parent: tk.Widget) -> dict:
        """Create and return a process flow diagram on ``parent``."""
        canvas = tk.Canvas(parent, width=780, height=170, bg="white")
        canvas.pack(pady=(2, 0))

        btn_opts = {"width": 2, "height": 1, "ipadx": 2, "ipady": 0}
        btn_frame = tk.Frame(canvas, bg="white")
        help_btn = tk.Button(btn_frame, text="?", command=self._show_control_narrative, **btn_opts)
        close_btn = tk.Button(btn_frame, text="X", command=self._confirm_exit, **btn_opts)
        help_btn.pack(side="left", padx=(0, 2))
        close_btn.pack(side="left")
        canvas.create_window(770, 10, window=btn_frame, anchor="ne")

        canvas.create_rectangle(75, 30, 125, 80, fill="lightblue")
        canvas.create_text(100, 20, text="BW water")
        pi1_text = canvas.create_text(100, 70, text="-- PSI")

        canvas.create_rectangle(75, 110, 125, 160, fill="lightblue")
        canvas.create_text(100, 100, text="Influent water")
        pi2_text = canvas.create_text(100, 150, text="-- PSI")

        canvas.create_rectangle(265, 45, 445, 65, fill="lightgray")
        canvas.create_rectangle(275, 65, 290, 85, fill="lightgray")
        canvas.create_rectangle(420, 65, 435, 85, fill="lightgray")
        canvas.create_text(355, 35, text="Mini-module")

        canvas.create_rectangle(565, 30, 615, 80, fill="lightblue")
        canvas.create_text(590, 20, text="Effluent")
        effluent_weight_text = canvas.create_text(590, 70, text="-- g")

        canvas.create_rectangle(565, 120, 615, 170, fill="lightblue")
        canvas.create_text(590, 110, text="Backwash")
        backwash_weight_text = canvas.create_text(590, 160, text="-- g")

        canvas.create_rectangle(665, 75, 715, 125, fill="lightblue")
        canvas.create_text(690, 65, text="Drain")

        lines = {}
        valve_labels = {}
        valve_to_lines = {
            0: [0],
            1: [1],
            2: [2, 'v3_vert1', 'v3_vert2'],
            3: [3, 'v3_vert2'],
            4: [4],
        }

        lines[0] = canvas.create_line(125, 55, 265, 55, arrow="last", fill="gray", width=2)
        valve_labels['V1'] = canvas.create_text(195, 55, text="V1")

        lines[1] = canvas.create_line(125, 125, 290, 125, fill="gray", width=2)
        lines['v2_vert'] = canvas.create_line(282.5, 125, 282.5, 85, arrow="last", fill="gray", width=2)
        valve_to_lines[1].append('v2_vert')
        valve_labels['V2'] = canvas.create_text(195, 125, text="V2")
        canvas.create_rectangle(290, 117.5, 340, 132.5, fill="white", outline="black")
        te_text = canvas.create_text(315, 125, text="-- C")

        lines[2] = canvas.create_line(427.5, 145, 565, 145, arrow="last", fill="gray", width=2)
        lines['v3_vert1'] = canvas.create_line(427.5, 100, 427.5, 145, fill="gray", width=2)
        lines['v3_vert2'] = canvas.create_line(427.5, 85, 427.5, 100, fill="gray", width=2)
        valve_to_lines[2].extend(['v3_vert1', 'v3_vert2'])
        valve_labels['V3'] = canvas.create_text(505, 145, text="V3")

        lines[3] = canvas.create_line(427.5, 100, 665, 100, arrow="last", fill="gray", width=2)
        valve_labels['V4'] = canvas.create_text(505, 100, text="V4")

        lines[4] = canvas.create_line(445, 55, 565, 55, arrow="last", fill="gray", width=2)
        valve_labels['V5'] = canvas.create_text(505, 55, text="V5")

        solenoid_buttons = []
        valve_keys = ['V1', 'V2', 'V3', 'V4', 'V5']
        for i in range(5):
            btn = tk.Button(canvas, text=f"V{i+1}", width=3, bg="lightgray", command=lambda ch=i: self.toggle_solenoid(ch))
            x, y = canvas.coords(valve_labels[valve_keys[i]])
            canvas.create_window(x, y, window=btn)
            solenoid_buttons.append(btn)

        prime_btn = tk.Button(canvas, text="Prime", command=self.prime)
        canvas.create_window(355, 90, window=prime_btn)

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
        for pfd in self.pfds.values():
            for idx, line_ids in pfd["valve_to_lines"].items():
                for lid in line_ids:
                    if lid == 'v3_vert2':
                        continue
                    color = "green" if self.solenoid_states[idx] else "gray"
                    pfd["canvas"].itemconfig(pfd["lines"][lid], fill=color)
            color = "green" if self.solenoid_states[2] or self.solenoid_states[3] else "gray"
            pfd["canvas"].itemconfig(pfd["lines"]["v3_vert2"], fill=color)

    def toggle_solenoid(self, channel: int) -> None:
        state = not self.solenoid_states[channel]
        self.solenoid_states[channel] = state
        self.module.set_solenoid(channel + 1, state)
        bg = "green" if state else "lightgray"
        for pfd in self.pfds.values():
            pfd["solenoid_buttons"][channel].config(bg=bg)
        self._update_lines()

    def _set_valves(self, state: bool, *valves: int) -> None:
        for v in valves:
            idx = v - 1
            self.solenoid_states[idx] = state
            self.module.set_solenoid(v, state)
            bg = "green" if state else "lightgray"
            for pfd in self.pfds.values():
                pfd["solenoid_buttons"][idx].config(bg=bg)
        self._update_lines()

    def _automation_valve_change(self, valve: int, state: bool) -> None:
        """Callback invoked by the automation system when a valve changes."""
        idx = valve - 1
        if 0 <= idx < len(self.solenoid_states):
            self.solenoid_states[idx] = state
            bg = "green" if state else "lightgray"
            for pfd in self.pfds.values():
                pfd["solenoid_buttons"][idx].config(bg=bg)
            self._update_lines()

    def _automation_progress(self, step: str, count: int, total: int) -> None:
        """Update cycle progress information."""
        self.cycle_step_var.set(step)
        self.cycle_count_var.set(f"{count} of {total}")

    def _open_valves(self, *valves: int) -> None:
        self._set_valves(True, *valves)

    def _close_valves(self, *valves: int) -> None:
        self._set_valves(False, *valves)

    def _close_all_valves(self) -> None:
        self._close_valves(1, 2, 3, 4, 5)

    def _disable_manual_controls(self) -> None:
        """Disable the valve and prime buttons while a test is running."""
        for pfd in self.pfds.values():
            for btn in pfd["solenoid_buttons"]:
                btn.config(state="disabled")
            pfd["prime_btn"].config(state="disabled")

    def _enable_manual_controls(self) -> None:
        """Re-enable manual control buttons after a test completes."""
        for pfd in self.pfds.values():
            for btn in pfd["solenoid_buttons"]:
                btn.config(state="normal")
            pfd["prime_btn"].config(state="normal")

    def prime(self) -> None:
        if self.prime_frame:
            return
        self.prime_stage = 1
        self.prime_frame = tk.Frame(self)
        self.prime_frame.place(relx=0.5, rely=0.35, anchor="center", y=50)
        tk.Label(self.prime_frame, text="Confirm Prime").pack(side="left", padx=5)
        tk.Button(self.prime_frame, text="Cancel", command=self._cancel_prime).pack(side="left", padx=5)
        tk.Button(self.prime_frame, text="Start", command=self._start_prime).pack(side="left", padx=5)

    def _cancel_prime(self) -> None:
        self._close_all_valves()
        if self.prime_frame:
            self.prime_frame.destroy()
            self.prime_frame = None
        self.prime_stage = 0

    def _start_prime(self) -> None:
        self.prime_stage = 2
        self._show_prime_stage()

    def _advance_prime(self) -> None:
        self.prime_stage += 1
        if self.prime_stage > 4:
            self._finish_prime()
        else:
            self._show_prime_stage()

    def _show_prime_stage(self) -> None:
        if not self.prime_frame:
            return
        for widget in self.prime_frame.winfo_children():
            widget.destroy()
        step_text = {2: "Step 1", 3: "Step 2", 4: "Step 3"}
        self._close_all_valves()
        if self.prime_stage == 2:
            self._open_valves(2, 3, 4)
        elif self.prime_stage == 3:
            self._open_valves(1, 5)
        elif self.prime_stage == 4:
            self._open_valves(2, 4)
        tk.Label(self.prime_frame, text=step_text.get(self.prime_stage, "")).pack(side="left", padx=5)
        btn_text = "Continue" if self.prime_stage < 4 else "Finish"
        tk.Button(self.prime_frame, text=btn_text, command=self._advance_prime).pack(side="left", padx=5)

    def _finish_prime(self) -> None:
        self._close_all_valves()
        if self.prime_frame:
            self.prime_frame.destroy()
            self.prime_frame = None
        self.prime_stage = 0

    def _toggle_filt_weight(self) -> None:
        if self.filt_use_weight_var.get():
            self.filt_use_time_var.set(False)
        elif not self.filt_use_time_var.get():
            self.filt_use_time_var.set(True)

    def _toggle_filt_time(self) -> None:
        if self.filt_use_time_var.get():
            self.filt_use_weight_var.set(False)
        elif not self.filt_use_weight_var.get():
            self.filt_use_weight_var.set(True)

    def _toggle_bw_weight(self) -> None:
        if self.bw_use_weight_var.get():
            self.bw_use_time_var.set(False)
        elif not self.bw_use_time_var.get():
            self.bw_use_time_var.set(True)

    def _toggle_bw_time(self) -> None:
        if self.bw_use_time_var.get():
            self.bw_use_weight_var.set(False)
        elif not self.bw_use_weight_var.get():
            self.bw_use_weight_var.set(True)

    def _toggle_test(self) -> None:
        if getattr(self, "is_running", False):
            self.cancel_test()
        else:
            self._cancel_prime()
            self.is_running = True
            self.start_btn_test.config(text="Cancel")
            self.start_test()

    def _toggle_clean(self) -> None:
        if getattr(self, "is_running", False):
            self.cancel_test()
        else:
            self._cancel_prime()
            self.is_running = True
            self.start_btn_clean.config(text="Cancel")
            self.start_clean()

    def start_test(self) -> None:
        # Disable manual valve controls and ensure all valves are closed before
        # handing control over to the automation routine.
        self._disable_manual_controls()
        self._close_all_valves()

        if self.filt_use_weight_var.get():
            filt_target = self.filt_target_weight_var.get()
            filt_by_vol = True
        else:
            filt_target = self.filt_target_time_var.get()
            filt_by_vol = False

        if self.bw_use_weight_var.get():
            bw_target = self.bw_target_weight_var.get()
            bw_by_vol = True
        else:
            bw_target = self.bw_target_time_var.get()
            bw_by_vol = False

        config = FiltrationConfig(
            filtration_target=filt_target,
            filtration_by_volume=filt_by_vol,
            backwash_target=bw_target,
            backwash_by_volume=bw_by_vol,
            refill_time=self.refill_time_var.get(),
            repeat_count=self.repeat_count_var.get(),
            sample_time=self.sample_time_var.get(),
            project_name=self.project_name_var.get(),
        )
        self.test_system = FiltrationTestSystem(
            self.module,
            config,
            valve_callback=self._automation_valve_change,
            progress_callback=self._automation_progress,
        )
        self.test_thread = threading.Thread(target=self._run_test_thread)
        self.test_thread.start()

    def start_clean(self) -> None:
        self._disable_manual_controls()
        self._close_all_valves()

        if self.clean_fwd_use_weight_var.get():
            fwd_target = self.clean_fwd_target_weight_var.get()
            fwd_by_vol = True
        else:
            fwd_target = self.clean_fwd_target_time_var.get()
            fwd_by_vol = False

        if self.clean_bw_use_weight_var.get():
            bw_target = self.clean_bw_target_weight_var.get()
            bw_by_vol = True
        else:
            bw_target = self.clean_bw_target_time_var.get()
            bw_by_vol = False

        config = CleanConfig(
            forward_target=fwd_target,
            forward_by_volume=fwd_by_vol,
            forward_soak=self.clean_fwd_soak_var.get(),
            backwash_target=bw_target,
            backwash_by_volume=bw_by_vol,
            backwash_soak=self.clean_bw_soak_var.get(),
            cycle_count=self.clean_cycle_count_var.get(),
            sample_time=self.clean_sample_time_var.get(),
            rinse_time=self.clean_rinse_time_var.get(),
            project_name=self.clean_project_name_var.get(),
        )
        self.test_system = CleanTestSystem(
            self.module,
            config,
            valve_callback=self._automation_valve_change,
            progress_callback=self._automation_progress,
        )
        self.test_thread = threading.Thread(target=self._run_test_thread)
        self.test_thread.start()

    def _run_test_thread(self) -> None:
        self.test_system.start_test()
        self.after(0, self._test_finished)

    def cancel_test(self) -> None:
        if hasattr(self, "test_system"):
            self.test_system.cancel()
        self._test_finished()

    def _test_finished(self) -> None:
        self.is_running = False
        self.start_btn_test.config(text="Start")
        self.start_btn_clean.config(text="Start")
        self.cycle_step_var.set("Idle")
        self.cycle_count_var.set("")
        self._enable_manual_controls()

    # Backwards compatibility
    def stop_test(self) -> None:
        self.cancel_test()
    def calibrate(self) -> None:
        win = tk.Toplevel(self)
        try:
            win.transient(self)
            win.wait_visibility()
            win.focus_set()
        except Exception as e:
            print("Calibration window focus error:", e)
        win.title("Calibration")

        bw_var = tk.DoubleVar(value=self.module.pressure_offset_bw)
        in_var = tk.DoubleVar(value=self.module.pressure_offset_in)
        temp_var = tk.DoubleVar(value=self.module.temp_offset)

        tk.Label(win, text="BW Pressure Offset").grid(row=0, column=0, sticky="w")
        NumericEntry(win, textvariable=bw_var, width=8, allow_negative=True).grid(row=0, column=1)
        tk.Label(win, text="Influent Pressure Offset").grid(row=1, column=0, sticky="w")
        NumericEntry(win, textvariable=in_var, width=8, allow_negative=True).grid(row=1, column=1)
        tk.Label(win, text="Temp Offset").grid(row=2, column=0, sticky="w")
        NumericEntry(win, textvariable=temp_var, width=8, allow_negative=True).grid(row=2, column=1)

        def apply() -> None:
            self.module.apply_offsets(
                pressure_bw=bw_var.get(),
                pressure_in=in_var.get(),
                temperature=temp_var.get(),
            )
            win.destroy()

        tk.Button(win, text="Apply", command=apply).grid(row=3, column=0, columnspan=2, pady=5)

        self.wait_window(win)

    def _read_sensors(self) -> None:
        """Read sensors once and store the values."""
        weight = self.module.read_scale(0)
        bw_weight = self.module.read_scale(1)
        pressure_bw = self.module.read_pressure(1)
        pressure_raw = self.module.read_pressure(2)
        temp = self.module.read_rtd(0)

        with self._sensor_lock:
            self.latest_weight = weight
            self.latest_bw_weight = bw_weight
            self.latest_pressure_bw = pressure_bw
            self.latest_pressure_raw = pressure_raw
            self.latest_temp = temp

    def _sensor_worker(self) -> None:
        """Continuously poll sensors in a background thread."""
        while not self._stop_event.is_set():
            self._read_sensors()
            time.sleep(1)

    @staticmethod
    def _strip_weight(text: str) -> str:
        """Return the numeric portion of a scale reading without sign or units."""
        match = re.search(r"[+-]?([0-9]*\.?[0-9]+)", text)
        return match.group(1) if match else text.strip()

    def update_data(self) -> None:
        """Refresh displayed values using the latest sensor readings."""
        if not self.winfo_exists():
            return
        with self._sensor_lock:
            weight = self.latest_weight
            bw_weight = self.latest_bw_weight
            pressure_bw = self.latest_pressure_bw
            pressure_raw = self.latest_pressure_raw
            temp = self.latest_temp
        # Strip units and sign for the sensor labels
        clean_w = self._strip_weight(weight)
        clean_bw = self._strip_weight(bw_weight)
        self.weight_var.set(clean_w)
        self.backwash_weight_var.set(clean_bw)
        self.pressure_bw_var.set(f"{pressure_bw:.2f}")
        self.pressure_raw_var.set(f"{pressure_raw:.2f}")
        self.temp_var.set(f"{temp:.2f}")

        for pfd in self.pfds.values():
            pfd["canvas"].itemconfig(pfd["pi1_text"], text=f"{self.pressure_bw_var.get()} PSI")
            pfd["canvas"].itemconfig(pfd["pi2_text"], text=f"{self.pressure_raw_var.get()} PSI")
            pfd["canvas"].itemconfig(pfd["te_text"], text=f"{self.temp_var.get()} C")
            # Display raw weight values (with units) on the process diagram
            pfd["canvas"].itemconfig(pfd["effluent_weight_text"], text=weight)
            pfd["canvas"].itemconfig(pfd["backwash_weight_text"], text=bw_weight)

        self._update_lines()
        self.after(1000, self.update_data)

    def _show_control_narrative(self) -> None:
        """Open a window displaying the control narrative documentation."""
        win = tk.Toplevel(self)
        try:
            win.transient(self)
            win.focus_set()
        except Exception:
            pass
        win.title("Control Narrative")
        path = os.path.join(os.path.dirname(__file__), "..", "resources", "CONTROL_NARRATIVE.md")
        try:
            with open(path, "r", encoding="utf-8") as fh:
                text = fh.read()
        except Exception:
            text = "Control narrative not found."
        txt = scrolledtext.ScrolledText(win, wrap="word", width=80, height=30)
        txt.insert("1.0", text)
        txt.configure(state="disabled")
        txt.pack(fill="both", expand=True)
        tk.Button(win, text="Close", command=win.destroy).pack(pady=5)
        self.wait_window(win)

    def _confirm_exit(self) -> None:
        """Ask the user to confirm before closing the application."""
        if messagebox.askokcancel("Quit", "Are you sure you want to exit?"):
            self.destroy()

    def destroy(self) -> None:
        """Stop background threads and close the GUI."""
        if hasattr(self, "_stop_event"):
            self._stop_event.set()
        if hasattr(self, "_worker"):
            self._worker.join(timeout=1)
        super().destroy()
