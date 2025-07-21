import os
import unittest

from tests.test_interfaces import SimulatedPencilModule
from system_control import FiltrationConfig, FiltrationTestSystem


class TestAutomation(unittest.TestCase):
    def test_run_single_cycle(self):
        mod = SimulatedPencilModule()
        config = FiltrationConfig(
            filtration_target=0.1,
            filtration_by_volume=False,
            backwash_target=0.1,
            backwash_by_volume=False,
            refill_time=0.1,
            repeat_count=1,
            sample_time=0.01,
            project_name="testproj",
        )
        system = FiltrationTestSystem(mod, config, log_dir="logs")
        system.start_test()
        self.assertTrue(mod.relay.calls)
        # Verify log files created
        files = os.listdir("logs")
        self.assertTrue(any(fname.startswith("testproj_") for fname in files))

    def test_valve_callback_invoked(self):
        mod = SimulatedPencilModule()
        config = FiltrationConfig(
            filtration_target=0.01,
            filtration_by_volume=False,
            backwash_target=0.01,
            backwash_by_volume=False,
            refill_time=0.01,
            repeat_count=1,
            sample_time=0.001,
            project_name="cbtest",
        )
        calls = []
        system = FiltrationTestSystem(
            mod,
            config,
            valve_callback=lambda v, s: calls.append((v, s)),
        )
        system.start_test()
        self.assertTrue(calls, "valve callback not invoked")


if __name__ == "__main__":
    unittest.main()
