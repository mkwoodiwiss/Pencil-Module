"""Tkinter based HMI for the Pencil Module."""

import os
import tkinter as tk

from .automation import FiltrationConfig, FiltrationTestSystem
from .hardware import PencilModule


class HMI(tk.Tk):
    """Simple Tkinter graphical interface with a process diagram."""

    def __init__(self, module: PencilModule) -> None:
        super().__init__()
        self.module = module
        self.title("Pencil Module")
        self.geometry("800x480")
        self.update_idletasks()

        self.weight_var = tk.StringVar()
        self.backwash_weight_var = tk.StringVar()
        self.pressure_bw_var = tk.StringVar()
        self.pressure_raw_var = tk.StringVar()
        self.temp_var = tk.StringVar()

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
        self.is_running = False
        self.prime_frame = None
        self.prime_stage = 0

        self._create_pfd()

        self.area = tk.Frame(self)
        self.area.pack(fill="both", expand=True, padx=5, pady=5)

        settings = tk.LabelFrame(self.area, text="Settings")
        settings.pack(side="left", padx=5, pady=5, anchor="n")
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
        tk.Label(info, text="Filtrate Weight:").grid(row=0, column=0, sticky="w")
        tk.Label(info, textvariable=self.weight_var, font=("Arial", 12)).grid(row=0, column=1, sticky="w")
        tk.Label(info, text="Backwash Weight:").grid(row=1, column=0, sticky="w")
        tk.Label(info, textvariable=self.backwash_weight_var, font=("Arial", 12)).grid(row=1, column=1, sticky="w")
        tk.Label(info, text="BW Pressure:").grid(row=2, column=0, sticky="w")
        tk.Label(info, textvariable=self.pressure_bw_var, font=("Arial", 12)).grid(row=2, column=1, sticky="w")
        tk.Label(info, text="Influent Pressure:").grid(row=3, column=0, sticky="w")
        tk.Label(info, textvariable=self.pressure_raw_var, font=("Arial", 12)).grid(row=3, column=1, sticky="w")
        tk.Label(info, text="Temperature:").grid(row=4, column=0, sticky="w")
        tk.Label(info, textvariable=self.temp_var, font=("Arial", 12)).grid(row=4, column=1, sticky="w")

        self.start_btn = tk.Button(right_col, text="Start", command=self._toggle_test, font=("Arial", 12), width=8, height=2)
        self.start_btn.pack(pady=10)

        tk.Label(settings, text="Filtration Target").grid(row=0, column=0, sticky="w")
        tk.Entry(settings, textvariable=self.filt_target_weight_var, width=7).grid(row=0, column=1)
        tk.Checkbutton(settings, text="g", variable=self.filt_use_weight_var, command=self._toggle_filt_weight).grid(row=0, column=2, sticky="w")
        tk.Entry(settings, textvariable=self.filt_target_time_var, width=7).grid(row=0, column=3)
        tk.Checkbutton(settings, text="s", variable=self.filt_use_time_var, command=self._toggle_filt_time).grid(row=0, column=4, sticky="w")

        tk.Label(settings, text="Backwash Target").grid(row=1, column=0, sticky="w")
        tk.Entry(settings, textvariable=self.bw_target_weight_var, width=7).grid(row=1, column=1)
        tk.Checkbutton(settings, text="g", variable=self.bw_use_weight_var, command=self._toggle_bw_weight).grid(row=1, column=2, sticky="w")
        tk.Entry(settings, textvariable=self.bw_target_time_var, width=7).grid(row=1, column=3)
        tk.Checkbutton(settings, text="s", variable=self.bw_use_time_var, command=self._toggle_bw_time).grid(row=1, column=4, sticky="w")

        tk.Label(settings, text="Refill Time").grid(row=2, column=0, sticky="w")
        tk.Entry(settings, textvariable=self.refill_time_var, width=7).grid(row=2, column=1)

        tk.Label(settings, text="Repeat Count").grid(row=3, column=0, sticky="w")
        tk.Entry(settings, textvariable=self.repeat_count_var, width=7).grid(row=3, column=1)

        tk.Label(settings, text="Sample Time").grid(row=4, column=0, sticky="w")
        tk.Entry(settings, textvariable=self.sample_time_var, width=7).grid(row=4, column=1)

        tk.Label(settings, text="Project Name").grid(row=5, column=0, sticky="w")
        tk.Entry(settings, textvariable=self.project_name_var, width=7).grid(row=5, column=1)

        btn_frame = tk.Frame(settings)
        btn_frame.grid(row=6, column=0, columnspan=5, pady=8, sticky="ew")
        btn_frame.columnconfigure((0, 1, 2), weight=1)

        tk.Button(btn_frame, text="Calibrate", command=self.calibrate).grid(row=0, column=0, padx=5, sticky="ew")
        tk.Button(btn_frame, text="Tare EFL", command=lambda: self.module.zero_scale(0)).grid(row=0, column=1, padx=5, sticky="ew")
        tk.Button(btn_frame, text="Tare BW", command=lambda: self.module.zero_scale(1)).grid(row=0, column=2, padx=5, sticky="ew")

        self.update_data()

    def _create_pfd(self) -> None:
        self.canvas = tk.Canvas(self, width=780, height=190, bg="white")
        self.canvas.pack(pady=5)

        self.canvas.create_rectangle(75, 30, 125, 80, fill="lightblue")
        self.canvas.create_text(100, 20, text="BW water")
        self.pi1_text = self.canvas.create_text(100, 70, text="-- PSI")

        self.canvas.create_rectangle(75, 110, 125, 160, fill="lightblue")
        self.canvas.create_text(100, 100, text="Influent water")
        self.pi2_text = self.canvas.create_text(100, 150, text="-- PSI")

        self.canvas.create_rectangle(265, 45, 445, 65, fill="lightgray")
        self.canvas.create_rectangle(275, 65, 290, 85, fill="lightgray")
        self.canvas.create_rectangle(420, 65, 435, 85, fill="lightgray")
        self.canvas.create_text(355, 35, text="Mini-module")

        self.canvas.create_rectangle(565, 30, 615, 80, fill="lightblue")
        self.canvas.create_text(590, 20, text="Effluent")
        self.canvas.create_text(590, 70, text="-- g")

        self.canvas.create_rectangle(565, 120, 615, 170, fill="lightblue")
        self.canvas.create_text(590, 110, text="Backwash")
        self.canvas.create_text(590, 160, text="-- g")

        self.canvas.create_rectangle(665, 75, 715, 125, fill="lightblue")
        self.canvas.create_text(690, 65, text="Drain")

        self.lines = {}
        self.valve_labels = {}
        self.valve_to_lines = {
            0: [0],
            1: [1],
            2: [2, 'v3_vert1', 'v3_vert2'],
            3: [3, 'v3_vert2'],
            4: [4],
        }

        self.lines[0] = self.canvas.create_line(125, 55, 265, 55, arrow="last", fill="gray", width=2)
        self.valve_labels['V1'] = self.canvas.create_text(195, 55, text="V1")

        self.lines[1] = self.canvas.create_line(125, 125, 290, 125, fill="gray", width=2)
        self.lines['v2_vert'] = self.canvas.create_line(282.5, 125, 282.5, 85, arrow="last", fill="gray", width=2)
        self.valve_to_lines[1].append('v2_vert')
        self.valve_labels['V2'] = self.canvas.create_text(195, 125, text="V2")
        self.canvas.create_rectangle(290, 117.5, 340, 132.5, fill="white", outline="black")
        self.te_text = self.canvas.create_text(315, 125, text="-- C")

        self.lines[2] = self.canvas.create_line(427.5, 145, 565, 145, arrow="last", fill="gray", width=2)
        self.lines['v3_vert1'] = self.canvas.create_line(427.5, 100, 427.5, 145, fill="gray", width=2)
        self.lines['v3_vert2'] = self.canvas.create_line(427.5, 85, 427.5, 100, fill="gray", width=2)
        self.valve_to_lines[2].extend(['v3_vert1', 'v3_vert2'])
        self.valve_labels['V3'] = self.canvas.create_text(505, 145, text="V3")

        self.lines[3] = self.canvas.create_line(427.5, 100, 665, 100, arrow="last", fill="gray", width=2)
        self.valve_labels['V4'] = self.canvas.create_text(505, 100, text="V4")

        self.lines[4] = self.canvas.create_line(445, 55, 565, 55, arrow="last", fill="gray", width=2)
        self.valve_labels['V5'] = self.canvas.create_text(505, 55, text="V5")

        self.solenoid_states = [False] * 5
        self.solenoid_buttons = []
        valve_keys = ['V1', 'V2', 'V3', 'V4', 'V5']
        for i in range(5):
            btn = tk.Button(self.canvas, text=f"V{i+1}", width=3, bg="lightgray", command=lambda ch=i: self.toggle_solenoid(ch))
            x, y = self.canvas.coords(self.valve_labels[valve_keys[i]])
            self.canvas.create_window(x, y, window=btn)
            self.solenoid_buttons.append(btn)

        self.prime_btn = tk.Button(self.canvas, text="Prime", command=self.prime)
        self.canvas.create_window(355, 90, window=self.prime_btn)

    def _update_lines(self) -> None:
        for idx, line_ids in self.valve_to_lines.items():
            for lid in line_ids:
                if lid == 'v3_vert2':
                    continue
                color = "green" if self.solenoid_states[idx] else "gray"
                self.canvas.itemconfig(self.lines[lid], fill=color)
        color = "green" if self.solenoid_states[2] or self.solenoid_states[3] else "gray"
        self.canvas.itemconfig(self.lines['v3_vert2'], fill=color)

    def toggle_solenoid(self, channel: int) -> None:
        state = not self.solenoid_states[channel]
        self.solenoid_states[channel] = state
        self.module.set_solenoid(channel + 1, state)
        bg = "red" if state else "lightgray"
        self.solenoid_buttons[channel].config(bg=bg)
        self._update_lines()

    def _set_valves(self, state: bool, *valves: int) -> None:
        for v in valves:
            idx = v - 1
            self.solenoid_states[idx] = state
            self.module.set_solenoid(v, state)
            bg = "red" if state else "lightgray"
            self.solenoid_buttons[idx].config(bg=bg)
        self._update_lines()

    def _open_valves(self, *valves: int) -> None:
        self._set_valves(True, *valves)

    def _close_valves(self, *valves: int) -> None:
        self._set_valves(False, *valves)

    def _close_all_valves(self) -> None:
        self._close_valves(1, 2, 3, 4, 5)

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
            self.stop_test()
            self.is_running = False
            self.start_btn.config(text="Start")
        else:
            self.is_running = True
            self.start_btn.config(text="Stop")
            self.start_test()
            self.is_running = False
            self.start_btn.config(text="Start")

    def start_test(self) -> None:
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
        self.test_system = FiltrationTestSystem(self.module, config)
        self.test_system.start_test()

    def stop_test(self) -> None:
        if hasattr(self, "test_system"):
            self.test_system.stop_test()

    def calibrate(self) -> None:
        win = tk.Toplevel(self)
        win.title("Calibration")

        bw_var = tk.DoubleVar(value=self.module.pressure_offset_bw)
        in_var = tk.DoubleVar(value=self.module.pressure_offset_in)
        temp_var = tk.DoubleVar(value=self.module.temp_offset)

        tk.Label(win, text="BW Pressure Offset").grid(row=0, column=0, sticky="w")
        tk.Entry(win, textvariable=bw_var, width=8).grid(row=0, column=1)
        tk.Label(win, text="Influent Pressure Offset").grid(row=1, column=0, sticky="w")
        tk.Entry(win, textvariable=in_var, width=8).grid(row=1, column=1)
        tk.Label(win, text="Temp Offset").grid(row=2, column=0, sticky="w")
        tk.Entry(win, textvariable=temp_var, width=8).grid(row=2, column=1)

        def apply() -> None:
            self.module.apply_offsets(
                pressure_bw=bw_var.get(),
                pressure_in=in_var.get(),
                temperature=temp_var.get(),
            )
            win.destroy()

        tk.Button(win, text="Apply", command=apply).grid(row=3, column=0, columnspan=2, pady=5)

    def update_data(self) -> None:
        self.weight_var.set(self.module.read_scale(0))
        self.backwash_weight_var.set(self.module.read_scale(1))
        self.pressure_bw_var.set(f"{self.module.read_pressure(0):.2f}")
        self.pressure_raw_var.set(f"{self.module.read_pressure(1):.2f}")
        self.temp_var.set(f"{self.module.read_rtd(0):.2f}")

        self.canvas.itemconfig(self.pi1_text, text=f"{self.pressure_bw_var.get()} PSI")
        self.canvas.itemconfig(self.pi2_text, text=f"{self.pressure_raw_var.get()} PSI")
        self.canvas.itemconfig(self.te_text, text=f"{self.temp_var.get()} C")

        self._update_lines()
        self.after(1000, self.update_data)
