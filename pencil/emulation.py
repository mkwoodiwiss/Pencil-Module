"""Deterministic Raspberry Pi hardware emulation for MEU development and tests."""

from __future__ import annotations

from dataclasses import dataclass
import threading
import time
from typing import Callable


@dataclass(frozen=True)
class RelayEvent:
    """One relay state transition recorded by the emulator."""

    timestamp: float
    relay: int
    state: bool


class EmulatedMEU:
    """Drop-in replacement for the production MEU hardware interface.

    The emulator mirrors the public methods used by the HMI and automation
    systems. It does not import Raspberry Pi vendor drivers or open serial
    ports, so it is safe on Windows, macOS, CI runners, and headless Linux.
    """

    def __init__(
        self,
        relay_stack: int = 1,
        io_stack: int = 2,
        effluent_port: str = "/dev/ttyAMA3",
        backwash_port: str = "/dev/ttyAMA2",
        baud: int = 9600,
        read_delay: float = 0.0,
        *,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self.relay_stack = relay_stack
        self.io_stack = io_stack
        self.effluent_port = effluent_port
        self.backwash_port = backwash_port
        self.baud = baud
        self._read_delay = read_delay
        self._clock = clock
        self._lock = threading.RLock()
        self.effluent_lock = self._lock
        self.backwash_lock = self._lock

        self.pressure_offset_bw = 0.0
        self.pressure_offset_in = 0.0
        self.temp_offset = 0.0

        self._relay_states = {relay: False for relay in range(1, 9)}
        self._relay_events: list[RelayEvent] = []
        self._scale_values = {0: 0.0, 1: 0.0}
        self._scale_connected = {0: True, 1: True}
        self._tare_allowed = {0: True, 1: True}
        self._pressure_values = {1: 0.0, 2: 0.0}
        self._rtd_values = {0: 20.0}
        self._closed = False

        # Compatibility attributes used by diagnostics.
        self.relay = self
        self.io = self

    @property
    def effluent_ser(self):
        return self if self._scale_connected[0] and not self._closed else None

    @property
    def backwash_ser(self):
        return self if self._scale_connected[1] and not self._closed else None

    @property
    def relay_events(self) -> tuple[RelayEvent, ...]:
        with self._lock:
            return tuple(self._relay_events)

    def relay_state(self, relay: int) -> bool:
        self._validate_relay(relay)
        with self._lock:
            return self._relay_states[relay]

    def set_solenoid(self, relay: int, state: bool) -> None:
        self._ensure_open()
        self._validate_relay(relay)
        with self._lock:
            state = bool(state)
            self._relay_states[relay] = state
            self._relay_events.append(RelayEvent(self._clock(), relay, state))

    # Relay-wrapper compatibility.
    def on(self, relay: int) -> None:
        self.set_solenoid(relay, True)

    def off(self, relay: int) -> None:
        self.set_solenoid(relay, False)

    def set_scale_value(self, channel: int, value: float) -> None:
        self._validate_scale(channel)
        with self._lock:
            self._scale_values[channel] = float(value)

    def add_scale_weight(self, channel: int, amount: float) -> None:
        self._validate_scale(channel)
        with self._lock:
            self._scale_values[channel] += float(amount)

    def set_scale_connected(self, channel: int, connected: bool) -> None:
        self._validate_scale(channel)
        with self._lock:
            self._scale_connected[channel] = bool(connected)

    def set_tare_allowed(self, channel: int, allowed: bool) -> None:
        self._validate_scale(channel)
        with self._lock:
            self._tare_allowed[channel] = bool(allowed)

    def read_scale(self, channel: int = 0) -> str:
        self._ensure_open()
        self._validate_scale(channel)
        if self._read_delay:
            time.sleep(self._read_delay)
        with self._lock:
            if not self._scale_connected[channel]:
                return "--"
            value = self._scale_values[channel]
        sign = "+" if value >= 0 else "-"
        return f"{sign}{abs(value):.1f} g"

    def zero_scale(self, channel: int) -> bool:
        self._ensure_open()
        self._validate_scale(channel)
        with self._lock:
            if not self._scale_connected[channel] or not self._tare_allowed[channel]:
                return False
            self._scale_values[channel] = 0.0
            return True

    def zero_scales(self) -> bool:
        failures = []
        if not self.zero_scale(0):
            failures.append("Filtrate scale")
        if not self.zero_scale(1):
            failures.append("BW Effluent scale")
        if failures:
            names = " and ".join(failures)
            raise RuntimeError(
                f"{names} did not accept tare or did not return two verified zero readings. "
                "The run was not started. Confirm the scale is stable and communicating, then try again."
            )
        return True

    def scale_health(self, channel: int) -> dict:
        self._validate_scale(channel)
        with self._lock:
            connected = self._scale_connected[channel] and not self._closed
        return {
            "port": self.effluent_port if channel == 0 else self.backwash_port,
            "connected": connected,
            "reading": self.read_scale(channel) if not self._closed else "--",
            "age_seconds": 0.0 if connected else float("inf"),
            "last_error": "" if connected else "emulated scale disconnected",
        }

    def set_pressure(self, channel: int, psi: float) -> None:
        if channel not in (1, 2):
            raise ValueError(f"unsupported pressure channel: {channel}")
        with self._lock:
            self._pressure_values[channel] = float(psi)

    def read_pressure(self, channel: int) -> float:
        self._ensure_open()
        with self._lock:
            value = self._pressure_values.get(channel, 0.0)
            if channel == 1:
                return value + self.pressure_offset_bw
            if channel == 2:
                return value + self.pressure_offset_in
            return value

    def set_rtd(self, channel: int, temperature_c: float) -> None:
        with self._lock:
            self._rtd_values[channel] = float(temperature_c)

    def read_rtd(self, channel: int) -> float:
        self._ensure_open()
        with self._lock:
            return self._rtd_values.get(channel, 0.0) + self.temp_offset

    # Multi-IO compatibility for code that accesses the simulated board directly.
    def get_i_in(self, channel: int) -> float:
        psi = self.read_pressure(channel)
        return 4.0 + psi * (16.0 / 30.0)

    def get_rtd_temp(self, channel: int) -> float:
        return self.read_rtd(channel - 1)

    def apply_offsets(
        self,
        pressure_bw: float = 0.0,
        pressure_in: float = 0.0,
        temperature: float = 0.0,
    ) -> None:
        self.pressure_offset_bw = float(pressure_bw)
        self.pressure_offset_in = float(pressure_in)
        self.temp_offset = float(temperature)

    def reset(self) -> None:
        """Return emulator state to a safe, powered-on baseline."""
        with self._lock:
            for relay in self._relay_states:
                self._relay_states[relay] = False
            self._relay_events.clear()
            self._scale_values.update({0: 0.0, 1: 0.0})
            self._scale_connected.update({0: True, 1: True})
            self._tare_allowed.update({0: True, 1: True})
            self._pressure_values.update({1: 0.0, 2: 0.0})
            self._rtd_values = {0: 20.0}
            self.pressure_offset_bw = 0.0
            self.pressure_offset_in = 0.0
            self.temp_offset = 0.0
            self._closed = False

    def close(self) -> None:
        with self._lock:
            for relay in self._relay_states:
                self._relay_states[relay] = False
            self._closed = True

    def _ensure_open(self) -> None:
        if self._closed:
            raise RuntimeError("emulated MEU is closed")

    @staticmethod
    def _validate_relay(relay: int) -> None:
        if relay not in range(1, 9):
            raise ValueError(f"relay must be between 1 and 8: {relay}")

    @staticmethod
    def _validate_scale(channel: int) -> None:
        if channel not in (0, 1):
            raise ValueError(f"scale channel must be 0 or 1: {channel}")


EmulatedPencilModule = EmulatedMEU
