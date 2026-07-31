"""Compatibility wrapper for extracted Tk clone behavior."""

from __future__ import annotations

from .hmi_tk_clone_compat import TkCloneCompatibilityMixin
from .hmi_v2_clone_test_layout import HMI as _CloneLayoutHMI


class HMI(TkCloneCompatibilityMixin, _CloneLayoutHMI):
    """Backward-compatible HMI retaining the historical module path."""


__all__ = ["HMI"]
