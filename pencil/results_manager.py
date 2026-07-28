"""Touchscreen results manager for exporting completed MEU tests to USB."""

from __future__ import annotations

import threading
import tkinter as tk
from pathlib import Path
from typing import Iterable

from .usb_export import USBDrive, USBExportError, export_test_results, find_usb_drives


class ResultsManager(tk.Toplevel):
    """Modal touchscreen window for verified USB export."""

    def __init__(
        self,
        master: tk.Widget,
        result_files: Iterable[str | Path],
        title: str = "MEU Results",
    ) -> None:
        super().__init__(master)
        self.result_files = tuple(Path(path) for path in result_files)
        self.drives: list[USBDrive] = []
        self.selected_drive = tk.IntVar(value=0)
        self.status_var = tk.StringVar(value="Insert a USB drive, then press Refresh.")
        self.busy = False

        self.title(title)
        self.transient(master)
        self.resizable(False, False)
        self.protocol("WM_DELETE_WINDOW", self._close)
        self.attributes("-topmost", True)

        outer = tk.Frame(self, padx=18, pady=10)
        outer.pack(fill="both", expand=True)

        tk.Label(
            outer,
            text="TEST COMPLETE",
            font=("Arial", 19, "bold"),
        ).pack(pady=(0, 3))
        tk.Label(
            outer,
            text="Results are saved locally on the MEU.",
            font=("Arial", 13),
        ).pack(pady=(0, 5))

        self.files_label = tk.Label(
            outer,
            text=self._file_summary(),
            font=("Arial", 11),
            justify="left",
            wraplength=700,
        )
        self.files_label.pack(fill="x", pady=(0, 5))

        drive_box = tk.LabelFrame(
            outer,
            text="USB Drive",
            font=("Arial", 13, "bold"),
            padx=9,
            pady=5,
        )
        drive_box.pack(fill="x", pady=4)
        self.drive_frame = tk.Frame(drive_box)
        self.drive_frame.pack(fill="x")

        self.status_label = tk.Label(
            outer,
            textvariable=self.status_var,
            font=("Arial", 12),
            justify="center",
            wraplength=700,
        )
        self.status_label.pack(fill="x", pady=6)

        buttons = tk.Frame(outer)
        buttons.pack(pady=(2, 0))
        self.refresh_button = tk.Button(
            buttons,
            text="Refresh USB",
            font=("Arial", 14),
            width=13,
            height=1,
            pady=5,
            command=self.refresh_drives,
        )
        self.refresh_button.pack(side="left", padx=5)
        self.export_button = tk.Button(
            buttons,
            text="Export to USB",
            font=("Arial", 14, "bold"),
            width=14,
            height=1,
            pady=5,
            state="disabled",
            command=self.export_selected,
        )
        self.export_button.pack(side="left", padx=5)
        self.done_button = tk.Button(
            buttons,
            text="Keep Locally",
            font=("Arial", 14),
            width=13,
            height=1,
            pady=5,
            command=self._close,
        )
        self.done_button.pack(side="left", padx=5)

        self.update_idletasks()
        self._center_on_screen()
        try:
            self.wait_visibility()
            self.lift()
            self.focus_force()
            self.grab_set()
        except Exception:
            pass
        # Some Pi window managers reposition a Toplevel while decorating it.
        # Reapply the screen-centered geometry after the window is mapped.
        self.after_idle(self._center_on_screen)
        self.after(150, self.refresh_drives)

    def _file_summary(self) -> str:
        if not self.result_files:
            return "No completed result files were found."
        names = [path.name for path in self.result_files]
        return "Files ready: " + "  |  ".join(names)

    def _center_on_screen(self) -> None:
        """Center against the physical screen rather than the parent window."""
        try:
            self.update_idletasks()
            screen_width = self.winfo_screenwidth()
            screen_height = self.winfo_screenheight()
            width = min(screen_width - 24, max(700, self.winfo_reqwidth()))
            height = min(screen_height - 70, max(330, self.winfo_reqheight()))
            x = max(0, (screen_width - width) // 2)
            y = max(0, (screen_height - height) // 2)
            self.geometry(f"{width}x{height}+{x}+{y}")
        except Exception:
            pass

    def _set_busy(self, busy: bool) -> None:
        self.busy = busy
        state = "disabled" if busy else "normal"
        self.refresh_button.config(state=state)
        self.done_button.config(state=state)
        self.export_button.config(
            state="normal" if not busy and self.drives and self.result_files else "disabled"
        )

    def refresh_drives(self) -> None:
        if self.busy:
            return
        self.drives = find_usb_drives()
        for child in self.drive_frame.winfo_children():
            child.destroy()

        if not self.drives:
            tk.Label(
                self.drive_frame,
                text="No mounted USB drive detected",
                font=("Arial", 13),
            ).pack(pady=4)
            self.status_var.set("Insert a USB drive, wait a few seconds, then press Refresh USB.")
            self.export_button.config(state="disabled")
            return

        self.selected_drive.set(0)
        for index, drive in enumerate(self.drives):
            free_mb = drive.free_bytes / (1024 * 1024)
            text = f"{drive.label}   {drive.mount_point}   {free_mb:,.0f} MB free"
            tk.Radiobutton(
                self.drive_frame,
                text=text,
                variable=self.selected_drive,
                value=index,
                font=("Arial", 12),
                anchor="w",
                padx=6,
                pady=3,
            ).pack(fill="x")
        self.status_var.set("USB drive detected. Press Export to USB to copy and verify the files.")
        self.export_button.config(state="normal" if self.result_files else "disabled")

    def export_selected(self) -> None:
        if self.busy or not self.drives or not self.result_files:
            return
        index = self.selected_drive.get()
        if index < 0 or index >= len(self.drives):
            self.status_var.set("Select a USB drive first.")
            return
        drive = self.drives[index]
        self._set_busy(True)
        self.status_var.set("Copying and verifying results. Do not remove the USB drive...")

        def worker() -> None:
            try:
                result = export_test_results(self.result_files, drive, unmount=True)
            except USBExportError as exc:
                message = str(exc)
                self.after(0, lambda message=message: self._export_failed(message))
            except Exception as exc:
                message = f"Unexpected export error: {exc}"
                self.after(0, lambda message=message: self._export_failed(message))
            else:
                unmounted = result.unmounted
                self.after(0, lambda unmounted=unmounted: self._export_complete(unmounted))

        threading.Thread(target=worker, daemon=True).start()

    def _export_failed(self, message: str) -> None:
        self._set_busy(False)
        self.status_var.set(f"EXPORT FAILED\n{message}\nThe local files are unchanged.")

    def _export_complete(self, unmounted: bool) -> None:
        self._set_busy(False)
        self.refresh_button.config(state="disabled")
        self.export_button.config(state="disabled")
        self.done_button.config(text="Done", state="normal")
        if unmounted:
            self.status_var.set(
                "EXPORT COMPLETE\nFiles copied and verified. The USB drive was safely unmounted and can be removed."
            )
        else:
            self.status_var.set(
                "EXPORT COMPLETE\nFiles copied and verified. Wait for drive activity to stop before removing the USB drive."
            )

    def _close(self) -> None:
        if self.busy:
            self.status_var.set("Export is still running. Do not remove the USB drive.")
            return
        try:
            self.grab_release()
        except Exception:
            pass
        self.destroy()


def open_results_manager(master: tk.Widget, result_files: Iterable[str | Path]) -> ResultsManager:
    """Open the modal USB results manager."""
    return ResultsManager(master, result_files)
