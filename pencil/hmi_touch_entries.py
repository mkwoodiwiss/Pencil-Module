"""Touchscreen-aware entry creation for legacy MEU settings dialogs."""

from __future__ import annotations

import tkinter as tk

from .widgets import KeyboardEntry, NumericEntry


class TouchEntryMixin:
    """Use MEU popup-enabled entries in settings forms."""

    @staticmethod
    def _entry(
        body: tk.Frame,
        row: int,
        label: str,
        variable: tk.Variable,
    ) -> None:
        tk.Label(body, text=label).grid(
            row=row,
            column=0,
            sticky="e",
            padx=6,
            pady=4,
        )
        entry_class = KeyboardEntry if isinstance(variable, tk.StringVar) else NumericEntry
        entry_class(body, textvariable=variable, width=16).grid(
            row=row,
            column=1,
            sticky="w",
            padx=6,
            pady=4,
        )


__all__ = ["TouchEntryMixin"]
