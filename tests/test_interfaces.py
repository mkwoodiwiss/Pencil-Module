import sys
import types
import unittest

from tests.simulated_hardware import FakeSerial, FakeRelay8, FakeMultiIO

# Always provide fake modules before importing the code under test so the
# tests do not require real hardware libraries to be installed. This also
# ensures the simulated hardware is used even when running on a Raspberry
# Pi that may have the vendor packages installed.
sys.modules['serial'] = types.SimpleNamespace(Serial=FakeSerial)
sys.modules['relay8'] = types.SimpleNamespace(Relay8=FakeRelay8)
sys.modules['multiio'] = types.SimpleNamespace(MultiIO=FakeMultiIO)

from system_control import PencilModule


class SimulatedPencilModule(PencilModule):
    """A PencilModule that uses simulated hardware."""

    def __init__(self):
        # Do not call super().__init__ to avoid accessing real hardware
        self.ser = FakeSerial()
        self.relay = FakeRelay8()
        self.io = FakeMultiIO()
        self.pressure_offset_bw = 0.0
        self.pressure_offset_in = 0.0
        self.temp_offset = 0.0


class TestPencilModule(unittest.TestCase):
    def setUp(self):
        self.module = SimulatedPencilModule()

    def test_read_pressure(self):
        self.assertAlmostEqual(self.module.read_pressure(0), 3.21)

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
        self.assertIn(b"Z\r\n", self.module.ser.commands)
        self.assertAlmostEqual(self.module.read_pressure(0), 4.21)
        self.assertAlmostEqual(self.module.read_rtd(0), 22.5)


if __name__ == "__main__":
    unittest.main()
