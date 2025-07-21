import unittest
from unittest import mock

from tests.test_interfaces import SimulatedPencilModule
import system_control


_created_apps = []

class HeadlessHMI:
    """Minimal HMI replacement that runs without a GUI."""

    def __init__(self, module):
        _created_apps.append(self)
        self.module = module
        self.weight = ""
        self.backwash_weight = ""
        self.pressure = ""
        self.temp = ""
        self.update_count = 0

    def after(self, delay, callback):
        # Immediately invoke the callback a limited number of times
        if self.update_count < 2:
            callback()

    def update_data(self):
        self.weight = self.module.read_scale(0)
        self.backwash_weight = self.module.read_scale(1)
        self.pressure = f"{self.module.read_pressure(1):.2f}"
        self.temp = f"{self.module.read_rtd(0):.2f}"
        self.update_count += 1
        self.after(1000, self.update_data)

    def mainloop(self):
        self.update_data()


class TestFullApplication(unittest.TestCase):
    def test_run_main_with_headless_hmi(self):
        with mock.patch("system_control.PencilModule", SimulatedPencilModule), \
             mock.patch("system_control.HMI", HeadlessHMI):
            system_control.main()
        self.assertTrue(_created_apps, "HMI was not instantiated")
        app = _created_apps[-1]
        self.assertEqual(app.weight, "+123.45 g")
        self.assertEqual(app.pressure, "15.00")
        self.assertEqual(app.temp, "20.50")
        self.assertEqual(app.update_count, 2)


if __name__ == "__main__":
    unittest.main()
