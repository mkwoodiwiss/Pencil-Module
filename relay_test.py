"""Interactive CLI for the 8-Relay hat."""

import sys

try:
    import lib8relind  # type: ignore
except ModuleNotFoundError as exc:  # pragma: no cover - running without drivers
    sys.exit(f"lib8relind driver not available: {exc}")


def main(stack: int = 1) -> None:
    """Toggle relays on the specified stack interactively."""
    states = [False] * 8
    prompt = (
        "Enter 'on N', 'off N', or 'toggle N' for relay N (1-8). "
        "Enter 'q' to quit: "
    )
    while True:
        try:
            choice = input(prompt).strip().lower()
        except (KeyboardInterrupt, EOFError):
            print()
            break

        if not choice:
            continue
        if choice.startswith("q"):
            break
        parts = choice.split()
        if len(parts) != 2 or not parts[1].isdigit():
            print("Invalid command")
            continue
        cmd, num = parts[0], int(parts[1])
        if not 1 <= num <= 8:
            print("Relay number must be between 1 and 8")
            continue
        if cmd in {"on", "off", "toggle"}:
            if cmd == "on":
                states[num - 1] = True
            elif cmd == "off":
                states[num - 1] = False
            else:
                states[num - 1] = not states[num - 1]
            lib8relind.set(stack, num, 1 if states[num - 1] else 0)
            print(f"Relay {num} {'ON' if states[num - 1] else 'OFF'}")
        else:
            print("Unknown command")


if __name__ == "__main__":
    main()
