"""Build Flush and Post-Scrub from the actual rendered Test widget tree."""

from __future__ import annotations

import tkinter as tk

from .hmi_v2_layout_fix import HMI as _V2LayoutHMI
from .hmi_widget_clone import WidgetTreeCloneMixin


class HMI(WidgetTreeCloneMixin, _V2LayoutHMI):
    """MEU v2 HMI whose new process panels are exact Test-layout clones."""

    CLONE_DELAY_MS = 400

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)

        self.flush_summary_left_var = tk.StringVar()
        self.flush_summary_right_var = tk.StringVar()
        self.post_scrub_summary_left_var = tk.StringVar()
        self.post_scrub_summary_right_var = tk.StringVar()
        self._update_flush_summary()
        self._update_post_scrub_summary()

        self.after(self.CLONE_DELAY_MS, self._rebuild_new_pages_from_test)

    def _test_lower_area(self) -> tk.Widget | None:
        top_section = self.pfds.get("test", {}).get("top_section")
        for child in self._managed_children(self.test_tab):
            if child is not top_section:
                return child
        return None

    def _clear_lower_area(self, tab: tk.Widget, key: str) -> None:
        top_section = self.pfds.get(key, {}).get("top_section")
        for child in list(tab.winfo_children()):
            if child is top_section:
                continue
            try:
                child.destroy()
            except tk.TclError:
                pass

    def _summary_variable_for_clone(self, key: str) -> tk.StringVar:
        index = self._summary_clone_index
        self._summary_clone_index += 1
        if key == "flush":
            return (
                self.flush_summary_left_var
                if index == 0
                else self.flush_summary_right_var
            )
        return (
            self.post_scrub_summary_left_var
            if index == 0
            else self.post_scrub_summary_right_var
        )

    def _clone_button_command(self, text: str, key: str):
        if text == "Start":
            return self._toggle_flush if key == "flush" else self._toggle_post_scrub
        if text == "Edit Settings":
            return self._edit_flush_settings if key == "flush" else self._edit_post_scrub_settings
        if text == "Calibrate":
            return self.calibrate
        if text in {"Tare FIL", "Tare EFL"}:
            return lambda: self.module.zero_scale(0)
        if text in {"Tare BW EFL", "Tare BW"}:
            return lambda: self.module.zero_scale(1)
        return None

    def _create_cloned_widget(
        self,
        source: tk.Widget,
        parent: tk.Widget,
        key: str,
        options: dict,
    ) -> tk.Widget:
        if isinstance(source, tk.LabelFrame):
            return tk.LabelFrame(parent, **options)
        if isinstance(source, tk.Frame):
            return tk.Frame(parent, **options)
        if isinstance(source, tk.Button):
            text = str(source.cget("text"))
            target = tk.Button(
                parent,
                command=self._clone_button_command(text, key),
                **options,
            )
            if text == "Start":
                if key == "flush":
                    self.start_btn_flush = target
                else:
                    self.start_btn_post_scrub = target
            return target
        if isinstance(source, tk.Label):
            label_options = dict(options)
            try:
                variable_name = str(source.cget("textvariable"))
            except tk.TclError:
                variable_name = ""

            source_summary_names = {
                str(self.test_summary_var),
                str(getattr(self, "_test_summary_left", "")),
                str(getattr(self, "_test_summary_right", "")),
            }
            if variable_name and variable_name in source_summary_names:
                label_options["textvariable"] = self._summary_variable_for_clone(key)
            elif variable_name:
                label_options["textvariable"] = variable_name

            try:
                image_name = str(source.cget("image"))
            except tk.TclError:
                image_name = ""
            if image_name:
                label_options["image"] = image_name
            return tk.Label(parent, **label_options)
        return tk.Frame(parent)

    def _clone_test_lower_area(self, tab: tk.Widget, key: str) -> None:
        source = self._test_lower_area()
        if source is None:
            return

        self._clear_lower_area(tab, key)
        self._summary_clone_index = 0
        target = self._clone_widget(source, tab, key)
        self._apply_geometry(source, target)

    def _rebuild_new_pages_from_test(self) -> None:
        try:
            self.update_idletasks()
            self._clone_test_lower_area(self.flush_tab, "flush")
            self._clone_test_lower_area(self.post_scrub_tab, "post_scrub")
            self.update_idletasks()
            self._refresh_navigation_rails()
            self._apply_selected_accents(self)
        except tk.TclError:
            pass


__all__ = ["HMI"]
