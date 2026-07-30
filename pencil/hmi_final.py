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

    @staticmethod
    def _set_valve_button_color(button, state: bool) -> None:
        """Keep normal and touchscreen-active colors matched to valve state."""
        color = "green" if state else "lightgray"
        button.configure(bg=color, activebackground=color)

    def _sync_all_valve_buttons(self) -> None:
        """Synchronize every PFD valve button and process line with current state."""
        states = list(getattr(self, "solenoid_states", ()))
        for pfd in getattr(self, "pfds", {}).values():
            buttons = pfd.get("solenoid_buttons", ())
            for index, button in enumerate(buttons):
                state = bool(states[index]) if index < len(states) else False
                try:
                    self._set_valve_button_color(button, state)
                except tk.TclError:
                    pass

        try:
            self._update_lines()
        except (tk.TclError, AttributeError):
            pass

    def toggle_solenoid(self, channel: int) -> None:
        """Toggle one valve and immediately refresh its touchscreen appearance."""
        super().toggle_solenoid(channel)
        state = bool(self.solenoid_states[channel])
        for pfd in self.pfds.values():
            try:
                self._set_valve_button_color(pfd["solenoid_buttons"][channel], state)
            except tk.TclError:
                pass

    def _set_valve_buttons_state(self, state: str) -> None:
        """Set every PFD valve button to the requested Tkinter state."""
        for pfd in getattr(self, "pfds", {}).values():
            for button in pfd.get("solenoid_buttons", ()):
                try:
                    button.configure(state=state)
                except tk.TclError:
                    pass

    def _settings_window_closed(self, window) -> None:
        """Restore valve controls after the last settings dialog closes."""
        windows = getattr(self, "_open_settings_windows", set())
        windows.discard(window)
        if windows or getattr(self, "is_running", False):
            return
        self._set_valve_buttons_state("normal")
        self._sync_all_valve_buttons()

    def _register_settings_window(self, window) -> None:
        """Track one settings dialog and keep valve buttons locked behind it."""
        windows = getattr(self, "_open_settings_windows", None)
        if windows is None:
            windows = set()
            self._open_settings_windows = windows
        windows.add(window)
        self._set_valve_buttons_state("disabled")

        def closed(event) -> None:
            if getattr(event, "widget", None) is window:
                self._settings_window_closed(window)

        window.bind("<Destroy>", closed, add="+")

    def _style_settings_window(self, window: tk.Toplevel) -> None:
        """Make settings dialogs and their action buttons fill the touchscreen."""
        super()._style_settings_window(window)

        def enlarge_actions(parent) -> None:
            for child in parent.winfo_children():
                try:
                    if isinstance(child, tk.Button):
                        child.configure(font=("Arial", 18, "bold"), height=2, padx=22, pady=10)
                    elif isinstance(child, tk.Checkbutton):
                        child.configure(font=("Arial", 16), padx=11, pady=7)
                    elif isinstance(child, tk.Entry):
                        child.configure(font=("Arial", 17), width=max(10, int(child.cget("width"))))
                    elif isinstance(child, tk.Label):
                        child.configure(font=("Arial", 16))
                except (tk.TclError, ValueError):
                    pass
                enlarge_actions(child)

        enlarge_actions(window)
        try:
            window.update_idletasks()
            screen_width = self.winfo_screenwidth()
            screen_height = self.winfo_screenheight()
            width = min(screen_width - 12, max(720, window.winfo_reqwidth() + 80))
            height = min(screen_height - 20, max(440, window.winfo_reqheight() + 40))
            x = max(0, self.winfo_rootx() + (self.winfo_width() - width) // 2)
            y = max(0, self.winfo_rooty() + (self.winfo_height() - height) // 2)
            window.geometry(f"{width}x{height}+{x}+{y}")
            window.lift()
            window.focus_force()
        except tk.TclError:
            pass

    def _open_settings_dialog(self, open_dialog) -> None:
        """Open, enlarge, and register one settings dialog."""
        try:
            before = {
                child
                for child in self.winfo_children()
                if isinstance(child, tk.Toplevel)
            }
        except tk.TclError:
            before = set()

        self._set_valve_buttons_state("disabled")
        try:
            open_dialog()
        except Exception:
            if not getattr(self, "is_running", False):
                self._set_valve_buttons_state("normal")
                self._sync_all_valve_buttons()
            raise

        try:
            windows = [
                child
                for child in self.winfo_children()
                if isinstance(child, tk.Toplevel) and child not in before
            ]
        except tk.TclError:
            windows = []

        if not windows:
            if not getattr(self, "is_running", False):
                self._set_valve_buttons_state("normal")
                self._sync_all_valve_buttons()
            return

        window = windows[-1]
        self._register_settings_window(window)
        self._style_settings_window(window)

    def _edit_test_settings(self) -> None:
        self._open_settings_dialog(super()._edit_test_settings)

    def _edit_benchmark_settings(self) -> None:
        self._open_settings_dialog(super()._edit_benchmark_settings)

    def _edit_clean_settings(self) -> None:
        self._open_settings_dialog(super()._edit_clean_settings)

    def _test_finished(self) -> None:
        """Use only the original runtime results manager after a completed run."""
        super(_ThemedHMI, self)._test_finished()


__all__ = ["HMI"]