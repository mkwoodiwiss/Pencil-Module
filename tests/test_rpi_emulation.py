"""Hardware-independent tests for the Raspberry Pi MEU emulator."""

from __future__ import annotations

import unittest

from pencil.emulation import EmulatedMEU


class EmulatedMEUTests(unittest.TestCase):
    def setUp(self) -> None:
        self.meu = EmulatedMEU()

    def tearDown(self) -> None:
        self.meu.close()

    def test_defaults_match_safe_powered_on_state(self) -> None:
        self.assertEqual(self.meu.read_scale(0), "+0.0 g")
        self.assertEqual(self.meu.read_scale(1), "+0.0 g")
        self.assertEqual(self.meu.read_pressure(1), 0.0)
        self.assertEqual(self.meu.read_pressure(2), 0.0)
        self.assertEqual(self.meu.read_rtd(0), 20.0)
        self.assertTrue(all(not self.meu.relay_state(relay) for relay in range(1, 9)))

    def test_relay_transitions_are_applied_and_recorded(self) -> None:
        self.meu.set_solenoid(2, True)
        self.meu.set_solenoid(2, False)

        self.assertFalse(self.meu.relay_state(2))
        events = self.meu.relay_events
        self.assertEqual([(event.relay, event.state) for event in events], [(2, True), (2, False)])
        self.assertLessEqual(events[0].timestamp, events[1].timestamp)

    def test_scale_reading_and_tare(self) -> None:
        self.meu.set_scale_value(0, 123.45)
        self.meu.set_scale_value(1, -6.0)

        self.assertEqual(self.meu.read_scale(0), "+123.5 g")
        self.assertEqual(self.meu.read_scale(1), "-6.0 g")
        self.assertTrue(self.meu.zero_scales())
        self.assertEqual(self.meu.read_scale(0), "+0.0 g")
        self.assertEqual(self.meu.read_scale(1), "+0.0 g")

    def test_disconnected_scale_matches_runtime_failure_surface(self) -> None:
        self.meu.set_scale_connected(1, False)

        self.assertEqual(self.meu.read_scale(1), "--")
        health = self.meu.scale_health(1)
        self.assertFalse(health["connected"])
        self.assertEqual(health["reading"], "--")
        self.assertIn("disconnected", health["last_error"])

    def test_failed_dual_tare_raises_same_operator_error_as_production(self) -> None:
        self.meu.set_tare_allowed(0, False)

        with self.assertRaisesRegex(RuntimeError, "Filtrate scale did not accept tare"):
            self.meu.zero_scales()

    def test_pressure_temperature_and_offsets(self) -> None:
        self.meu.set_pressure(1, 12.5)
        self.meu.set_pressure(2, 8.0)
        self.meu.set_rtd(0, 21.25)
        self.meu.apply_offsets(pressure_bw=0.5, pressure_in=-0.25, temperature=1.0)

        self.assertAlmostEqual(self.meu.read_pressure(1), 13.0)
        self.assertAlmostEqual(self.meu.read_pressure(2), 7.75)
        self.assertAlmostEqual(self.meu.read_rtd(0), 22.25)
        self.assertAlmostEqual(self.meu.get_i_in(1), 4.0 + 13.0 * 16.0 / 30.0)
        self.assertAlmostEqual(self.meu.get_rtd_temp(1), 22.25)

    def test_close_forces_relays_off_and_rejects_reads(self) -> None:
        self.meu.set_solenoid(5, True)
        self.meu.close()

        self.assertFalse(self.meu.relay_state(5))
        with self.assertRaisesRegex(RuntimeError, "closed"):
            self.meu.read_scale(0)

    def test_invalid_channels_fail_loudly(self) -> None:
        with self.assertRaises(ValueError):
            self.meu.set_solenoid(0, True)
        with self.assertRaises(ValueError):
            self.meu.read_scale(2)
        with self.assertRaises(ValueError):
            self.meu.set_pressure(3, 1.0)


if __name__ == "__main__":
    unittest.main()
