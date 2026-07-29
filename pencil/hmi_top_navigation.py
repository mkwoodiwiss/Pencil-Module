"""Top-button navigation layout for the MEU touchscreen HMI."""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk

from .hmi_layout_validated import HMI as _ValidatedHMI
from .hmi_navigation_fix import HMI as _PreviousHMI


class HMI(_PreviousHMI):
    """MEU HMI with uniform top navigation and a centered PFD."""

    EDGE_GAP = 3
    NAV_HEIGHT = 34
    PFD_HEIGHT = 217
    PFD_WIDTH = 780
    PFD_SCALE_X = 1.0
    NAV_FONT = ("Arial", 9)
    NAV_FONT_ACTIVE = ("Arial", 9, "bold")
    START_FONT = ("Arial", 15, "bold")
    SENSOR_FRAME_EXTRA_HEIGHT = 11

    def _remove_native_tabs(self) -> None:
        """Remove native tabs and flatten the notebook client styling."""
        super()._remove_native_tabs()

        style = ttk.Style(self)
        style.layout(
            "MEU.FlatClient.TNotebook",
            [("Notebook.client", {"sticky": "nswe"})],
        )
        style.configure(
            "MEU.FlatClient.TNotebook",
            borderwidth=0,
            padding=0,
            tabmargins=0,
        )
        self.notebook.configure(style="MEU.FlatClient.TNotebook")

    def _finish_navigation_layout(self) -> None:
        """Finalize the tabless page stack and operator control sizing."""
        super()._finish_navigation_layout()
        self._remove_native_tabs()
        self._enlarge_start_buttons()
        self._arrange_lower_panels()
        self._refresh_navigation_rails()
        self.update_idletasks()
        self._align_notebook_client_to_screen()
        self.after_idle(self._verify_top_spacing)
        self.after_idle(self._arrange_lower_panels)

    def _align_notebook_client_to_screen(self) -> None:
        """Remove the real ttk client inset instead of guessing with padding."""
        self.update_idletasks()
        try:
            page = self._active_tab
            client_inset = max(
                0,
                page.winfo_rooty() - self.notebook.winfo_rooty(),
            )
            notebook_top = self.notebook.winfo_y()
            total_offset = max(0, notebook_top + client_inset)

            self.notebook.pack_forget()
            self.notebook.place(
                x=0,
                y=-total_offset,
                relwidth=1.0,
                relheight=1.0,
                height=total_offset,
            )
            self._measured_notebook_top_offset = total_offset
        except Exception:
            self._measured_notebook_top_offset = 0

    def _verify_top_spacing(self) -> None:
        """Recheck geometry after placement and correct any remaining offset once."""
        self.update_idletasks()
        try:
            first_pfd = next(iter(self.pfds.values()))
            buttons = first_pfd.get("navigation_buttons", [])
            if not buttons:
                return

            actual_top_gap = buttons[0].winfo_rooty() - self.winfo_rooty()
            correction = actual_top_gap - self.EDGE_GAP
            if correction == 0:
                return

            current_y = int(self.notebook.place_info().get("y", 0))
            current_height = int(self.notebook.place_info().get("height", 0))
            self.notebook.place_configure(
                y=current_y - correction,
                height=current_height + correction,
            )
        except Exception:
            pass

    def _arrange_lower_panels(self) -> None:
        """Precisely center Settings and guarantee full Sensors-frame height."""
        self.update_idletasks()
        for tab in (self.test_tab, self.benchmark_tab, self.clean_tab):
            settings = None
            sensors = None
            cycle_status = None

            for widget in self._walk_widgets(tab):
                if not isinstance(widget, tk.LabelFrame):
                    continue
                try:
                    title = str(widget.cget("text"))
                except Exception:
                    continue
                if title == "Settings":
                    settings = widget
                elif title == "Sensors":
                    sensors = widget
                elif title == "Cycle Status":
                    cycle_status = widget

            if settings is not None:
                try:
                    left_column = settings.master
                    left_column.pack_configure(fill="y", expand=False, pady=0, anchor="n")
                    self.update_idletasks()

                    settings_width = settings.winfo_reqwidth()
                    left_column.configure(width=settings_width)
                    left_column.pack_propagate(False)

                    settings.pack_forget()
                    settings.place(
                        relx=0.5,
                        rely=0.5,
                        anchor="center",
                    )
                except Exception:
                    pass

            if sensors is not None:
                try:
                    right_column = sensors.master
                    right_column.pack_configure(fill="y", pady=0)

                    natural_height = getattr(
                        sensors,
                        "_meu_natural_height",
                        None,
                    )
                    if natural_height is None:
                        natural_height = sensors.winfo_reqheight()
                        sensors._meu_natural_height = natural_height

                    sensors.configure(
                        height=natural_height + self.SENSOR_FRAME_EXTRA_HEIGHT
                    )
                    sensors.pack_propagate(False)
                    sensors.pack_configure(padx=5, pady=(0, 2), anchor="n")
                except Exception:
                    pass

            if cycle_status is not None:
                try:
                    cycle_status.pack_configure(pady=(2, 0), anchor="n")
                except Exception:
                    pass

    def _create_pfd(self, parent: tk.Widget) -> dict:
        """Create a centered PFD with equal spacing above and below the tabs."""
        section = tk.Frame(
            parent,
            width=self.PFD_WIDTH,
            height=(2 * self.EDGE_GAP) + self.NAV_HEIGHT + self.PFD_HEIGHT,
            bg=parent.cget("bg"),
            bd=0,
            highlightthickness=0,
        )
        section.pack(side="top", anchor="n", padx=10, pady=0)
        section.pack_propagate(False)

        nav = tk.Frame(
            section,
            width=self.PFD_WIDTH,
            height=(2 * self.EDGE_GAP) + self.NAV_HEIGHT,
            bg=parent.cget("bg"),
            bd=0,
            highlightthickness=0,
        )
        nav.pack(side="top", fill="x")
        nav.pack_propagate(False)

        pfd_holder = tk.Frame(
            section,
            width=self.PFD_WIDTH,
            height=self.PFD_HEIGHT,
            bg="white",
            bd=1,
            relief="solid",
            highlightthickness=0,
        )
        pfd_holder.pack(side="top", anchor="n")
        pfd_holder.pack_propagate(False)

        pfd = _ValidatedHMI._create_pfd(self, pfd_holder)
        canvas = pfd["canvas"]

        # Info and Exit are now full-size navigation buttons, so remove the
        # legacy controls that were drawn over the PFD canvas.
        for widget in list(self._walk_widgets(canvas)):
            if not isinstance(widget, tk.Button):
                continue
            try:
                if widget.cget("text") not in {"?", "X"}:
                    continue
                owner = widget.master
                widget.destroy()
                if isinstance(owner, tk.Frame) and not owner.winfo_children():
                    owner.destroy()
            except Exception:
                pass

        self._resize_pfd_vessels_and_routes(canvas)
        canvas.configure(width=self.PFD_WIDTH - 2, height=self.PFD_HEIGHT - 2)
        canvas.pack_configure(side="top", anchor="n", pady=0)

        pfd["top_section"] = section
        pfd["navigation_rail"] = nav
        pfd["navigation_buttons"] = self._populate_top_navigation(nav, parent)
        return pfd

    def _populate_top_navigation(
        self, nav: tk.Frame, current_tab: tk.Widget
    ) -> list[tk.Button]:
        """Create five equal-size top navigation buttons."""
        nav.columnconfigure((0, 1, 2, 3, 4), weight=1, uniform="meu_nav")
        nav.rowconfigure(0, weight=1)
        buttons: list[tk.Button] = []
        items = (
            ("Test", self.test_tab, lambda: self._select_tab(self.test_tab)),
            (
                "Benchmark",
                self.benchmark_tab,
                lambda: self._select_tab(self.benchmark_tab),
            ),
            ("Clean", self.clean_tab, lambda: self._select_tab(self.clean_tab)),
            ("Info", None, self._show_control_narrative),
            ("Exit", None, self._confirm_exit),
        )

        for column, (label, tab, command) in enumerate(items):
            selected = tab is not None and tab is current_tab
            button = tk.Button(
                nav,
                text=label,
                command=command,
                font=self.NAV_FONT_ACTIVE if selected else self.NAV_FONT,
                relief="sunken" if selected else "raised",
                borderwidth=2,
                highlightthickness=0,
                bg="#cfcfcf" if selected else "#e8e8e8",
                activebackground="#d8d8d8",
                padx=4,
                pady=3,
                cursor="hand2",
            )
            button.grid(
                row=0,
                column=column,
                sticky="nsew",
                padx=(0 if column == 0 else 2, 0),
                pady=(self.EDGE_GAP, self.EDGE_GAP),
            )
            buttons.append(button)
        return buttons

    def _refresh_navigation_rails(self) -> None:
        """Show one consistent active state across every top navigation row."""
        active_index = {
            self.test_tab: 0,
            self.benchmark_tab: 1,
            self.clean_tab: 2,
        }.get(self._active_tab)

        for pfd in self.pfds.values():
            buttons = pfd.get("navigation_buttons", [])
            for index, button in enumerate(buttons):
                selected = index == active_index and index < 3
                try:
                    button.configure(
                        relief="sunken" if selected else "raised",
                        bg="#cfcfcf" if selected else "#e8e8e8",
                        font=self.NAV_FONT_ACTIVE if selected else self.NAV_FONT,
                    )
                except Exception:
                    pass

    def _enlarge_start_buttons(self) -> None:
        """Increase every Start/Stop control without affecting other buttons."""
        for tab in (self.test_tab, self.benchmark_tab, self.clean_tab):
            for widget in self._walk_widgets(tab):
                if not isinstance(widget, tk.Button):
                    continue
                try:
                    if str(widget.cget("text")) not in {"Start", "Stop"}:
                        continue
                    widget.configure(
                        font=self.START_FONT,
                        width=9,
                        height=1,
                        padx=8,
                        pady=5,
                    )
                except Exception:
                    pass


__all__ = ["HMI"]