class Serial:
    """Minimal stub of pyserial's Serial class for tests."""
    def __init__(self, port="/dev/ttyAMA3", baudrate=9600, timeout=1):
        self.port = port
        self.baudrate = baudrate
        self.timeout = timeout
        self._buffer = b""
    
    def write(self, data: bytes):
        # Pretend to talk to weight scales and return deterministic responses
        if data == b"P\r\n":
            self._buffer = b"+123.45 g\r\n"
        elif data == b"S\r\n":
            self._buffer = b"+54.32 g\r\n"
        elif data in (b"Z\r\n", b"Q\r\n"):
            self._buffer = b"OK\r\n"
        else:
            self._buffer = b""
    
    def read_until(self, sep: bytes = b"\r\n") -> bytes:
        response = self._buffer or b""
        self._buffer = b""
        return response

    def reset_input_buffer(self) -> None:
        self._buffer = b""

