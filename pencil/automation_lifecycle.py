"""Shared run lifecycle for MEU automation systems."""

from __future__ import annotations

import time
from collections.abc import Callable
from typing import Any


class AutomationLifecycleMixin:
    """Centralize safe startup and guaranteed shutdown for process runs."""

    config: Any

    def _prepare_run(
        self,
        *,
        prefix: str,
        final_id: str,
        close_valves: bool,
        tare_scales: bool,
    ) -> None:
        """Reset cancellation, establish safe state, open logs, and apply offsets."""
        self._stop_event.clear()
        if close_valves:
            self.close_all_valves()
        config = self.config
        self._open_logs(
            prefix,
            config.project,
            config.module_id,
            final_id,
            config,
        )
        self._apply_offsets(config)
        if tare_scales:
            self.module.zero_scales()
            time.sleep(1.0)

    def _run_managed(
        self,
        body: Callable[[], None],
        *,
        prefix: str,
        final_id: str,
        close_valves: bool = True,
        tare_scales: bool = True,
    ) -> None:
        """Run one process body and always return hardware and files to a safe state."""
        try:
            self._prepare_run(
                prefix=prefix,
                final_id=final_id,
                close_valves=close_valves,
                tare_scales=tare_scales,
            )
            body()
        finally:
            self.stop_test()


__all__ = ["AutomationLifecycleMixin"]
