import sys
import types
import unittest
import threading

from tests.simulated_hardware import (
    FakeSerial,
    FakeRelay8,
    FakeMultiIO,
    FakeLib8Relind,
)

# Always provide fake modules before importing the code under test so the
# tests do not require real hardware libraries to be installed. This also
# ensures the simulated hardware is used even on a Raspberry Pi.
sys.modules["serial"] = types.SimpleNamespace(Serial=FakeSerial)
sys.modules["lib8relind"] = FakeLib8Relind()
sys.modules["multiio"] = types.SimpleNamespace(SMmultiio=FakeMultiIO)

from system_control import MEU


class _FakeScaleManager:
    """Minimal scale-manager test double matching the current MEU interface."""

    def __init__(self, port: str):
        self.serial = FakeSerial(port=port)
        self.lock = threading.Lock()

    def read(self) -> str:
        self.serial.write(b"P\r\n")
        return self.serial.read_until().decode("ascii").strip()

    def tare(self, attempts: int = 3, timeout: float = 5.0) -> bool:
        del attempts, timeout
        self.serial.write(b"Z\r\n")
        return True

    def health(self) -> dict:
        return {
            "port": self.serial.port,
            "connected": True,
            "reading": self.read(),
            "age_seconds": 0.0,
            "last_error": "",
        }

    def close(self) -> None:
        pass


class SimulatedMEU(MEU):
    """An MEU using simulated hardware interfaces."""

    def __init__(self):
        # Do not call super().__init__ to avoid accessing real hardware.
        self._effluent_scale = _FakeScaleManager("/dev/ttyAMA3")
        self._backwash_scale = _FakeScaleManager("/dev/ttyAMA2")
        self.effluent_lock = self._effluent_scale.lock
        self.backwash_lock = self._backwash_scale.lock
        self._read_delay = 0.0
        self.relay = FakeRelay8()
        self.io = FakeMultiIO()
        self.pressure_offset_bw = 0.0
        self.pressure_offset_in = 0.0
        self.temp_offset = 0.0


# Compatibility alias for scripts that imported the previous test fixture name.
SimulatedPencilModule = SimulatedMEU


class TestMEU(unittest.TestCase):
    def setUp(self):
        self.module = SimulatedMEU()

    def test_read_pressure(self):
        self.assertAlmostEqual(self.module.read_pressure(1), 15.0)

    def test_read_rtd(self):
        self.assertAlmostEqual(self.module.read_rtd(0), 20.5)

    def test_set_solenoid(self):
        self.module.set_solenoid(1, True)
        self.module.set_solenoid(1, False)
        self.assertEqual(
            self.module.relay.calls,
            [("on", 1), ("off", 1)],
        )

    def test_read_scale(self):
        weight = self.module.read_scale()
        self.assertEqual(weight, "+123.45 g")

    def test_second_scale(self):
        weight = self.module.read_scale(1)
        self.assertEqual(weight, "+54.32 g")

    def test_zero_scales_and_offsets(self):
        self.module.apply_offsets(pressure_bw=1.0, pressure_in=1.0, temperature=2.0)
        self.module.zero_scales()
        self.assertIn(b"Z\r\n", self.module.effluent_ser.commands)
        self.assertIn(b"Z\r\n", self.module.backwash_ser.commands)
        self.assertAlmostEqual(self.module.read_pressure(1), 16.0)
        self.assertAlmostEqual(self.module.read_rtd(0), 22.5)


if __name__ == "__main__":
    unittest.main()
