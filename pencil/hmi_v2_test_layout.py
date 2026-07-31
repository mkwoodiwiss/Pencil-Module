"""Match the MEU v2 Flush and Post-Scrub lower panels to Test."""

from __future__ import annotations

import tkinter as tk

from .hmi_v2_layout_fix import HMI as _V2LayoutHMI


class HMI(_V2LayoutHMI):
    """Apply the rendered Test geometry to the two new v2 process pages."""

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.after_idle(self._match_v2_pages_to_test)
        self.after(100, self._match_v2_pages_to_test)
        self.after(250, self._match_v2_pages_to_test)

    @staticmethod
    def _button_map(frame: tk.Widget) -> dict[str, tk.Button]:
        buttons: dict[str, tk.Button] = {}
        for child in frame.winfo_children():
            if isinstance(child, tk.Button):
                try:
                    buttons[str(child.cget("text"))] = child
                except tk.TclError:
                    pass
            buttons.update(HMI._button_map(child))
        return buttons

    @staticmethod
    def _copy_button_style(source: tk.Button, target: tk.Button) -> None:
        for option in (
            "font",
            "width",
            "height",
            "padx",
            "pady",
            "borderwidth",
            "relief",
            "highlightthickness",
            "anchor",
        ):
            try:
                target.configure(**{option: source.cget(option)})
            except tk.TclError:
                pass

    @staticmethod
    def _copy_pack_geometry(source: tk.Widget, target: tk.Widget) -> None:
        try:
            info = source.pack_info()
        except tk.TclError:
            return
        allowed = {
            key: value
            for key, value in info.items()
            if key in {"side", "anchor", "fill", "expand", "padx", "pady", "ipadx", "ipady"}
        }
        try:
            target.pack_configure(**allowed)
        except tk.TclError:
            pass

    def _match_one_page(self, target_tab: tk.Widget) -> None:
        test_settings, test_sensors, test_status = self._find_lower_frames(self.test_tab)
        target_settings, target_sensors, target_status = self._find_lower_frames(target_tab)
        if not all((test_settings, test_sensors, test_status, target_settings, target_sensors, target_status)):
            return

        self.update_idletasks()

        for source, target in (
            (test_settings, target_settings),
            (test_sensors, target_sensors),
            (test_status, target_status),
        ):
            try:
                target.configure(
                    width=source.winfo_width(),
                    height=source.winfo_height(),
                    font=source.cget("font"),
                    borderwidth=source.cget("borderwidth"),
                    relief=source.cget("relief"),
                )
                target.pack_propagate(False)
                target.grid_propagate(False)
            except tk.TclError:
                pass
            self._copy_pack_geometry(source, target)

        source_columns = (
            test_settings.master,
            self.start_btn_test.master,
            test_sensors.master,
        )
        target_start = self.start_btn_flush if target_tab is self.flush_tab else self.start_btn_post_scrub
        target_columns = (
            target_settings.master,
            target_start.master,
            target_sensors.master,
        )
        for source, target in zip(source_columns, target_columns):
            try:
                target.configure(width=source.winfo_width(), height=source.winfo_height())
                target.pack_propagate(False)
            except tk.TclError:
                pass
            self._copy_pack_geometry(source, target)

        self._copy_button_style(self.start_btn_test, target_start)
        self._copy_pack_geometry(self.start_btn_test, target_start)

        test_buttons = self._button_map(test_settings)
        target_buttons = self._button_map(target_settings)
        for text, source in test_buttons.items():
            target = target_buttons.get(text)
            if target is None:
                continue
            self._copy_button_style(source, target)
            try:
                source_grid = source.grid_info()
                if source_grid:
                    target.grid_configure(
                        row=source_grid.get("row", 0),
                        column=source_grid.get("column", 0),
                        rowspan=source_grid.get("rowspan", 1),
                        columnspan=source_grid.get("columnspan", 1),
                        padx=source_grid.get("padx", 0),
                        pady=source_grid.get("pady", 0),
                        ipadx=source_grid.get("ipadx", 0),
                        ipady=source_grid.get("ipady", 0),
                        sticky=source_grid.get("sticky", ""),
                    )
            except tk.TclError:
                pass

        try:
            source_place = test_settings.place_info()
            if source_place:
                target_settings.pack_forget()
                target_settings.place(
                    x=source_place.get("x", 0),
                    y=source_place.get("y", 0),
                    relx=source_place.get("relx", 0),
                    rely=source_place.get("rely", 0),
                    anchor=source_place.get("anchor", "nw"),
                )
        except tk.TclError:
            pass

    def _match_v2_pages_to_test(self) -> None:
        if not hasattr(self, "flush_tab"):
            return
        self._match_one_page(self.flush_tab)
        self._match_one_page(self.post_scrub_tab)
        self.update_idletasks()


__all__ = ["HMI"]
