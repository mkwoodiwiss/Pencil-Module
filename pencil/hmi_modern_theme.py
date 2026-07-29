"""Modern visual theme for the MEU touchscreen HMI.

This module changes presentation only. Existing widget geometry, grouping,
packing, placement, and operator workflow remain owned by the lower-panel HMI.
"""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk

from .hmi_lower_panel_fix import HMI as _LayoutHMI


class HMI(_LayoutHMI):
    """MEU HMI with a clean, high-contrast industrial visual theme."""

    BG = "#E8EEF3"
    SURFACE = "#F4F7F9"
    PANEL = "#FFFFFF"
    TEXT = "#172633"
    MUTED = "#536573"
    BORDER = "#9FB0BC"
    PRIMARY = "#176B87"
    PRIMARY_ACTIVE = "#12566D"
    SECONDARY = "#DCE5EC"
    SECONDARY_ACTIVE = "#C7D4DE"
    SUCCESS = "#2B8A5A"
    DANGER = "#B94747"
    DANGER_ACTIVE = "#963A3A"
    PIPE = "#718795"
    TANK = "#D5EAF2"
    MEMBRANE = "#D9E1E7"

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.configure(bg=self.BG)
        self._configure_ttk_theme()
        self._apply_modern_theme(self)
        self.bind_all("<Map>", self._style_mapped_widget, add="+")
        self.after_idle(self._post_theme_layout_check)
        self.after(100, self._post_theme_layout_check)

    def _configure_ttk_theme(self) -> None:
        """Color ttk navigation without changing tab dimensions or padding."""
        style = ttk.Style(self)
        style.configure("TNotebook", background=self.BG, borderwidth=0)
        style.configure(
            "TNotebook.Tab",
            background=self.SECONDARY,
            foreground=self.TEXT,
            borderwidth=0,
        )
        style.map(
            "TNotebook.Tab",
            background=[("selected", self.PANEL), ("active", self.SECONDARY_ACTIVE)],
            foreground=[("selected", self.PRIMARY)],
        )

    def _style_mapped_widget(self, event) -> None:
        widget = event.widget
        try:
            widget.after_idle(lambda target=widget: self._apply_modern_theme(target))
        except tk.TclError:
            pass

    def _post_theme_layout_check(self) -> None:
        """Re-run established geometry correction after visual styling."""
        try:
            self._arrange_lower_panels()
            self.update_idletasks()
        except (AttributeError, tk.TclError):
            pass

    def _button_palette(self, text: str) -> tuple[str, str, str]:
        normalized = text.strip().lower()
        if normalized in {"start", "continue", "finish", "save", "ok"}:
            return self.PRIMARY, "white", self.PRIMARY_ACTIVE
        if normalized in {"cancel", "exit", "quit", "stop"}:
            return self.DANGER, "white", self.DANGER_ACTIVE
        if normalized == "prime":
            return self.PRIMARY, "white", self.PRIMARY_ACTIVE
        return self.SECONDARY, self.TEXT, self.SECONDARY_ACTIVE

    def _style_button(self, button: tk.Button) -> None:
        text = str(button.cget("text"))
        bg, fg, active_bg = self._button_palette(text)
        button.configure(
            bg=bg,
            fg=fg,
            activebackground=active_bg,
            activeforeground=fg,
            disabledforeground=self.MUTED,
            relief="flat",
            borderwidth=0,
            highlightthickness=1,
            highlightbackground=self.BORDER,
            highlightcolor=self.PRIMARY,
            cursor="hand2",
        )

    def _style_canvas(self, canvas: tk.Canvas) -> None:
        canvas.configure(
            bg=self.SURFACE,
            highlightthickness=1,
            highlightbackground=self.BORDER,
        )
        for item in canvas.find_all():
            try:
                item_type = canvas.type(item)
                if item_type == "text":
                    canvas.itemconfigure(item, fill=self.TEXT)
                elif item_type == "rectangle":
                    fill = str(canvas.itemcget(item, "fill")).lower()
                    if fill == "lightblue":
                        canvas.itemconfigure(item, fill=self.TANK, outline=self.BORDER)
                    elif fill == "lightgray":
                        canvas.itemconfigure(item, fill=self.MEMBRANE, outline=self.BORDER)
                    elif fill == "white":
                        canvas.itemconfigure(item, fill=self.PANEL, outline=self.BORDER)
                elif item_type == "line":
                    fill = str(canvas.itemcget(item, "fill")).lower()
                    canvas.itemconfigure(
                        item,
                        fill=self.SUCCESS if fill in {"green", self.SUCCESS.lower()} else self.PIPE,
                    )
            except tk.TclError:
                continue

    def _apply_modern_theme(self, parent: tk.Widget) -> None:
        """Apply visual properties recursively without changing geometry."""
        try:
            if isinstance(parent, (tk.Tk, tk.Toplevel)):
                parent.configure(bg=self.BG)
            elif isinstance(parent, tk.LabelFrame):
                parent.configure(
                    bg=self.PANEL,
                    fg=self.TEXT,
                    relief="solid",
                    borderwidth=1,
                    highlightthickness=0,
                )
            elif isinstance(parent, tk.Frame):
                parent.configure(bg=self.SURFACE)
            elif isinstance(parent, tk.Label):
                master_bg = parent.master.cget("bg") if "bg" in parent.master.keys() else self.SURFACE
                parent.configure(bg=master_bg, fg=self.TEXT)
            elif isinstance(parent, tk.Button):
                self._style_button(parent)
            elif isinstance(parent, (tk.Entry, tk.Spinbox)):
                parent.configure(
                    bg=self.PANEL,
                    fg=self.TEXT,
                    insertbackground=self.TEXT,
                    relief="solid",
                    borderwidth=1,
                    highlightthickness=1,
                    highlightbackground=self.BORDER,
                    highlightcolor=self.PRIMARY,
                )
            elif isinstance(parent, tk.Checkbutton):
                master_bg = parent.master.cget("bg") if "bg" in parent.master.keys() else self.SURFACE
                parent.configure(
                    bg=master_bg,
                    fg=self.TEXT,
                    activebackground=master_bg,
                    activeforeground=self.TEXT,
                    selectcolor=self.PANEL,
                    highlightthickness=0,
                )
            elif isinstance(parent, tk.Canvas):
                self._style_canvas(parent)
            elif isinstance(parent, tk.Text):
                parent.configure(
                    bg=self.PANEL,
                    fg=self.TEXT,
                    insertbackground=self.TEXT,
                    relief="solid",
                    borderwidth=1,
                )
        except (tk.TclError, AttributeError):
            pass

        try:
            children = parent.winfo_children()
        except tk.TclError:
            return
        for child in children:
            self._apply_modern_theme(child)

        self._refresh_valve_button_colors()

    def _refresh_valve_button_colors(self) -> None:
        if not hasattr(self, "pfds") or not hasattr(self, "solenoid_states"):
            return
        for pfd in self.pfds.values():
            for index, button in enumerate(pfd.get("solenoid_buttons", [])):
                active = index < len(self.solenoid_states) and self.solenoid_states[index]
                try:
                    button.configure(
                        bg=self.SUCCESS if active else self.SECONDARY,
                        fg="white" if active else self.TEXT,
                        activebackground=self.SUCCESS if active else self.SECONDARY_ACTIVE,
                        activeforeground="white" if active else self.TEXT,
                    )
                except tk.TclError:
                    pass

    def _update_lines(self) -> None:
        super()._update_lines()
        for pfd in getattr(self, "pfds", {}).values():
            canvas = pfd.get("canvas")
            if canvas is not None:
                self._style_canvas(canvas)
        self._refresh_valve_button_colors()

    def _build_prime_popup(self, title: str, action_text: str, action_command) -> None:
        super()._build_prime_popup(title, action_text, action_command)
        if self.prime_frame:
            self._apply_modern_theme(self.prime_frame)
            self._center_prime_window()


__all__ = ["HMI"]
