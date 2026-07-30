"""Final modal-safety and Prime-sequence corrections for the MEU HMI."""

from __future__ import annotations

import tkinter as tk

from . import hmi_final as _hmi_final_module
from .hmi_clean_match import HMI as _CleanMatchHMI


class HMI(_CleanMatchHMI):
    """MEU HMI with safe Prime routing and modal main-screen controls."""

    CLEAN_BUTTON_SIDE_INSET = 12
    CLEAN_SUMMARY_SIDE_INSET = 8

    def __init__(self, *args, **kwargs) -> None:
        self._open_modal_windows: set[tk.Toplevel] = set()
        self._main_button_states: dict[tk.Button, str] = {}
        super().__init__(*args, **kwargs)
        self.bind_all("<Map>", self._register_mapped_popup, add="+")

    @classmethod
    def _place_button_container(
        cls,
        test_buttons: dict[str, tk.Button],
        clean_buttons: dict[str, tk.Button],
    ) -> None:
        """Center Clean controls without allowing their frame to cover the border."""
        super()._place_button_container(test_buttons, clean_buttons)

        target_parent = clean_buttons["Edit Settings"].master
        settings_frame = target_parent.master
        try:
            settings_frame.update_idletasks()
            frame_width = settings_frame.winfo_width()
            if frame_width <= 1:
                frame_width = settings_frame.winfo_reqwidth()

            current_width = target_parent.winfo_width()
            if current_width <= 1:
                current_width = target_parent.winfo_reqwidth()

            maximum_width = max(
                1,
                frame_width - (2 * cls.CLEAN_BUTTON_SIDE_INSET),
            )
            container_width = min(current_width, maximum_width)
            target_parent.configure(width=container_width)
            target_parent.place_configure(
                relx=0.5,
                anchor="s",
                width=container_width,
            )
        except tk.TclError:
            pass

    def _find_clean_summary_frame(self, clean_settings: tk.LabelFrame) -> tk.Frame | None:
        """Return the frame containing the two Clean summary labels."""
        expected_variables = {
            str(self.clean_summary_left_var),
            str(self.clean_summary_right_var),
        }
        for child in clean_settings.winfo_children():
            if not isinstance(child, tk.Frame):
                continue
            found_variables = set()
            for descendant in self._walk_widgets(child):
                if not isinstance(descendant, tk.Label):
                    continue
                try:
                    variable = str(descendant.cget("textvariable"))
                except tk.TclError:
                    continue
                if variable:
                    found_variables.add(variable)
            if expected_variables.issubset(found_variables):
                return child
        return None

    def _fit_clean_summary_frame(self) -> None:
        """Keep the summary container inside the LabelFrame client area."""
        clean_settings = self._find_settings_frame(self.clean_tab)
        if clean_settings is None:
            return
        summary_frame = self._find_clean_summary_frame(clean_settings)
        if summary_frame is None:
            return

        try:
            clean_settings.update_idletasks()
            frame_width = clean_settings.winfo_width()
            if frame_width <= 1:
                frame_width = clean_settings.winfo_reqwidth()

            requested_width = summary_frame.winfo_reqwidth()
            requested_height = summary_frame.winfo_reqheight()
            maximum_width = max(
                1,
                frame_width - (2 * self.CLEAN_SUMMARY_SIDE_INSET),
            )
            summary_width = min(requested_width, maximum_width)

            summary_frame.configure(
                width=summary_width,
                height=requested_height,
                bd=0,
                highlightthickness=0,
            )
            summary_frame.grid_propagate(False)
            summary_frame.grid_configure(
                sticky="nw",
                padx=(self.CLEAN_SUMMARY_SIDE_INSET, self.CLEAN_SUMMARY_SIDE_INSET),
            )
        except tk.TclError:
            pass

    def _apply_clean_settings_layout(self) -> None:
        """Apply the Clean layout without allowing children to cover its border."""
        super()._apply_clean_settings_layout()
        self._fit_clean_summary_frame()
        self.after_idle(self._fit_clean_summary_frame)
        self.after(75, self._fit_clean_summary_frame)

    def _show_prime_stage(self) -> None:
        """Apply the corrected valve combination for each Prime step."""
        if not self.prime_frame:
            return

        step_text = {2: "Step 1", 3: "Step 2", 4: "Step 3"}
        self._close_all_valves()
        if self.prime_stage == 2:
            self._open_valves(2, 3)
        elif self.prime_stage == 3:
            self._open_valves(1, 5)
        elif self.prime_stage == 4:
            self._open_valves(2, 4)

        action_text = "Continue" if self.prime_stage < 4 else "Finish"
        self._build_prime_popup(
            step_text.get(self.prime_stage, "Prime"),
            action_text,
            self._advance_prime,
        )

    def _register_mapped_popup(self, event) -> None:
        """Disable every root-window button whenever a Toplevel is visible."""
        window = getattr(event, "widget", None)
        if not isinstance(window, tk.Toplevel):
            return
        self._register_modal_window(window)

    def _register_modal_window(self, window: tk.Toplevel) -> None:
        """Track a popup and lock all buttons belonging to the main window."""
        try:
            if not window.winfo_exists() or window in self._open_modal_windows:
                return
        except tk.TclError:
            return

        self._open_modal_windows.add(window)
        self._disable_main_window_buttons()

        def closed(event) -> None:
            if getattr(event, "widget", None) is window:
                self._modal_window_closed(window)

        window.bind("<Destroy>", closed, add="+")

    def _disable_main_window_buttons(self) -> None:
        """Disable root-window buttons without changing popup button states."""
        for widget in self._walk_widgets(self):
            if not isinstance(widget, tk.Button):
                continue
            try:
                if widget.winfo_toplevel() is not self:
                    continue
                if widget not in self._main_button_states:
                    self._main_button_states[widget] = str(widget.cget("state"))
                widget.configure(state="disabled")
            except tk.TclError:
                pass

    def _modal_window_closed(self, window: tk.Toplevel) -> None:
        """Restore main controls only after the final popup has closed."""
        self._open_modal_windows.discard(window)
        if self._open_modal_windows:
            return

        saved_states = self._main_button_states
        self._main_button_states = {}
        if getattr(self, "is_running", False):
            return

        for button, state in saved_states.items():
            try:
                if button.winfo_exists():
                    button.configure(state=state)
            except tk.TclError:
                pass

        self._sync_all_valve_buttons()


_hmi_final_module.HMI = HMI

__all__ = ["HMI"]
