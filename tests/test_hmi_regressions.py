"""Hardware-independent regression tests for fragile final HMI integration fixes."""

import types
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


class _FakeVar:
    def __init__(self, value=""):
        self.value = value
        self.callbacks = []

    def get(self):
        return self.value

    def set(self, value):
        self.value = value
        for callback in tuple(self.callbacks):
            callback("name", "index", "write")

    def trace_add(self, mode, callback):
        self.callbacks.append(callback)
        return f"trace-{len(self.callbacks)}"


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

    def __init__(self):
        self._shared_identifier_sync_active = False
        self.project_var = _FakeVar("Initial Project")
        self.benchmark_project_var = _FakeVar("")
        self.clean_project_var = _FakeVar("")
        self.module_id_var = _FakeVar("Module-A")
        self.benchmark_module_id_var = _FakeVar("")
        self.clean_module_id_var = _FakeVar("")
        self.sample_id_var = _FakeVar("Sample-A")
        self.benchmark_sample_id_var = _FakeVar("")
        self._refresh_identifier_summaries = mock.Mock()


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
        self.assertEqual(first.active_backgrounds, ["green"])
        self.assertEqual(second.backgrounds, ["lightgray"])
        self.assertEqual(second.active_backgrounds, ["lightgray"])
        self.assertEqual(missing_state.backgrounds, ["lightgray"])
        self.assertEqual(missing_state.active_backgrounds, ["lightgray"])
        instance._update_lines.assert_called_once_with()

    def test_valve_sync_tolerates_missing_runtime_state(self):
        instance = types.SimpleNamespace(
            _update_lines=mock.Mock(side_effect=AttributeError("screen closed"))
        )

        hmi_final.HMI._sync_all_valve_buttons(instance)

        instance._update_lines.assert_called_once_with()

    def test_touchscreen_toggle_matches_active_and_normal_colors(self):
        instance = object.__new__(hmi_final.HMI)
        first = _FakeButton()
        second = _FakeButton()
        instance.solenoid_states = [False]
        instance.pfds = {
            "test": {"solenoid_buttons": [first]},
            "clean": {"solenoid_buttons": [second]},
        }

        def parent_toggle(target, channel):
            target.solenoid_states[channel] = not target.solenoid_states[channel]

        with mock.patch.object(
            hmi_final._ThemedHMI,
            "toggle_solenoid",
            autospec=True,
            side_effect=parent_toggle,
        ) as parent:
            hmi_final.HMI.toggle_solenoid(instance, 0)

        parent.assert_called_once_with(instance, 0)
        self.assertEqual(first.backgrounds, ["green"])
        self.assertEqual(first.active_backgrounds, ["green"])
        self.assertEqual(second.backgrounds, ["green"])
        self.assertEqual(second.active_backgrounds, ["green"])

    def test_settings_dialog_disables_valves_and_is_styled(self):
        instance = _SettingsHarness()
        window = _FakeToplevel()

        def open_dialog():
            instance.children.append(window)

        with mock.patch.object(hmi_final.tk, "Toplevel", _FakeToplevel):
            instance._open_settings_dialog(open_dialog)

        self.assertEqual(instance.button.states, ["disabled", "disabled"])
        instance._style_settings_window.assert_called_once_with(window)
        self.assertIn(window, instance._open_settings_windows)

    def test_valves_restore_after_last_settings_dialog_closes(self):
        instance = _SettingsHarness()
        first = _FakeToplevel()
        second = _FakeToplevel()
        instance._register_settings_window(first)
        instance._register_settings_window(second)

        first.destroy()
        self.assertEqual(instance.button.states, ["disabled", "disabled"])

        second.destroy()
        self.assertEqual(instance.button.states[-1], "normal")
        instance._sync_all_valve_buttons.assert_called_once_with()

    def test_settings_dialog_close_does_not_enable_valves_during_run(self):
        instance = _SettingsHarness()
        instance.is_running = True
        window = _FakeToplevel()
        instance._register_settings_window(window)

        window.destroy()

        self.assertNotIn("normal", instance.button.states)
        instance._sync_all_valve_buttons.assert_not_called()

    def test_shared_identifiers_initialize_and_update_every_matching_tab(self):
        instance = _IdentifierHarness()
        instance._install_shared_identifier_sync()

        self.assertEqual(instance.benchmark_project_var.get(), "Initial Project")
        self.assertEqual(instance.clean_project_var.get(), "Initial Project")
        self.assertEqual(instance.benchmark_module_id_var.get(), "Module-A")
        self.assertEqual(instance.clean_module_id_var.get(), "Module-A")
        self.assertEqual(instance.benchmark_sample_id_var.get(), "Sample-A")

        instance.clean_project_var.set("Updated Project")
        instance.benchmark_module_id_var.set("Module-B")
        instance.benchmark_sample_id_var.set("Sample-B")

        self.assertEqual(instance.project_var.get(), "Updated Project")
        self.assertEqual(instance.benchmark_project_var.get(), "Updated Project")
        self.assertEqual(instance.module_id_var.get(), "Module-B")
        self.assertEqual(instance.clean_module_id_var.get(), "Module-B")
        self.assertEqual(instance.sample_id_var.get(), "Sample-B")

    def test_long_summary_identifiers_are_ellipsized_without_changing_source(self):
        source = "A very long project identifier"
        summary = f"Filter: 10 s\nProject: {source}\nModule: Short\nSample: Sample-123456789"

        displayed = hmi_final.HMI._truncate_summary_text(summary)

        self.assertIn("Project: A very long p...", displayed)
        self.assertIn("Module: Short", displayed)
        self.assertIn("Sample: Sample-123456...", displayed)
        self.assertEqual(source, "A very long project identifier")

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
