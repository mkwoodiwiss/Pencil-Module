import os
import tempfile
import unittest

from system_control import (
    BenchmarkConfig,
    BenchmarkTestSystem,
    FiltrationConfig,
    FiltrationTestSystem,
    CleanConfig,
)
from pencil.automation import normalize_io_text
from tests.test_interfaces import SimulatedPencilModule


class TestAutomation(unittest.TestCase):
    def test_run_single_cycle(self):
        mod = SimulatedPencilModule()
        config = FiltrationConfig(
            filtration_time=0.0,
            backwash_time=0.0,
            cycle_count=1,
            sample_time=0.0,
            project="p",
            module_id="m",
            sample_id="s",
        )
        with tempfile.TemporaryDirectory() as tmp:
            system = FiltrationTestSystem(mod, config, output_dir=tmp)
            path = system.run()
            self.assertTrue(os.path.exists(path))

    def test_pressure_columns_follow_io_list_channels(self):
        mod = SimulatedPencilModule()
        config = FiltrationConfig(
            filtration_time=0.0,
            backwash_time=0.0,
            cycle_count=1,
            sample_time=0.0,
            project="p",
            module_id="m",
            sample_id="s",
        )
        with tempfile.TemporaryDirectory() as tmp:
            system = FiltrationTestSystem(mod, config, output_dir=tmp)
            path = system.run()
            with open(path, "r", encoding="utf-8") as handle:
                header = handle.readline().strip()
                row = handle.readline().strip()
            self.assertIn("Influent Supply Pressure (psi)", header)
            self.assertIn("Backwash Supply Pressure (psi)", header)
            self.assertTrue(row)

    def test_benchmark_cycle_uses_benchmark_prefix(self):
        mod = SimulatedPencilModule()
        config = BenchmarkConfig(cycle_count=1, sample_time=0.0)
        with tempfile.TemporaryDirectory() as tmp:
            system = BenchmarkTestSystem(mod, config, output_dir=tmp)
            path = system.run()
            self.assertTrue(os.path.basename(path).startswith("benchmark_"))

    def test_valve_callback_invoked(self):
        mod = SimulatedPencilModule()
        config = FiltrationConfig(
            filtration_time=0.0,
            backwash_time=0.0,
            cycle_count=1,
            sample_time=0.0,
            project="p",
            module_id="m",
            sample_id="s",
        )
        events = []
        with tempfile.TemporaryDirectory() as tmp:
            system = FiltrationTestSystem(
                mod,
                config,
                output_dir=tmp,
                valve_callback=lambda relay, state: events.append((relay, state)),
            )
            system.run()
        self.assertTrue(events)

    def test_progress_callback_invoked(self):
        mod = SimulatedPencilModule()
        config = FiltrationConfig(
            filtration_time=0.0,
            backwash_time=0.0,
            cycle_count=1,
            sample_time=0.0,
            project="p",
            module_id="m",
            sample_id="s",
        )
        events = []
        with tempfile.TemporaryDirectory() as tmp:
            system = FiltrationTestSystem(
                mod,
                config,
                output_dir=tmp,
                progress_callback=lambda *args: events.append(args),
            )
            system.run()
        self.assertTrue(events)

    def test_separate_offsets_are_applied(self):
        mod = SimulatedPencilModule()
        mod.apply_offsets(pressure_bw=1.0, pressure_in=2.0, temperature=3.0)
        self.assertAlmostEqual(mod.read_pressure(1), 16.0)
        self.assertAlmostEqual(mod.read_pressure(2), 17.0)
        self.assertAlmostEqual(mod.read_rtd(0), 23.5)

    def test_clean_config_preserves_weight_stop_flags(self):
        config = CleanConfig(
            forward_target=1.0,
            forward_by_weight=True,
            soak_time=1.0,
            backwash_target=1.0,
            backwash_by_weight=True,
            rinse_forward_target=1.0,
            rinse_forward_by_weight=False,
            rinse_backwash_target=1.0,
            rinse_backwash_by_weight=False,
            cycle_count=1,
            sample_time=1.0,
            purge_time=1.0,
            project="p",
            module_id="m",
            solution="s",
        )
        self.assertTrue(config.forward_by_weight)
        self.assertTrue(config.backwash_by_weight)
        self.assertFalse(config.rinse_forward_by_weight)
        self.assertFalse(config.rinse_backwash_by_weight)

    def test_io_text_normalization_handles_labels_and_canvas_phrases(self):
        text = "Influent Pressure / BW Pressure / Effluent Weight / Influent Drain"
        self.assertEqual(
            normalize_io_text(text),
            "Feed Tank Pressure / Backwash Tank Pressure / Filtrate Weight / Waste",
        )


if __name__ == "__main__":
    unittest.main()
