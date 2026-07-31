"""Build Flush and Post-Scrub from the actual rendered Test widget tree."""

from __future__ import annotations

import tkinter as tk

from .hmi_v2_layout_fix import HMI as _V2LayoutHMI


class HMI(_V2LayoutHMI):
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

    @staticmethod
    def _managed_children(parent: tk.Widget) -> list[tk.Widget]:
        children = []
        for child in parent.winfo_children():
            try:
                if child.winfo_manager():
                    children.append(child)
            except tk.TclError:
                pass
        return children

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

    @staticmethod
    def _copy_widget_options(source: tk.Widget) -> dict:
        excluded = {
            "class",
            "colormap",
            "container",
            "command",
            "image",
            "menu",
            "name",
            "screen",
            "textvariable",
            "use",
            "variable",
            "visual",
        }
        options = {}
        try:
            configuration = source.configure()
        except tk.TclError:
            return options

        for name in configuration:
            if name in excluded:
                continue
            try:
                options[name] = source.cget(name)
            except tk.TclError:
                pass
        return options

    @staticmethod
    def _copy_grid_configuration(source: tk.Widget, target: tk.Widget) -> None:
        try:
            columns, rows = source.grid_size()
        except tk.TclError:
            return

        for column in range(columns):
            try:
                config = source.grid_columnconfigure(column)
                target.grid_columnconfigure(
                    column,
                    minsize=config.get("minsize", 0),
                    pad=config.get("pad", 0),
                    weight=config.get("weight", 0),
                    uniform=config.get("uniform", ""),
                )
            except tk.TclError:
                pass

        for row in range(rows):
            try:
                config = source.grid_rowconfigure(row)
                target.grid_rowconfigure(
                    row,
                    minsize=config.get("minsize", 0),
                    pad=config.get("pad", 0),
                    weight=config.get("weight", 0),
                    uniform=config.get("uniform", ""),
                )
            except tk.TclError:
                pass

    def _summary_variable_for_clone(self, key: str) -> tk.StringVar:
        index = self._summary_clone_index
        self._summary_clone_index += 1
        if key == "flush":
            return self.flush_summary_left_var if index == 0 else self.flush_summary_right_var
        return (
            self.post_scrub_summary_left_var
            if index == 0
            else self.post_scrub_summary_right_var
        )

    def _clone_widget(
        self,
        source: tk.Widget,
        parent: tk.Widget,
        key: str,
    ) -> tk.Widget:
        options = self._copy_widget_options(source)

        if isinstance(source, tk.LabelFrame):
            target = tk.LabelFrame(parent, **options)
        elif isinstance(source, tk.Frame):
            target = tk.Frame(parent, **options)
        elif isinstance(source, tk.Button):
            text = str(source.cget("text"))
            command = None
            if text == "Start":
                command = self._toggle_flush if key == "flush" else self._toggle_post_scrub
            elif text == "Edit Settings":
                command = self._edit_flush_settings if key == "flush" else self._edit_post_scrub_settings
            elif text == "Calibrate":
                command = self.calibrate
            elif text in {"Tare FIL", "Tare EFL"}:
                command = lambda: self.module.zero_scale(0)
            elif text in {"Tare BW EFL", "Tare BW"}:
                command = lambda: self.module.zero_scale(1)
            target = tk.Button(parent, command=command, **options)
            if text == "Start":
                if key == "flush":
                    self.start_btn_flush = target
                else:
                    self.start_btn_post_scrub = target
        elif isinstance(source, tk.Label):
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
            target = tk.Label(parent, **label_options)
        else:
            target = tk.Frame(parent)

        self._copy_grid_configuration(source, target)

        for child in self._managed_children(source):
            cloned_child = self._clone_widget(child, target, key)
            manager = child.winfo_manager()
            try:
                if manager == "pack":
                    info = child.pack_info()
                    info.pop("in", None)
                    cloned_child.pack(**info)
                elif manager == "grid":
                    info = child.grid_info()
                    info.pop("in", None)
                    cloned_child.grid(**info)
                elif manager == "place":
                    info = child.place_info()
                    info.pop("in", None)
                    cloned_child.place(**info)
            except tk.TclError:
                pass

        try:
            if not source.tk.getboolean(source.pack_propagate()):
                target.pack_propagate(False)
        except tk.TclError:
            pass
        try:
            if not source.tk.getboolean(source.grid_propagate()):
                target.grid_propagate(False)
        except tk.TclError:
            pass
        return target

    def _clone_test_lower_area(self, tab: tk.Widget, key: str) -> None:
        source = self._test_lower_area()
        if source is None:
            return

        self._clear_lower_area(tab, key)
        self._summary_clone_index = 0
        target = self._clone_widget(source, tab, key)
        manager = source.winfo_manager()
        if manager == "pack":
            info = source.pack_info()
            info.pop("in", None)
            target.pack(**info)
        elif manager == "grid":
            info = source.grid_info()
            info.pop("in", None)
            target.grid(**info)
        elif manager == "place":
            info = source.place_info()
            info.pop("in", None)
            target.place(**info)

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
