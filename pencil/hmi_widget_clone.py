"""Reusable Tk widget-tree cloning mechanics for MEU layouts."""

from __future__ import annotations

import tkinter as tk


class WidgetTreeCloneMixin:
    """Clone managed Tk widget trees while preserving geometry configuration."""

    _CLONE_OPTION_EXCLUSIONS = frozenset(
        {
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
    )

    @staticmethod
    def _managed_children(parent: tk.Widget) -> list[tk.Widget]:
        children: list[tk.Widget] = []
        for child in parent.winfo_children():
            try:
                if child.winfo_manager():
                    children.append(child)
            except tk.TclError:
                pass
        return children

    @classmethod
    def _copy_widget_options(cls, source: tk.Widget) -> dict:
        options = {}
        try:
            configuration = source.configure()
        except tk.TclError:
            return options

        for name in configuration:
            if name in cls._CLONE_OPTION_EXCLUSIONS:
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

    @staticmethod
    def _apply_geometry(source: tk.Widget, target: tk.Widget) -> None:
        manager = source.winfo_manager()
        try:
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
        except tk.TclError:
            pass

    def _create_cloned_widget(
        self,
        source: tk.Widget,
        parent: tk.Widget,
        key: str,
        options: dict,
    ) -> tk.Widget:
        """Create one cloned widget; subclasses provide application-specific policy."""
        raise NotImplementedError

    def _clone_widget(
        self,
        source: tk.Widget,
        parent: tk.Widget,
        key: str,
    ) -> tk.Widget:
        target = self._create_cloned_widget(
            source,
            parent,
            key,
            self._copy_widget_options(source),
        )
        self._copy_grid_configuration(source, target)

        for child in self._managed_children(source):
            cloned_child = self._clone_widget(child, target, key)
            self._apply_geometry(child, cloned_child)

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


__all__ = ["WidgetTreeCloneMixin"]
