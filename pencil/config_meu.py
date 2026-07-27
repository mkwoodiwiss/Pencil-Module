"""Configuration models for the MF/UF Membrane Evaluation Unit."""

from dataclasses import dataclass


@dataclass
class FiltrationConfig:
    filtration_target: float
    filtration_by_volume: bool
    backwash_target: float
    backwash_by_volume: bool
    purge_time: float
    cycle_count: int
    sample_time: float
    project: str
    module_id: str
    sample_id: str
    feed_tank_pressure_offset: float = 0.0
    backwash_tank_pressure_offset: float = 0.0
    feed_temperature_offset: float = 0.0
    max_weight_phase_time: float = 3600.0
    file_prefix: str = "Test"

    @property
    def refill_time(self) -> float:
        """Backward-compatible alias for the former purge-time field."""
        return self.purge_time


@dataclass
class CleanConfig:
    forward_target: float
    forward_by_volume: bool
    soak_time: float
    backwash_target: float
    backwash_by_volume: bool
    rinse_forward_target: float
    rinse_forward_by_volume: bool
    rinse_backwash_target: float
    rinse_backwash_by_volume: bool
    cycle_count: int
    sample_time: float
    purge_time: float
    project: str
    module_id: str
    solution: str
    feed_tank_pressure_offset: float = 0.0
    backwash_tank_pressure_offset: float = 0.0
    feed_temperature_offset: float = 0.0
    max_weight_phase_time: float = 3600.0


@dataclass
class BenchmarkConfig:
    """Passive benchmark logging configuration retained for maintenance use."""

    duration: float
    interval: float
    project: str
    module_id: str
    sample_id: str
    feed_tank_pressure_offset: float = 0.0
    backwash_tank_pressure_offset: float = 0.0
    feed_temperature_offset: float = 0.0
