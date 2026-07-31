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
    parent_device: str = ""

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
            ["lsblk", "-J", "-o", "NAME,PATH,PKNAME,LABEL,RM,TYPE,MOUNTPOINTS"],
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

    def visit(
        node: dict,
        removable_parent: bool = False,
        inherited_parent_device: str = "",
    ) -> None:
        removable = bool(node.get("rm")) or removable_parent
        device = node.get("path") or ""
        node_type = node.get("type") or ""
        parent_name = node.get("pkname") or ""
        parent_device = f"/dev/{parent_name}" if parent_name else inherited_parent_device
        if node_type == "disk" and device:
            parent_device = device

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
                            device=device,
                            parent_device=parent_device or device,
                        )
                    )
        for child in node.get("children") or []:
            visit(child, removable, parent_device)

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


def _run_command(command: list[str], timeout: float = 15.0) -> bool:
    """Run one removable-media command and return whether it succeeded."""
    try:
        result = subprocess.run(
            command,
            check=False,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except Exception:
        return False
    return result.returncode == 0


def safely_eject_drive(drive: USBDrive) -> bool:
    """Unmount the filesystem and power off its parent USB block device."""
    unmounted = False
    if drive.device:
        unmounted = _run_command(["udisksctl", "unmount", "-b", drive.device])
    if not unmounted:
        unmounted = _run_command(["umount", str(drive.mount_point)])
    if not unmounted:
        return False

    power_device = drive.parent_device or drive.device
    if not power_device:
        return True
    return _run_command(["udisksctl", "power-off", "-b", power_device])


def export_test_results(
    files: Iterable[os.PathLike[str] | str],
    drive: USBDrive,
    folder_name: str | None = None,
    unmount: bool = True,
) -> ExportResult:
    """Copy result files to a USB drive, verify checksums, then optionally eject."""
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

    ejected = safely_eject_drive(drive) if unmount else False
    return ExportResult(destination, tuple(copied), True, ejected)
