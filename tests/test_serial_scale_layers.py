"""Regression tests for separated serial transport and Highland protocol layers."""

import unittest
from unittest import mock

from pencil import hardware
from pencil.highland_scale import HighlandScaleManager
from pencil.serial_transport import SerialLineTransport


class _Connection:
    def __init__(self, lines=()):
        self.lines = list(lines)
        self.writes = []
        self.closed = False
        self.reset_count = 0
        self.flush_count = 0

    def reset_input_buffer(self):
        self.reset_count += 1

    def readline(self):
        return self.lines.pop(0) if self.lines else b""

    def write(self, command):
        self.writes.append(command)

    def flush(self):
        self.flush_count += 1

    def close(self):
        self.closed = True


class TestSerialLineTransport(unittest.TestCase):
    def test_open_uses_existing_port_baud_timeout_and_resets_input(self):
        connection = _Connection()
        factory = mock.Mock(return_value=connection)
        transport = SerialLineTransport(
            "/dev/test",
            9600,
            timeout=0.25,
            serial_factory=factory,
        )

        self.assertTrue(transport.open(force=True))

        factory.assert_called_once_with("/dev/test", 9600, timeout=0.25)
        self.assertIs(transport.connection, connection)
        self.assertEqual(connection.reset_count, 1)
        self.assertEqual(transport.last_error, "")

    def test_write_delegates_and_flushes(self):
        connection = _Connection()
        transport = SerialLineTransport("port", 9600, serial_factory=lambda *_args, **_kwargs: connection)
        transport.open(force=True)

        self.assertTrue(transport.write(b"P\r\n"))

        self.assertEqual(connection.writes, [b"P\r\n"])
        self.assertEqual(connection.flush_count, 1)

    def test_read_failure_records_error_and_closes_connection(self):
        connection = _Connection()
        connection.readline = mock.Mock(side_effect=OSError("serial failed"))
        transport = SerialLineTransport("port", 9600, serial_factory=lambda *_args, **_kwargs: connection)
        transport.open(force=True)

        with self.assertRaisesRegex(OSError, "serial failed"):
            transport.readline()

        self.assertFalse(transport.connected)
        self.assertTrue(connection.closed)
        self.assertIn("serial failed", transport.last_error)


class TestHighlandProtocolLayer(unittest.TestCase):
    def test_historical_scale_manager_alias_points_to_protocol_layer(self):
        self.assertIs(hardware._ScaleManager, HighlandScaleManager)
        self.assertIs(hardware.MEU.SCALE_MANAGER_CLASS, HighlandScaleManager)

    def test_parser_preserves_highland_weight_formatting(self):
        self.assertEqual(
            HighlandScaleManager._parse(b"  +12.34 g\r\n"),
            ("+12.3 g", 12.34, "g"),
        )
        self.assertEqual(
            HighlandScaleManager._parse(b" - 6.0 g\r\n"),
            ("-6.0 g", -6.0, "g"),
        )
        self.assertIsNone(HighlandScaleManager._parse(b"not a weight"))

    def test_protocol_commands_remain_unchanged(self):
        self.assertEqual(HighlandScaleManager.TARE_COMMAND, b"Z\r\n")
        self.assertEqual(HighlandScaleManager.PRINT_COMMAND, b"P\r\n")


if __name__ == "__main__":
    unittest.main()
