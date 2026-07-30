"""Final Clean-tab settings geometry correction."""

from __future__ import annotations

import tkinter as tk

from . import hmi_final as _hmi_final_module
from .hmi_touchscreen import HMI as _TouchscreenHMI


class HMI(_TouchscreenHMI):
    """Touchscreen HMI with fully visible settings panels and dialogs."""

    CLEAN_EXTRA_HEIGHT = 8
    CLEAN_BOTTOM_MARGIN = 10
    COMPACT_SUMMARY_LINE_WIDTH = 16
    SETTINGS_SCREEN_MARGIN_X = 12
    SETTINGS_SCREEN_MARGIN_Y = 12

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.after(300, self._apply_clean_settings_layout)
        try:
            self.notebook.bind(
                "<<NotebookTabChanged>>", self._clean_tab_selected, add="+"
            )
        except tk.TclError:
            pass

    def _style_settings_window(self, window: tk.Toplevel) -> None:
        """Shrink inherited dialog styling and center it on the display."""
        super()._style_settings_window(window)
        self._compact_settings_widgets(window)
        self._fit_and_center_settings_window(window)
        window.after_idle(lambda: self._fit_and_center_settings_window(window))
        window.after(40, lambda: self._fit_and_center_settings_window(window))

    def _compact_settings_widgets(self, parent: tk.Widget) -> None:
        """Reduce only popup controls enough to fit the 800x480 display."""
        for child in parent.winfo_children():
            try:
                if isinstance(child, tk.Button):
                    child.configure(font=("Arial", 13), height=1, padx=10, pady=3)
                elif isinstance(child, tk.Checkbutton):
                    child.configure(font=("Arial", 12), padx=5, pady=2)
                elif isinstance(child, tk.Entry):
                    child.configure(
                        font=("Arial", 13),
                        width=max(8, min(18, int(child.cget("width")))),
                    )
                elif isinstance(child, tk.Label):
                    child.configure(font=("Arial", 12))
            except (tk.TclError, ValueError, TypeError):
                pass

            try:
                manager = child.winfo_manager()
                if manager == "grid":
                    info = child.grid_info()
                    child.grid_configure(
                        padx=min(5, int(info.get("padx", 0) or 0)),
                        pady=min(3, int(info.get("pady", 0) or 0)),
                    )
                elif manager == "pack":
                    info = child.pack_info()
                    child.pack_configure(
                        padx=min(5, int(info.get("padx", 0) or 0)),
                        pady=min(3, int(info.get("pady", 0) or 0)),
                    )
            except (tk.TclError, ValueError, TypeError):
                pass

            self._compact_settings_widgets(child)

    def _fit_and_center_settings_window(self, window: tk.Toplevel) -> None:
        """Use the natural dialog size, constrained to the visible screen."""
        try:
            if not window.winfo_exists():
                return

            window.update_idletasks()
            screen_width = window.winfo_screenwidth()
            screen_height = window.winfo_screenheight()
            max_width = max(1, screen_width - (2 * self.SETTINGS_SCREEN_MARGIN_X))
            max_height = max(1, screen_height - (2 * self.SETTINGS_SCREEN_MARGIN_Y))

            width = min(max_width, window.winfo_reqwidth())
            height = min(max_height, window.winfo_reqheight())
            x = max(0, (screen_width - width) // 2)
            y = max(0, (screen_height - height) // 2)

            window.geometry(f"{width}x{height}+{x}+{y}")
            window.lift()
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

    @classmethod
    def _place_button_container(
        cls,
        test_buttons: dict[str, tk.Button],
        clean_buttons: dict[str, tk.Button],
    ) -> None:
        """Center the Test-sized Clean control block clear of the frame border."""
        pairs = (
            ("Edit Settings", "Calibrate"),
            ("Tare FIL", "Tare BW EFL"),
        )
        source_parent = test_buttons["Edit Settings"].master
        target_parent = clean_buttons["Edit Settings"].master

        source_parent.update_idletasks()
        source_width = source_parent.winfo_width()
        source_height = source_parent.winfo_height()
        if source_width <= 1 or source_height <= 1:
            source_width = source_parent.winfo_reqwidth()
            source_height = source_parent.winfo_reqheight()

        for column in (0, 1):
            source_column = source_parent.grid_columnconfigure(column)
            target_parent.grid_columnconfigure(
                column,
                minsize=source_column.get("minsize", 0),
                pad=source_column.get("pad", 0),
                weight=source_column.get("weight", 0),
                uniform=source_column.get("uniform", ""),
            )

        for row_index, row in enumerate(pairs):
            for column, text in enumerate(row):
                source = test_buttons[text]
                target = clean_buttons[text]
                cls._copy_button_style(source, target)
                source_grid = source.grid_info()
                target.grid_configure(
                    row=row_index,
                    column=column,
                    padx=source_grid.get("padx", 0),
                    pady=source_grid.get("pady", 0),
                    ipadx=source_grid.get("ipadx", 0),
                    ipady=source_grid.get("ipady", 0),
                    sticky=source_grid.get("sticky", ""),
                )

        target_parent.grid_forget()
        target_parent.configure(width=source_width, height=source_height)
        target_parent.grid_propagate(False)
        target_parent.place(
            relx=0.5,
            rely=1.0,
            y=-cls.CLEAN_BOTTOM_MARGIN,
            anchor="s",
            width=source_width,
            height=source_height,
        )

    def _apply_clean_settings_layout(self) -> None:
        """Fit Clean inside the screen and center Test-sized buttons."""
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
                self._place_button_container(test_buttons, clean_buttons)
            except tk.TclError:
                pass

        try:
            self.update_idletasks()
        except tk.TclError:
            pass


_hmi_final_module.HMI = HMI

__all__ = ["HMI"]
