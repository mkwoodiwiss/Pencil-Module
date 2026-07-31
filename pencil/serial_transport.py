"""Serial connection ownership for MEU line-oriented devices."""

from __future__ import annotations

import time

try:
    import serial  # type: ignore
except ModuleNotFoundError:  # pragma: no cover
    from . import serial_stub as serial


class SerialLineTransport:
    """Own one reconnectable line-oriented serial connection."""

    def __init__(self, port: str, baud: int, timeout: float = 0.25, serial_factory=None) -> None:
        self.port = port
        self.baud = baud
        self.timeout = timeout
        self._factory = serial.Serial if serial_factory is None else serial_factory
        self._connection = None
        self._last_open_attempt = 0.0
        self.last_error = ""

    @property
    def connection(self):
        return self._connection

    @property
    def connected(self) -> bool:
        return self._connection is not None

    def open(self, force: bool = False) -> bool:
        now = time.monotonic()
        if not force and now - self._last_open_attempt < 1.0:
            return False
        self._last_open_attempt = now
        self.close()
        try:
            self._connection = self._factory(self.port, self.baud, timeout=self.timeout)
            self.reset_input_buffer()
            self.last_error = ""
            return True
        except Exception as exc:
            self.last_error = repr(exc)
            self._connection = None
            return False

    def close(self) -> None:
        connection = self._connection
        self._connection = None
        if connection is not None:
            try:
                connection.close()
            except Exception:
                pass

    def reset_input_buffer(self) -> None:
        if self._connection is None:
            return
        try:
            self._connection.reset_input_buffer()
        except Exception:
            pass

    def readline(self) -> bytes:
        if self._connection is None:
            return b""
        try:
            if hasattr(self._connection, "readline"):
                return self._connection.readline()
            return self._connection.read_until(b"\r\n")
        except Exception as exc:
            self.last_error = repr(exc)
            self.close()
            raise

    def write(self, command: bytes) -> bool:
        if self._connection is None and not self.open(force=True):
            return False
        try:
            self._connection.write(command)
            try:
                self._connection.flush()
            except Exception:
                pass
            return True
        except Exception as exc:
            self.last_error = repr(exc)
            self.close()
            return False


__all__ = ["SerialLineTransport"]
