"""Runtime fixes for the MEU touchscreen HMI."""

from __future__ import annotations

import os
import threading
import tkinter as tk
from tkinter import messagebox

from .hmi_meu import HMI as _MEUHMI
from .results_manager import open_results_manager


class HMI(_MEUHMI):
    """MEU HMI with reliable callbacks and touchscreen run-state behavior."""

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._manual_tare_channels: set[int] = set()
        self._bind_settings_action_buttons()
        self._run_started = False

    def _create_pfd(self, parent: tk.Widget) -> dict:
        """Create a clean, orthogonal MEU PFD with unobstructed labels."""
        canvas = tk.Canvas(parent, width=780, height=175, bg="white")
        canvas.pack(pady=(2, 0))

        btn_opts = {"width": 2, "height": 1}
        btn_frame = tk.Frame(canvas, bg="white")
        help_btn = tk.Button(btn_frame, text="?", command=self._show_control_narrative, **btn_opts)
        close_btn = tk.Button(btn_frame, text="X", command=self._confirm_exit, **btn_opts)
        help_btn.pack(side="left", padx=(0, 2), ipadx=4, ipady=4)
        close_btn.pack(side="left", ipadx=4, ipady=4)
        canvas.create_window(770, 10, window=btn_frame, anchor="ne")

        # Inlet tanks and valves.
        canvas.create_rectangle(25, 25, 105, 75, fill="lightblue")
        canvas.create_text(65, 15, text="Feed Tank")
        pi2_text = canvas.create_text(65, 65, text="-- PSI")

        canvas.create_rectangle(25, 105, 105, 155, fill="lightblue")
        canvas.create_text(65, 95, text="BW Tank")
        pi1_text = canvas.create_text(65, 145, text="-- PSI")

        # Keep the membrane 180 px long. Move it right enough to reduce the
        # membrane-to-valve-column gap by one third, and down to give the feed
        # inlet a clear vertical approach above the downward arrow.
        membrane_left = 293
        membrane_right = 473
        membrane_center = (membrane_left + membrane_right) / 2
        top_port_center = membrane_left + 22.5
        lower_port_center = membrane_right - 22.5
        membrane_top = 55
        membrane_bottom = 75
        top_port_top = 35
        lower_port_bottom = 95

        canvas.create_rectangle(
            membrane_left, membrane_top, membrane_right, membrane_bottom, fill="lightgray"
        )
        canvas.create_rectangle(
            top_port_center - 7.5,
            top_port_top,
            top_port_center + 7.5,
            membrane_top,
            fill="lightgray",
        )
        canvas.create_rectangle(
            lower_port_center - 7.5,
            membrane_bottom,
            lower_port_center + 7.5,
            lower_port_bottom,
            fill="lightgray",
        )
        canvas.create_text(membrane_center, 45, text="Membrane")

        # Outlet vessels with labels kept clear of all valve buttons and piping.
        canvas.create_rectangle(600, 20, 650, 70, fill="lightblue")
        canvas.create_text(625, 10, text="Filtrate")
        effluent_weight_text = canvas.create_text(625, 60, text="-- g")

        canvas.create_rectangle(600, 115, 650, 165, fill="lightblue")
        canvas.create_text(625, 105, text="BW Effluent")
        backwash_weight_text = canvas.create_text(625, 155, text="-- g")

        canvas.create_rectangle(690, 70, 740, 120, fill="lightblue")
        canvas.create_text(715, 60, text="Waste")

        lines = {}
        valve_labels = {}
        valve_to_lines = {
            0: [0, "v1_vert", "v1_end"],
            1: [1, "v2_rise", "v2_top", "v2_drop"],
            2: [2, "v3_vert1", "v3_vert2"],
            3: [3, "v3_vert2"],
            4: [4],
        }

        # V1: BW Tank to the membrane left-end port.
        lines[0] = canvas.create_line(105, 130, 260, 130, fill="gray", width=2)
        lines["v1_vert"] = canvas.create_line(260, 130, 260, 65, fill="gray", width=2)
        lines["v1_end"] = canvas.create_line(
            260, 65, membrane_left, 65, arrow="last", fill="gray", width=2
        )
        valve_labels["V1"] = canvas.create_text(165, 130, text="V1")

        # V2: Feed Tank rises above the top port, runs horizontally, then has a
        # short visible vertical section before the downward arrow enters the port.
        feed_header_y = 25
        lines[1] = canvas.create_line(105, 50, 220, 50, fill="gray", width=2)
        lines["v2_rise"] = canvas.create_line(220, 50, 220, feed_header_y, fill="gray", width=2)
        lines["v2_top"] = canvas.create_line(
            220, feed_header_y, top_port_center, feed_header_y, fill="gray", width=2
        )
        lines["v2_drop"] = canvas.create_line(
            top_port_center,
            feed_header_y,
            top_port_center,
            top_port_top,
            arrow="last",
            fill="gray",
            width=2,
        )
        valve_labels["V2"] = canvas.create_text(165, 50, text="V2")
        canvas.create_rectangle(225, 17.5, 280, 32.5, fill="white", outline="black")
        te_text = canvas.create_text(252.5, 25, text="-- C")

        # V3, V4, and V5 use one aligned valve column.
        outlet_valve_x = 520

        lines[2] = canvas.create_line(lower_port_center, 140, 600, 140, arrow="last", fill="gray", width=2)
        lines["v3_vert1"] = canvas.create_line(lower_port_center, 105, lower_port_center, 140, fill="gray", width=2)
        lines["v3_vert2"] = canvas.create_line(lower_port_center, lower_port_bottom, lower_port_center, 105, fill="gray", width=2)
        valve_labels["V3"] = canvas.create_text(outlet_valve_x, 140, text="V3")

        lines[3] = canvas.create_line(lower_port_center, 105, 690, 105, arrow="last", fill="gray", width=2)
        valve_labels["V4"] = canvas.create_text(outlet_valve_x, 105, text="V4")

        lines[4] = canvas.create_line(membrane_right, 65, 600, 65, arrow="last", fill="gray", width=2)
        valve_labels["V5"] = canvas.create_text(outlet_valve_x, 65, text="V5")

        solenoid_buttons = []
        valve_keys = ["V1", "V2", "V3", "V4", "V5"]
        for i in range(5):
            btn = tk.Button(
                canvas,
                text=f"V{i + 1}",
                width=3,
                bg="lightgray",
                command=lambda ch=i: self.toggle_solenoid(ch),
            )
            x, y = canvas.coords(valve_labels[valve_keys[i]])
            canvas.create_window(x, y, window=btn)
            solenoid_buttons.append(btn)

        prime_btn = tk.Button(canvas, text="Prime", command=self.prime)
        canvas.create_window(membrane_center, 110, window=prime_btn)

        return {
            "canvas": canvas,
            "pi1_text": pi1_text,
            "pi2_text": pi2_text,
            "te_text": te_text,
            "effluent_weight_text": effluent_weight_text,
            "backwash_weight_text": backwash_weight_text,
            "lines": lines,
            "valve_labels": valve_labels,
            "valve_to_lines": valve_to_lines,
            "solenoid_buttons": solenoid_buttons,
            "prime_btn": prime_btn,
        }

    @staticmethod
    def _is_descendant(widget: tk.Widget, ancestor: tk.Widget) -> bool:
        current = widget
        while current is not None:
            if current is ancestor:
                return True
            try:
                parent_name = current.winfo_parent()
                if not parent_name:
                    break
                current = current.nametowidget(parent_name)
            except Exception:
                break
        return False

    def _bind_settings_action_buttons(self) -> None:
        """Bind Python callables after the settings buttons are rearranged."""
        for widget in self._walk_widgets(self):
            if not isinstance(widget, tk.Button):
                continue

            try:
                text = widget.cget("text")
            except Exception:
                continue

            if self._is_descendant(widget, self.test_tab):
                edit_command = self._edit_test_settings
            elif self._is_descendant(widget, self.benchmark_tab):
                edit_command = self._edit_benchmark_settings
            elif self._is_descendant(widget, self.clean_tab):
                edit_command = self._edit_clean_settings
            else:
                continue

            if text == "Edit Settings":
                widget.config(command=edit_command)
            elif text == "Calibrate":
                widget.config(command=self.calibrate)
            elif text == "Tare FIL":
                widget.config(command=lambda button=widget: self._start_manual_tare(0, button))
            elif text == "Tare BW EFL":
                widget.config(command=lambda button=widget: self._start_manual_tare(1, button))

    def _start_manual_tare(self, channel: int, button: tk.Button) -> None:
        """Tare one scale on a worker thread so the touchscreen stays responsive."""
        if channel in self._manual_tare_channels or getattr(self, "is_running", False):
            return

        self._manual_tare_channels.add(channel)
        normal_text = "Tare FIL" if channel == 0 else "Tare BW EFL"
        try:
            button.config(text="Taring...", state="disabled")
        except Exception:
            pass

        def worker() -> None:
            error = ""
            success = False
            try:
                success = bool(self.module.zero_scale(channel))
            except Exception as exc:
                error = str(exc)
            self.after(
                0,
                lambda: self._manual_tare_finished(
                    channel, button, normal_text, success, error
                ),
            )

        threading.Thread(target=worker, daemon=True).start()

    def _manual_tare_finished(
        self,
        channel: int,
        button: tk.Button,
        normal_text: str,
        success: bool,
        error: str,
    ) -> None:
        self._manual_tare_channels.discard(channel)
        try:
            button.config(text=normal_text, state="normal")
        except Exception:
            pass

        scale_name = "Filtrate scale" if channel == 0 else "BW Effluent scale"
        if error:
            messagebox.showerror("Scale Tare Failed", f"{scale_name}: {error}")
        elif not success:
            messagebox.showerror(
                "Scale Tare Failed",
                f"{scale_name} did not accept tare or did not return two verified zero readings. "
                "Confirm the reading is stable and try again.",
            )

    def _style_settings_window(self, window: tk.Toplevel) -> None:
        """Use a larger, centered touchscreen-friendly settings dialog."""
        super()._style_settings_window(window)

        def enlarge(parent: tk.Widget) -> None:
            for child in parent.winfo_children():
                try:
                    if isinstance(child, tk.Button):
                        child.config(font=("Arial", 16), height=2, padx=14, pady=7)
                    elif isinstance(child, tk.Checkbutton):
                        child.config(font=("Arial", 15), padx=9, pady=6)
                    elif isinstance(child, tk.Entry):
                        child.config(font=("Arial", 16), width=max(9, int(child.cget("width"))))
                    elif isinstance(child, tk.Label):
                        child.config(font=("Arial", 15))
                except Exception:
                    pass

                try:
                    manager = child.winfo_manager()
                    if manager == "grid":
                        info = child.grid_info()
                        child.grid_configure(
                            padx=max(7, int(info.get("padx", 0) or 0)),
                            pady=max(5, int(info.get("pady", 0) or 0)),
                        )
                    elif manager == "pack":
                        info = child.pack_info()
                        child.pack_configure(
                            padx=max(7, int(info.get("padx", 0) or 0)),
                            pady=max(5, int(info.get("pady", 0) or 0)),
                        )
                except Exception:
                    pass

                enlarge(child)

        enlarge(window)

        try:
            window.grid_anchor("center")
            window.update_idletasks()

            screen_width = self.winfo_screenwidth()
            screen_height = self.winfo_screenheight()
            width = min(screen_width - 24, max(600, window.winfo_reqwidth() + 100))
            height = min(screen_height - 40, max(400, window.winfo_reqheight() + 80))

            x = max(0, self.winfo_rootx() + (self.winfo_width() - width) // 2)
            y = max(0, self.winfo_rooty() + (self.winfo_height() - height) // 2)
            window.geometry(f"{width}x{height}+{x}+{y}")
        except Exception:
            pass

    def _disable_manual_controls(self) -> None:
        """Disable every HMI button except Cancel, help, and close during a run."""
        for widget in self._walk_widgets(self):
            if not isinstance(widget, tk.Button):
                continue
            try:
                text = widget.cget("text")
                if text in {"Cancel", "?", "X"}:
                    widget.config(state="normal")
                else:
                    widget.config(state="disabled")
            except Exception:
                pass

    def _enable_manual_controls(self) -> None:
        """Restore all HMI buttons after a run finishes."""
        for widget in self._walk_widgets(self):
            if isinstance(widget, tk.Button):
                try:
                    widget.config(state="normal")
                except Exception:
                    pass
        self._bind_settings_action_buttons()
        self._sync_all_valve_buttons()

    def _finish_start_attempt(self) -> None:
        if getattr(self, "is_running", False):
            self._disable_manual_controls()
        else:
            self._run_started = False
            self._enable_manual_controls()

    def start_test(self) -> None:
        self._run_started = True
        super().start_test()
        self._finish_start_attempt()

    def start_benchmark(self) -> None:
        self._run_started = True
        super().start_benchmark()
        self._finish_start_attempt()

    def start_clean(self) -> None:
        self._run_started = True
        super().start_clean()
        self._finish_start_attempt()

    def _latest_saved_files(self) -> list[str]:
        """Return the newest data/settings files from the active log directory."""
        log_dir = getattr(getattr(self, "test_system", None), "log_dir", "logs")
        try:
            names = [
                name for name in os.listdir(log_dir)
                if name.endswith("_data.csv") or name.endswith("_settings.csv")
            ]
            names.sort(
                key=lambda name: os.path.getmtime(os.path.join(log_dir, name)),
                reverse=True,
            )
            if not names:
                return []

            newest = names[0]
            stem = newest.removesuffix("_data.csv").removesuffix("_settings.csv")
            matching = [name for name in names if name.startswith(stem)]
            return [os.path.abspath(os.path.join(log_dir, name)) for name in sorted(matching)]
        except Exception:
            return []

    def _test_finished(self) -> None:
        had_error = bool(getattr(self, "_automation_error", None))
        saved_files = self._latest_saved_files() if self._run_started and not had_error else []
        completed = self._run_started and not had_error

        super()._test_finished()
        self._run_started = False

        if completed:
            open_results_manager(self, saved_files)
