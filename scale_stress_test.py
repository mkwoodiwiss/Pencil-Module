"""Convenience wrapper for the stress test script."""

from scripts.scale_stress_test import *  # noqa: F401,F403


if __name__ == "__main__":
    # ``scripts.scale_stress_test`` exposes a ``main`` function. Importing the
    # module alone does not execute it, so running this wrapper would appear to
    # do nothing. Call ``main()`` here so ``python scale_stress_test.py`` works
    # as expected.
    try:
        main()  # type: ignore[name-defined]
    except KeyboardInterrupt:
        pass
