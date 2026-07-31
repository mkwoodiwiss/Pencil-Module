"""Regression tests for the flattened production HMI composition."""

import types
import unittest
from unittest import mock

from pencil.hmi_filtration_dialogs import FiltrationSettingsDialogMixin
from pencil.hmi_identifier_state import IdentifierStateMixin
from pencil.hmi_post_scrub_state import PostScrubStateMixin
from pencil.hmi_summary_formatting import SummaryFormattingMixin
from pencil.hmi_tk_clone_compat import TkCloneCompatibilityMixin
from pencil.hmi_v2_clone_test_layout import HMI as CloneLayoutHMI
from pencil.hmi_v2_integrated import HMI
from pencil.hmi_widget_clone import WidgetTreeCloneMixin


class TestHMIComposition(unittest.TestCase):
    def test_production_mro_uses_focused_components_directly(self):
        mro = HMI.__mro__
        self.assertIn(FiltrationSettingsDialogMixin, mro)
        self.assertIn(IdentifierStateMixin, mro)
        self.assertIn(PostScrubStateMixin, mro)
        self.assertIn(SummaryFormattingMixin, mro)
        self.assertIn(TkCloneCompatibilityMixin, mro)
        self.assertIn(CloneLayoutHMI, mro)
        self.assertIn(WidgetTreeCloneMixin, mro)

    def test_obsolete_patch_classes_are_not_in_production_mro(self):
        module_names = {base.__module__ for base in HMI.__mro__}
        self.assertNotIn("pencil.hmi_v2_post_scrub_dialog", module_names)
        self.assertNotIn("pencil.hmi_v2_summary_text", module_names)
        self.assertNotIn("pencil.hmi_v2_tk_compat", module_names)

    def test_clone_layout_delegates_summary_formatting(self):
        self.assertNotIn("_update_flush_summary", CloneLayoutHMI.__dict__)
        self.assertNotIn("_update_post_scrub_summary", CloneLayoutHMI.__dict__)
        self.assertIs(HMI._update_flush_summary, SummaryFormattingMixin._update_flush_summary)
        self.assertIs(
            HMI._update_post_scrub_summary,
            SummaryFormattingMixin._update_post_scrub_summary,
        )

    def test_clone_layout_delegates_generic_widget_copying(self):
        for method_name in (
            "_managed_children",
            "_copy_widget_options",
            "_copy_grid_configuration",
            "_apply_geometry",
            "_clone_widget",
        ):
            self.assertNotIn(method_name, CloneLayoutHMI.__dict__)
            self.assertTrue(hasattr(WidgetTreeCloneMixin, method_name))

    def test_clone_button_commands_preserve_process_actions(self):
        hmi = CloneLayoutHMI.__new__(CloneLayoutHMI)
        hmi._toggle_flush = mock.Mock()
        hmi._toggle_post_scrub = mock.Mock()
        hmi._edit_flush_settings = mock.Mock()
        hmi._edit_post_scrub_settings = mock.Mock()
        hmi.calibrate = mock.Mock()
        hmi.module = types.SimpleNamespace(zero_scale=mock.Mock())

        self.assertIs(hmi._clone_button_command("Start", "flush"), hmi._toggle_flush)
        self.assertIs(
            hmi._clone_button_command("Start", "post_scrub"),
            hmi._toggle_post_scrub,
        )
        self.assertIs(
            hmi._clone_button_command("Edit Settings", "flush"),
            hmi._edit_flush_settings,
        )
        self.assertIs(
            hmi._clone_button_command("Edit Settings", "post_scrub"),
            hmi._edit_post_scrub_settings,
        )
        self.assertIs(hmi._clone_button_command("Calibrate", "flush"), hmi.calibrate)

        hmi._clone_button_command("Tare FIL", "flush")()
        hmi._clone_button_command("Tare BW EFL", "flush")()
        self.assertEqual(
            hmi.module.zero_scale.call_args_list,
            [mock.call(0), mock.call(1)],
        )
        self.assertIsNone(hmi._clone_button_command("Unknown", "flush"))

    def test_sample_identifier_rename_leaves_sample_time_unchanged(self):
        text = "Sample Time: 1 s\nSample: ABC"
        self.assertEqual(
            SummaryFormattingMixin._rename_identifier_sample_line(text),
            "Sample Time: 1 s\nSample ID: ABC",
        )


if __name__ == "__main__":
    unittest.main()
