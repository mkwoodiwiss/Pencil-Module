"""Regression tests for the flattened production HMI composition."""

import unittest

from pencil.hmi_filtration_dialogs import FiltrationSettingsDialogMixin
from pencil.hmi_identifier_state import IdentifierStateMixin
from pencil.hmi_post_scrub_state import PostScrubStateMixin
from pencil.hmi_summary_formatting import SummaryFormattingMixin
from pencil.hmi_tk_clone_compat import TkCloneCompatibilityMixin
from pencil.hmi_v2_clone_test_layout import HMI as CloneLayoutHMI
from pencil.hmi_v2_integrated import HMI


class TestHMIComposition(unittest.TestCase):
    def test_production_mro_uses_focused_components_directly(self):
        mro = HMI.__mro__
        self.assertIn(FiltrationSettingsDialogMixin, mro)
        self.assertIn(IdentifierStateMixin, mro)
        self.assertIn(PostScrubStateMixin, mro)
        self.assertIn(SummaryFormattingMixin, mro)
        self.assertIn(TkCloneCompatibilityMixin, mro)
        self.assertIn(CloneLayoutHMI, mro)

    def test_obsolete_patch_classes_are_not_in_production_mro(self):
        module_names = {base.__module__ for base in HMI.__mro__}
        self.assertNotIn("pencil.hmi_v2_post_scrub_dialog", module_names)
        self.assertNotIn("pencil.hmi_v2_summary_text", module_names)
        self.assertNotIn("pencil.hmi_v2_tk_compat", module_names)

    def test_sample_identifier_rename_leaves_sample_time_unchanged(self):
        text = "Sample Time: 1 s\nSample: ABC"
        self.assertEqual(
            SummaryFormattingMixin._rename_identifier_sample_line(text),
            "Sample Time: 1 s\nSample ID: ABC",
        )


if __name__ == "__main__":
    unittest.main()
