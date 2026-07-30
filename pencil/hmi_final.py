"""Final MEU HMI integration fixes."""

from __future__ import annotations

import tkinter as tk

from .hmi_modern_theme import HMI as _ThemedHMI


PSI_TO_KPA = 6.894757293168


class HMI(_ThemedHMI):
    """Themed HMI with final runtime integration fixes."""

    SUMMARY_VALUE_WIDTH = 16

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._shared_identifier_sync_active = False
        self._install_shared_identifier_sync()
        self._refresh_identifier_summaries()
        self._replace_pressure_unit_labels()

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
                        child.configure(
                            font=("Arial", 18, "bold"),
                            height=2,
                            padx=22,
                            pady=10,
                        )
                    elif isinstance(child, tk.Checkbutton):
                        child.configure(font=("Arial", 16), padx=11, pady=7)
                    elif isinstance(child, tk.Entry):
                        child.configure(
                            font=("Arial", 17),
                            width=max(10, int(child.cget("width"))),
                        )
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

    @staticmethod
    def _shared_identifier_groups() -> tuple[tuple[str, ...], ...]:
        return (
            ("project_var", "benchmark_project_var", "clean_project_var"),
            ("module_id_var", "benchmark_module_id_var", "clean_module_id_var"),
            ("sample_id_var", "benchmark_sample_id_var"),
        )

    def _install_shared_identifier_sync(self) -> None:
        """Keep shared project, module, and sample identifiers synchronized."""
        for group in self._shared_identifier_groups():
            available = [name for name in group if hasattr(self, name)]
            if not available:
                continue
            source_name = available[0]
            self._sync_identifier_group(source_name, group)
            for name in available:
                variable = getattr(self, name)
                variable.trace_add(
                    "write",
                    lambda *_args, changed=name, members=group: self._sync_identifier_group(
                        changed, members
                    ),
                )

    def _sync_identifier_group(self, source_name: str, group: tuple[str, ...]) -> None:
        """Copy one identifier value to every matching tab without trace loops."""
        if getattr(self, "_shared_identifier_sync_active", False):
            return
        source = getattr(self, source_name, None)
        if source is None:
            return

        self._shared_identifier_sync_active = True
        try:
            value = source.get()
            for name in group:
                target = getattr(self, name, None)
                if target is not None and target is not source and target.get() != value:
                    target.set(value)
            self._refresh_identifier_summaries()
        finally:
            self._shared_identifier_sync_active = False

    @classmethod
    def _ellipsize(cls, value: str) -> str:
        """Return a fixed-width display value while retaining the full source text."""
        text = str(value)
        limit = cls.SUMMARY_VALUE_WIDTH
        if len(text) <= limit:
            return text
        return f"{text[: limit - 3]}..."

    @classmethod
    def _truncate_summary_text(cls, text: str) -> str:
        """Shorten identifier values in summary text without changing stored data."""
        prefixes = ("Project: ", "Module: ", "Sample: ")
        output = []
        for line in str(text).splitlines():
            for prefix in prefixes:
                if line.startswith(prefix):
                    line = prefix + cls._ellipsize(line[len(prefix) :])
                    break
            output.append(line)
        return "\n".join(output)

    def _refresh_identifier_summaries(self) -> None:
        """Refresh every visible summary and constrain long identifier text."""
        for updater_name in (
            "_update_test_summary",
            "_update_benchmark_summary",
            "_update_clean_summary",
        ):
            updater = getattr(self, updater_name, None)
            if callable(updater):
                updater()

    def _truncate_summary_variables(self, *names: str) -> None:
        for name in names:
            variable = getattr(self, name, None)
            if variable is not None:
                variable.set(self._truncate_summary_text(variable.get()))

    def _update_test_summary(self) -> None:
        super()._update_test_summary()
        self._truncate_summary_variables(
            "test_summary_var",
            "_test_summary_left",
            "_test_summary_right",
        )

    def _update_benchmark_summary(self) -> None:
        super()._update_benchmark_summary()
        self._truncate_summary_variables(
            "benchmark_summary_var",
            "_benchmark_summary_left",
            "_benchmark_summary_right",
        )

    def _update_clean_summary(self) -> None:
        super()._update_clean_summary()
        self._truncate_summary_variables(
            "clean_summary_left_var",
            "clean_summary_right_var",
        )

    def _replace_pressure_unit_labels(self) -> None:
        """Replace static PSI labels with kPa throughout the final HMI."""
        for widget in self._walk_widgets(self):
            if not isinstance(widget, tk.Label):
                continue
            try:
                if str(widget.cget("text")).strip().upper() == "PSI":
                    widget.configure(text="kPa")
            except tk.TclError:
                pass

    @staticmethod
    def _psi_to_kpa(value: float) -> float:
        return float(value) * PSI_TO_KPA

    def update_data(self) -> None:
        """Refresh displayed values, converting internal psi readings to kPa."""
        if not self.winfo_exists():
            return
        with self._sensor_lock:
            weight = self.latest_weight
            bw_weight = self.latest_bw_weight
            pressure_bw_kpa = self._psi_to_kpa(self.latest_pressure_bw)
            pressure_feed_kpa = self._psi_to_kpa(self.latest_pressure_raw)
            temp = self.latest_temp

        clean_w = self._strip_weight(weight)
        clean_bw = self._strip_weight(bw_weight)
        self.weight_var.set(clean_w)
        self.backwash_weight_var.set(clean_bw)
        self.pressure_bw_var.set(f"{pressure_bw_kpa:.2f}")
        self.pressure_raw_var.set(f"{pressure_feed_kpa:.2f}")
        self.temp_var.set(f"{temp:.2f}")

        for pfd in self.pfds.values():
            pfd["canvas"].itemconfig(
                pfd["pi1_text"], text=f"{self.pressure_bw_var.get()} kPa"
            )
            pfd["canvas"].itemconfig(
                pfd["pi2_text"], text=f"{self.pressure_raw_var.get()} kPa"
            )
            pfd["canvas"].itemconfig(pfd["te_text"], text=f"{self.temp_var.get()} C")
            pfd["canvas"].itemconfig(pfd["effluent_weight_text"], text=weight)
            pfd["canvas"].itemconfig(pfd["backwash_weight_text"], text=bw_weight)

        self._update_cycle_time()
        self._update_lines()
        self.after(1000, self.update_data)

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
