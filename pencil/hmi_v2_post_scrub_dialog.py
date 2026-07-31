"""Compatibility wrapper for the extracted Post-Scrub selector state."""

from __future__ import annotations

from .hmi_post_scrub_state import PostScrubStateMixin
from .hmi_v2_tk_compat import HMI as _V2TkCompatHMI


class HMI(PostScrubStateMixin, _V2TkCompatHMI):
    """Backward-compatible HMI retaining the historical module path."""


__all__ = ["HMI"]
