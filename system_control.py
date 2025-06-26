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
from dataclasses import dataclass, asdict

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


# Solenoid channel assignments
INFLUENT_SUPPLY_VALVE = 1
BACKWASH_SUPPLY_VALVE = 2
EFFLUENT_VALVE = 3
BACKWASH_EFFLUENT_VALVE = 4
INFLUENT_DRAIN_VALVE = 5


@dataclass
class TestSettings:
    """Configuration for an automated filtration test."""

    project_name: str = "test"
    filtration_time: float | None = None
    filtration_volume: float | None = None
    backwash_time: float | None = None
    backwash_volume: float | None = None
    refill_time: float = 0.0
    repeat_count: int = 1
    sample_time: float = 1.0


class PencilModule:
    """Interface to the hardware boards."""

    def __init__(self, relay_stack=0, io_stack=0, port="/dev/ttyUSB0", baud=9600):
        self.ser = serial.Serial(port, baud, timeout=1)
        self.relay = relay8.Relay8(stack=relay_stack) if relay8 else None
        self.io = multiio.MultiIO(stack=io_stack) if multiio else None

    def read_pressure(self, channel: int) -> float:
        """Return pressure value from ADC channel."""
        if self.io:
            return self.io.get_adc(channel)
        return 0.0

    def read_rtd(self, channel: int) -> float:
        """Return temperature value from RTD channel."""
        if self.io:
            return self.io.get_rtd(channel)
        return 0.0

    def set_solenoid(self, relay: int, state: bool) -> None:
        """Activate or deactivate a solenoid."""
        if self.relay:
            if state:
                self.relay.on(relay)
            else:
                self.relay.off(relay)

    def read_scale(self) -> str:
        """Query the serial scale and return the weight string."""
        self.ser.write(b"P\r\n")
        time.sleep(0.1)
        response = self.ser.read_until(b"\r\n").decode("ascii", "ignore").strip()
        match = re.search(r"([+-]?)\s*(\d+\.\d+)\s*(\w)", response)
        if match:
            sign, weight, unit = match.groups()
            return f"{sign}{weight} {unit}"
        return "--"

    def read_weight(self) -> float:
        """Return the scale weight as a floating point number."""
        text = self.read_scale()
        match = re.search(r"([+-]?\d+\.\d+)", text)
        if match:
            return float(match.group(1))
        return 0.0

    def zero_scales(self) -> None:
        """Send the zero command to the scale."""
        self.ser.write(b"Z\r\n")


class FiltrationController:
    """Run automated filtration cycles based on :class:`TestSettings`."""

    def __init__(self, module: PencilModule):
        self.module = module

    def _log_headers(self, writer):
        writer.writerow(
            [
                "timestamp",
                "influent_pressure",
                "backwash_pressure",
                "influent_temp",
                "weight",
            ]
        )

    def _log_row(self, writer):
        writer.writerow(
            [
                time.time(),
                self.module.read_pressure(0),
                self.module.read_pressure(1),
                self.module.read_rtd(0),
                self.module.read_weight(),
            ]
        )

    def _wait(self, duration: float, writer, sample_time: float):
        end = time.time() + duration
        while time.time() < end:
            self._log_row(writer)
            time.sleep(sample_time)

    def run_test(self, settings: TestSettings) -> None:
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        data_file = f"{settings.project_name}_{timestamp}_data.csv"
        settings_file = f"{settings.project_name}_{timestamp}_settings.csv"

        with open(settings_file, "w", newline="") as sf:
            sw = csv.writer(sf)
            for k, v in asdict(settings).items():
                sw.writerow([k, v])

        with open(data_file, "w", newline="") as df:
            dw = csv.writer(df)
            self._log_headers(dw)

            self.module.zero_scales()

            for _ in range(settings.repeat_count):
                # Refill phase
                self.module.set_solenoid(INFLUENT_SUPPLY_VALVE, True)
                self.module.set_solenoid(INFLUENT_DRAIN_VALVE, True)
                self._wait(settings.refill_time, dw, settings.sample_time)
                self.module.set_solenoid(INFLUENT_SUPPLY_VALVE, False)
                self.module.set_solenoid(INFLUENT_DRAIN_VALVE, False)

                # Filtration phase
                self.module.set_solenoid(INFLUENT_SUPPLY_VALVE, True)
                self.module.set_solenoid(EFFLUENT_VALVE, True)
                if settings.filtration_time is not None:
                    self._wait(settings.filtration_time, dw, settings.sample_time)
                else:
                    while self.module.read_weight() < (settings.filtration_volume or 0):
                        self._log_row(dw)
                        time.sleep(settings.sample_time)
                self.module.set_solenoid(INFLUENT_SUPPLY_VALVE, False)
                self.module.set_solenoid(EFFLUENT_VALVE, False)

                # Backwash phase
                self.module.set_solenoid(BACKWASH_SUPPLY_VALVE, True)
                self.module.set_solenoid(BACKWASH_EFFLUENT_VALVE, True)
                if settings.backwash_time is not None:
                    self._wait(settings.backwash_time, dw, settings.sample_time)
                else:
                    while self.module.read_weight() < (settings.backwash_volume or 0):
                        self._log_row(dw)
                        time.sleep(settings.sample_time)
                self.module.set_solenoid(BACKWASH_SUPPLY_VALVE, False)
                self.module.set_solenoid(BACKWASH_EFFLUENT_VALVE, False)

            # Cycle complete
            self._log_row(dw)


class HMI(tk.Tk):
    """Simple Tkinter graphical interface."""

    def __init__(self, module: PencilModule):
        super().__init__()
        self.module = module
        self.title("Pencil Module")
        self.geometry("480x320")  # fits 7" display

        self.weight_var = tk.StringVar()
        self.pressure_var = tk.StringVar()
        self.temp_var = tk.StringVar()

        tk.Label(self, text="Weight:").pack()
        tk.Label(self, textvariable=self.weight_var, font=("Arial", 24)).pack()
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

        tk.Button(self, text="Start Test", command=self.start_test).pack(pady=5)

        self.update_data()

    def toggle_solenoid(self, channel: int) -> None:
        state = not self.solenoid_states[channel]
        self.solenoid_states[channel] = state
        self.module.set_solenoid(channel + 1, state)
        text = f"Sol {channel + 1} {'ON' if state else 'OFF'}"
        self.solenoid_buttons[channel].config(text=text)

    def start_test(self) -> None:
        controller = FiltrationController(self.module)
        settings = TestSettings(filtration_time=1, backwash_time=1, refill_time=1)
        controller.run_test(settings)

    def update_data(self) -> None:
        self.weight_var.set(self.module.read_scale())
        self.pressure_var.set(f"{self.module.read_pressure(0):.2f}")
        self.temp_var.set(f"{self.module.read_rtd(0):.2f}")
        self.after(1000, self.update_data)


def main() -> None:
    module = PencilModule()
    app = HMI(module)
    app.mainloop()


if __name__ == "__main__":
    main()
