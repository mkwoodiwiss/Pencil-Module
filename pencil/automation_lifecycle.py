"""Shared startup and shutdown policy for all MEU automation systems.

Every process type should enter through :meth:`_run_managed`.  That wrapper is
the safety boundary that guarantees ``stop_test()`` runs after normal
completion, operator cancellation, or an exception.  Do not bypass it when
adding a new process unless the caller provides an equivalent ``try/finally``
with valve and log cleanup.

The mixin intentionally assumes the concrete automation class provides:

* ``config`` with project/module/offset fields;
* ``module`` with scale and instrument methods;
* ``_stop_event``;
* ``close_all_valves()``;
* ``_open_logs()``;
* ``_apply_offsets()``; and
* ``stop_test()``.

This keeps common lifecycle policy in one place without forcing another deep
inheritance tree.
"""

from __future__ import annotations

import time
from collections.abc import Callable
from typing import Any


class AutomationLifecycleMixin:
    """Centralize safe startup and guaranteed shutdown for process runs."""

    # The concrete automation classes provide richer config types.  ``Any`` is
    # used here to avoid coupling the lifecycle helper to every process model.
    config: Any

    def _prepare_run(
        self,
        *,
        prefix: str,
        final_id: str,
        close_valves: bool,
        tare_scales: bool,
    ) -> None:
        """Prepare one run in the required safety and logging order.

        Order matters:

        1. Clear a previous cancellation request.
        2. Establish the requested all-valves-closed state.
        3. Open this run's exact data/settings files.
        4. Apply the configuration's instrument offsets.
        5. Tare and verify both scales when the process requires it.

        Opening logs before tare means a later startup failure still has a
        deterministic lifecycle and can be closed by ``stop_test()``.  Valves
        remain closed throughout preparation.
        """
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
            # Production ``zero_scales`` raises when either scale fails verified
            # tare.  That exception deliberately prevents the process body from
            # opening valves and is cleaned up by ``_run_managed`` below.
            self.module.zero_scales()

            # Allow the first stable post-tare readings to populate the cache
            # before a process body begins evaluating weight stop conditions.
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
        """Run one process body and always leave hardware and files safe.

        ``stop_test`` is the single cleanup path.  It must remain idempotent
        because it can be reached after partial preparation, normal completion,
        cancellation, or an unexpected exception.
        """
        try:
            self._prepare_run(
                prefix=prefix,
                final_id=final_id,
                close_valves=close_valves,
                tare_scales=tare_scales,
            )
            body()
        finally:
            # Never replace this with cleanup only on the success path.  The
            # finally block is what prevents exceptions from leaving outputs on
            # or file handles open.
            self.stop_test()


__all__ = ["AutomationLifecycleMixin"]
