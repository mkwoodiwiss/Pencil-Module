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
        # Optional calibration offsets applied to readings
        self.pressure_offset = 0.0
        self.temp_offset = 0.0

    def read_pressure(self, channel: int) -> float:
        """Return pressure value from ADC channel."""
        # When running on the real hardware ``self.io`` provides the
        # analog pressure input. The unit tests leave ``self.io`` as
        # ``None`` and return a deterministic value instead.
        if self.io:
            return self.io.get_adc(channel) + self.pressure_offset
        return 0.0 + self.pressure_offset

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

    def apply_offsets(self, pressure: float = 0.0, temperature: float = 0.0) -> None:
        """Store calibration offsets for later readings."""
        # Offsets are added to raw sensor data to allow simple field
        # calibration via the GUI.
        self.pressure_offset = pressure
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

        self.module.apply_offsets(self.config.pressure_offset, self.config.temp_offset)
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

        self._create_pfd()

        info = tk.Frame(self)
        info.pack(pady=5)
        # Slightly smaller fonts so all data fits the screen
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

        # Only five solenoids are used
        self.solenoid_states = [False] * 5
        self.solenoid_buttons = []
        btn_frame = tk.Frame(self)
        btn_frame.pack(pady=5)
        for i in range(5):
            btn = tk.Button(
                btn_frame,
                text=f"Sol {i+1} OFF",
                width=8,
                command=lambda ch=i: self.toggle_solenoid(ch),
            )
            btn.grid(row=i // 4, column=i % 4, padx=5, pady=2)
            self.solenoid_buttons.append(btn)

        control_frame = tk.Frame(self)
        control_frame.pack(pady=5)
        tk.Button(control_frame, text="Prime", command=self.prime).grid(row=0, column=0, padx=5)
        tk.Button(control_frame, text="Start", command=self.start_test).grid(row=0, column=1, padx=5)
        tk.Button(control_frame, text="Stop", command=self.stop_test).grid(row=0, column=2, padx=5)
        tk.Button(control_frame, text="Tare EFL", command=lambda: self.module.zero_scale(0)).grid(row=1, column=0, padx=5)
        tk.Button(control_frame, text="Tare BW", command=lambda: self.module.zero_scale(1)).grid(row=1, column=1, padx=5)
        tk.Button(control_frame, text="Calibrate", command=self.calibrate).grid(row=1, column=2, padx=5)

        self.update_data()

    def _create_pfd(self) -> None:
        """Draw a process flow diagram that visually resembles the reference image."""
        self.canvas = tk.Canvas(self, width=750, height=220, bg="white")
        self.canvas.pack(pady=5)

        # === LEFT: BW and Raw Water Tanks ===
        self.canvas.create_rectangle(30, 30, 80, 80, fill="lightblue")  # BW Water
        self.canvas.create_text(55, 20, text="BW water")
        self.pi1_text = self.canvas.create_text(55, 85, text="PI1: --")  # PI1 value
        self.canvas.create_text(55, 95, text="Air")

        self.canvas.create_rectangle(30, 100, 80, 150, fill="lightblue")  # Raw Water
        self.canvas.create_text(55, 90, text="Raw water")
        self.pi2_text = self.canvas.create_text(55, 155, text="PI2: --")  # PI2 value
        self.canvas.create_text(55, 165, text="Air")

        # === Mini-module in Center ===
        self.canvas.create_rectangle(220, 65, 300, 115, fill="lightgray")  # Mini-module
        self.canvas.create_text(260, 55, text="Mini-module")
        self.te_text = self.canvas.create_text(260, 125, text="TE: --")

        # === RIGHT: Destinations (updated positions) ===
        # Effluent (top right)
        self.canvas.create_rectangle(420, 30, 470, 80, fill="lightblue")  # WeightF
        self.canvas.create_text(445, 20, text="Effluent")
        self.canvas.create_text(445, 85, text="-- g")

        # Backwash (directly under Effluent)
        self.canvas.create_rectangle(420, 90, 470, 140, fill="lightblue")  # WeightB
        self.canvas.create_text(445, 150, text="Backwash")
        self.canvas.create_text(445, 145, text="-- g")

        # Drain (move further right)
        self.canvas.create_rectangle(520, 60, 570, 110, fill="lightblue")  # Drainage
        self.canvas.create_text(545, 120, text="Drain")

        # === Flow Lines & Valves (gray initially) ===
        self.lines = {}
        self.valve_labels = {}

        # From BW to Mini-module (V1)
        self.lines[0] = self.canvas.create_line(80, 55, 220, 80, arrow="last", fill="gray", width=2)
        self.valve_labels['V1'] = self.canvas.create_text(150, 60, text="V1")

        # From Raw to Mini-module (V2)
        self.lines[1] = self.canvas.create_line(80, 125, 220, 100, arrow="last", fill="gray", width=2)
        self.valve_labels['V2'] = self.canvas.create_text(150, 110, text="V2")

        # Mini-module to Backwash (V3) - now goes to new Backwash position
        self.lines[2] = self.canvas.create_line(300, 100, 420, 115, arrow="last", fill="gray", width=2)
        self.valve_labels['V3'] = self.canvas.create_text(360, 110, text="V3")

        # Mini-module to Drainage (V4) - now goes to new Drain position
        self.lines[3] = self.canvas.create_line(300, 105, 520, 85, arrow="last", fill="gray", width=2)
        self.valve_labels['V4'] = self.canvas.create_text(410, 90, text="V4")

        # Mini-module to Effluent (V5)
        self.lines[4] = self.canvas.create_line(300, 85, 420, 55, arrow="last", fill="gray", width=2)
        self.valve_labels['V5'] = self.canvas.create_text(360, 65, text="V5")

    def _update_lines(self) -> None:
        """Color flow lines based on valve states."""
        for idx, line_id in self.lines.items():
            color = "green" if self.solenoid_states[idx] else "gray"
            self.canvas.itemconfig(line_id, fill=color)

    def toggle_solenoid(self, channel: int) -> None:
        state = not self.solenoid_states[channel]
        self.solenoid_states[channel] = state
        self.module.set_solenoid(channel + 1, state)
        text = f"Sol {channel + 1} {'ON' if state else 'OFF'}"
        self.solenoid_buttons[channel].config(text=text)
        self._update_lines()

    def prime(self) -> None:
        """Activate the priming routine using a temporary test system."""
        FiltrationTestSystem(
            self.module,
            FiltrationConfig(0, False, 0, False, 0, 0, 1, "prime")
        ).prime()

    def start_test(self) -> None:
        """Begin an automated cycle using the stored configuration."""
        if not hasattr(self, "test_system"):
            # Minimal demo configuration
            config = FiltrationConfig(
                filtration_target=1.0,
                filtration_by_volume=False,
                backwash_target=1.0,
                backwash_by_volume=False,
                refill_time=0.5,
                repeat_count=1,
                sample_time=0.1,
                project_name="demo",
            )
            self.test_system = FiltrationTestSystem(self.module, config)
        self.test_system.start_test()

    def stop_test(self) -> None:
        """Stop the currently running test."""
        if hasattr(self, "test_system"):
            self.test_system.stop_test()

    def calibrate(self) -> None:
        """Apply hard coded offsets for demonstration purposes."""
        self.module.apply_offsets(pressure=0.1, temperature=0.2)

    def update_data(self) -> None:
        """Refresh all displayed sensor values."""
        self.weight_var.set(self.module.read_scale(0))
        self.backwash_weight_var.set(self.module.read_scale(1))
        self.pressure_bw_var.set(f"{self.module.read_pressure(0):.2f}")
        self.pressure_raw_var.set(f"{self.module.read_pressure(1):.2f}")
        self.temp_var.set(f"{self.module.read_rtd(0):.2f}")

        # Update text on process diagram
        self.canvas.itemconfig(self.pi1_text, text=f"PI1: {self.pressure_bw_var.get()}")
        self.canvas.itemconfig(self.pi2_text, text=f"PI2: {self.pressure_raw_var.get()}")
        self.canvas.itemconfig(self.te_text, text=f"TE: {self.temp_var.get()}")

        self._update_lines()
        self.after(1000, self.update_data)


def main() -> None:
    """Entry point when running the module directly."""
    module = PencilModule()
    app = HMI(module)
    app.mainloop()


if __name__ == "__main__":
    main()
