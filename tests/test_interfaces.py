import sys
import types
import unittest

from tests.simulated_hardware import FakeSerial, FakeRelay8, FakeMultiIO

# Provide fake modules before importing the code under test
sys.modules.setdefault('serial', types.SimpleNamespace(Serial=FakeSerial))
sys.modules.setdefault('relay8', types.SimpleNamespace(Relay8=FakeRelay8))
sys.modules.setdefault('multiio', types.SimpleNamespace(MultiIO=FakeMultiIO))

from system_control import PencilModule


class SimulatedPencilModule(PencilModule):
    """A PencilModule that uses simulated hardware."""

    def __init__(self):
        # Do not call super().__init__ to avoid accessing real hardware
        self.ser = FakeSerial()
        self.relay = FakeRelay8()
        self.io = FakeMultiIO()


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


if __name__ == "__main__":
    unittest.main()
