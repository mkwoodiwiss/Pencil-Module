"""Hardware-independent regression tests for fragile final HMI integration fixes."""

import types
import unittest
from unittest import mock

import pencil
from pencil import hmi_final, hmi_v2_integrated


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
        self.active_backgrounds = []
        self.states = []

    def configure(self, **kwargs):
        if self.fail:
            raise hmi_final.tk.TclError("destroyed widget")
        if "bg" in kwargs:
            self.backgrounds.append(kwargs["bg"])
        if "activebackground" in kwargs:
            self.active_backgrounds.append(kwargs["activebackground"])
        if "state" in kwargs:
            self.states.append(kwargs["state"])


class _FakeToplevel:
    def __init__(self):
        self.bindings = {}

    def bind(self, sequence, callback, add=None):
        self.bindings[sequence] = callback

    def destroy(self):
        callback = self.bindings.get("<Destroy>")
        if callback:
            callback(types.SimpleNamespace(widget=self))


class _FakeVariable:
    def __init__(self, value=""):
        self.value = value
        self.callbacks = []

    def get(self):
        return self.value

    def set(self, value):
        self.value = value
        for callback in tuple(self.callbacks):
            callback("", "", "write")

    def trace_add(self, mode, callback):
        self.callbacks.append(callback)


class _SettingsHarness:
    _set_valve_buttons_state = hmi_final.HMI._set_valve_buttons_state
    _settings_window_closed = hmi_final.HMI._settings_window_closed
    _register_settings_window = hmi_final.HMI._register_settings_window
    _open_settings_dialog = hmi_final.HMI._open_settings_dialog

    def __init__(self):
        self.button = _FakeButton()
        self.pfds = {"test": {"solenoid_buttons": [self.button]}}
        self.solenoid_states = [False]
        self.is_running = False
        self.children = []
        self._style_settings_window = mock.Mock()
        self._sync_all_valve_buttons = mock.Mock()

    def winfo_children(self):
        return list(self.children)


class _IdentifierHarness:
    _shared_identifier_groups = staticmethod(hmi_final.HMI._shared_identifier_groups)
    _install_shared_identifier_sync = hmi_final.HMI._install_shared_identifier_sync
    _sync_identifier_group = hmi_final.HMI._sync_identifier_group
    _ellipsize = hmi_final.HMI._ellipsize
    _truncate_summary_text = hmi_final.HMI._truncate_summary_text
    SUMMARY_VALUE_WIDTH = hmi_final.HMI.SUMMARY_VALUE_WIDTH

    def __init__(self):
        self.project_var = _FakeVariable("project-a")
        self.benchmark_project_var = _FakeVariable("")
        self.clean_project_var = _FakeVariable("")
        self.module_id_var = _FakeVariable("module-a")
        self.benchmark_module_id_var = _FakeVariable("")
        self.clean_module_id_var = _FakeVariable("")
        self.sample_id_var = _FakeVariable("sample-a")
        self.benchmark_sample_id_var = _FakeVariable("")
        self._shared_identifier_sync_active = False
        self._refresh_identifier_summaries = mock.Mock()


class TestFinalHMIRegressions(unittest.TestCase):
    def test_public_api_exports_final_hmi(self):
        self.assertIs(pencil.HMI, hmi_v2_integrated.HMI)

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
        self.assertEqual(first.active_backgrounds, ["green"])
        self.assertEqual(second.backgrounds, ["lightgray"])
        self.assertEqual(second.active_backgrounds, ["lightgray"])
        self.assertEqual(missing_state.backgrounds, ["lightgray"])
        instance._update_lines.assert_called_once_with()

    def test_settings_window_disables_and_restores_valve_buttons(self):
        harness = _SettingsHarness()
        window = _FakeToplevel()

        harness._register_settings_window(window)

        self.assertIn("disabled", harness.button.states)
        window.destroy()
        self.assertEqual(harness.button.states[-1], "normal")
        harness._sync_all_valve_buttons.assert_called_once_with()

    def test_open_settings_dialog_registers_new_toplevel(self):
        harness = _SettingsHarness()
        window = _FakeToplevel()
        harness.children = []

        def builder():
            harness.children.append(window)

        harness._open_settings_dialog(builder)

        harness._style_settings_window.assert_called_once_with(window)
        self.assertIn("disabled", harness.button.states)

    def test_identifier_sync_updates_all_members(self):
        harness = _IdentifierHarness()
        harness._install_shared_identifier_sync()

        harness.project_var.set("project-b")

        self.assertEqual(harness.benchmark_project_var.get(), "project-b")
        self.assertEqual(harness.clean_project_var.get(), "project-b")
        harness._refresh_identifier_summaries.assert_called()

    def test_summary_truncation_preserves_short_values(self):
        harness = _IdentifierHarness()
        self.assertEqual(harness._ellipsize("short", 10), "short")

    def test_summary_truncation_ellipsizes_long_values(self):
        harness = _IdentifierHarness()
        self.assertEqual(harness._ellipsize("abcdefghijkl", 8), "abcde...")


if __name__ == "__main__":
    unittest.main()
