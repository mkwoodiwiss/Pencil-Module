"""Final modal-safety and Prime-sequence corrections for the MEU HMI."""

from __future__ import annotations

import tkinter as tk

from . import hmi_final as _hmi_final_module
from .hmi_clean_match import HMI as _CleanMatchHMI


class HMI(_CleanMatchHMI):
    """MEU HMI with safe Prime routing and modal main-screen controls."""

    CLEAN_CONTROL_SIDE_PAD = 12

    def __init__(self, *args, **kwargs) -> None:
        self._open_modal_windows: set[tk.Toplevel] = set()
        self._main_button_states: dict[tk.Button, str] = {}
        super().__init__(*args, **kwargs)
        self.bind_all("<Map>", self._register_mapped_popup, add="+")

    @staticmethod
    def _match_button_style(source: tk.Button, target: tk.Button) -> None:
        """Copy every visible style property from a reference-tab button."""
        target.configure(
            font=source.cget("font"),
            width=source.cget("width"),
            height=source.cget("height"),
            padx=source.cget("padx"),
            pady=source.cget("pady"),
            borderwidth=source.cget("borderwidth"),
            relief=source.cget("relief"),
        )

    @classmethod
    def _place_button_container(
        cls,
        test_buttons: dict[str, tk.Button],
        clean_buttons: dict[str, tk.Button],
    ) -> None:
        """Match the Clean controls to the Test block's rendered pixel geometry."""
        pairs = (
            ("Edit Settings", "Calibrate"),
            ("Tare FIL", "Tare BW EFL"),
        )
        source_parent = test_buttons["Edit Settings"].master
        target_parent = clean_buttons["Edit Settings"].master
        settings_frame = target_parent.master

        try:
            source_parent.update_idletasks()
        except tk.TclError:
            return

        column_widths = [0, 0]
        row_heights = [0, 0]
        source_grid_options: dict[str, dict] = {}

        for row_index, row in enumerate(pairs):
            for column, text in enumerate(row):
                source = test_buttons[text]
                target = clean_buttons[text]
                cls._match_button_style(source, target)

                try:
                    source.update_idletasks()
                    column_widths[column] = max(
                        column_widths[column], source.winfo_width()
                    )
                    row_heights[row_index] = max(
                        row_heights[row_index], source.winfo_height()
                    )
                    source_grid_options[text] = source.grid_info()
                except tk.TclError:
                    source_grid_options[text] = {}

        for column, width in enumerate(column_widths):
            target_parent.grid_columnconfigure(
                column,
                minsize=width,
                weight=0,
                uniform="clean_controls",
            )

        for row_index, height in enumerate(row_heights):
            target_parent.grid_rowconfigure(
                row_index,
                minsize=height,
                weight=0,
            )

        for row_index, row in enumerate(pairs):
            for column, text in enumerate(row):
                target = clean_buttons[text]
                source_grid = source_grid_options[text]
                target.grid_configure(
                    row=row_index,
                    column=column,
                    padx=source_grid.get("padx", 0),
                    pady=source_grid.get("pady", 0),
                    ipadx=source_grid.get("ipadx", 0),
                    ipady=source_grid.get("ipady", 0),
                    sticky="nsew",
                )

        try:
            target_parent.place_forget()
        except tk.TclError:
            pass

        target_parent.configure(width=0, height=0)
        target_parent.grid_propagate(True)
        target_parent.grid(
            row=1,
            column=0,
            columnspan=5,
            padx=(cls.CLEAN_CONTROL_SIDE_PAD, cls.CLEAN_CONTROL_SIDE_PAD),
            pady=(2, 10),
            sticky="s",
        )
        settings_frame.grid_columnconfigure(0, weight=1)

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
