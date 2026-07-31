"""Post-Scrub filtration mode state for the MEU v2 HMI."""

from __future__ import annotations

import tkinter as tk


class PostScrubStateMixin:
    """Create and coordinate Post-Scrub weight/time selector variables."""

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.post_scrub_filt_use_time_var = tk.BooleanVar(
            value=not self.post_scrub_filt_use_weight_var.get()
        )
        self.post_scrub_bw_use_time_var = tk.BooleanVar(
            value=not self.post_scrub_bw_use_weight_var.get()
        )

    def _toggle_post_scrub_filt_weight(self) -> None:
        self._set_post_scrub_mode(
            self.post_scrub_filt_use_weight_var,
            self.post_scrub_filt_use_time_var,
        )

    def _toggle_post_scrub_filt_time(self) -> None:
        self._set_post_scrub_mode(
            self.post_scrub_filt_use_time_var,
            self.post_scrub_filt_use_weight_var,
        )

    def _toggle_post_scrub_bw_weight(self) -> None:
        self._set_post_scrub_mode(
            self.post_scrub_bw_use_weight_var,
            self.post_scrub_bw_use_time_var,
        )

    def _toggle_post_scrub_bw_time(self) -> None:
        self._set_post_scrub_mode(
            self.post_scrub_bw_use_time_var,
            self.post_scrub_bw_use_weight_var,
        )

    @staticmethod
    def _set_post_scrub_mode(selected: tk.BooleanVar, alternate: tk.BooleanVar) -> None:
        if selected.get():
            alternate.set(False)
        elif not alternate.get():
            selected.set(True)


__all__ = ["PostScrubStateMixin"]
