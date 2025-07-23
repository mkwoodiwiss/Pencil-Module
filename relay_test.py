"""Compatibility wrapper for the relay test CLI."""

from scripts import relay_test as _relay_test

# Re-export for tests that patch these names
lib8relind = _relay_test.lib8relind


def main(stack: int = 1) -> None:
    """Entry point that forwards to the script version."""
    _relay_test.lib8relind = lib8relind
    _relay_test.main(stack)
