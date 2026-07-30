"""Hardware-independent regression tests for fragile final HMI integration fixes."""

import unittest
from unittest import mock

import pencil
from pencil import hmi_final


class _FakeWidget:
    def __init__(self, *, exists=True, after_error=None):
        self.exists = exists
        self.after_error = after_error
        self.after_calls = 0

    def winfo_exists(self):
        return self.exists

    def after_idle(self, callback):
        self.after_calls += 1
        if self.after_error is not None:
            raise self.after_error
        callback()


class _FakeButton:
    def __init__(self, *, fail=False):
        self.fail = fail
        self.backgrounds = []

    def configure(self, **kwargs):
        if self.fail:
            raise hmi_final.tk.TclError("destroyed widget")
        self.backgrounds.append(kwargs["bg"])


class TestFinalHMIRegressions(unittest.TestCase):
    def test_public_api_exports_final_hmi(self):
        self.assertIs(pencil.HMI, hmi_final.HMI)

    def test_map_callback_ignores_non_widget_targets(self):
        instance = object.__new__(hmi_final.HMI)
        instance._apply_selected_accents = mock.Mock()
        event = mock.Mock(widget="destroyed-widget-name")

        with mock.patch.object(hmi_final.tk, "Misc", _FakeWidget):
            hmi_final.HMI._style_mapped_widget(instance, event)

        instance._apply_selected_accents.assert_not_called()

    def test_map_callback_ignores_destroyed_widgets(self):
        instance = object.__new__(hmi_final.HMI)
        instance._apply_selected_accents = mock.Mock()
        widget = _FakeWidget(exists=False)

        with mock.patch.object(hmi_final.tk, "Misc", _FakeWidget):
            hmi_final.HMI._style_mapped_widget(instance, mock.Mock(widget=widget))

        self.assertEqual(widget.after_calls, 0)
        instance._apply_selected_accents.assert_not_called()

    def test_map_callback_styles_live_widget_once(self):
        instance = object.__new__(hmi_final.HMI)
        instance._apply_selected_accents = mock.Mock()
        widget = _FakeWidget(exists=True)

        with mock.patch.object(hmi_final.tk, "Misc", _FakeWidget):
            hmi_final.HMI._style_mapped_widget(instance, mock.Mock(widget=widget))

        self.assertEqual(widget.after_calls, 1)
        instance._apply_selected_accents.assert_called_once_with(widget)

    def test_map_callback_swallows_shutdown_scheduling_errors(self):
        instance = object.__new__(hmi_final.HMI)
        instance._apply_selected_accents = mock.Mock()
        widget = _FakeWidget(exists=True, after_error=AttributeError("closing"))

        with mock.patch.object(hmi_final.tk, "Misc", _FakeWidget):
            hmi_final.HMI._style_mapped_widget(instance, mock.Mock(widget=widget))

        instance._apply_selected_accents.assert_not_called()

    def test_valve_sync_updates_buttons_and_process_lines(self):
        instance = object.__new__(hmi_final.HMI)
        first = _FakeButton()
        second = _FakeButton()
        missing_state = _FakeButton()
        destroyed = _FakeButton(fail=True)
        instance.solenoid_states = [True, False]
        instance.pfds = {
            "main": {
                "solenoid_buttons": [first, second, missing_state, destroyed],
            }
        }
        instance._update_lines = mock.Mock()

        hmi_final.HMI._sync_all_valve_buttons(instance)

        self.assertEqual(first.backgrounds, ["green"])
        self.assertEqual(second.backgrounds, ["lightgray"])
        self.assertEqual(missing_state.backgrounds, ["lightgray"])
        instance._update_lines.assert_called_once_with()

    def test_valve_sync_tolerates_missing_runtime_state(self):
        instance = object.__new__(hmi_final.HMI)
        instance._update_lines = mock.Mock(side_effect=AttributeError("screen closed"))

        hmi_final.HMI._sync_all_valve_buttons(instance)

        instance._update_lines.assert_called_once_with()

    def test_completion_bypasses_themed_duplicate_dialog(self):
        instance = object.__new__(hmi_final.HMI)
        mro = hmi_final.HMI.__mro__
        themed_index = mro.index(hmi_final._ThemedHMI)
        original_completion_class = next(
            cls
            for cls in mro[themed_index + 1 :]
            if "_test_finished" in cls.__dict__
        )

        with mock.patch.object(
            hmi_final._ThemedHMI,
            "_test_finished",
            autospec=True,
        ) as themed_completion, mock.patch.object(
            original_completion_class,
            "_test_finished",
            autospec=True,
        ) as original_completion:
            hmi_final.HMI._test_finished(instance)

        themed_completion.assert_not_called()
        original_completion.assert_called_once_with(instance)


if __name__ == "__main__":
    unittest.main()
