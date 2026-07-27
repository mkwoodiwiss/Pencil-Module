import csv
import os
import tempfile
import unittest

from tests.test_interfaces import SimulatedPencilModule
from system_control import FiltrationConfig, FiltrationTestSystem


EXPECTED_HEADER = [
    "timestamp",
    "feed_temperature",
    "feed_tank_pressure",
    "backwash_tank_pressure",
    "feed_weight",
    "backwash_weight",
    "step",
]


class TestAutomation(unittest.TestCase):
    def make_config(self, **overrides):
        values = dict(
            filtration_target=0.01,
            filtration_by_volume=False,
            backwash_target=0.01,
            backwash_by_volume=False,
            refill_time=0.01,
            cycle_count=1,
            sample_time=0.001,
            project="proj",
            module_id="mod1",
            sample_id="sampleA",
        )
        values.update(overrides)
        return FiltrationConfig(**values)

    def test_run_single_cycle(self):
        mod = SimulatedPencilModule()
        with tempfile.TemporaryDirectory() as log_dir:
            system = FiltrationTestSystem(mod, self.make_config(), log_dir=log_dir)
            system.start_test()
            self.assertTrue(mod.relay.calls)
            files = os.listdir(log_dir)
            prefix = "Test_proj_mod1_sampleA_"
            self.assertTrue(any(fname.startswith(prefix) for fname in files))
            data_file = next(
                f for f in files if f.startswith(prefix) and f.endswith("_data.csv")
            )
            with open(os.path.join(log_dir, data_file), newline="", encoding="utf-8") as fp:
                rows = list(csv.reader(fp))
            self.assertEqual(rows[0], EXPECTED_HEADER)
            steps = {row[-1] for row in rows[1:]}
            self.assertIn("Purge", steps)
            self.assertIn("Filter", steps)
            self.assertIn("Backwash", steps)

    def test_pressure_columns_follow_io_list_channels(self):
        mod = SimulatedPencilModule()
        with tempfile.TemporaryDirectory() as log_dir:
            system = FiltrationTestSystem(mod, self.make_config(), log_dir=log_dir)
            system.start_test()
            data_file = next(f for f in os.listdir(log_dir) if f.endswith("_data.csv"))
            with open(os.path.join(log_dir, data_file), newline="", encoding="utf-8") as fp:
                rows = list(csv.DictReader(fp))
            self.assertTrue(rows)
            self.assertAlmostEqual(float(rows[0]["feed_tank_pressure"]), mod.read_pressure(2))
            self.assertAlmostEqual(float(rows[0]["backwash_tank_pressure"]), mod.read_pressure(1))

    def test_benchmark_cycle_uses_benchmark_prefix(self):
        mod = SimulatedPencilModule()
        config = self.make_config(file_prefix="Benchmark")
        with tempfile.TemporaryDirectory() as log_dir:
            FiltrationTestSystem(mod, config, log_dir=log_dir).start_test()
            self.assertTrue(any(name.startswith("Benchmark_") for name in os.listdir(log_dir)))

    def test_valve_callback_invoked(self):
        mod = SimulatedPencilModule()
        calls = []
        with tempfile.TemporaryDirectory() as log_dir:
            system = FiltrationTestSystem(
                mod,
                self.make_config(project="cb", module_id="m", sample_id="s"),
                log_dir=log_dir,
                valve_callback=lambda valve, state: calls.append((valve, state)),
            )
            system.start_test()
        self.assertTrue(calls, "valve callback not invoked")

    def test_progress_callback_invoked(self):
        mod = SimulatedPencilModule()
        steps = []
        with tempfile.TemporaryDirectory() as log_dir:
            system = FiltrationTestSystem(
                mod,
                self.make_config(project="prog", module_id="m1", sample_id="s1"),
                log_dir=log_dir,
                progress_callback=lambda step, count, total: steps.append((step, count, total)),
            )
            system.start_test()
        self.assertEqual(
            steps,
            [("Purge", 1, 1), ("Filter", 1, 1), ("Backwash", 1, 1)],
        )

    def test_separate_offsets_are_applied(self):
        mod = SimulatedPencilModule()
        config = self.make_config(
            feed_tank_pressure_offset=1.5,
            backwash_tank_pressure_offset=-0.5,
            feed_temperature_offset=2.0,
        )
        with tempfile.TemporaryDirectory() as log_dir:
            FiltrationTestSystem(mod, config, log_dir=log_dir).start_test()
        self.assertEqual(mod.pressure_offset_in, 1.5)
        self.assertEqual(mod.pressure_offset_bw, -0.5)
        self.assertEqual(mod.temp_offset, 2.0)


if __name__ == "__main__":
    unittest.main()
