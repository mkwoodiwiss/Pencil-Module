import os
import unittest
from unittest import mock

from tests.simulated_hardware import FakeRelay8, FakeMultiIO, FakeLib8Relind
import system_control


class TestScaleDisplayIntegration(unittest.TestCase):
    """Integration test using real scales and display."""

    def setUp(self):
        # Skip the test when no display is available (e.g., headless CI)
        if not os.environ.get("DISPLAY"):
            self.skipTest("Display not available")

    def test_real_scales_and_display(self):
        # Patch relay and IO boards with simulated versions
        with mock.patch.object(system_control, "lib8relind", FakeLib8Relind(), create=True), \
             mock.patch.object(system_control, "multiio", mock.Mock(SMmultiio=FakeMultiIO), create=True), \
             mock.patch.object(system_control.HMI, "after", lambda self, ms, cb: None):
            module = system_control.PencilModule()
            app = system_control.HMI(module)
            # Perform a single data refresh without entering the main loop
            app.update_data()
            weight = app.weight_var.get()
            # Weight string should contain a numeric value and unit
            self.assertRegex(weight, r"[+-]?\d+\.\d+\s*\w")
            # GUI should be sized for the official Pi display
            self.assertTrue(app.winfo_geometry().startswith("800x480"))
            app.destroy()


if __name__ == "__main__":
    unittest.main()
