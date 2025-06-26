"""High level controller for the Pencil Module.

This script targets a Raspberry Pi 5 equipped with:
- Sequent Microsystems 8 Relay HAT
- Sequent Microsystems Multi IO HAT
- A weight scale connected via USB serial
- A 7" Raspberry Pi touchscreen used as an HMI
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
    """Interface to the hardware boards."""

    def __init__(
        self,
        relay_stack: int = 0,
        io_stack: int = 0,
        port: str = "/dev/ttyUSB0",
        baud: int = 9600,
    ) -> None:
        self.ser = serial.Serial(port, baud, timeout=1)
        self.relay = relay8.Relay8(stack=relay_stack) if relay8 else None
        self.io = multiio.MultiIO(stack=io_stack) if multiio else None
        self.pressure_offset = 0.0
        self.temp_offset = 0.0

    def read_pressure(self, channel: int) -> float:
        """Return pressure value from ADC channel."""
        if self.io:
            return self.io.get_adc(channel) + self.pressure_offset
        return 0.0 + self.pressure_offset

    def read_rtd(self, channel: int) -> float:
        """Return temperature value from RTD channel."""
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
        self.pressure_offset = pressure
        self.temp_offset = temperature

    def read_scale(self, channel: int = 0) -> str:
        """Query one of the serial scales and return the weight string."""
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
    """Configuration for an automated filtration test."""

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
        match = re.search(r"([+-]?\d+\.\d+)", text)
        return float(match.group(1)) if match else 0.0

    def _log_row(self) -> None:
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
        for v in valves:
            self.module.set_solenoid(v, True)

    def _close(self, *valves: int) -> None:
        for v in valves:
            self.module.set_solenoid(v, False)

    def prime(self, duration: float = 1.0) -> None:
        """Simple priming routine."""
        self._open(self.INFLUENT_SUPPLY)
        time.sleep(duration)
        self._close(self.INFLUENT_SUPPLY)

    def start_test(self) -> None:
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
    """Simple Tkinter graphical interface."""

    def __init__(self, module: PencilModule):
        super().__init__()
        self.module = module
        self.title("Pencil Module")
        self.geometry("480x320")  # fits 7" display

        self.weight_var = tk.StringVar()
        self.backwash_weight_var = tk.StringVar()
        self.pressure_var = tk.StringVar()
        self.temp_var = tk.StringVar()

        tk.Label(self, text="Effluent Weight:").pack()
        tk.Label(self, textvariable=self.weight_var, font=("Arial", 24)).pack()
        tk.Label(self, text="Backwash Weight:").pack()
        tk.Label(self, textvariable=self.backwash_weight_var, font=("Arial", 24)).pack()
        tk.Label(self, text="Pressure:").pack()
        tk.Label(self, textvariable=self.pressure_var, font=("Arial", 24)).pack()
        tk.Label(self, text="Temperature:").pack()
        tk.Label(self, textvariable=self.temp_var, font=("Arial", 24)).pack()

        self.solenoid_states = [False] * 8
        self.solenoid_buttons = []
        btn_frame = tk.Frame(self)
        btn_frame.pack(pady=10)
        for i in range(8):
            btn = tk.Button(
                btn_frame,
                text=f"Sol {i+1} OFF",
                width=8,
                command=lambda ch=i: self.toggle_solenoid(ch),
            )
            btn.grid(row=i // 4, column=i % 4, padx=5, pady=5)
            self.solenoid_buttons.append(btn)

        control_frame = tk.Frame(self)
        control_frame.pack(pady=10)
        tk.Button(control_frame, text="Prime", command=self.prime).grid(row=0, column=0, padx=5)
        tk.Button(control_frame, text="Start Test", command=self.start_test).grid(row=0, column=1, padx=5)
        tk.Button(control_frame, text="Stop Test", command=self.stop_test).grid(row=0, column=2, padx=5)
        tk.Button(control_frame, text="Zero Scale 1", command=lambda: self.module.zero_scale(0)).grid(row=1, column=0, padx=5)
        tk.Button(control_frame, text="Zero Scale 2", command=lambda: self.module.zero_scale(1)).grid(row=1, column=1, padx=5)
        tk.Button(control_frame, text="Calibrate", command=self.calibrate).grid(row=1, column=2, padx=5)

        self.update_data()

    def toggle_solenoid(self, channel: int) -> None:
        state = not self.solenoid_states[channel]
        self.solenoid_states[channel] = state
        self.module.set_solenoid(channel + 1, state)
        text = f"Sol {channel + 1} {'ON' if state else 'OFF'}"
        self.solenoid_buttons[channel].config(text=text)

    def prime(self) -> None:
        FiltrationTestSystem(self.module, FiltrationConfig(0, False, 0, False, 0, 0, 1, "prime")).prime()

    def start_test(self) -> None:
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
        if hasattr(self, "test_system"):
            self.test_system.stop_test()

    def calibrate(self) -> None:
        self.module.apply_offsets(pressure=0.1, temperature=0.2)

    def update_data(self) -> None:
        self.weight_var.set(self.module.read_scale(0))
        self.backwash_weight_var.set(self.module.read_scale(1))
        self.pressure_var.set(f"{self.module.read_pressure(0):.2f}")
        self.temp_var.set(f"{self.module.read_rtd(0):.2f}")
        self.after(1000, self.update_data)


def main() -> None:
    module = PencilModule()
    app = HMI(module)
    app.mainloop()


if __name__ == "__main__":
    main()
