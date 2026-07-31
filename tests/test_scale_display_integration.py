import gc
import os
import unittest
from unittest import mock

from tests.simulated_hardware import FakeMultiIO, FakeLib8Relind
import system_control


class TestScaleDisplayIntegration(unittest.TestCase):
    """Integration test using production scale managers and the real Tk display."""

    def setUp(self):
        if not os.environ.get("DISPLAY"):
            self.skipTest("Display not available")

    def test_real_scales_and_display(self):
        module = None
        app = None
        try:
            with mock.patch.object(
                system_control,
                "lib8relind",
                FakeLib8Relind(),
                create=True,
            ), mock.patch.object(
                system_control,
                "multiio",
                mock.Mock(SMmultiio=FakeMultiIO),
                create=True,
            ), mock.patch.object(
                system_control.HMI,
                "after",
                lambda self, ms, cb: None,
            ):
                module = system_control.PencilModule()
                app = system_control.HMI(module)
                app.update_data()

                weight = app.weight_var.get()
                self.assertRegex(weight, r"^\d+\.\d+$")
                self.assertTrue(app.winfo_geometry().startswith("800x480"))
        finally:
            # Tk must be destroyed on the main test thread, then the scale worker
            # threads must be stopped before their owning objects are collected.
            if app is not None:
                app.destroy()
                app = None
            if module is not None:
                module.close()
                module = None
            gc.collect()


if __name__ == "__main__":
    unittest.main()
