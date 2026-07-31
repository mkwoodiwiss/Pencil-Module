"""Low-level hardware composition for the MF/UF Membrane Evaluation Unit.

This module owns the stable application-facing hardware API.  Automation and
HMI code should call methods on :class:`MEU` instead of importing the Sequent
Microsystems or serial libraries directly.

Important production mappings
-----------------------------

Scales use zero-based application channels:

* channel 0 = effluent/filtrate scale = ``/dev/ttyAMA3``
* channel 1 = backwash-effluent scale = ``/dev/ttyAMA2``

Pressure inputs use the physical Multi-IO channel numbers:

* channel 1 = backwash supply pressure
* channel 2 = influent supply pressure

The RTD driver is one-based while the application API is zero-based.  Therefore
``read_rtd(0)`` intentionally calls physical RTD input 1.

This base class contains the common composition and simple tare behavior.
``hardware_runtime.MEU`` subclasses it to add the stricter production tare
verification used before process runs.  Keep that distinction when modifying
scale behavior.
"""

from __future__ import annotations

from .highland_scale import HighlandScaleManager

# Hardware libraries are optional at import time so documentation tools, tests,
# and the emulator can import the package on non-Pi machines.  A missing driver
# produces a disconnected interface rather than an import-time crash.
try:
    import lib8relind  # type: ignore
except Exception:  # pragma: no cover - depends on Raspberry Pi installation
    lib8relind = None

try:
    import multiio  # type: ignore
except Exception:  # pragma: no cover - depends on Raspberry Pi installation
    multiio = None


class _RelayWrapper:
    """Adapt the function-based 8-relay driver to the small object API we use."""

    def __init__(self, stack: int) -> None:
        self.stack = stack

    def on(self, relay: int) -> None:
        """Energize one physical relay on the configured HAT stack."""
        lib8relind.set(self.stack, relay, 1)

    def off(self, relay: int) -> None:
        """De-energize one physical relay on the configured HAT stack."""
        lib8relind.set(self.stack, relay, 0)


# Historical internal imports refer to ``_ScaleManager``.  Preserve this alias
# unless all downstream scripts and subclasses are migrated in the same change.
_ScaleManager = HighlandScaleManager


class MEU:
    """Compose relays, Multi-IO instruments, and two Highland scale managers.

    ``SCALE_MANAGER_CLASS`` and ``RELAY_WRAPPER_CLASS`` are class attributes on
    purpose.  Production runtime code and tests replace them without duplicating
    the rest of the hardware constructor.
    """

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
        # Do not swap these ports.  Channel 0 is used throughout the application
        # for filtrate/effluent weight and channel 1 for backwash-effluent weight.
        scale_manager_class = self.SCALE_MANAGER_CLASS
        self._effluent_scale = scale_manager_class(effluent_port, baud)
        self._backwash_scale = scale_manager_class(backwash_port, baud)

        # Expose the manager locks for older code that coordinates reads and
        # tare operations directly.  New code should prefer the public methods.
        self.effluent_lock = self._effluent_scale.lock
        self.backwash_lock = self._backwash_scale.lock
        self._read_delay = read_delay

        # ``None`` means the driver is unavailable.  This permits imports and
        # dry tests off the Pi, while production validation confirms the devices.
        self.relay = self.RELAY_WRAPPER_CLASS(relay_stack) if lib8relind else None
        self.io = self._create_multiio(io_stack)

        # Calibration offsets are applied after raw engineering-unit conversion.
        # They are runtime values supplied by the current test configuration.
        self.pressure_offset_bw = 0.0
        self.pressure_offset_in = 0.0
        self.temp_offset = 0.0

    @staticmethod
    def _create_multiio(io_stack: int):
        """Create the Multi-IO object, returning ``None`` when unavailable."""
        if not multiio:
            return None
        try:
            # i2c=1 is the Raspberry Pi's normal I2C bus used by this machine.
            return multiio.SMmultiio(stack=io_stack, i2c=1)
        except Exception:  # pragma: no cover - physical driver failure path
            return None

    def _scale_manager(self, channel: int):
        """Map application scale channel 0/1 to the corresponding manager.

        Existing callers only pass 0 or 1.  Channel validation is intentionally
        handled at higher-level interfaces and in the emulator compatibility
        tests, so changing this fallback behavior can break legacy code.
        """
        return self._effluent_scale if channel == 0 else self._backwash_scale

    @property
    def effluent_ser(self):
        """Expose the effluent serial object for legacy diagnostics."""
        return self._effluent_scale.serial

    @property
    def backwash_ser(self):
        """Expose the backwash serial object for legacy diagnostics."""
        return self._backwash_scale.serial

    def read_pressure(self, channel: int) -> float:
        """Read one 4-20 mA pressure input and return psi including its offset.

        The transmitter basis is fixed at 0-30 psi:
        ``psi = (mA - 4) * (30 / 16)``.
        Conversion to kPa, where required, happens in the HMI/logging layer.
        """
        if channel == 1:
            offset = self.pressure_offset_bw
        elif channel == 2:
            offset = self.pressure_offset_in
        else:
            offset = 0.0
        if self.io:
            ma = self.io.get_i_in(channel)
            return (ma - 4.0) * (30.0 / 16.0) + offset
        # Returning the offset keeps the API numeric during disconnected dry
        # execution.  Physical startup/validation is responsible for detecting
        # unavailable hardware before relying on a process measurement.
        return offset

    def read_rtd(self, channel: int) -> float:
        """Read a zero-based application RTD channel and return degrees C."""
        if self.io:
            # Multi-IO RTD channels are one-based; application channels are not.
            return self.io.get_rtd_temp(channel + 1) + self.temp_offset
        return self.temp_offset

    def set_solenoid(self, relay: int, state: bool) -> None:
        """Set one relay output.  ``False`` always means de-energized/off."""
        if self.relay:
            self.relay.on(relay) if state else self.relay.off(relay)

    def zero_scales(self) -> bool:
        """Tare both scales sequentially in the base implementation.

        The production runtime overrides this method to tare concurrently and to
        raise an operator-facing error unless both scales verify zero.
        """
        effluent_ok = self.zero_scale(0)
        backwash_ok = self.zero_scale(1)
        return effluent_ok and backwash_ok

    def zero_scale(self, channel: int) -> bool:
        """Request a tare from one scale manager."""
        return self._scale_manager(channel).tare()

    def scale_health(self, channel: int) -> dict:
        """Return connection, age, and last-error information for one scale."""
        return self._scale_manager(channel).health()

    def apply_offsets(
        self,
        pressure_bw: float = 0.0,
        pressure_in: float = 0.0,
        temperature: float = 0.0,
    ) -> None:
        """Replace all current instrument offsets as one configuration snapshot."""
        self.pressure_offset_bw = pressure_bw
        self.pressure_offset_in = pressure_in
        self.temp_offset = temperature

    def read_scale(self, channel: int = 0) -> str:
        """Return the scale's latest formatted display string."""
        return self._scale_manager(channel).read()

    def close(self) -> None:
        """Stop both scale workers and release their serial ports."""
        self._effluent_scale.close()
        self._backwash_scale.close()


# Keep the former equipment name as a public alias.  It is still imported by
# startup scripts and possibly external service files on deployed Pi images.
PencilModule = MEU


__all__ = ["MEU", "PencilModule", "_RelayWrapper", "_ScaleManager"]
