import unittest
from unittest import mock

from tests.simulated_hardware import FakeLib8Relind
import relay_test


class TestRelayCLI(unittest.TestCase):
    def test_basic_commands(self):
        fake_lib = FakeLib8Relind()
        commands = iter(["on 1", "toggle 2", "off 1", "q"])
        with mock.patch.object(relay_test, "lib8relind", fake_lib):
            with mock.patch("builtins.input", lambda _: next(commands)):
                relay_test.main()
        self.assertEqual(
            fake_lib.calls,
            [
                ("set", 1, 1, 1),
                ("set", 1, 2, 1),
                ("set", 1, 1, 0),
            ],
        )


if __name__ == "__main__":
    unittest.main()
