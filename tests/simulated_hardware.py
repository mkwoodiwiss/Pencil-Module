class FakeSerial:
    """Simple in-memory serial port simulator."""

    def __init__(self, port="/dev/ttyAMA3", baud=9600, timeout=1):
        self.port = port
        self.baud = baud
        self.timeout = timeout
        self._buffer = b""
        self.commands = []
        # Determine which weight value this fake port should return
        if port == "/dev/ttyAMA3":
            self.weight = b"+123.45 g\r\n"
        else:
            self.weight = b"+54.32 g\r\n"

    def write(self, data: bytes):
        self.commands.append(data)
        # When the weight query command is received return the preset value
        if data == b"P\r\n":
            self._buffer = self.weight
        elif data == b"Z\r\n":
            self._buffer = b"OK\r\n"

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

    def __init__(self, stack=0, i2c=1):
        self.stack = stack
        self.i2c = i2c

    def get_i_in(self, channel: int) -> float:
        """Return a deterministic 4-20 mA value for testing (12 mA -> 15 PSI)."""
        return 12.0

    def get_rtd_temp(self, channel: int) -> float:
        """Return a deterministic temperature."""
        return 20.5

    # Backwards compatibility with older method names
    get_adc = get_i_in
    get_rtd = get_rtd_temp


class FakeLib8Relind:
    """Simulate the lib8relind module."""

    def __init__(self):
        self.states = [0] * 8
        self.calls = []

    def set(self, stack: int, relay: int, value: int) -> None:
        self.calls.append(("set", stack, relay, value))
        self.states[relay - 1] = value

    def set_all(self, stack: int, value: int) -> None:
        self.calls.append(("set_all", stack, value))
        for i in range(8):
            self.states[i] = (value >> i) & 1

    def get(self, stack: int, relay: int) -> int:
        self.calls.append(("get", stack, relay))
        return self.states[relay - 1]

    def get_all(self, stack: int) -> int:
        self.calls.append(("get_all", stack))
        value = 0
        for i, bit in enumerate(self.states):
            value |= (bit << i)
        return value
