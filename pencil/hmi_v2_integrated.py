"""Production composition point for the MEU v2 HMI."""

from __future__ import annotations

from .hmi_filtration_dialogs import FiltrationSettingsDialogMixin
from .hmi_identifier_state import IdentifierStateMixin
from .hmi_post_scrub_state import PostScrubStateMixin
from .hmi_summary_formatting import SummaryFormattingMixin
from .hmi_tk_clone_compat import TkCloneCompatibilityMixin
from .hmi_touch_entries import TouchEntryMixin
from .hmi_v2_clone_test_layout import HMI as _CloneLayoutHMI


class HMI(
    FiltrationSettingsDialogMixin,
    IdentifierStateMixin,
    PostScrubStateMixin,
    SummaryFormattingMixin,
    TouchEntryMixin,
    TkCloneCompatibilityMixin,
    _CloneLayoutHMI,
):
    """Final v2 HMI assembled from focused behavior components."""

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._initialize_v2_identifier_state()


__all__ = ["HMI"]
