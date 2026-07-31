"""Production composition point for the MEU v2 HMI."""

from __future__ import annotations

from .hmi_filtration_dialogs import FiltrationSettingsDialogMixin
from .hmi_identifier_state import IdentifierStateMixin
from .hmi_post_scrub_state import PostScrubStateMixin
from .hmi_summary_formatting import SummaryFormattingMixin
from .hmi_v2_tk_compat import HMI as _V2TkCompatHMI


class HMI(
    FiltrationSettingsDialogMixin,
    IdentifierStateMixin,
    PostScrubStateMixin,
    SummaryFormattingMixin,
    _V2TkCompatHMI,
):
    """Final v2 HMI assembled from focused behavior components."""

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._initialize_v2_identifier_state()


__all__ = ["HMI"]
