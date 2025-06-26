class FakeSerial:
    """Simple in-memory serial port simulator."""
    def __init__(self, port="/dev/ttyUSB0", baud=9600, timeout=1):
        self.port = port
        self.baud = baud
        self.timeout = timeout
        self._buffer = b""

    def write(self, data: bytes):
        # The real system expects a 'P' command to read weight
        if data == b"P\r\n":
            self._buffer = b"+123.45 g\r\n"

    def read_until(self, sep: bytes = b"\r\n") -> bytes:
        response = self._buffer or b""
        self._buffer = b""
        return response


class FakeRelay8:
    """Simulate the Relay8 board."""
    def __init__(self, stack=0):
        self.stack = stack
        self.states = [False] * 8
        self.calls = []

    def on(self, relay: int) -> None:
        self.states[relay - 1] = True
        self.calls.append(("on", relay))

    def off(self, relay: int) -> None:
        self.states[relay - 1] = False
        self.calls.append(("off", relay))


class FakeMultiIO:
    """Simulate the MultiIO board."""
    def __init__(self, stack=0):
        self.stack = stack

    def get_adc(self, channel: int) -> float:
        # Return a deterministic value for testing
        return 3.21

    def get_rtd(self, channel: int) -> float:
        # Return a deterministic temperature
        return 20.5
