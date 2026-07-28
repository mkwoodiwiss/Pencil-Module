"""Production hardware safeguards layered on the MEU hardware interface."""

from __future__ import annotations

import threading

from .hardware import MEU as _BaseMEU


class MEU(_BaseMEU):
    """MEU hardware interface with mandatory verified dual-scale tare."""

    def zero_scale(self, channel: int) -> bool:
        """Tare one scale with faster two-reading verification.

        The serial worker still requires two consecutive fresh readings within
        +/-0.2 g, but each attempt now has a shorter two-second verification
        window and only one retry. This keeps successful tares quick without
        weakening the two-reading confirmation.
        """
        manager = self._effluent_scale if channel == 0 else self._backwash_scale
        return manager.tare(attempts=2, timeout=2.0)

    def zero_scales(self) -> bool:
        """Tare both scales concurrently and refuse to continue unless both verify.

        Each scale manager waits for two fresh, near-zero readings after issuing
        its tare command. Running both operations concurrently prevents one slow
        scale from unnecessarily delaying the other while still blocking the run
        until both have completed.
        """
        results = {0: False, 1: False}

        def tare_one(channel: int) -> None:
            results[channel] = self.zero_scale(channel)

        threads = [
            threading.Thread(target=tare_one, args=(0,), daemon=True),
            threading.Thread(target=tare_one, args=(1,), daemon=True),
        ]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()

        failed = []
        if not results[0]:
            failed.append("Filtrate scale")
        if not results[1]:
            failed.append("BW Effluent scale")

        if failed:
            names = " and ".join(failed)
            raise RuntimeError(
                f"{names} did not complete a verified tare. "
                "The run was not started. Check the scale connection and try again."
            )
        return True


PencilModule = MEU
