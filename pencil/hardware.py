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
except Exception as e:  # pragma: no cover - running without hardware
    print(f"[debug] vendor libraries missing: {e}")
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
                 effluent_port: str = "/dev/ttyUSB0",
                 backwash_port: str = "/dev/ttyUSB1", baud: int = 9600) -> None:
        """Initialize connections to the hardware."""
        # Individual serial connections to each scale
        self.effluent_ser = serial.Serial(effluent_port, baud, timeout=1)
        self.backwash_ser = serial.Serial(backwash_port, baud, timeout=1)
        # Interfaces to the relay and IO boards if available
        if lib8relind:
            self.relay = _RelayWrapper(relay_stack)
        else:
            self.relay = None
        if multiio:
            try:
                self.io = multiio.SMmultiio(stack=io_stack)
            except Exception as e:  # pragma: no cover - hardware init failed
                print(f"[debug] failed to init Multi IO: {e}")
                self.io = None
        else:
            self.io = None
        print(
            f"[debug] PencilModule init: relay={'yes' if self.relay else 'no'}, "
            f"io={'yes' if self.io else 'no'}"
        )
        # Calibration offsets
        self.pressure_offset_bw = 0.0
        self.pressure_offset_in = 0.0
        self.temp_offset = 0.0

    def read_pressure(self, channel: int) -> float:
        """Return pressure in PSI from a 4-20 mA input channel."""
        # Channel numbers correspond to the Multi IO hat numbering (1/2)
        if channel == 1:
            offset = self.pressure_offset_bw
        elif channel == 2:
            offset = self.pressure_offset_in
        else:
            offset = 0.0
        if self.io:
            ma = self.io.get_adc(channel)
            psi = (ma - 4.0) * (30.0 / 16.0)
            value = psi + offset
            print(
                f"[debug] read_pressure: ch={channel}, raw={ma:.2f}, "
                f"psi={psi:.2f}, offset={offset:.2f}, value={value:.2f}"
            )
            return value
        print(
            f"[debug] read_pressure: ch={channel}, io unavailable, offset={offset:.2f}"
        )
        return 0.0 + offset

    def read_rtd(self, channel: int) -> float:
        """Return temperature value from an RTD channel."""
        if self.io:
            # Library channels are 1-indexed
            temp = self.io.get_rtd(channel + 1)
            value = temp + self.temp_offset
            print(
                f"[debug] read_rtd: ch={channel}, raw={temp:.2f}, "
                f"offset={self.temp_offset:.2f}, value={value:.2f}"
            )
            return value
        print(
            f"[debug] read_rtd: ch={channel}, io unavailable, offset={self.temp_offset:.2f}"
        )
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
        self.zero_scale(0)
        self.zero_scale(1)

    def zero_scale(self, channel: int) -> None:
        """Zero an individual scale."""
        ser = self.effluent_ser if channel == 0 else self.backwash_ser
        cmd = b"Z\r\n"
        try:
            ser.write(cmd)
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
        ser = self.effluent_ser if channel == 0 else self.backwash_ser
        cmd = b"P\r\n"
        try:
            try:
                ser.reset_input_buffer()
            except Exception:
                pass
            ser.write(cmd)
            time.sleep(0.1)
            response = ser.read_until(b"\r\n").decode("ascii", errors="ignore")
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
