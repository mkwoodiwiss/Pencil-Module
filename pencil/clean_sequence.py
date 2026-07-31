"""Authoritative Clean process sequence for the MEU."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal


StepKind = Literal["prompt", "timed", "process"]


@dataclass(frozen=True)
class CleanStep:
    """One immutable operator or process action in a Clean cycle."""

    kind: StepKind
    name: str
    target_attribute: str = ""
    mode_attribute: str = ""
    scale_channel: int = 0
    valve_names: tuple[str, ...] = ()


CLEAN_SEQUENCE: tuple[CleanStep, ...] = (
    CleanStep(
        "prompt",
        "Fill the Feed tank with caustic solution, then confirm to continue.",
    ),
    CleanStep("timed", "Caustic Purge", "purge_time", valve_names=("FEED", "WASTE")),
    CleanStep(
        "process",
        "Caustic Filter 1",
        "forward_target",
        "forward_by_weight",
        0,
        ("FEED", "FILTRATE"),
    ),
    CleanStep(
        "process",
        "Caustic Backwash 1",
        "backwash_target",
        "backwash_by_weight",
        1,
        ("BACKWASH", "BACKWASH_EFFLUENT"),
    ),
    CleanStep("timed", "Caustic Soak", "soak_time"),
    CleanStep(
        "process",
        "Caustic Filter 2",
        "forward_target",
        "forward_by_weight",
        0,
        ("FEED", "FILTRATE"),
    ),
    CleanStep(
        "process",
        "Caustic Backwash 2",
        "backwash_target",
        "backwash_by_weight",
        1,
        ("BACKWASH", "BACKWASH_EFFLUENT"),
    ),
    CleanStep(
        "prompt",
        "Replace the Feed tank contents with DI water, then confirm to continue.",
    ),
    CleanStep("timed", "DI Rinse 1 Purge", "purge_time", valve_names=("FEED", "WASTE")),
    CleanStep(
        "process",
        "DI Rinse 1 Filter",
        "rinse_forward_target",
        "rinse_forward_by_weight",
        0,
        ("FEED", "FILTRATE"),
    ),
    CleanStep(
        "process",
        "DI Rinse 1 Backwash",
        "rinse_backwash_target",
        "rinse_backwash_by_weight",
        1,
        ("BACKWASH", "BACKWASH_EFFLUENT"),
    ),
    CleanStep(
        "prompt",
        "Fill the Feed tank with acid solution, then confirm to continue.",
    ),
    CleanStep("timed", "Acid Purge", "purge_time", valve_names=("FEED", "WASTE")),
    CleanStep(
        "process",
        "Acid Filter 1",
        "forward_target",
        "forward_by_weight",
        0,
        ("FEED", "FILTRATE"),
    ),
    CleanStep(
        "process",
        "Acid Backwash 1",
        "backwash_target",
        "backwash_by_weight",
        1,
        ("BACKWASH", "BACKWASH_EFFLUENT"),
    ),
    CleanStep("timed", "Acid Soak", "soak_time"),
    CleanStep(
        "process",
        "Acid Filter 2",
        "forward_target",
        "forward_by_weight",
        0,
        ("FEED", "FILTRATE"),
    ),
    CleanStep(
        "process",
        "Acid Backwash 2",
        "backwash_target",
        "backwash_by_weight",
        1,
        ("BACKWASH", "BACKWASH_EFFLUENT"),
    ),
    CleanStep(
        "prompt",
        "Replace the acid in the Feed tank with DI water, then confirm before DI Rinse 2.",
    ),
    CleanStep("timed", "DI Rinse 2 Purge", "purge_time", valve_names=("FEED", "WASTE")),
    CleanStep(
        "process",
        "DI Rinse 2 Filter",
        "rinse_forward_target",
        "rinse_forward_by_weight",
        0,
        ("FEED", "FILTRATE"),
    ),
    CleanStep(
        "process",
        "DI Rinse 2 Backwash",
        "rinse_backwash_target",
        "rinse_backwash_by_weight",
        1,
        ("BACKWASH", "BACKWASH_EFFLUENT"),
    ),
)


def resolve_valves(owner: object, step: CleanStep) -> tuple[int, ...]:
    """Resolve symbolic valve names against an automation system instance."""
    return tuple(int(getattr(owner, name)) for name in step.valve_names)


class CleanSequenceMixin:
    """Execute the authoritative Clean sequence using automation phase methods."""

    def _run_clean_cycle(self) -> None:
        config = self.config
        for step in CLEAN_SEQUENCE:
            if step.kind == "prompt":
                self._prompt(step.name)
                continue

            valves = resolve_valves(self, step)
            target = float(getattr(config, step.target_attribute))
            if step.kind == "timed":
                self._timed_phase(step.name, target, valves, config.sample_time)
                continue

            self._process_phase(
                step.name,
                target,
                bool(getattr(config, step.mode_attribute)),
                step.scale_channel,
                valves,
            )


__all__ = ["CLEAN_SEQUENCE", "CleanSequenceMixin", "CleanStep", "resolve_valves"]
