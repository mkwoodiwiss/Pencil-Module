"""Tests for deterministic MEU CSV row construction."""

import unittest

from pencil.data_logging import DATA_HEADER, PSI_TO_KPA, build_data_row, write_header


class _Module:
    def __init__(self):
        self.calls = []

    def read_rtd(self, channel):
        self.calls.append(("rtd", channel))
        return 21.5

    def read_pressure(self, channel):
        self.calls.append(("pressure", channel))
        return {1: 3.0, 2: 4.0}[channel]


class _Writer:
    def __init__(self):
        self.rows = []

    def writerow(self, row):
        self.rows.append(tuple(row))


class TestDataLogging(unittest.TestCase):
    def test_header_order_is_authoritative(self):
        self.assertEqual(
            DATA_HEADER,
            (
                "timestamp",
                "feed_temperature",
                "feed_tank_pressure_kpa",
                "backwash_tank_pressure_kpa",
                "feed_weight",
                "backwash_weight",
                "cycle",
                "step",
            ),
        )

    def test_write_header_uses_authoritative_schema(self):
        writer = _Writer()
        write_header(writer)
        self.assertEqual(writer.rows, [DATA_HEADER])

    def test_build_data_row_preserves_sensor_and_channel_mapping(self):
        module = _Module()
        weight_calls = []

        def read_weight(channel):
            weight_calls.append(channel)
            return {0: 125.0, 1: 80.0}[channel]

        row = build_data_row(
            module,
            read_weight,
            3,
            "Filter",
            timestamp="10:15:30",
        )

        self.assertEqual(row[0], "10:15:30")
        self.assertEqual(row[1], 21.5)
        self.assertAlmostEqual(row[2], 4.0 * PSI_TO_KPA)
        self.assertAlmostEqual(row[3], 3.0 * PSI_TO_KPA)
        self.assertEqual(row[4:], [125.0, 80.0, 3, "Filter"])
        self.assertEqual(
            module.calls,
            [("rtd", 0), ("pressure", 2), ("pressure", 1)],
        )
        self.assertEqual(weight_calls, [0, 1])


if __name__ == "__main__":
    unittest.main()
