"""Production-only safeguards layered on the common MEU hardware interface.

The base hardware module knows how to talk to a Highland scale.  This module
adds the stricter behavior required before a real process run starts:

* issue the Highland ``T`` tare command;
* wait for fresh readings produced after that command;
* require two consecutive readings within +/-0.2 g;
* use at most two ``P`` print requests when continuous output is quiet;
* tare both physical scales concurrently; and
* refuse to start the process if either scale cannot verify zero.

Keep these safeguards in the runtime layer.  The lighter base scale manager is
used by tests and compatibility code, while production startup imports this
subclass through the package exports.
"""

from __future__ import annotations

import threading
import time

from .hardware import MEU as _BaseMEU, _ScaleManager


class _RuntimeScaleManager(_ScaleManager):
    """Highland manager with verified tare and conservative polling fallback."""

    # Highland protocol commands include CRLF terminators.  Do not replace this
    # with a bare ``T`` unless the scale communication mode is changed and
    # physically revalidated.
    TARE_COMMAND = b"T\r\n"

    def __init__(self, *args, **kwargs) -> None:
        # While tare is active, ordinary HMI reads must not enqueue additional
        # print commands and interfere with the verification exchange.
        self._tare_active = False
        super().__init__(*args, **kwargs)

    def _process_tare(self, payload: object) -> None:
        """Execute one queued tare request and signal its waiting caller.

        ``payload`` contains a shared result dictionary, a completion event,
        retry count, and per-attempt timeout.  The operation runs on the scale
        worker thread so all serial writes and reads remain serialized.
        """
        result, completed, attempts, timeout = payload  # type: ignore[misc]
        success = False
        self._tare_active = True
        try:
            for _attempt in range(int(attempts)):
                # A forced reconnect is appropriate here because a process is
                # waiting to start.  Normal background reads use reconnect
                # throttling to avoid repeatedly hammering a missing device.
                if not self._transport.connected and not self._open_serial(force=True):
                    time.sleep(0.2)
                    continue

                # Discard pre-tare bytes.  Verification must be based only on
                # readings received after the T command was sent.
                self._reset_input_buffer()
                if not self._write(self.TARE_COMMAND):
                    time.sleep(0.2)
                    continue

                started = time.monotonic()
                deadline = started + float(timeout)
                consecutive_zero = 0
                received_after_tare = 0
                print_requests = 0

                # Highland scales normally stream readings continuously.  Some
                # configurations are quiet, so request one reading after 0.75 s
                # and, if still necessary, one final reading 0.75 s later.  The
                # two-request cap prevents command flooding on a failing port.
                next_print_fallback = started + 0.75

                while time.monotonic() < deadline and not self._stop_event.is_set():
                    now = time.monotonic()
                    if (
                        received_after_tare < 2
                        and print_requests < 2
                        and now >= next_print_fallback
                    ):
                        if self._write(self.PRINT_COMMAND):
                            print_requests += 1
                        next_print_fallback = now + 0.75

                    try:
                        parsed = self._parse(self._readline())
                    except Exception:
                        # Serial failures close the transport in the lower layer.
                        # Break this attempt so the retry can reconnect cleanly.
                        break
                    if parsed is None:
                        continue

                    received_after_tare += 1
                    self._record(parsed)
                    _text, value, _unit = parsed

                    # Two consecutive values are required because a single zero
                    # can be an old/transitional display response immediately
                    # following the tare command.
                    if abs(value) <= 0.2:
                        consecutive_zero += 1
                        if consecutive_zero >= 2:
                            success = True
                            break
                    else:
                        consecutive_zero = 0

                if success:
                    break

                if not self._transport.connected:
                    self._open_serial(force=True)
                time.sleep(0.2)
        finally:
            # Always wake the waiting automation thread, even if unexpected
            # parsing or transport errors occurred during verification.
            self._tare_active = False
            result["success"] = success
            completed.set()

    def read(self) -> str:
        """Return cached data without disturbing an active tare transaction."""
        if self._tare_active:
            with self._state_lock:
                if self._latest_time > 0:
                    return self._latest_text
        return super().read()


class MEU(_BaseMEU):
    """Production MEU interface with mandatory verified dual-scale tare."""

    # The base constructor reads this class attribute, so replacing it here is
    # enough to build both scale channels with the runtime manager.
    SCALE_MANAGER_CLASS = _RuntimeScaleManager

    def zero_scale(self, channel: int) -> bool:
        """Tare one scale with two attempts and a four-second attempt window."""
        manager = self._effluent_scale if channel == 0 else self._backwash_scale
        return manager.tare(attempts=2, timeout=4.0)

    def zero_scales(self) -> bool:
        """Tare both scales concurrently and raise unless both verify zero.

        Concurrent tare keeps startup time reasonable and ensures one slow or
        disconnected scale does not postpone beginning the other scale's retry
        window.  The method raises rather than returning ``False`` because every
        process run must stop before valves open when either measurement cannot
        be trusted.
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
                f"{names} did not accept tare or did not return two verified zero readings. "
                "The run was not started. Confirm the scale is stable and communicating, then try again."
            )
        return True


# Historical production startup imports this name.  Keep it aligned with MEU.
PencilModule = MEU
