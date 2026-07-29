"""Production hardware safeguards layered on the MEU hardware interface."""

from __future__ import annotations

from collections import deque
from datetime import datetime
import os
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
    """Highland scale manager with deterministic tare verification.

    The scale worker remains the sole owner of the serial port. Tare does not
    clear the input buffer, issue Print commands, or reconnect a healthy port.
    Every command and received line is written to a commissioning trace.
    """

    def __init__(self, *args, scale_name: str, **kwargs) -> None:
        self.scale_name = scale_name
        self._tare_active = False
        self._reading_sequence = 0
        self._recent_values: deque[tuple[float, float]] = deque(maxlen=12)
        self._last_tare_error = ""
        self._trace_lock = threading.Lock()
        self._trace_path = os.path.join("logs", "scale_serial_trace.log")
        super().__init__(*args, **kwargs)
        self._trace("STATE", f"manager started port={self.port} baud={self.baud}")

    def _trace(self, direction: str, message: str) -> None:
        """Append a timestamped scale communication entry without affecting I/O."""
        try:
            os.makedirs(os.path.dirname(self._trace_path), exist_ok=True)
            stamp = datetime.now().isoformat(timespec="milliseconds")
            line = f"{stamp} [{self.scale_name}] {direction} {message}\n"
            with self._trace_lock:
                with open(self._trace_path, "a", encoding="utf-8") as handle:
                    handle.write(line)
        except Exception:
            # Diagnostics must never interrupt scale operation.
            pass

    def _readline(self) -> bytes:
        raw = super()._readline()
        if raw:
            self._trace("RX", repr(raw))
        return raw

    def _write(self, command: bytes) -> bool:
        self._trace("TX", repr(command))
        success = super()._write(command)
        if not success:
            self._trace("ERROR", f"write failed: {self._last_error}")
        return success

    def _record(self, parsed: tuple[str, float, str]) -> None:
        super()._record(parsed)
        _text, value, _unit = parsed
        with self._state_lock:
            self._reading_sequence += 1
            self._recent_values.append((time.monotonic(), value))

    def _wait_for_stable_input(self, timeout: float = 5.0) -> tuple[bool, str]:
        """Wait for a fresh, stable group of readings before sending tare."""
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline and not self._stop_event.is_set():
            now = time.monotonic()
            with self._state_lock:
                recent = [
                    value
                    for timestamp, value in self._recent_values
                    if now - timestamp <= 2.0
                ]
                latest_time = self._latest_time

            if latest_time <= 0 or now - latest_time > self.stale_after:
                time.sleep(0.05)
                continue

            # Three recent readings within a 0.2 g band provide a software
            # stability check before asking the Highland to tare.
            if len(recent) >= 3 and max(recent) - min(recent) <= 0.2:
                return True, ""
            time.sleep(0.05)

        with self._state_lock:
            latest_time = self._latest_time
        if latest_time <= 0 or time.monotonic() - latest_time > self.stale_after:
            return False, "no fresh serial readings before tare"
        return False, "weight was not stable before tare"

    def _process_tare(self, payload: object) -> None:
        """Send one Highland T command and verify two new near-zero readings."""
        result, completed, _attempts, timeout = payload  # type: ignore[misc]
        success = False
        self._tare_active = True
        self._last_tare_error = ""

        try:
            if self._serial is None and not self._open_serial(force=True):
                self._last_tare_error = f"serial port unavailable: {self._last_error}"
                return

            stable, reason = self._wait_for_stable_input(timeout=5.0)
            if not stable:
                self._last_tare_error = reason
                self._trace("TARE", f"rejected before command: {reason}")
                return

            # Mark the last parsed reading. We deliberately do not clear the
            # receive buffer. Only readings parsed after this sequence number
            # can verify the command.
            with self._state_lock:
                sequence_before_tare = self._reading_sequence

            self._trace("TARE", f"sending T after sequence={sequence_before_tare}")
            if not self._write(b"T\r\n"):
                self._last_tare_error = f"tare command write failed: {self._last_error}"
                return

            deadline = time.monotonic() + max(float(timeout), 8.0)
            consecutive_zero = 0
            post_tare_readings = 0

            while time.monotonic() < deadline and not self._stop_event.is_set():
                try:
                    raw = self._readline()
                except Exception as exc:
                    self._last_error = repr(exc)
                    self._last_tare_error = f"serial read failed after tare: {exc!r}"
                    self._trace("ERROR", self._last_tare_error)
                    self._close_serial()
                    break

                parsed = self._parse(raw)
                if parsed is None:
                    continue

                self._record(parsed)
                with self._state_lock:
                    current_sequence = self._reading_sequence

                if current_sequence <= sequence_before_tare:
                    continue

                post_tare_readings += 1
                _text, value, _unit = parsed
                if abs(value) <= 0.2:
                    consecutive_zero += 1
                    if consecutive_zero >= 2:
                        success = True
                        self._trace(
                            "TARE",
                            f"verified after {post_tare_readings} post-command readings",
                        )
                        break
                else:
                    consecutive_zero = 0

            if not success and not self._last_tare_error:
                if post_tare_readings == 0:
                    self._last_tare_error = "no serial readings received after tare command"
                else:
                    self._last_tare_error = (
                        f"received {post_tare_readings} readings after tare, but not two at zero"
                    )
                self._trace("TARE", f"failed: {self._last_tare_error}")
        finally:
            self._tare_active = False
            result["success"] = success
            result["reason"] = self._last_tare_error
            completed.set()

    def read(self) -> str:
        """Return the latest continuous reading without issuing Print commands."""
        with self._state_lock:
            text = self._latest_text
            timestamp = self._latest_time
        if self._tare_active and timestamp > 0:
            return text
        if timestamp > 0 and time.monotonic() - timestamp <= self.stale_after:
            return text
        return "--"

    @property
    def last_tare_error(self) -> str:
        return self._last_tare_error


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
        self._effluent_scale = _RuntimeScaleManager(
            effluent_port, baud, scale_name="Filtrate"
        )
        self._backwash_scale = _RuntimeScaleManager(
            backwash_port, baud, scale_name="BW Effluent"
        )
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
        """Tare one scale using the deterministic Highland state machine."""
        manager = self._effluent_scale if channel == 0 else self._backwash_scale
        return manager.tare(attempts=1, timeout=8.0)

    def zero_scales(self) -> bool:
        """Automatically tare both scales at test start and verify both."""
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
            failed.append(f"Filtrate scale: {self._effluent_scale.last_tare_error}")
        if not results[1]:
            failed.append(f"BW Effluent scale: {self._backwash_scale.last_tare_error}")

        if failed:
            details = "; ".join(failed)
            raise RuntimeError(
                f"Verified automatic tare failed. {details}. "
                "The run was not started. See logs/scale_serial_trace.log for the raw RS-232 trace."
            )
        return True


PencilModule = MEU
