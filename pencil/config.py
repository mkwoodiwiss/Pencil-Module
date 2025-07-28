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
    project: str
    module_id: str
    sample_id: str
    pressure_offset: float = 0.0
    temp_offset: float = 0.0


@dataclass
class CleanConfig:
    """Configuration for an automated clean cycle."""

    forward_target: float
    forward_by_volume: bool
    forward_soak: float
    backwash_target: float
    backwash_by_volume: bool
    backwash_soak: float
    cycle_count: int
    sample_time: float
    rinse_time: float
    project: str
    module_id: str
    solution: str
    pressure_offset: float = 0.0
    temp_offset: float = 0.0


@dataclass
class BenchmarkConfig:
    """Configuration for a benchmark logging run."""

    duration: float
    interval: float
    project: str
    module_id: str
    sample_id: str
    pressure_offset: float = 0.0
    temp_offset: float = 0.0
