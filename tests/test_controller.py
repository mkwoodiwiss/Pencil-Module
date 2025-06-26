import unittest
from unittest import mock

from tests.test_interfaces import SimulatedPencilModule
from system_control import FiltrationController, TestSettings


class TestFiltrationController(unittest.TestCase):
    def setUp(self):
        self.module = SimulatedPencilModule()
        self.controller = FiltrationController(self.module)

    @mock.patch('time.sleep', lambda *_: None)
    def test_run_single_cycle(self):
        settings = TestSettings(
            project_name="unit",
            filtration_time=0.01,
            backwash_time=0.01,
            refill_time=0.01,
            repeat_count=1,
            sample_time=0.01,
        )
        self.controller.run_test(settings)
        # Expect solenoids toggled
        calls = [call[0] for call in self.module.relay.calls]
        self.assertIn('on', calls)
        self.assertIn('off', calls)


if __name__ == '__main__':
    unittest.main()
