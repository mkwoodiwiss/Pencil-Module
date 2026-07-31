"""Startup compatibility fix for the MEU v2 notebook tab ordering."""

from __future__ import annotations

from tkinter import ttk

from .hmi_v2 import HMI as _V2HMI


class HMI(_V2HMI):
    """MEU v2 HMI with safe ttk.Notebook append handling during startup."""

    def __init__(self, *args, **kwargs) -> None:
        original_insert = ttk.Notebook.insert

        def safe_insert(notebook, pos, child, **options):
            """Use Tk's explicit append token when a numeric append is requested."""
            if isinstance(pos, int):
                try:
                    tab_count = len(notebook.tabs())
                except Exception:
                    tab_count = 0
                if pos >= tab_count:
                    pos = "end"
            return original_insert(notebook, pos, child, **options)

        ttk.Notebook.insert = safe_insert
        try:
            super().__init__(*args, **kwargs)
        finally:
            ttk.Notebook.insert = original_insert


__all__ = ["HMI"]
