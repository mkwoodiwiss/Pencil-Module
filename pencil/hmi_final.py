"""Final MEU HMI integration fixes."""

from __future__ import annotations

import tkinter as tk

from .hmi_modern_theme import HMI as _ThemedHMI


class HMI(_ThemedHMI):
    """Themed HMI with the runtime valve-state synchronization hook restored."""

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


__all__ = ["HMI"]
