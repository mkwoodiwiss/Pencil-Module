"""Production hardware safeguards layered on the MEU hardware interface."""

from __future__ import annotations

import threading
import time

from .hardware import (
    MEU as _BaseMEU,
    _RelayWrapper,
    _ScaleManager,
    lib8relind,
    multiio,
)


class _RuntimeScaleManager(_ScaleManager):
    """Highland scale manager with continuous receive and controlled polling fallback."""

    def __init__(self, *args, **kwargs) -> None:
        self._tare_active = False
        super().__init__(*args, **kwargs)

    def _process_tare(self, payload: object) -> None:
        """Send T and verify two post-tare readings without flooding Print commands."""
        result, completed, attempts, timeout = payload  # type: ignore[misc]
        success = False
        self._tare_active = True
        try:
            for _attempt in range(int(attempts)):
                if self._serial is None and not self._open_serial(force=True):
                    time.sleep(0.2)
                    continue

                # Discard only lines received before the command. The worker remains
                # the sole serial owner, so no other reader can consume the reply.
                try:
                    self._serial.reset_input_buffer()
                except Exception:
                    pass

                # Highland manual: T<CR><LF> is the remote equivalent of the tare key.
                if not self._write(b"T\r\n"):
                    time.sleep(0.2)
                    continue

                started = time.monotonic()
                deadline = started + float(timeout)
                consecutive_zero = 0
                received_after_tare = 0
                print_requests = 0
                next_print_fallback = started + 0.75

                while time.monotonic() < deadline and not self._stop_event.is_set():
                    now = time.monotonic()

                    # Some Highland configurations pause continuous output after T,
                    # or are configured for requested output. Ask for at most two
                    # readings, and only if no fresh line has arrived in time.
                    if (
                        received_after_tare < 2
                        and print_requests < 2
                        and now >= next_print_fallback
                    ):
                        if self._write(b"P\r\n"):
                            print_requests += 1
                        next_print_fallback = now + 0.75

                    try:
                        raw = self._readline()
                    except Exception as exc:
                        self._last_error = repr(exc)
                        self._close_serial()
                        break

                    parsed = self._parse(raw)
                    if parsed is None:
                        continue

                    received_after_tare += 1
                    self._record(parsed)
                    _text, value, _unit = parsed
                    if abs(value) <= 0.2:
                        consecutive_zero += 1
                        if consecutive_zero >= 2:
                            success = True
                            break
                    else:
                        consecutive_zero = 0

                if success:
                    break

                # A timeout can mean tare was rejected because the scale was unstable.
                # Reconnect only when the serial object actually failed.
                if self._serial is None:
                    self._open_serial(force=True)
                time.sleep(0.2)
        finally:
            self._tare_active = False
            result["success"] = success
            completed.set()

    def read(self) -> str:
        """Return cached data, using one queued Print request only when stale."""
        if self._tare_active:
            with self._state_lock:
                if self._latest_time > 0:
                    return self._latest_text
        # The base implementation queues one P command when stale and waits for a
        # genuinely newer reading. It prevents repeated overlapping requests.
        return super().read()


class MEU(_BaseMEU):
    """MEU hardware interface with mandatory verified dual-scale tare."""

    def __init__(
        self,
        relay_stack: int = 1,
        io_stack: int = 2,
        effluent_port: str = "/dev/ttyAMA3",
        backwash_port: str = "/dev/ttyAMA2",
        baud: int = 9600,
        read_delay: float = 0.25,
    ) -> None:
        self._effluent_scale = _RuntimeScaleManager(effluent_port, baud)
        self._backwash_scale = _RuntimeScaleManager(backwash_port, baud)
        self.effluent_lock = self._effluent_scale.lock
        self.backwash_lock = self._backwash_scale.lock
        self._read_delay = read_delay
        self.relay = _RelayWrapper(relay_stack) if lib8relind else None
        if multiio:
            try:
                self.io = multiio.SMmultiio(stack=io_stack, i2c=1)
            except Exception:
                self.io = None
        else:
            self.io = None
        self.pressure_offset_bw = 0.0
        self.pressure_offset_in = 0.0
        self.temp_offset = 0.0

    def zero_scale(self, channel: int) -> bool:
        """Tare one scale and verify two consecutive fresh zero readings."""
        manager = self._effluent_scale if channel == 0 else self._backwash_scale
        return manager.tare(attempts=2, timeout=4.0)

    def zero_scales(self) -> bool:
        """Tare both scales concurrently and refuse to run unless both verify."""
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


PencilModule = MEU
