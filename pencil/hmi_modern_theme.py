"""Classic MEU HMI styling with selected visual accents.

The original HMI appearance and geometry are preserved. Process-vessel colors,
outlines, Exit and Cancel colors, classic top-navigation tabs, and the post-run
USB export dialog are customized.
"""

from __future__ import annotations

import getpass
import os
from pathlib import Path
import shutil
import subprocess
import time
import tkinter as tk
from tkinter import messagebox

from .hmi_lower_panel_fix import HMI as _LayoutHMI


class HMI(_LayoutHMI):
    """MEU HMI using the original style with selected retained accents."""

    VESSEL_FILL = "#D5EAF2"
    MEMBRANE_FILL = "#D9E1E7"
    VESSEL_OUTLINE = "#9FB0BC"
    DANGER = "#B94747"
    DANGER_ACTIVE = "#963A3A"
    TAB_IDLE = "#D9D9D9"
    TAB_ACTIVE = "#F7F7F7"
    TAB_HOVER = "#E8E8E8"

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._run_started_at: float | None = None
        self._usb_dialog_run_token: float | None = None
        self._usb_export_window: tk.Toplevel | None = None
        self._apply_selected_accents(self)
        self._refresh_navigation_rails()
        self.bind_all("<Map>", self._style_mapped_widget, add="+")

    def _style_mapped_widget(self, event) -> None:
        """Style newly opened dialogs without changing their layout or theme."""
        widget = event.widget
        try:
            widget.after_idle(lambda target=widget: self._apply_selected_accents(target))
        except tk.TclError:
            pass

    def _style_button(self, button: tk.Button) -> None:
        """Retain red treatment only for Exit and Cancel actions."""
        try:
            text = str(button.cget("text")).strip().lower()
            if text not in {"exit", "cancel"}:
                return
            button.configure(
                bg=self.DANGER,
                fg="white",
                activebackground=self.DANGER_ACTIVE,
                activeforeground="white",
            )
        except tk.TclError:
            pass

    def _style_navigation_button(self, button: tk.Button, selected: bool) -> None:
        """Present the existing top controls as classic raised navigation tabs."""
        try:
            label = str(button.cget("text")).strip().lower()
            if label == "exit":
                button.configure(
                    bg=self.DANGER,
                    fg="white",
                    activebackground=self.DANGER_ACTIVE,
                    activeforeground="white",
                    relief="raised",
                    borderwidth=2,
                    highlightthickness=0,
                    font=self.NAV_FONT,
                )
                return

            button.configure(
                bg=self.TAB_ACTIVE if selected else self.TAB_IDLE,
                fg="black",
                activebackground=self.TAB_ACTIVE if selected else self.TAB_HOVER,
                activeforeground="black",
                relief="sunken" if selected else "raised",
                borderwidth=2,
                highlightthickness=0,
                font=self.NAV_FONT_ACTIVE if selected else self.NAV_FONT,
            )
        except tk.TclError:
            pass

    def _refresh_navigation_rails(self) -> None:
        """Retain navigation geometry while presenting controls as tabs."""
        active_index = {
            self.test_tab: 0,
            self.benchmark_tab: 1,
            self.clean_tab: 2,
        }.get(self._active_tab)

        for pfd in getattr(self, "pfds", {}).values():
            buttons = pfd.get("navigation_buttons", [])
            for index, button in enumerate(buttons):
                self._style_navigation_button(
                    button,
                    selected=index == active_index and index < 3,
                )

    def _style_vessels(self, canvas: tk.Canvas) -> None:
        """Retain modern vessel fills and outlines on the classic PFD."""
        for item in canvas.find_all():
            try:
                if canvas.type(item) != "rectangle":
                    continue
                fill = str(canvas.itemcget(item, "fill")).lower()
                if fill in {"lightblue", self.VESSEL_FILL.lower()}:
                    canvas.itemconfigure(
                        item,
                        fill=self.VESSEL_FILL,
                        outline=self.VESSEL_OUTLINE,
                        width=1,
                    )
                elif fill in {"lightgray", self.MEMBRANE_FILL.lower()}:
                    canvas.itemconfigure(
                        item,
                        fill=self.MEMBRANE_FILL,
                        outline=self.VESSEL_OUTLINE,
                        width=1,
                    )
            except tk.TclError:
                continue

    def _apply_selected_accents(self, parent: tk.Widget) -> None:
        """Apply only the requested accents and leave all other styling intact."""
        try:
            if isinstance(parent, tk.Button):
                self._style_button(parent)
            elif isinstance(parent, tk.Canvas):
                self._style_vessels(parent)
        except (tk.TclError, AttributeError):
            pass

        try:
            children = parent.winfo_children()
        except tk.TclError:
            return
        for child in children:
            self._apply_selected_accents(child)

    def _mark_run_start(self) -> None:
        self._run_started_at = time.time()
        self._usb_dialog_run_token = None

    def start_test(self) -> None:
        self._mark_run_start()
        super().start_test()

    def start_benchmark(self) -> None:
        self._mark_run_start()
        super().start_benchmark()

    def start_clean(self) -> None:
        self._mark_run_start()
        super().start_clean()

    def _completed_log_files(self) -> tuple[Path, ...]:
        """Return CSV files created by the run that just finished."""
        started_at = self._run_started_at
        if started_at is None or not hasattr(self, "test_system"):
            return ()

        log_dir = Path(getattr(self.test_system, "log_dir", "logs")).expanduser()
        try:
            candidates = [
                path
                for path in log_dir.glob("*.csv")
                if path.is_file() and path.stat().st_mtime >= started_at - 2.0
            ]
        except OSError:
            return ()
        return tuple(sorted(candidates, key=lambda path: path.stat().st_mtime))

    @staticmethod
    def _find_usb_drives() -> tuple[Path, ...]:
        """Find writable removable-media mount points used by Raspberry Pi OS."""
        username = getpass.getuser()
        roots = (
            Path("/media") / username,
            Path("/run/media") / username,
            Path("/mnt"),
        )
        drives: list[Path] = []
        seen: set[str] = set()

        for root in roots:
            try:
                children = tuple(root.iterdir())
            except OSError:
                continue
            for child in children:
                try:
                    resolved = child.resolve()
                    key = str(resolved)
                    if (
                        key not in seen
                        and child.is_dir()
                        and os.path.ismount(child)
                        and os.access(child, os.W_OK)
                    ):
                        seen.add(key)
                        drives.append(child)
                except OSError:
                    continue
        return tuple(sorted(drives, key=lambda path: path.name.lower()))

    def _center_window(self, window: tk.Toplevel) -> None:
        window.update_idletasks()
        width = window.winfo_reqwidth()
        height = window.winfo_reqheight()
        x = max(0, (window.winfo_screenwidth() - width) // 2)
        y = max(0, (window.winfo_screenheight() - height) // 2)
        window.geometry(f"{width}x{height}+{x}+{y}")

    def _copy_run_files_to_usb(
        self,
        drive: Path,
        files: tuple[Path, ...],
        status_var: tk.StringVar,
    ) -> None:
        try:
            destination = drive / "MEU Test Data"
            destination.mkdir(parents=True, exist_ok=True)
            copied = []
            for source in files:
                target = destination / source.name
                shutil.copy2(source, target)
                copied.append(target)
            status_var.set(f"Saved {len(copied)} files to {destination}")
            try:
                subprocess.Popen(
                    ["xdg-open", str(destination)],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
            except (OSError, subprocess.SubprocessError):
                pass
            messagebox.showinfo(
                "USB Export Complete",
                f"Saved {len(copied)} files to:\n{destination}",
                parent=self._usb_export_window,
            )
        except OSError as exc:
            status_var.set("USB export failed.")
            messagebox.showerror(
                "USB Export Failed",
                str(exc),
                parent=self._usb_export_window,
            )

    def _open_usb_export_window(self, files: tuple[Path, ...]) -> None:
        """Open the post-run USB export window on every successful completion."""
        if self._usb_export_window and self._usb_export_window.winfo_exists():
            self._usb_export_window.lift()
            self._usb_export_window.focus_force()
            return

        window = tk.Toplevel(self)
        self._usb_export_window = window
        window.title("Test Complete")
        window.transient(self)
        window.resizable(False, False)

        def close_window() -> None:
            self._usb_export_window = None
            window.destroy()

        window.protocol("WM_DELETE_WINDOW", close_window)
        content = tk.Frame(window, padx=22, pady=18)
        content.pack(fill="both", expand=True)
        tk.Label(content, text="Test Complete", font=("Arial", 16, "bold")).pack()
        tk.Label(
            content,
            text=f"{len(files)} test files are ready to save.",
            font=("Arial", 11),
        ).pack(pady=(5, 12))

        status_var = tk.StringVar(value="")
        drive_frame = tk.Frame(content)
        drive_frame.pack(fill="x")

        def refresh_drives() -> None:
            for child in drive_frame.winfo_children():
                child.destroy()
            drives = self._find_usb_drives()
            if not drives:
                tk.Label(
                    drive_frame,
                    text="Insert a USB drive, then press Refresh.",
                    font=("Arial", 11),
                ).pack(pady=8)
                return
            for drive in drives:
                tk.Button(
                    drive_frame,
                    text=f"Save to {drive.name}",
                    command=lambda selected=drive: self._copy_run_files_to_usb(
                        selected,
                        files,
                        status_var,
                    ),
                    font=("Arial", 12, "bold"),
                    width=24,
                    height=2,
                ).pack(pady=4)

        refresh_drives()
        tk.Label(
            content,
            textvariable=status_var,
            wraplength=430,
            justify="center",
        ).pack(pady=(6, 4))
        controls = tk.Frame(content)
        controls.pack(pady=(6, 0))
        tk.Button(controls, text="Refresh", command=refresh_drives, width=10).pack(
            side="left", padx=5
        )
        tk.Button(controls, text="Close", command=close_window, width=10).pack(
            side="left", padx=5
        )

        self._apply_selected_accents(window)
        self._center_window(window)
        window.lift()
        window.focus_force()

    def _test_finished(self) -> None:
        had_error = bool(getattr(self, "_automation_error", None))
        files = self._completed_log_files() if not had_error else ()
        run_token = self._run_started_at
        super()._test_finished()

        if (
            not had_error
            and files
            and run_token is not None
            and self._usb_dialog_run_token != run_token
        ):
            self._usb_dialog_run_token = run_token
            self.after(100, lambda completed=files: self._open_usb_export_window(completed))

    def _build_prime_popup(self, title: str, action_text: str, action_command) -> None:
        super()._build_prime_popup(title, action_text, action_command)
        if self.prime_frame:
            self._apply_selected_accents(self.prime_frame)
            self._center_prime_window()


__all__ = ["HMI"]
