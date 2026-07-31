"""Regression tests for the authoritative MEU Clean sequence."""

import types
import unittest

from pencil.clean_sequence import CLEAN_SEQUENCE, CleanSequenceMixin, resolve_valves


class _Harness(CleanSequenceMixin):
    FEED = 2
    WASTE = 4
    FILTRATE = 5
    BACKWASH = 1
    BACKWASH_EFFLUENT = 3

    def __init__(self):
        self.config = types.SimpleNamespace(
            purge_time=3.0,
            sample_time=1.0,
            forward_target=10.0,
            forward_by_weight=True,
            backwash_target=20.0,
            backwash_by_weight=False,
            soak_time=30.0,
            rinse_forward_target=40.0,
            rinse_forward_by_weight=False,
            rinse_backwash_target=50.0,
            rinse_backwash_by_weight=True,
        )
        self.calls = []

    def _prompt(self, message):
        self.calls.append(("prompt", message))

    def _timed_phase(self, name, target, valves, sample_time):
        self.calls.append(("timed", name, target, valves, sample_time))

    def _process_phase(self, name, target, by_weight, scale_channel, valves):
        self.calls.append(
            ("process", name, target, by_weight, scale_channel, valves)
        )


class TestCleanSequence(unittest.TestCase):
    def test_sequence_has_expected_operator_and_process_step_count(self):
        self.assertEqual(len(CLEAN_SEQUENCE), 22)
        self.assertEqual(
            [step.kind for step in CLEAN_SEQUENCE].count("prompt"),
            4,
        )
        self.assertEqual(
            [step.kind for step in CLEAN_SEQUENCE].count("timed"),
            6,
        )
        self.assertEqual(
            [step.kind for step in CLEAN_SEQUENCE].count("process"),
            12,
        )

    def test_sequence_preserves_exact_step_order(self):
        self.assertEqual(
            [step.name for step in CLEAN_SEQUENCE],
            [
                "Fill the Feed tank with caustic solution, then confirm to continue.",
                "Caustic Purge",
                "Caustic Filter 1",
                "Caustic Backwash 1",
                "Caustic Soak",
                "Caustic Filter 2",
                "Caustic Backwash 2",
                "Replace the Feed tank contents with DI water, then confirm to continue.",
                "DI Rinse 1 Purge",
                "DI Rinse 1 Filter",
                "DI Rinse 1 Backwash",
                "Fill the Feed tank with acid solution, then confirm to continue.",
                "Acid Purge",
                "Acid Filter 1",
                "Acid Backwash 1",
                "Acid Soak",
                "Acid Filter 2",
                "Acid Backwash 2",
                "Replace the acid in the Feed tank with DI water, then confirm before DI Rinse 2.",
                "DI Rinse 2 Purge",
                "DI Rinse 2 Filter",
                "DI Rinse 2 Backwash",
            ],
        )

    def test_symbolic_valves_resolve_to_current_relay_mapping(self):
        harness = _Harness()
        purge = CLEAN_SEQUENCE[1]
        backwash = CLEAN_SEQUENCE[3]

        self.assertEqual(resolve_valves(harness, purge), (2, 4))
        self.assertEqual(resolve_valves(harness, backwash), (1, 3))

    def test_dispatch_uses_configured_targets_modes_and_scale_channels(self):
        harness = _Harness()
        harness._run_clean_cycle()

        self.assertIn(
            ("process", "Caustic Filter 1", 10.0, True, 0, (2, 5)),
            harness.calls,
        )
        self.assertIn(
            ("process", "Caustic Backwash 1", 20.0, False, 1, (1, 3)),
            harness.calls,
        )
        self.assertIn(
            ("process", "DI Rinse 1 Filter", 40.0, False, 0, (2, 5)),
            harness.calls,
        )
        self.assertIn(
            ("process", "DI Rinse 2 Backwash", 50.0, True, 1, (1, 3)),
            harness.calls,
        )

    def test_soaks_remain_timed_phases_with_no_open_valves(self):
        harness = _Harness()
        harness._run_clean_cycle()

        self.assertIn(("timed", "Caustic Soak", 30.0, (), 1.0), harness.calls)
        self.assertIn(("timed", "Acid Soak", 30.0, (), 1.0), harness.calls)


if __name__ == "__main__":
    unittest.main()
