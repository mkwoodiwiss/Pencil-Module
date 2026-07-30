"""Final MEU HMI integration fixes."""

from __future__ import annotations

import tkinter as tk

from .hmi_modern_theme import HMI as _ThemedHMI


class HMI(_ThemedHMI):
    """Themed HMI with final runtime integration fixes."""

    def _style_mapped_widget(self, event) -> None:
        """Ignore non-widget and destroyed targets during mapping and shutdown."""
        widget = getattr(event, "widget", None)
        if not isinstance(widget, tk.Misc):
            return
        try:
            if not widget.winfo_exists():
                return
            widget.after_idle(
                lambda target=widget: (
                    self._apply_selected_accents(target)
                    if target.winfo_exists()
                    else None
                )
            )
        except (tk.TclError, AttributeError):
            pass

    def _sync_all_valve_buttons(self) -> None:
        """Synchronize every PFD valve button and process line with current state."""
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
        """Use only the original runtime results manager after a completed run."""
        super(_ThemedHMI, self)._test_finished()


__all__ = ["HMI"]
