"""Configuration models for the MF/UF Membrane Evaluation Unit."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


def _resolve_weight_mode(preferred: bool | None, legacy: bool | None) -> bool:
    """Resolve a current weight-mode option with its legacy volume alias."""
    return bool(legacy) if preferred is None else bool(preferred)


def _assign(instance: object, **values: Any) -> None:
    """Assign declared dataclass fields without repeating constructor boilerplate."""
    for name, value in values.items():
        setattr(instance, name, value)


@dataclass(init=False)
class FiltrationConfig:
    filtration_target: float
    filtration_by_weight: bool
    backwash_target: float
    backwash_by_weight: bool
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
        filtration_by_weight: bool | None = None,
        backwash_target: float = 0.0,
        backwash_by_weight: bool | None = None,
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
        filtration_by_volume: bool | None = None,
        backwash_by_volume: bool | None = None,
    ) -> None:
        selected_purge_time = purge_time if purge_time is not None else refill_time
        if selected_purge_time is None:
            raise TypeError("purge_time or refill_time is required")

        _assign(
            self,
            filtration_target=filtration_target,
            filtration_by_weight=_resolve_weight_mode(
                filtration_by_weight,
                filtration_by_volume,
            ),
            backwash_target=backwash_target,
            backwash_by_weight=_resolve_weight_mode(
                backwash_by_weight,
                backwash_by_volume,
            ),
            purge_time=selected_purge_time,
            cycle_count=cycle_count,
            sample_time=sample_time,
            project=project,
            module_id=module_id,
            sample_id=sample_id,
            feed_tank_pressure_offset=feed_tank_pressure_offset,
            backwash_tank_pressure_offset=backwash_tank_pressure_offset,
            feed_temperature_offset=feed_temperature_offset,
            max_weight_phase_time=max_weight_phase_time,
            file_prefix=file_prefix,
        )

    @property
    def refill_time(self) -> float:
        """Backward-compatible alias for Purge Time."""
        return self.purge_time

    @property
    def filtration_by_volume(self) -> bool:
        """Deprecated alias for filtration_by_weight."""
        return self.filtration_by_weight

    @property
    def backwash_by_volume(self) -> bool:
        """Deprecated alias for backwash_by_weight."""
        return self.backwash_by_weight


@dataclass(init=False)
class CleanConfig:
    forward_target: float
    forward_by_weight: bool
    soak_time: float
    backwash_target: float
    backwash_by_weight: bool
    rinse_forward_target: float
    rinse_forward_by_weight: bool
    rinse_backwash_target: float
    rinse_backwash_by_weight: bool
    cycle_count: int
    sample_time: float
    purge_time: float
    project: str
    module_id: str
    solution: str
    feed_tank_pressure_offset: float
    backwash_tank_pressure_offset: float
    feed_temperature_offset: float
    max_weight_phase_time: float

    def __init__(
        self,
        forward_target: float,
        forward_by_weight: bool | None = None,
        soak_time: float = 0.0,
        backwash_target: float = 0.0,
        backwash_by_weight: bool | None = None,
        rinse_forward_target: float = 0.0,
        rinse_forward_by_weight: bool | None = None,
        rinse_backwash_target: float = 0.0,
        rinse_backwash_by_weight: bool | None = None,
        cycle_count: int = 1,
        sample_time: float = 1.0,
        purge_time: float = 0.0,
        project: str = "",
        module_id: str = "",
        solution: str = "",
        feed_tank_pressure_offset: float = 0.0,
        backwash_tank_pressure_offset: float = 0.0,
        feed_temperature_offset: float = 0.0,
        max_weight_phase_time: float = 3600.0,
        forward_by_volume: bool | None = None,
        backwash_by_volume: bool | None = None,
        rinse_forward_by_volume: bool | None = None,
        rinse_backwash_by_volume: bool | None = None,
    ) -> None:
        _assign(
            self,
            forward_target=forward_target,
            forward_by_weight=_resolve_weight_mode(
                forward_by_weight,
                forward_by_volume,
            ),
            soak_time=soak_time,
            backwash_target=backwash_target,
            backwash_by_weight=_resolve_weight_mode(
                backwash_by_weight,
                backwash_by_volume,
            ),
            rinse_forward_target=rinse_forward_target,
            rinse_forward_by_weight=_resolve_weight_mode(
                rinse_forward_by_weight,
                rinse_forward_by_volume,
            ),
            rinse_backwash_target=rinse_backwash_target,
            rinse_backwash_by_weight=_resolve_weight_mode(
                rinse_backwash_by_weight,
                rinse_backwash_by_volume,
            ),
            cycle_count=cycle_count,
            sample_time=sample_time,
            purge_time=purge_time,
            project=project,
            module_id=module_id,
            solution=solution,
            feed_tank_pressure_offset=feed_tank_pressure_offset,
            backwash_tank_pressure_offset=backwash_tank_pressure_offset,
            feed_temperature_offset=feed_temperature_offset,
            max_weight_phase_time=max_weight_phase_time,
        )

    @property
    def forward_by_volume(self) -> bool:
        """Deprecated alias for forward_by_weight."""
        return self.forward_by_weight

    @property
    def backwash_by_volume(self) -> bool:
        """Deprecated alias for backwash_by_weight."""
        return self.backwash_by_weight

    @property
    def rinse_forward_by_volume(self) -> bool:
        """Deprecated alias for rinse_forward_by_weight."""
        return self.rinse_forward_by_weight

    @property
    def rinse_backwash_by_volume(self) -> bool:
        """Deprecated alias for rinse_backwash_by_weight."""
        return self.rinse_backwash_by_weight


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


__all__ = ["BenchmarkConfig", "CleanConfig", "FiltrationConfig"]
