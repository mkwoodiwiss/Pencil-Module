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
            project="proj",
            module_id="mod1",
            sample_id="sampleA",
        )
        system = FiltrationTestSystem(mod, config, log_dir="logs")
        system.start_test()
        self.assertTrue(mod.relay.calls)
        # Verify log files created
        files = os.listdir("logs")
        prefix = "proj_mod1_sampleA_test_"
        self.assertTrue(any(fname.startswith(prefix) for fname in files))

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
            project="cb",
            module_id="m",
            sample_id="s",
        )
        calls = []
        system = FiltrationTestSystem(
            mod,
            config,
            valve_callback=lambda v, s: calls.append((v, s)),
        )
        system.start_test()
        self.assertTrue(calls, "valve callback not invoked")

    def test_progress_callback_invoked(self):
        mod = SimulatedPencilModule()
        config = FiltrationConfig(
            filtration_target=0.01,
            filtration_by_volume=False,
            backwash_target=0.01,
            backwash_by_volume=False,
            refill_time=0.01,
            repeat_count=1,
            sample_time=0.001,
            project="prog",
            module_id="m1",
            sample_id="s1",
        )
        steps = []
        system = FiltrationTestSystem(
            mod,
            config,
            progress_callback=lambda s, c, t: steps.append((s, c, t)),
        )
        system.start_test()
        self.assertEqual(
            steps,
            [
                ("Purge", 1, 1),
                ("Filter", 1, 1),
                ("Backwash", 1, 1),
            ],
        )


if __name__ == "__main__":
    unittest.main()
