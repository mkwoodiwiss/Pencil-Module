"""Tests for production-safe selection of the emulated hardware backend."""

from __future__ import annotations

import unittest
from unittest import mock

import system_control
from pencil.emulation import EmulatedMEU


class EmulatedStartupTests(unittest.TestCase):
    def test_emulation_flag_accepts_explicit_true_values(self) -> None:
        for value in ("1", "true", "TRUE", "yes", "on", " On "):
            with self.subTest(value=value):
                self.assertTrue(system_control._emulation_requested({"MEU_EMULATE_RPI": value}))

    def test_emulation_flag_defaults_to_production(self) -> None:
        for value in ("", "0", "false", "no", "production", "unexpected"):
            with self.subTest(value=value):
                self.assertFalse(system_control._emulation_requested({"MEU_EMULATE_RPI": value}))

    def test_factory_returns_emulator_only_when_requested(self) -> None:
        with mock.patch.dict("os.environ", {"MEU_EMULATE_RPI": "1"}, clear=False):
            module = system_control._create_module()
        try:
            self.assertIsInstance(module, EmulatedMEU)
        finally:
            module.close()

    def test_factory_preserves_patchable_production_constructor(self) -> None:
        sentinel = object()
        with mock.patch.dict("os.environ", {}, clear=True):
            with mock.patch.object(system_control, "PencilModule", return_value=sentinel) as constructor:
                self.assertIs(system_control._create_module(), sentinel)
        constructor.assert_called_once_with()


if __name__ == "__main__":
    unittest.main()
