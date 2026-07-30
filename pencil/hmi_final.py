"""Final MEU HMI integration fixes."""

from __future__ import annotations

import tkinter as tk

from .hmi_modern_theme import HMI as _ThemedHMI


class HMI(_ThemedHMI):
    """Themed HMI with final runtime integration fixes."""

    def _sync_all_valve_buttons(self) -> None:
        """Synchronize every PFD valve button and process line with current state.

        ``hmi_runtime.HMI._enable_manual_controls`` calls this hook after a run.
        The hook was referenced but never implemented, which interrupted the
        completion callback before the results/USB window could open.
        """
        states = list(getattr(self, "solenoid_states", ()))
        for pfd in getattr(self, "pfds", {}).values():
            buttons = pfd.get("solenoid_buttons", ())
            for index, button in enumerate(buttons):
                state = bool(states[index]) if index < len(states) else False
                try:
                    button.configure(bg="green" if state else "lightgray")
                except tk.TclError:
                    pass

        try:
            self._update_lines()
        except (tk.TclError, AttributeError):
            pass

    def _test_finished(self) -> None:
        """Use only the original runtime results manager after a completed run.

        ``hmi_modern_theme.HMI`` added a second USB export dialog while
        ``hmi_runtime.HMI`` already opens the original results manager. Start the
        cooperative call after the themed class so the original completion path
        runs once without opening the duplicate dialog.
        """
        super(_ThemedHMI, self)._test_finished()


__all__ = ["HMI"]
