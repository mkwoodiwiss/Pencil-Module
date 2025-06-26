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

        self.update_data()

    def toggle_solenoid(self, channel: int) -> None:
        state = not self.solenoid_states[channel]
        self.solenoid_states[channel] = state
        self.module.set_solenoid(channel + 1, state)
        text = f"Sol {channel + 1} {'ON' if state else 'OFF'}"
        self.solenoid_buttons[channel].config(text=text)

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
