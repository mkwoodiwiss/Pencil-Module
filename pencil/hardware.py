"""Hardware interface classes for the Pencil Module."""

from __future__ import annotations

import re
import string
import time
from typing import Optional

try:
    import serial  # type: ignore
except ModuleNotFoundError:  # pragma: no cover - fallback for tests
    from . import serial_stub as serial

# Optional vendor libraries. These are unavailable in the test environment,
# so the code falls back to ``None`` which tests patch as needed.
try:
    import lib8relind  # type: ignore
    import multiio  # type: ignore
except ModuleNotFoundError:  # pragma: no cover - running without hardware
    lib8relind = None
    multiio = None


class _RelayWrapper:
    """Wrap the 8-relay hat functions with a simple object API."""

    def __init__(self, stack: int) -> None:
        self.stack = stack

    def on(self, relay: int) -> None:
        lib8relind.set(self.stack, relay, 1)

    def off(self, relay: int) -> None:
        lib8relind.set(self.stack, relay, 0)


class PencilModule:
    """Interface to the hardware boards."""

    def __init__(self, relay_stack: int = 1, io_stack: int = 2,
                 port: str = "/dev/ttyUSB0", baud: int = 9600) -> None:
        # Serial connection to the pair of scales
        self.ser = serial.Serial(port, baud, timeout=1)
        # Interfaces to the relay and IO boards if available
        if lib8relind:
            self.relay = _RelayWrapper(relay_stack)
        else:
            self.relay = None
        self.io = multiio.SMmultiio(stack=io_stack) if multiio else None
        # Calibration offsets
        self.pressure_offset_bw = 0.0
        self.pressure_offset_in = 0.0
        self.temp_offset = 0.0

    def read_pressure(self, channel: int) -> float:
        """Return pressure value from ADC channel."""
        offset = self.pressure_offset_bw if channel == 0 else self.pressure_offset_in
        if self.io:
            return self.io.get_adc(channel) + offset
        return 0.0 + offset

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
        try:
            self.ser.write(b"Z\r\n")
        except Exception:
            pass

    def zero_scale(self, channel: int) -> None:
        """Zero an individual scale."""
        cmd = b"Z\r\n" if channel == 0 else b"Q\r\n"
        try:
            self.ser.write(cmd)
        except Exception:
            pass

    def apply_offsets(self, pressure_bw: float = 0.0, pressure_in: float = 0.0,
                      temperature: float = 0.0) -> None:
        """Store calibration offsets for later readings."""
        self.pressure_offset_bw = pressure_bw
        self.pressure_offset_in = pressure_in
        self.temp_offset = temperature

    def read_scale(self, channel: int = 0) -> str:
        """Return the weight from one of the scales."""
        cmd = b"P\r\n" if channel == 0 else b"S\r\n"
        try:
            try:
                self.ser.reset_input_buffer()
            except Exception:
                pass
            self.ser.write(cmd)
            time.sleep(0.1)
            response = self.ser.read_until(b"\r\n").decode("ascii", errors="ignore")
            cleaned = ''.join(c for c in response if c in string.printable)
            match = re.search(r'([ +-])\s*([\d\.]+)\s*([a-zA-Z]+)', cleaned)
            if match:
                sign = match.group(1)
                value = match.group(2)
                unit = match.group(3)
                if sign == " ":
                    sign = "+"
                return f"{sign}{value} {unit}"
        except Exception:
            pass
        return "--"
