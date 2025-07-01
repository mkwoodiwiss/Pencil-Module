"""High level controller for the Pencil Module.

This module ties together the hardware interfaces, automation
logic and a Tkinter based HMI for a small filtration test rig. It
is primarily intended to run on a Raspberry Pi 5 equipped with:

* Sequent Microsystems **8 Relay** HAT controlling the solenoid valves.
* Sequent Microsystems **Multi IO** HAT providing pressure and RTD inputs.
* Two weight scales attached via a USB serial connection.
* A 7" Raspberry Pi touch screen which hosts the HMI.

The code is structured in the following way:

``PencilModule``
    Low level wrapper around the hardware boards.

``FiltrationTestSystem``
    Runs automatic prime, filtration and backwash cycles using a
    :class:`FiltrationConfig` data object for parameters.

``HMI``
    Tkinter based user interface that exposes manual controls and
    buttons to launch automated tests.

The :func:`main` function instantiates these pieces and starts the GUI.
"""

import tkinter as tk
import re
import serial
import time
import csv
import os
from dataclasses import dataclass, asdict
from typing import Optional

# Third party drivers for the Sequent Microsystems boards.
# These names follow the vendor examples and must be installed on the Pi.
# They are not available in this environment, so imports will fail here
# if the packages are missing.
try:
    import relay8   # type: ignore
    import multiio  # type: ignore
except ModuleNotFoundError:
    relay8 = None  # placeholders to allow running type checks
    multiio = None


class PencilModule:
    """Interface to the hardware boards.

    This class provides a very small abstraction layer around the
    vendor supplied libraries. It exposes methods that the rest of
    the application can use without directly depending on the
    external packages. When running the unit tests the same API is
    implemented by :class:`tests.test_interfaces.SimulatedPencilModule`.
    """

    def __init__(
        self,
        relay_stack: int = 0,
        io_stack: int = 0,
        port: str = "/dev/ttyUSB0",
        baud: int = 9600,
    ) -> None:
        # Serial connection to the pair of scales
        self.ser = serial.Serial(port, baud, timeout=1)
        # Interfaces to the relay and IO boards. When the vendor modules are
        # not installed these remain ``None`` so the rest of the code can
        # still be imported and type checked.
        self.relay = relay8.Relay8(stack=relay_stack) if relay8 else None
        self.io = multiio.MultiIO(stack=io_stack) if multiio else None
        # Optional calibration offsets applied to readings. Pressure is tracked
        # separately for each sensor so the user can calibrate the backwash and
        # influent inputs individually.
        self.pressure_offset_bw = 0.0
        self.pressure_offset_in = 0.0
        self.temp_offset = 0.0

    def read_pressure(self, channel: int) -> float:
        """Return pressure value from ADC channel."""
        # When running on the real hardware ``self.io`` provides the
        # analog pressure input. The unit tests leave ``self.io`` as
        # ``None`` and return a deterministic value instead.
        offset = self.pressure_offset_bw if channel == 0 else self.pressure_offset_in
        if self.io:
            return self.io.get_adc(channel) + offset
        return 0.0 + offset

    def read_rtd(self, channel: int) -> float:
        """Return temperature value from RTD channel."""
        # Similar to :meth:`read_pressure` this falls back to a fixed
        # value when no hardware is available.
        if self.io:
            return self.io.get_rtd(channel) + self.temp_offset
        return 0.0 + self.temp_offset

    def set_solenoid(self, relay: int, state: bool) -> None:
        """Activate or deactivate a solenoid."""
        if self.relay:
            if state:
                self.relay.on(relay)
            else:
                self.relay.off(relay)

    def zero_scales(self) -> None:
        """Issue a zeroing command for both scales."""
        self.ser.write(b"Z\r\n")

    def zero_scale(self, channel: int) -> None:
        """Zero an individual scale."""
        cmd = b"Z\r\n" if channel == 0 else b"Q\r\n"
        self.ser.write(cmd)

    def apply_offsets(
        self,
        pressure_bw: float = 0.0,
        pressure_in: float = 0.0,
        temperature: float = 0.0,
    ) -> None:
        """Store calibration offsets for later readings."""
        # Offsets are added to raw sensor data to allow simple field
        # calibration via the GUI.
        self.pressure_offset_bw = pressure_bw
        self.pressure_offset_in = pressure_in
        self.temp_offset = temperature

    def read_scale(self, channel: int = 0) -> str:
        """Query one of the serial scales and return the weight string."""
        # Each scale is queried with a short command. The response is
        # parsed and normalised into a human readable string. When no
        # matching pattern is found ``"--"`` is returned so the GUI can
        # display a placeholder value.
        cmd = b"P\r\n" if channel == 0 else b"S\r\n"
        self.ser.write(cmd)
        time.sleep(0.1)
        response = self.ser.read_until(b"\r\n").decode("ascii", "ignore").strip()
        match = re.search(r"([+-]?)\s*(\d+\.\d+)\s*(\w)", response)
        if match:
            sign, weight, unit = match.groups()
            return f"{sign}{weight} {unit}"
        return "--"


@dataclass
class FiltrationConfig:
    """Configuration for an automated filtration test.

    All numeric values are expressed in seconds, millilitres or
    whatever units the connected sensors report. The configuration is
    serialised to a CSV file at the start of each test run so the
    parameters used for data logging are preserved.
    """

    filtration_target: float
    filtration_by_volume: bool
    backwash_target: float
    backwash_by_volume: bool
    refill_time: float
    repeat_count: int
    sample_time: float
    project_name: str
    pressure_offset: float = 0.0
    temp_offset: float = 0.0


class FiltrationTestSystem:
    """Run automated filtration cycles based on a FiltrationConfig."""

    # Relay assignments
    INFLUENT_SUPPLY = 1
    BACKWASH_SUPPLY = 2
    EFFLUENT_VALVE = 3
    BACKWASH_EFFLUENT = 4
    INFLUENT_DRAIN = 5

    def __init__(self, module: PencilModule, config: FiltrationConfig, log_dir: str = "logs"):
        self.module = module
        self.config = config
        self.log_dir = log_dir
        self.data_writer: Optional[csv.writer] = None
        self.data_file: Optional[object] = None

    def _parse_weight(self, text: str) -> float:
        """Extract the numeric portion from a scale string."""
        match = re.search(r"([+-]?\d+\.\d+)", text)
        return float(match.group(1)) if match else 0.0

    def _log_row(self) -> None:
        """Write the current sensor readings to the data CSV."""
        if not self.data_writer:
            return
        row = [
            time.time(),
            self.module.read_rtd(0),
            self.module.read_pressure(1),
            self.module.read_pressure(0),
            self._parse_weight(self.module.read_scale(0)),
            self._parse_weight(self.module.read_scale(1)),
        ]
        self.data_writer.writerow(row)

    def _open(self, *valves: int) -> None:
        """Convenience helper to open multiple solenoids."""
        for v in valves:
            self.module.set_solenoid(v, True)

    def _close(self, *valves: int) -> None:
        """Convenience helper to close multiple solenoids."""
        for v in valves:
            self.module.set_solenoid(v, False)

    def prime(self, duration: float = 1.0) -> None:
        """Simple priming routine.

        Opens the influent supply valve for a short time to fill the
        lines. This can also be triggered manually from the HMI.
        """
        self._open(self.INFLUENT_SUPPLY)
        time.sleep(duration)
        self._close(self.INFLUENT_SUPPLY)

    def start_test(self) -> None:
        """Run the configured number of filtration/backwash cycles."""
        # Create log files for both the raw data and the configuration
        os.makedirs(self.log_dir, exist_ok=True)
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        base = os.path.join(self.log_dir, f"{self.config.project_name}_{timestamp}")

        self.data_file = open(base + "_data.csv", "w", newline="")
        self.data_writer = csv.writer(self.data_file)
        self.data_writer.writerow(
            [
                "timestamp",
                "influent_temp",
                "backwash_pressure",
                "influent_pressure",
                "effluent_weight",
                "backwash_weight",
            ]
        )

        with open(base + "_settings.csv", "w", newline="") as sfile:
            writer = csv.writer(sfile)
            for k, v in asdict(self.config).items():
                writer.writerow([k, v])

        self.module.apply_offsets(
            pressure_bw=self.config.pressure_offset,
            pressure_in=self.config.pressure_offset,
            temperature=self.config.temp_offset,
        )
        self.module.zero_scales()

        for _ in range(self.config.repeat_count):
            # Refill phase
            self._open(self.INFLUENT_SUPPLY, self.INFLUENT_DRAIN)
            start = time.time()
            while time.time() - start < self.config.refill_time:
                self._log_row()
                time.sleep(self.config.sample_time)
            self._close(self.INFLUENT_SUPPLY, self.INFLUENT_DRAIN)

            # Filtration phase
            self._open(self.INFLUENT_SUPPLY, self.EFFLUENT_VALVE)
            start = time.time()
            start_w = self._parse_weight(self.module.read_scale(0))
            while True:
                self._log_row()
                if self.config.filtration_by_volume:
                    vol = self._parse_weight(self.module.read_scale(0)) - start_w
                    if vol >= self.config.filtration_target:
                        break
                else:
                    if time.time() - start >= self.config.filtration_target:
                        break
                time.sleep(self.config.sample_time)
            self._close(self.INFLUENT_SUPPLY, self.EFFLUENT_VALVE)

            # Backwash phase
            self._open(self.BACKWASH_SUPPLY, self.BACKWASH_EFFLUENT)
            start = time.time()
            start_w = self._parse_weight(self.module.read_scale(1))
            while True:
                self._log_row()
                if self.config.backwash_by_volume:
                    vol = self._parse_weight(self.module.read_scale(1)) - start_w
                    if vol >= self.config.backwash_target:
                        break
                else:
                    if time.time() - start >= self.config.backwash_target:
                        break
                time.sleep(self.config.sample_time)
            self._close(self.BACKWASH_SUPPLY, self.BACKWASH_EFFLUENT)

        self.stop_test()

    def stop_test(self) -> None:
        """Stop all hardware and close any open log files."""
        self._close(
            self.INFLUENT_SUPPLY,
            self.BACKWASH_SUPPLY,
            self.EFFLUENT_VALVE,
            self.BACKWASH_EFFLUENT,
            self.INFLUENT_DRAIN,
        )
        if self.data_file:
            self.data_file.close()
            self.data_file = None
        self.data_writer = None

class HMI(tk.Tk):
    """Simple Tkinter graphical interface with a process diagram.

    The HMI polls the :class:`PencilModule` for live data and provides
    buttons for manual valve control as well as starting the automated
    test sequence. It intentionally avoids advanced GUI frameworks so
    it can run easily on the Pi's builtin touch screen.
    """

    def __init__(self, module: PencilModule):
        super().__init__()
        self.module = module
        self.title("Pencil Module")
        # Use the full 7" touch screen resolution
        self.geometry("800x480")

        # Readout variables
        self.weight_var = tk.StringVar()
        self.backwash_weight_var = tk.StringVar()
        self.pressure_bw_var = tk.StringVar()
        self.pressure_raw_var = tk.StringVar()
        self.temp_var = tk.StringVar()

        # Configuration variables
        # Filtration target settings
        self.filt_target_weight_var = tk.DoubleVar(value=1.0)
        self.filt_target_time_var = tk.DoubleVar(value=1.0)
        self.filt_use_weight_var = tk.BooleanVar(value=False)
        self.filt_use_time_var = tk.BooleanVar(value=True)
        # Backwash target settings
        self.bw_target_weight_var = tk.DoubleVar(value=1.0)
        self.bw_target_time_var = tk.DoubleVar(value=1.0)
        self.bw_use_weight_var = tk.BooleanVar(value=False)
        self.bw_use_time_var = tk.BooleanVar(value=True)
        self.refill_time_var = tk.DoubleVar(value=0.5)
        self.repeat_count_var = tk.IntVar(value=1)
        self.sample_time_var = tk.DoubleVar(value=0.1)
        self.project_name_var = tk.StringVar(value="demo")
        self.is_running = False

        self._create_pfd()

        area = tk.Frame(self)
        area.pack(fill="both", expand=True, padx=5, pady=5)

        settings = tk.LabelFrame(area, text="Settings")
        settings.pack(side="left", fill="y", padx=5, pady=5)

        centre = tk.Frame(area)
        centre.pack(side="left", expand=True)
        self.start_btn = tk.Button(centre, text="Start", command=self._toggle_test)
        self.start_btn.pack(pady=5)

        tk.Label(settings, text="Filtration Target").grid(row=0, column=0, sticky="w")
        tk.Entry(settings, textvariable=self.filt_target_weight_var, width=7).grid(row=0, column=1)
        tk.Checkbutton(
            settings,
            text="g",
            variable=self.filt_use_weight_var,
            command=self._toggle_filt_weight,
        ).grid(row=0, column=2, sticky="w")
        tk.Entry(settings, textvariable=self.filt_target_time_var, width=7).grid(row=0, column=3)
        tk.Checkbutton(
            settings,
            text="s",
            variable=self.filt_use_time_var,
            command=self._toggle_filt_time,
        ).grid(row=0, column=4, sticky="w")

        tk.Label(settings, text="Backwash Target").grid(row=1, column=0, sticky="w")
        tk.Entry(settings, textvariable=self.bw_target_weight_var, width=7).grid(row=1, column=1)
        tk.Checkbutton(
            settings,
            text="g",
            variable=self.bw_use_weight_var,
            command=self._toggle_bw_weight,
        ).grid(row=1, column=2, sticky="w")
        tk.Entry(settings, textvariable=self.bw_target_time_var, width=7).grid(row=1, column=3)
        tk.Checkbutton(
            settings,
            text="s",
            variable=self.bw_use_time_var,
            command=self._toggle_bw_time,
        ).grid(row=1, column=4, sticky="w")

        tk.Label(settings, text="Refill Time").grid(row=2, column=0, sticky="w")
        tk.Entry(settings, textvariable=self.refill_time_var, width=7).grid(row=2, column=1)

        tk.Label(settings, text="Repeat Count").grid(row=3, column=0, sticky="w")
        tk.Entry(settings, textvariable=self.repeat_count_var, width=7).grid(row=3, column=1)

        tk.Label(settings, text="Sample Time").grid(row=4, column=0, sticky="w")
        tk.Entry(settings, textvariable=self.sample_time_var, width=7).grid(row=4, column=1)

        tk.Label(settings, text="Project Name").grid(row=5, column=0, sticky="w")
        tk.Entry(settings, textvariable=self.project_name_var, width=7).grid(row=5, column=1)

        tk.Button(settings, text="Calibrate", command=self.calibrate).grid(row=6, column=0, columnspan=3, pady=4)
        tk.Button(
            settings,
            text="Tare EFL",
            command=lambda: self.module.zero_scale(0),
        ).grid(row=7, column=0, columnspan=3, pady=2)
        tk.Button(
            settings,
            text="Tare BW",
            command=lambda: self.module.zero_scale(1),
        ).grid(row=8, column=0, columnspan=3, pady=2)

        info = tk.LabelFrame(area, text="Sensors")
        info.pack(side="left", fill="y", padx=5, pady=5)
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

        self.update_data()

    def _create_pfd(self) -> None:
        """Draw a process flow diagram that visually resembles the reference image."""
        self.canvas = tk.Canvas(self, width=780, height=190, bg="white")
        self.canvas.pack(pady=5)

        # === LEFT: BW and Influent Water Tanks ===
        self.canvas.create_rectangle(75, 30, 125, 80, fill="lightblue")  # BW Water
        self.canvas.create_text(100, 20, text="BW water")
        self.pi1_text = self.canvas.create_text(100, 70, text="-- PSI")  # PI1 value

        self.canvas.create_rectangle(75, 110, 125, 160, fill="lightblue")  # Influent Water
        self.canvas.create_text(100, 100, text="Influent water")
        self.pi2_text = self.canvas.create_text(100, 150, text="-- PSI")  # PI2 value

        # === Mini-module in Center ===
        self.canvas.create_rectangle(265, 45, 445, 65, fill="lightgray")  # Mini-module
        self.canvas.create_rectangle(275, 65, 290, 85, fill="lightgray")
        self.canvas.create_rectangle(420, 65, 435, 85, fill="lightgray")
        self.canvas.create_text(355, 35, text="Mini-module")

        # === RIGHT: Destinations ===
        # Effluent (top right)
        self.canvas.create_rectangle(565, 30, 615, 80, fill="lightblue")  # WeightF
        self.canvas.create_text(590, 20, text="Effluent")
        self.canvas.create_text(590, 70, text="-- g")

        # Backwash
        self.canvas.create_rectangle(565, 120, 615, 170, fill="lightblue")  # WeightB
        self.canvas.create_text(590, 110, text="Backwash")
        self.canvas.create_text(590, 160, text="-- g")

        # Drain
        self.canvas.create_rectangle(665, 75, 715, 125, fill="lightblue")  # Drainage
        self.canvas.create_text(690, 65, text="Drain")

        # === Flow Lines & Valves (gray initially) ===
        self.lines = {}
        self.valve_labels = {}

        # Map each valve to the lines it controls
        self.valve_to_lines = {
            0: [0],    # V1 controls line 0
            1: [1],    # V2 controls line 1 and the vertical line to module
            2: [2, 'v3_vert1', 'v3_vert2'],  # V3 controls line 2 and both vertical lines
            3: [3, 'v3_vert2'],     # V4 controls line 3 AND v3_vert2
            4: [4],    # V5 controls line 4
        }

        # From BW to Mini-module (V1)
        self.lines[0] = self.canvas.create_line(125, 55, 265, 55, arrow="last", fill="gray", width=2)
        self.valve_labels['V1'] = self.canvas.create_text(195, 55, text="V1")

        # From Influent to Mini-module (V2)
        self.lines[1] = self.canvas.create_line(125, 125, 290, 125, fill="gray", width=2)
        self.lines['v2_vert'] = self.canvas.create_line(282.5, 125, 282.5, 85, arrow="last", fill="gray", width=2)
        self.valve_to_lines[1].append('v2_vert')
        self.valve_labels['V2'] = self.canvas.create_text(195, 125, text="V2")
        self.canvas.create_rectangle(290, 117.5, 340, 132.5, fill="white", outline="black")
        self.te_text = self.canvas.create_text(315, 125, text="-- C")

        # Mini-module to Backwash (V3)
        self.lines[2] = self.canvas.create_line(427.5, 145, 565, 145, arrow="last", fill="gray", width=2)
        self.lines['v3_vert1'] = self.canvas.create_line(427.5, 100, 427.5, 145, fill="gray", width=2)
        self.lines['v3_vert2'] = self.canvas.create_line(427.5, 85, 427.5, 100, fill="gray", width=2)
        self.valve_to_lines[2].extend(['v3_vert1', 'v3_vert2'])
        self.valve_labels['V3'] = self.canvas.create_text(505, 145, text="V3")

        # Mini-module to Drainage (V4)
        self.lines[3] = self.canvas.create_line(427.5, 100, 665, 100, arrow="last", fill="gray", width=2)
        self.valve_labels['V4'] = self.canvas.create_text(505, 100, text="V4")

        # Mini-module to Effluent (V5)
        self.lines[4] = self.canvas.create_line(445, 55, 565, 55, arrow="last", fill="gray", width=2)
        self.valve_labels['V5'] = self.canvas.create_text(505, 55, text="V5")

        # === Solenoid Buttons ===
        self.solenoid_states = [False] * 5
        self.solenoid_buttons = []
        valve_keys = ['V1', 'V2', 'V3', 'V4', 'V5']
        for i in range(5):
            btn = tk.Button(
                self.canvas,
                text=f"V{i+1}",
                width=3,
                command=lambda ch=i: self.toggle_solenoid(ch),
            )
            x, y = self.canvas.coords(self.valve_labels[valve_keys[i]])
            self.canvas.create_window(x, y, window=btn)
            self.solenoid_buttons.append(btn)

        self.prime_btn = tk.Button(self.canvas, text="Prime", command=self.prime)
        self.canvas.create_window(355, 180, window=self.prime_btn)

    def _update_lines(self) -> None:
        # Update all lines except v3_vert2 normally
        for idx, line_ids in self.valve_to_lines.items():
            for lid in line_ids:
                # Special handling for v3_vert2
                if lid == 'v3_vert2':
                    continue  # We'll handle this after the loop
                color = "green" if self.solenoid_states[idx] else "gray"
                self.canvas.itemconfig(self.lines[lid], fill=color)
        # Now handle v3_vert2: green if V3 or V4 is ON
        color = "green" if self.solenoid_states[2] or self.solenoid_states[3] else "gray"
        self.canvas.itemconfig(self.lines['v3_vert2'], fill=color)

    def toggle_solenoid(self, channel: int) -> None:
        state = not self.solenoid_states[channel]
        self.solenoid_states[channel] = state
        self.module.set_solenoid(channel + 1, state)
        bg = "red" if state else self.solenoid_buttons[channel].master.cget("bg")
        self.solenoid_buttons[channel].config(bg=bg)
        self._update_lines()

    def prime(self) -> None:
        """Activate the priming routine using a temporary test system."""
        FiltrationTestSystem(
            self.module,
            FiltrationConfig(0, False, 0, False, 0, 0, 1, "prime")
        ).prime()

    # === Checkbox toggle helpers ===
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
        """Start or stop the test depending on current state."""
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
        """Begin an automated cycle using the stored configuration."""
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
        """Stop the currently running test."""
        if hasattr(self, "test_system"):
            self.test_system.stop_test()

    def calibrate(self) -> None:
        """Open a small dialog to input calibration offsets."""
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

        def apply():
            self.module.apply_offsets(
                pressure_bw=bw_var.get(),
                pressure_in=in_var.get(),
                temperature=temp_var.get(),
            )
            win.destroy()

        tk.Button(win, text="Apply", command=apply).grid(row=3, column=0, columnspan=2, pady=5)

    def update_data(self) -> None:
        """Refresh all displayed sensor values."""
        self.weight_var.set(self.module.read_scale(0))
        self.backwash_weight_var.set(self.module.read_scale(1))
        self.pressure_bw_var.set(f"{self.module.read_pressure(0):.2f}")
        self.pressure_raw_var.set(f"{self.module.read_pressure(1):.2f}")
        self.temp_var.set(f"{self.module.read_rtd(0):.2f}")

        # Update text on process diagram
        self.canvas.itemconfig(self.pi1_text, text=f"{self.pressure_bw_var.get()} PSI")
        self.canvas.itemconfig(self.pi2_text, text=f"{self.pressure_raw_var.get()} PSI")
        self.canvas.itemconfig(self.te_text, text=f"{self.temp_var.get()} C")

        self._update_lines()
        self.after(1000, self.update_data)


def main() -> None:
    """Entry point when running the module directly."""
    module = PencilModule()
    app = HMI(module)
    app.mainloop()


if __name__ == "__main__":
    main()
