"""Compatibility wrapper for extracted MEU v2 summary formatting."""

from __future__ import annotations

from .hmi_summary_formatting import SummaryFormattingMixin
from .hmi_v2_post_scrub_dialog import HMI as _PostScrubDialogHMI


class HMI(SummaryFormattingMixin, _PostScrubDialogHMI):
    """Backward-compatible HMI retaining the historical module path."""


__all__ = ["HMI"]
