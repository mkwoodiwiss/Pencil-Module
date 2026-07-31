"""Tk 8.6 compatibility for MEU v2 Test-layout cloning."""

from __future__ import annotations

import tkinter as tk

from .hmi_v2_clone_test_layout import HMI as _CloneLayoutHMI


class HMI(_CloneLayoutHMI):
    """Use direct Tcl propagation queries while cloning nested Test widgets."""

    def _clone_widget(
        self,
        source: tk.Widget,
        parent: tk.Widget,
        key: str,
    ) -> tk.Widget:
        original_pack_propagate = source.pack_propagate
        original_grid_propagate = source.grid_propagate

        def pack_propagate_query(flag=None):
            if flag is not None:
                return source.tk.call("pack", "propagate", source._w, flag)
            return source.tk.call("pack", "propagate", source._w)

        def grid_propagate_query(flag=None):
            if flag is not None:
                return source.tk.call("grid", "propagate", source._w, flag)
            return source.tk.call("grid", "propagate", source._w)

        source.pack_propagate = pack_propagate_query
        source.grid_propagate = grid_propagate_query
        try:
            return super()._clone_widget(source, parent, key)
        finally:
            source.pack_propagate = original_pack_propagate
            source.grid_propagate = original_grid_propagate


__all__ = ["HMI"]
