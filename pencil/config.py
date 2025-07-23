"""Data model definitions for the Pencil Module."""

from dataclasses import dataclass


@dataclass
class FiltrationConfig:
    """Configuration for an automated filtration test."""

    filtration_target: float
    filtration_by_volume: bool
    backwash_target: float
    backwash_by_volume: bool
    refill_time: float
    repeat_count: int
    sample_time: float
    project_name: str
    pressure_offset: float = 0.0
    temp_offset: float = 0.0
