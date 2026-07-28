"""USB-drive discovery and verified MEU results export."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import os
from pathlib import Path
import shutil
import subprocess
from typing import Iterable


class USBExportError(RuntimeError):
    """Raised when a USB export cannot be completed safely."""


@dataclass(frozen=True)
class USBDrive:
    mount_point: Path
    label: str
    device: str = ""

    @property
    def free_bytes(self) -> int:
        return shutil.disk_usage(self.mount_point).free


@dataclass(frozen=True)
class ExportResult:
    destination: Path
    copied_files: tuple[Path, ...]
    verified: bool
    unmounted: bool


def _mounted_removable_drives() -> list[USBDrive]:
    """Return mounted removable filesystems reported by lsblk."""
    try:
        result = subprocess.run(
            ["lsblk", "-J", "-o", "NAME,PATH,LABEL,RM,TYPE,MOUNTPOINTS"],
            check=True,
            capture_output=True,
            text=True,
            timeout=5,
        )
        import json

        payload = json.loads(result.stdout)
    except Exception:
        return []

    drives: list[USBDrive] = []

    def visit(node: dict, removable_parent: bool = False) -> None:
        removable = bool(node.get("rm")) or removable_parent
        mount_points = node.get("mountpoints") or []
        if isinstance(mount_points, str):
            mount_points = [mount_points]
        if removable:
            for mount in mount_points:
                if mount and os.path.isdir(mount) and os.access(mount, os.W_OK):
                    drives.append(
                        USBDrive(
                            mount_point=Path(mount),
                            label=node.get("label") or Path(mount).name or "USB Drive",
                            device=node.get("path") or "",
                        )
                    )
        for child in node.get("children") or []:
            visit(child, removable)

    for device in payload.get("blockdevices") or []:
        visit(device)
    return drives


def _common_mount_fallbacks() -> list[USBDrive]:
    """Find writable mounted media when lsblk metadata is unavailable."""
    username = os.environ.get("USER") or os.environ.get("LOGNAME") or ""
    roots = [Path("/media") / username, Path("/run/media") / username, Path("/mnt")]
    drives: list[USBDrive] = []
    for root in roots:
        if not root.is_dir():
            continue
        try:
            children = list(root.iterdir())
        except OSError:
            continue
        for child in children:
            if child.is_dir() and os.path.ismount(child) and os.access(child, os.W_OK):
                drives.append(USBDrive(child, child.name or "USB Drive"))
    return drives


def find_usb_drives() -> list[USBDrive]:
    """Find mounted writable USB drives without requiring elevated privileges."""
    unique: dict[str, USBDrive] = {}
    for drive in _mounted_removable_drives() + _common_mount_fallbacks():
        unique[str(drive.mount_point.resolve())] = drive
    return sorted(unique.values(), key=lambda drive: drive.label.lower())


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _safe_folder_name(name: str) -> str:
    cleaned = "".join(ch if ch.isalnum() or ch in "._-" else "_" for ch in name.strip())
    return cleaned.strip("._") or "MEU_Test"


def test_name_from_files(files: Iterable[os.PathLike[str] | str]) -> str:
    paths = [Path(path) for path in files]
    if not paths:
        return "MEU_Test"
    stem = paths[0].name
    for suffix in ("_data.csv", "_settings.csv"):
        if stem.endswith(suffix):
            stem = stem[: -len(suffix)]
            break
    return _safe_folder_name(stem)


def export_test_results(
    files: Iterable[os.PathLike[str] | str],
    drive: USBDrive,
    folder_name: str | None = None,
    unmount: bool = True,
) -> ExportResult:
    """Copy result files to a USB drive, verify checksums, then optionally unmount."""
    sources = tuple(Path(path).resolve() for path in files)
    if not sources:
        raise USBExportError("No test-result files were provided.")
    missing = [str(path) for path in sources if not path.is_file()]
    if missing:
        raise USBExportError("Missing result file(s): " + ", ".join(missing))
    if not drive.mount_point.is_dir() or not os.access(drive.mount_point, os.W_OK):
        raise USBExportError("The selected USB drive is not mounted or writable.")

    required = sum(path.stat().st_size for path in sources) + 1024 * 1024
    if drive.free_bytes < required:
        raise USBExportError("The USB drive does not have enough free space.")

    destination = drive.mount_point / "MEU Results" / _safe_folder_name(
        folder_name or test_name_from_files(sources)
    )
    destination.mkdir(parents=True, exist_ok=True)

    copied: list[Path] = []
    for source in sources:
        target = destination / source.name
        temporary = destination / f".{source.name}.partial"
        try:
            with source.open("rb") as src, temporary.open("wb") as dst:
                shutil.copyfileobj(src, dst, length=1024 * 1024)
                dst.flush()
                os.fsync(dst.fileno())
            os.replace(temporary, target)
        finally:
            if temporary.exists():
                temporary.unlink(missing_ok=True)
        if source.stat().st_size != target.stat().st_size or _sha256(source) != _sha256(target):
            raise USBExportError(f"Verification failed for {source.name}.")
        copied.append(target)

    try:
        subprocess.run(["sync"], check=False, timeout=10)
    except Exception:
        pass

    unmounted = False
    if unmount and drive.device:
        try:
            result = subprocess.run(
                ["udisksctl", "unmount", "-b", drive.device],
                check=False,
                capture_output=True,
                text=True,
                timeout=15,
            )
            unmounted = result.returncode == 0
        except Exception:
            unmounted = False

    return ExportResult(destination, tuple(copied), True, unmounted)
