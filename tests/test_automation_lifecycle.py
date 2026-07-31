"""Regression tests for shared MEU automation startup and shutdown."""

import types
import unittest
from unittest import mock

from pencil.automation_lifecycle import AutomationLifecycleMixin


class _Harness(AutomationLifecycleMixin):
    def __init__(self):
        self.config = types.SimpleNamespace(
            project="project",
            module_id="module",
        )
        self.module = mock.Mock()
        self._stop_event = mock.Mock()
        self.close_all_valves = mock.Mock()
        self._open_logs = mock.Mock()
        self._apply_offsets = mock.Mock()
        self.stop_test = mock.Mock()


class TestAutomationLifecycle(unittest.TestCase):
    @mock.patch("pencil.automation_lifecycle.time.sleep")
    def test_prepare_process_run_preserves_safe_start_order(self, sleep):
        harness = _Harness()

        harness._prepare_run(
            prefix="Test",
            final_id="sample",
            close_valves=True,
            tare_scales=True,
        )

        harness._stop_event.clear.assert_called_once_with()
        harness.close_all_valves.assert_called_once_with()
        harness._open_logs.assert_called_once_with(
            "Test",
            "project",
            "module",
            "sample",
            harness.config,
        )
        harness._apply_offsets.assert_called_once_with(harness.config)
        harness.module.zero_scales.assert_called_once_with()
        sleep.assert_called_once_with(1.0)

    @mock.patch("pencil.automation_lifecycle.time.sleep")
    def test_passive_run_skips_valve_close_and_scale_tare(self, sleep):
        harness = _Harness()

        harness._prepare_run(
            prefix="BenchmarkPassive",
            final_id="sample",
            close_valves=False,
            tare_scales=False,
        )

        harness.close_all_valves.assert_not_called()
        harness.module.zero_scales.assert_not_called()
        sleep.assert_not_called()

    def test_managed_run_always_stops_after_success(self):
        harness = _Harness()
        body = mock.Mock()
        harness._prepare_run = mock.Mock()

        harness._run_managed(body, prefix="Test", final_id="sample")

        body.assert_called_once_with()
        harness.stop_test.assert_called_once_with()

    def test_managed_run_stops_when_prepare_fails(self):
        harness = _Harness()
        harness._prepare_run = mock.Mock(side_effect=RuntimeError("tare failed"))

        with self.assertRaisesRegex(RuntimeError, "tare failed"):
            harness._run_managed(mock.Mock(), prefix="Test", final_id="sample")

        harness.stop_test.assert_called_once_with()

    def test_managed_run_stops_when_body_fails(self):
        harness = _Harness()
        harness._prepare_run = mock.Mock()

        with self.assertRaisesRegex(RuntimeError, "phase failed"):
            harness._run_managed(
                mock.Mock(side_effect=RuntimeError("phase failed")),
                prefix="Clean",
                final_id="solution",
            )

        harness.stop_test.assert_called_once_with()


if __name__ == "__main__":
    unittest.main()
