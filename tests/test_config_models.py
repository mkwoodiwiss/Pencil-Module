"""Regression tests for MEU process configuration compatibility."""

from dataclasses import asdict
import unittest

from pencil.config_meu import CleanConfig, FiltrationConfig


class TestFiltrationConfig(unittest.TestCase):
    def test_current_mode_arguments_override_legacy_aliases(self):
        config = FiltrationConfig(
            filtration_target=10.0,
            filtration_by_weight=False,
            filtration_by_volume=True,
            backwash_target=5.0,
            backwash_by_weight=True,
            backwash_by_volume=False,
            purge_time=2.0,
        )

        self.assertFalse(config.filtration_by_weight)
        self.assertTrue(config.backwash_by_weight)

    def test_legacy_aliases_remain_supported(self):
        config = FiltrationConfig(
            filtration_target=10.0,
            filtration_by_volume=True,
            backwash_target=5.0,
            backwash_by_volume=False,
            refill_time=3.0,
        )

        self.assertTrue(config.filtration_by_weight)
        self.assertFalse(config.backwash_by_weight)
        self.assertEqual(config.purge_time, 3.0)
        self.assertEqual(config.refill_time, 3.0)
        self.assertTrue(config.filtration_by_volume)
        self.assertFalse(config.backwash_by_volume)

    def test_purge_time_takes_precedence_over_refill_time(self):
        config = FiltrationConfig(
            filtration_target=10.0,
            purge_time=4.0,
            refill_time=9.0,
        )
        self.assertEqual(config.purge_time, 4.0)

    def test_missing_purge_and_refill_time_is_rejected(self):
        with self.assertRaisesRegex(TypeError, "purge_time or refill_time"):
            FiltrationConfig(filtration_target=10.0)

    def test_asdict_retains_current_schema(self):
        config = FiltrationConfig(
            filtration_target=10.0,
            purge_time=2.0,
        )
        values = asdict(config)

        self.assertIn("filtration_by_weight", values)
        self.assertIn("backwash_by_weight", values)
        self.assertIn("purge_time", values)
        self.assertNotIn("filtration_by_volume", values)
        self.assertNotIn("refill_time", values)


class TestCleanConfig(unittest.TestCase):
    def test_all_legacy_mode_aliases_remain_supported(self):
        config = CleanConfig(
            forward_target=10.0,
            forward_by_volume=True,
            backwash_by_volume=False,
            rinse_forward_by_volume=True,
            rinse_backwash_by_volume=False,
        )

        self.assertTrue(config.forward_by_weight)
        self.assertFalse(config.backwash_by_weight)
        self.assertTrue(config.rinse_forward_by_weight)
        self.assertFalse(config.rinse_backwash_by_weight)
        self.assertEqual(config.forward_by_volume, config.forward_by_weight)
        self.assertEqual(config.backwash_by_volume, config.backwash_by_weight)
        self.assertEqual(
            config.rinse_forward_by_volume,
            config.rinse_forward_by_weight,
        )
        self.assertEqual(
            config.rinse_backwash_by_volume,
            config.rinse_backwash_by_weight,
        )

    def test_current_clean_modes_override_legacy_aliases(self):
        config = CleanConfig(
            forward_target=10.0,
            forward_by_weight=False,
            forward_by_volume=True,
            rinse_backwash_by_weight=True,
            rinse_backwash_by_volume=False,
        )

        self.assertFalse(config.forward_by_weight)
        self.assertTrue(config.rinse_backwash_by_weight)


if __name__ == "__main__":
    unittest.main()
