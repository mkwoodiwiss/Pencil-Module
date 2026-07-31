"""Regression tests for hardware construction and scale selection."""

import threading
import unittest
from unittest import mock

from pencil import hardware, hardware_runtime


class _FakeScaleManager:
    instances = []

    def __init__(self, port, baud):
        self.port = port
        self.baud = baud
        self.lock = threading.RLock()
        self.serial = object()
        self.tare_result = True
        self.tare_calls = 0
        self.closed = False
        self.__class__.instances.append(self)

    def tare(self, *args, **kwargs):
        self.tare_calls += 1
        return self.tare_result

    def read(self):
        return f"{self.port}:reading"

    def health(self):
        return {"port": self.port}

    def close(self):
        self.closed = True


class _FactoryMEU(hardware.MEU):
    SCALE_MANAGER_CLASS = _FakeScaleManager


class TestHardwareFactories(unittest.TestCase):
    def setUp(self):
        _FakeScaleManager.instances.clear()

    def _build_module(self):
        with mock.patch.object(hardware, "lib8relind", None), mock.patch.object(
            hardware, "multiio", None
        ):
            return _FactoryMEU(
                effluent_port="filtrate-port",
                backwash_port="backwash-port",
                baud=4800,
            )

    def test_factory_builds_both_scale_managers_with_existing_ports(self):
        module = self._build_module()
        self.addCleanup(module.close)

        self.assertEqual(
            [(item.port, item.baud) for item in _FakeScaleManager.instances],
            [("filtrate-port", 4800), ("backwash-port", 4800)],
        )
        self.assertIs(module.effluent_lock, _FakeScaleManager.instances[0].lock)
        self.assertIs(module.backwash_lock, _FakeScaleManager.instances[1].lock)

    def test_runtime_module_selects_verified_scale_manager(self):
        self.assertIs(
            hardware_runtime.MEU.SCALE_MANAGER_CLASS,
            hardware_runtime._RuntimeScaleManager,
        )
        self.assertTrue(
            issubclass(hardware_runtime._RuntimeScaleManager, hardware._ScaleManager)
        )

    def test_dual_tare_attempts_both_scales_when_first_fails(self):
        module = self._build_module()
        self.addCleanup(module.close)
        first, second = _FakeScaleManager.instances
        first.tare_result = False
        second.tare_result = True

        self.assertFalse(module.zero_scales())
        self.assertEqual(first.tare_calls, 1)
        self.assertEqual(second.tare_calls, 1)

    def test_scale_operations_keep_existing_channel_mapping(self):
        module = self._build_module()
        self.addCleanup(module.close)

        self.assertEqual(module.read_scale(0), "filtrate-port:reading")
        self.assertEqual(module.read_scale(1), "backwash-port:reading")
        self.assertEqual(module.scale_health(0), {"port": "filtrate-port"})
        self.assertEqual(module.scale_health(1), {"port": "backwash-port"})

    def test_close_stops_both_scale_managers(self):
        module = self._build_module()
        first, second = _FakeScaleManager.instances

        module.close()

        self.assertTrue(first.closed)
        self.assertTrue(second.closed)


if __name__ == "__main__":
    unittest.main()
