"""Regression tests for the focused v2 HMI components."""

import unittest
from unittest import mock

from pencil.hmi_filtration_dialogs import (
    FiltrationDialogSpec,
    FiltrationSettingsDialogMixin,
)
from pencil.hmi_identifier_state import IdentifierStateMixin
from pencil.hmi_v2_integrated import HMI


class _Variable:
    def __init__(self, value=""):
        self.value = value
        self.callbacks = []

    def get(self):
        return self.value

    def set(self, value):
        self.value = value
        for callback in tuple(self.callbacks):
            callback("", "", "write")

    def trace_add(self, _mode, callback):
        self.callbacks.append(callback)
        return str(len(self.callbacks))


class _IdentifierHarness(IdentifierStateMixin):
    def __init__(self):
        self.project_var = _Variable("project-a")
        self.benchmark_project_var = _Variable("")
        self.post_scrub_project_var = _Variable("")
        self.clean_project_var = _Variable("")
        self.module_id_var = _Variable("module-a")
        self.benchmark_module_id_var = _Variable("")
        self.post_scrub_module_id_var = _Variable("")
        self.clean_module_id_var = _Variable("")
        self.sample_id_var = _Variable("sample-a")
        self.benchmark_sample_id_var = _Variable("")
        self.post_scrub_sample_id_var = _Variable("")
        self._update_test_summary = mock.Mock()
        self._update_benchmark_summary = mock.Mock()
        self._update_post_scrub_summary = mock.Mock()
        self._update_clean_summary = mock.Mock()


class _DialogHarness(FiltrationSettingsDialogMixin):
    def __init__(self):
        self._open_settings_dialog = mock.Mock(side_effect=lambda callback: callback())
        self._build_filtration_settings_dialog = mock.Mock()
        self._update_test_summary = mock.Mock()
        self._toggle_filt_weight = mock.Mock()
        self._toggle_filt_time = mock.Mock()
        self._toggle_bw_weight = mock.Mock()
        self._toggle_bw_time = mock.Mock()
        self._update_post_scrub_summary = mock.Mock()
        self._toggle_post_scrub_filt_weight = mock.Mock()
        self._toggle_post_scrub_filt_time = mock.Mock()
        self._toggle_post_scrub_bw_weight = mock.Mock()
        self._toggle_post_scrub_bw_time = mock.Mock()


class TestIdentifierStateMixin(unittest.TestCase):
    def test_initialization_synchronizes_every_v2_tab(self):
        instance = _IdentifierHarness()

        instance._initialize_v2_identifier_state()

        self.assertEqual(instance.benchmark_project_var.get(), "project-a")
        self.assertEqual(instance.post_scrub_project_var.get(), "project-a")
        self.assertEqual(instance.clean_project_var.get(), "project-a")
        self.assertEqual(instance.post_scrub_module_id_var.get(), "module-a")
        self.assertEqual(instance.post_scrub_sample_id_var.get(), "sample-a")
        self.assertEqual(len(instance._v2_identifier_trace_ids), 11)

    def test_change_propagates_without_recursive_trace_loop(self):
        instance = _IdentifierHarness()
        instance._initialize_v2_identifier_state()

        instance.post_scrub_project_var.set("project-b")

        self.assertEqual(instance.project_var.get(), "project-b")
        self.assertEqual(instance.benchmark_project_var.get(), "project-b")
        self.assertEqual(instance.clean_project_var.get(), "project-b")


class TestFiltrationSettingsDialogMixin(unittest.TestCase):
    def test_test_and_post_scrub_use_same_dialog_builder(self):
        instance = _DialogHarness()

        instance._edit_test_settings()
        test_spec = instance._build_filtration_settings_dialog.call_args.args[0]
        instance._edit_post_scrub_settings()
        post_scrub_spec = instance._build_filtration_settings_dialog.call_args.args[0]

        self.assertIsInstance(test_spec, FiltrationDialogSpec)
        self.assertIsInstance(post_scrub_spec, FiltrationDialogSpec)
        self.assertEqual(test_spec.prefix, "")
        self.assertEqual(post_scrub_spec.prefix, "post_scrub_")
        self.assertEqual(test_spec.title, "Edit Test Settings")
        self.assertEqual(post_scrub_spec.title, "Edit Post-Scrub Settings")

    def test_variable_bindings_preserve_existing_names(self):
        test_bindings = FiltrationSettingsDialogMixin._filtration_dialog_bindings("")
        post_bindings = FiltrationSettingsDialogMixin._filtration_dialog_bindings(
            "post_scrub_"
        )

        self.assertEqual(test_bindings["purge_time"], "refill_time_var")
        self.assertEqual(test_bindings["sample_id"], "sample_id_var")
        self.assertEqual(
            post_bindings["purge_time"],
            "post_scrub_purge_time_var",
        )
        self.assertEqual(
            post_bindings["sample_id"],
            "post_scrub_sample_id_var",
        )


class TestProductionComposition(unittest.TestCase):
    def test_final_hmi_composes_focused_components(self):
        self.assertTrue(issubclass(HMI, IdentifierStateMixin))
        self.assertTrue(issubclass(HMI, FiltrationSettingsDialogMixin))

    def test_sample_identifier_rename_does_not_change_sample_time(self):
        result = HMI._rename_identifier_sample_line(
            "Sample Time: 10 sec\nSample: sample-1"
        )

        self.assertEqual(
            result,
            "Sample Time: 10 sec\nSample ID: sample-1",
        )


if __name__ == "__main__":
    unittest.main()
