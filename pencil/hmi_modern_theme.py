"""Classic MEU HMI styling with selected visual accents.

The original HMI appearance is preserved. Only process-vessel colors and
outlines, plus Exit and Cancel button colors, are customized.
"""

from __future__ import annotations

import tkinter as tk

from .hmi_lower_panel_fix import HMI as _LayoutHMI


class HMI(_LayoutHMI):
    """MEU HMI using the original style with selected retained accents."""

    VESSEL_FILL = "#D5EAF2"
    MEMBRANE_FILL = "#D9E1E7"
    VESSEL_OUTLINE = "#9FB0BC"
    DANGER = "#B94747"
    DANGER_ACTIVE = "#963A3A"

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._apply_selected_accents(self)
        self.bind_all("<Map>", self._style_mapped_widget, add="+")

    def _style_mapped_widget(self, event) -> None:
        """Style newly opened dialogs without changing their layout or theme."""
        widget = event.widget
        try:
            widget.after_idle(lambda target=widget: self._apply_selected_accents(target))
        except tk.TclError:
            pass

    def _style_button(self, button: tk.Button) -> None:
        """Retain red treatment only for Exit and Cancel actions."""
        try:
            text = str(button.cget("text")).strip().lower()
            if text not in {"exit", "cancel"}:
                return
            button.configure(
                bg=self.DANGER,
                fg="white",
                activebackground=self.DANGER_ACTIVE,
                activeforeground="white",
            )
        except tk.TclError:
            pass

    def _style_vessels(self, canvas: tk.Canvas) -> None:
        """Retain modern vessel fills and outlines on the classic PFD."""
        for item in canvas.find_all():
            try:
                if canvas.type(item) != "rectangle":
                    continue
                fill = str(canvas.itemcget(item, "fill")).lower()
                if fill in {"lightblue", self.VESSEL_FILL.lower()}:
                    canvas.itemconfigure(
                        item,
                        fill=self.VESSEL_FILL,
                        outline=self.VESSEL_OUTLINE,
                        width=1,
                    )
                elif fill in {"lightgray", self.MEMBRANE_FILL.lower()}:
                    canvas.itemconfigure(
                        item,
                        fill=self.MEMBRANE_FILL,
                        outline=self.VESSEL_OUTLINE,
                        width=1,
                    )
            except tk.TclError:
                continue

    def _apply_selected_accents(self, parent: tk.Widget) -> None:
        """Apply only the requested accents and leave all other styling intact."""
        try:
            if isinstance(parent, tk.Button):
                self._style_button(parent)
            elif isinstance(parent, tk.Canvas):
                self._style_vessels(parent)
        except (tk.TclError, AttributeError):
            pass

        try:
            children = parent.winfo_children()
        except tk.TclError:
            return
        for child in children:
            self._apply_selected_accents(child)

    def _build_prime_popup(self, title: str, action_text: str, action_command) -> None:
        super()._build_prime_popup(title, action_text, action_command)
        if self.prime_frame:
            self._apply_selected_accents(self.prime_frame)
            self._center_prime_window()


__all__ = ["HMI"]
