"""Final Clean-tab settings geometry correction."""

from __future__ import annotations

import tkinter as tk

from . import hmi_final as _hmi_final_module
from .hmi_touchscreen import HMI as _TouchscreenHMI


class HMI(_TouchscreenHMI):
    """Touchscreen HMI with a fully visible Clean settings panel."""

    CLEAN_EXTRA_HEIGHT = 8
    CLEAN_BOTTOM_MARGIN = 10
    COMPACT_SUMMARY_LINE_WIDTH = 16

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.after(300, self._apply_clean_settings_layout)
        try:
            self.notebook.bind(
                "<<NotebookTabChanged>>", self._clean_tab_selected, add="+"
            )
        except tk.TclError:
            pass

    @classmethod
    def _truncate_summary_text(cls, text: str) -> str:
        """Retain the established value-based truncation helper behavior."""
        prefixes = ("Project: ", "Module: ", "Sample: ", "Solution: ")
        output = []
        for line in str(text).splitlines():
            for prefix in prefixes:
                if line.startswith(prefix):
                    value = line[len(prefix) :]
                    if len(value) > cls.SUMMARY_VALUE_WIDTH:
                        value = f"{value[: cls.SUMMARY_VALUE_WIDTH - 3]}..."
                    line = prefix + value
                    break
            output.append(line)
        return "\n".join(output)

    @classmethod
    def _compact_summary_text(cls, text: str) -> str:
        """Fit visible identifier lines inside the fixed summary columns."""
        prefixes = (
            "Project: ",
            "Module: ",
            "Module ID: ",
            "Sample: ",
            "Sample ID: ",
            "Solution: ",
        )
        output = []
        for line in str(text).splitlines():
            for prefix in prefixes:
                if not line.startswith(prefix):
                    continue
                value = line[len(prefix) :]
                available = max(4, cls.COMPACT_SUMMARY_LINE_WIDTH - len(prefix))
                if len(value) > available:
                    value = f"{value[: available - 3]}..."
                line = prefix + value
                break
            output.append(line)
        return "\n".join(output)

    def _compact_summary_variables(self, *names: str) -> None:
        for name in names:
            variable = getattr(self, name, None)
            if variable is not None:
                variable.set(self._compact_summary_text(variable.get()))

    def _update_test_summary(self) -> None:
        super()._update_test_summary()
        self._compact_summary_variables(
            "test_summary_var", "_test_summary_left", "_test_summary_right"
        )

    def _update_benchmark_summary(self) -> None:
        super()._update_benchmark_summary()
        self._compact_summary_variables(
            "benchmark_summary_var",
            "_benchmark_summary_left",
            "_benchmark_summary_right",
        )

    def _update_clean_summary(self) -> None:
        super()._update_clean_summary()
        self._compact_summary_variables(
            "clean_summary_left_var", "clean_summary_right_var"
        )

    def _clean_tab_selected(self, _event=None) -> None:
        try:
            selected = self.notebook.select()
            if selected and self.nametowidget(selected) is self.clean_tab:
                self.after_idle(self._apply_clean_settings_layout)
        except (tk.TclError, KeyError):
            pass

    @staticmethod
    def _copy_button_style(source: tk.Button, target: tk.Button) -> None:
        """Copy visible button styling without relying on text-unit width."""
        target.configure(
            font=source.cget("font"),
            height=source.cget("height"),
            padx=source.cget("padx"),
            pady=source.cget("pady"),
            borderwidth=source.cget("borderwidth"),
            relief=source.cget("relief"),
        )

    @staticmethod
    def _match_button_container_pixels(
        test_buttons: dict[str, tk.Button], clean_buttons: dict[str, tk.Button]
    ) -> None:
        """Force Clean grid columns to the measured Test button pixel widths."""
        pairs = (
            ("Edit Settings", "Calibrate"),
            ("Tare FIL", "Tare BW EFL"),
        )
        source_parent = test_buttons["Edit Settings"].master
        target_parent = clean_buttons["Edit Settings"].master

        source_parent.update_idletasks()
        source_width = source_parent.winfo_width()
        source_height = source_parent.winfo_height()
        target_parent.configure(width=source_width, height=source_height)
        target_parent.grid_propagate(False)

        for column in (0, 1):
            measured_width = max(
                test_buttons[row[column]].winfo_width() for row in pairs
            )
            source_column = source_parent.grid_columnconfigure(column)
            target_parent.grid_columnconfigure(
                column,
                minsize=measured_width,
                pad=source_column.get("pad", 0),
                weight=0,
                uniform="",
            )

        for row_index, row in enumerate(pairs):
            for column, text in enumerate(row):
                source = test_buttons[text]
                target = clean_buttons[text]
                HMI._copy_button_style(source, target)
                source_grid = source.grid_info()
                target.grid_configure(
                    row=row_index,
                    column=column,
                    padx=source_grid.get("padx", 0),
                    pady=source_grid.get("pady", 0),
                    ipadx=source_grid.get("ipadx", 0),
                    ipady=source_grid.get("ipady", 0),
                    sticky="ew",
                )

    def _apply_clean_settings_layout(self) -> None:
        """Fit Clean inside the screen and match Test button pixels exactly."""
        test_settings = self._find_settings_frame(self.test_tab)
        clean_settings = self._find_settings_frame(self.clean_tab)
        if test_settings is None or clean_settings is None:
            return

        try:
            self.update_idletasks()
            test_width = test_settings.winfo_width()
            test_height = test_settings.winfo_height()
            if test_width <= 1 or test_height <= 1:
                self.after(100, self._apply_clean_settings_layout)
                return

            frame_top = clean_settings.winfo_rooty() - self.winfo_rooty()
            visible_height = max(
                1,
                self.winfo_height() - frame_top - self.CLEAN_BOTTOM_MARGIN,
            )
            clean_height = min(test_height + self.CLEAN_EXTRA_HEIGHT, visible_height)

            clean_settings.master.configure(width=test_width)
            clean_settings.master.pack_propagate(False)
            clean_settings.pack_configure(fill="none", anchor="sw")
            clean_settings.configure(width=test_width, height=clean_height)
            clean_settings.pack_propagate(False)
            clean_settings.grid_propagate(False)
        except tk.TclError:
            return

        test_buttons = self._buttons_by_text(test_settings)
        clean_buttons = self._buttons_by_text(clean_settings)
        required = {"Edit Settings", "Calibrate", "Tare FIL", "Tare BW EFL"}
        if required.issubset(test_buttons) and required.issubset(clean_buttons):
            try:
                self._match_button_container_pixels(test_buttons, clean_buttons)
            except tk.TclError:
                pass

        try:
            self.update_idletasks()
        except tk.TclError:
            pass


_hmi_final_module.HMI = HMI

__all__ = ["HMI"]
