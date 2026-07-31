"""Hardware interfaces for the MF/UF Membrane Evaluation Unit."""

from __future__ import annotations

from .highland_scale import HighlandScaleManager

try:
    import lib8relind  # type: ignore
except Exception:  # pragma: no cover
    lib8relind = None

try:
    import multiio  # type: ignore
except Exception:  # pragma: no cover
    multiio = None


class _RelayWrapper:
    """Wrap the 8-relay HAT functions with a small object API."""

    def __init__(self, stack: int) -> None:
        self.stack = stack

    def on(self, relay: int) -> None:
        lib8relind.set(self.stack, relay, 1)

    def off(self, relay: int) -> None:
        lib8relind.set(self.stack, relay, 0)


# Preserve the historical internal import used by runtime subclasses and tests.
_ScaleManager = HighlandScaleManager


class MEU:
    """Interface to the MF/UF Membrane Evaluation Unit hardware."""

    SCALE_MANAGER_CLASS = _ScaleManager
    RELAY_WRAPPER_CLASS = _RelayWrapper

    def __init__(
        self,
        relay_stack: int = 1,
        io_stack: int = 2,
        effluent_port: str = "/dev/ttyAMA3",
        backwash_port: str = "/dev/ttyAMA2",
        baud: int = 9600,
        read_delay: float = 0.25,
    ) -> None:
        scale_manager_class = self.SCALE_MANAGER_CLASS
        self._effluent_scale = scale_manager_class(effluent_port, baud)
        self._backwash_scale = scale_manager_class(backwash_port, baud)
        self.effluent_lock = self._effluent_scale.lock
        self.backwash_lock = self._backwash_scale.lock
        self._read_delay = read_delay
        self.relay = self.RELAY_WRAPPER_CLASS(relay_stack) if lib8relind else None
        self.io = self._create_multiio(io_stack)
        self.pressure_offset_bw = 0.0
        self.pressure_offset_in = 0.0
        self.temp_offset = 0.0

    @staticmethod
    def _create_multiio(io_stack: int):
        if not multiio:
            return None
        try:
            return multiio.SMmultiio(stack=io_stack, i2c=1)
        except Exception:  # pragma: no cover
            return None

    def _scale_manager(self, channel: int):
        return self._effluent_scale if channel == 0 else self._backwash_scale

    @property
    def effluent_ser(self):
        return self._effluent_scale.serial

    @property
    def backwash_ser(self):
        return self._backwash_scale.serial

    def read_pressure(self, channel: int) -> float:
        if channel == 1:
            offset = self.pressure_offset_bw
        elif channel == 2:
            offset = self.pressure_offset_in
        else:
            offset = 0.0
        if self.io:
            ma = self.io.get_i_in(channel)
            return (ma - 4.0) * (30.0 / 16.0) + offset
        return offset

    def read_rtd(self, channel: int) -> float:
        if self.io:
            return self.io.get_rtd_temp(channel + 1) + self.temp_offset
        return self.temp_offset

    def set_solenoid(self, relay: int, state: bool) -> None:
        if self.relay:
            self.relay.on(relay) if state else self.relay.off(relay)

    def zero_scales(self) -> bool:
        effluent_ok = self.zero_scale(0)
        backwash_ok = self.zero_scale(1)
        return effluent_ok and backwash_ok

    def zero_scale(self, channel: int) -> bool:
        return self._scale_manager(channel).tare()

    def scale_health(self, channel: int) -> dict:
        return self._scale_manager(channel).health()

    def apply_offsets(
        self,
        pressure_bw: float = 0.0,
        pressure_in: float = 0.0,
        temperature: float = 0.0,
    ) -> None:
        self.pressure_offset_bw = pressure_bw
        self.pressure_offset_in = pressure_in
        self.temp_offset = temperature

    def read_scale(self, channel: int = 0) -> str:
        return self._scale_manager(channel).read()

    def close(self) -> None:
        self._effluent_scale.close()
        self._backwash_scale.close()


PencilModule = MEU


__all__ = ["MEU", "PencilModule", "_RelayWrapper", "_ScaleManager"]
