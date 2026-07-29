"""Classic MEU HMI styling and reliable post-run USB export."""

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
    """MEU HMI using classic file-folder tabs and selected visual accents."""

    VESSEL_FILL = "#D5EAF2"
    MEMBRANE_FILL = "#DCE4E9"
    VESSEL_OUTLINE = "#9FB0BC"
    DANGER = "#B94747"
    DANGER_ACTIVE = "#963A3A"
    TAB_IDLE = "#CFCFCC"
    TAB_ACTIVE = "#F4F4F1"
    TAB_HOVER = "#E4E4E1"

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._run_started_at: float | None = None
        self._run_log_snapshot: set[Path] = set()
        self._run_was_cancelled = False
        self._usb_dialog_run_token: float | None = None
        self._usb_export_window: tk.Toplevel | None = None
        self._apply_selected_accents(self)
        self._refresh_navigation_rails()
        self.bind_all("<Map>", self._style_mapped_widget, add="+")

    def _style_mapped_widget(self, event) -> None:
        widget = event.widget
        try:
            widget.after_idle(lambda target=widget: self._apply_selected_accents(target))
        except tk.TclError:
            pass

    def _style_button(self, button: tk.Button) -> None:
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
        """Make each top control resemble a classic file-cabinet folder tab."""
        try:
            label = str(button.cget("text")).strip().lower()
            if label == "exit":
                button.configure(
                    bg=self.DANGER,
                    fg="white",
                    activebackground=self.DANGER_ACTIVE,
                    activeforeground="white",
                    relief="raised",
                    overrelief="raised",
                    borderwidth=2,
                    highlightthickness=0,
                    font=self.NAV_FONT,
                    anchor="s",
                )
                return

            button.configure(
                bg=self.TAB_ACTIVE if selected else self.TAB_IDLE,
                fg="black",
                activebackground=self.TAB_ACTIVE if selected else self.TAB_HOVER,
                activeforeground="black",
                relief="raised",
                overrelief="raised",
                borderwidth=3 if selected else 2,
                highlightthickness=0,
                font=self.NAV_FONT_ACTIVE if selected else self.NAV_FONT,
                anchor="s",
            )
            if selected:
                button.lift()
        except tk.TclError:
            pass

    def _refresh_navigation_rails(self) -> None:
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
        """Apply vessel colors and reduce the membrane module thickness."""
        for item in canvas.find_all():
            try:
                if canvas.type(item) != "rectangle":
                    continue
                fill = str(canvas.itemcget(item, "fill")).lower()
                coords = canvas.coords(item)

                if fill in {"lightblue", self.VESSEL_FILL.lower()}:
                    canvas.itemconfigure(
                        item,
                        fill=self.VESSEL_FILL,
                        outline=self.VESSEL_OUTLINE,
                        width=1,
                    )
                    continue

                if fill not in {"lightgray", self.MEMBRANE_FILL.lower()}:
                    continue

                canvas.itemconfigure(
                    item,
                    fill=self.MEMBRANE_FILL,
                    outline=self.VESSEL_OUTLINE,
                    width=1,
                )

                # Main membrane body: retain its centerline and length while
                # reducing its height from 20 px to 12 px.
                if len(coords) == 4 and coords[0] == 265 and coords[2] == 445:
                    canvas.coords(item, 265, 49, 445, 61)
                # Narrow support legs so the complete module reads lighter too.
                elif len(coords) == 4 and coords[0] == 275 and coords[2] == 290:
                    canvas.coords(item, 278, 61, 287, 78)
                elif len(coords) == 4 and coords[0] == 420 and coords[2] == 435:
                    canvas.coords(item, 423, 61, 432, 78)
            except tk.TclError:
                continue

    def _apply_selected_accents(self, parent: tk.Widget) -> None:
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

    @staticmethod
    def _csv_snapshot(log_dir: Path) -> set[Path]:
        try:
            return {path.resolve() for path in log_dir.glob("*.csv") if path.is_file()}
        except OSError:
            return set()

    def _current_log_dir(self) -> Path:
        if hasattr(self, "test_system"):
            return Path(getattr(self.test_system, "log_dir", "logs")).expanduser()
        return Path("logs")

    def _mark_run_start(self) -> None:
        # A previous stopped run can leave _automation_error populated until its
        # finish callback executes. Reset it before every new run so a later
        # successful completion is not incorrectly treated as failed.
        self._automation_error = None
        self._run_started_at = time.time()
        self._run_was_cancelled = False
        self._usb_dialog_run_token = None
        self._run_log_snapshot = self._csv_snapshot(Path("logs"))

    def start_test(self) -> None:
        self._mark_run_start()
        super().start_test()

    def start_benchmark(self) -> None:
        self._mark_run_start()
        super().start_benchmark()

    def start_clean(self) -> None:
        self._mark_run_start()
        super().start_clean()

    def cancel_test(self) -> None:
        self._run_was_cancelled = True
        super().cancel_test()

    def _completed_log_files(self) -> tuple[Path, ...]:
        """Find files from this run without relying on one timestamp test alone."""
        log_dir = self._current_log_dir()
        current = self._csv_snapshot(log_dir)
        new_files = current - self._run_log_snapshot
        if new_files:
            return tuple(sorted(new_files, key=lambda path: path.stat().st_mtime))

        started_at = self._run_started_at
        if started_at is not None:
            try:
                modified = [
                    path.resolve()
                    for path in log_dir.glob("*.csv")
                    if path.is_file() and path.stat().st_mtime >= started_at - 5.0
                ]
                if modified:
                    return tuple(sorted(modified, key=lambda path: path.stat().st_mtime))
            except OSError:
                pass

        # Final fallback for filesystems with coarse or unexpected timestamps.
        try:
            latest = sorted(
                (path.resolve() for path in log_dir.glob("*.csv") if path.is_file()),
                key=lambda path: path.stat().st_mtime,
                reverse=True,
            )[:2]
            return tuple(reversed(latest))
        except OSError:
            return ()

    @staticmethod
    def _find_usb_drives() -> tuple[Path, ...]:
        username = getpass.getuser()
        roots = (
            Path("/media") / username,
            Path("/run/media") / username,
            Path("/mnt"),
            Path("/media"),
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
                    if key in seen or not child.is_dir() or not os.access(child, os.W_OK):
                        continue
                    # Raspberry Pi OS normally mounts USB media as a mount point.
                    # Also accept writable child directories under standard media
                    # roots because some desktop automounters use bind mounts.
                    if os.path.ismount(child) or root in {Path("/mnt"), Path("/media")}:
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
        if not files:
            messagebox.showerror(
                "No Test Files",
                "The test completed, but no CSV files could be located.",
                parent=self._usb_export_window,
            )
            return
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
        """Always show a visible completion window after a successful run."""
        if self._usb_export_window and self._usb_export_window.winfo_exists():
            self._usb_export_window.deiconify()
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
        file_message = (
            f"{len(files)} test files are ready to save."
            if files
            else "The run finished, but no CSV files were found."
        )
        tk.Label(content, text=file_message, font=("Arial", 11)).pack(pady=(5, 12))

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
                        selected, files, status_var
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
        window.deiconify()
        window.lift()
        window.attributes("-topmost", True)
        window.focus_force()
        window.after(500, lambda: window.attributes("-topmost", False) if window.winfo_exists() else None)

    def _test_finished(self) -> None:
        had_error = bool(getattr(self, "_automation_error", None))
        was_cancelled = self._run_was_cancelled
        run_token = self._run_started_at
        files = self._completed_log_files() if not had_error and not was_cancelled else ()
        super()._test_finished()

        if (
            not had_error
            and not was_cancelled
            and run_token is not None
            and self._usb_dialog_run_token != run_token
        ):
            self._usb_dialog_run_token = run_token
            # Use after_idle plus a short delay so any final automation dialog and
            # control reset are fully processed before this window is raised.
            self.after_idle(
                lambda completed=files: self.after(
                    250,
                    lambda: self._open_usb_export_window(completed),
                )
            )

    def _build_prime_popup(self, title: str, action_text: str, action_command) -> None:
        super()._build_prime_popup(title, action_text, action_command)
        if self.prime_frame:
            self._apply_selected_accents(self.prime_frame)
            self._center_prime_window()


__all__ = ["HMI"]
