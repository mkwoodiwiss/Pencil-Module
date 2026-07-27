"""MEU-branded HMI entry point.

The legacy HMI implementation remains in :mod:`pencil.hmi` so existing imports
continue to work while the application presents the current equipment name.
"""

from .hmi import HMI as _BaseHMI


class HMI(_BaseHMI):
    """HMI for the MF/UF Membrane Evaluation Unit."""

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.title("MF/UF Membrane Evaluation Unit (MEU)")
