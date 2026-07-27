"""Configuration models for the MF/UF Membrane Evaluation Unit."""

from dataclasses import dataclass


@dataclass(init=False)
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
    feed_tank_pressure_offset: float
    backwash_tank_pressure_offset: float
    feed_temperature_offset: float
    max_weight_phase_time: float
    file_prefix: str

    def __init__(
        self,
        filtration_target: float,
        filtration_by_volume: bool,
        backwash_target: float,
        backwash_by_volume: bool,
        refill_time: float | None = None,
        cycle_count: int = 1,
        sample_time: float = 1.0,
        project: str = "",
        module_id: str = "",
        sample_id: str = "",
        feed_tank_pressure_offset: float = 0.0,
        backwash_tank_pressure_offset: float = 0.0,
        feed_temperature_offset: float = 0.0,
        max_weight_phase_time: float = 3600.0,
        file_prefix: str = "Test",
        purge_time: float | None = None,
    ) -> None:
        selected_purge_time = purge_time if purge_time is not None else refill_time
        if selected_purge_time is None:
            raise TypeError("purge_time or refill_time is required")
        self.filtration_target = filtration_target
        self.filtration_by_volume = filtration_by_volume
        self.backwash_target = backwash_target
        self.backwash_by_volume = backwash_by_volume
        self.purge_time = selected_purge_time
        self.cycle_count = cycle_count
        self.sample_time = sample_time
        self.project = project
        self.module_id = module_id
        self.sample_id = sample_id
        self.feed_tank_pressure_offset = feed_tank_pressure_offset
        self.backwash_tank_pressure_offset = backwash_tank_pressure_offset
        self.feed_temperature_offset = feed_temperature_offset
        self.max_weight_phase_time = max_weight_phase_time
        self.file_prefix = file_prefix

    @property
    def refill_time(self) -> float:
        """Backward-compatible alias for Purge Time."""
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
