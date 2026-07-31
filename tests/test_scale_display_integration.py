import os
import unittest
from unittest import mock

import system_control
from pencil.emulation import EmulatedMEU


class TestScaleDisplayIntegration(unittest.TestCase):
    """Integration test using the real Tk HMI with deterministic hardware."""

    def setUp(self):
        if not os.environ.get("DISPLAY"):
            self.skipTest("Display not available")

    def test_scale_values_and_display_geometry(self):
        module = EmulatedMEU()
        module.set_scale_value(0, 12.3)
        app = None
        try:
            with mock.patch.object(
                system_control.HMI,
                "after",
                lambda self, ms, cb: None,
            ):
                app = system_control.HMI(module)
                app.update_data()

                weight = app.weight_var.get()
                self.assertRegex(weight, r"^\d+\.\d+$")
                self.assertTrue(app.winfo_geometry().startswith("800x480"))
        finally:
            if app is not None:
                app.destroy()
            module.close()


if __name__ == "__main__":
    unittest.main()
