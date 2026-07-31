"""CSV schema and sensor-row construction for MEU test logs."""

from __future__ import annotations

import time
from collections.abc import Callable, Sequence


PSI_TO_KPA = 6.894757293168
DATA_HEADER = (
    "timestamp",
    "feed_temperature",
    "feed_tank_pressure_kpa",
    "backwash_tank_pressure_kpa",
    "feed_weight",
    "backwash_weight",
    "cycle",
    "step",
)


def build_data_row(
    module,
    read_weight: Callable[[int], float],
    cycle: int,
    step: str,
    *,
    timestamp: str | None = None,
) -> list[object]:
    """Read one synchronized application-level snapshot for a CSV data row."""
    row_timestamp = time.strftime("%H:%M:%S") if timestamp is None else timestamp
    return [
        row_timestamp,
        module.read_rtd(0),
        module.read_pressure(2) * PSI_TO_KPA,
        module.read_pressure(1) * PSI_TO_KPA,
        read_weight(0),
        read_weight(1),
        cycle,
        step,
    ]


def write_header(writer) -> None:
    """Write the authoritative MEU data header to a CSV writer."""
    writer.writerow(DATA_HEADER)


__all__ = ["DATA_HEADER", "PSI_TO_KPA", "build_data_row", "write_header"]
