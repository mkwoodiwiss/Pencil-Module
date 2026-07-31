"""Tests for safe USB unmount and power-off behavior."""

import unittest
from pathlib import Path
from unittest import mock

from pencil.usb_export import USBDrive, safely_eject_drive


class TestUSBEject(unittest.TestCase):
    def setUp(self):
        self.drive = USBDrive(
            mount_point=Path("/media/waterarc/RESULTS"),
            label="RESULTS",
            device="/dev/sda1",
            parent_device="/dev/sda",
        )

    @mock.patch("pencil.usb_export._run_command")
    def test_unmounts_partition_then_powers_off_parent_disk(self, run_command):
        run_command.return_value = True

        self.assertTrue(safely_eject_drive(self.drive))

        self.assertEqual(
            run_command.call_args_list,
            [
                mock.call(["udisksctl", "unmount", "-b", "/dev/sda1"]),
                mock.call(["udisksctl", "power-off", "-b", "/dev/sda"]),
            ],
        )

    @mock.patch("pencil.usb_export._run_command")
    def test_falls_back_to_mount_point_unmount(self, run_command):
        run_command.side_effect = [False, True, True]

        self.assertTrue(safely_eject_drive(self.drive))

        self.assertEqual(
            run_command.call_args_list,
            [
                mock.call(["udisksctl", "unmount", "-b", "/dev/sda1"]),
                mock.call(["umount", "/media/waterarc/RESULTS"]),
                mock.call(["udisksctl", "power-off", "-b", "/dev/sda"]),
            ],
        )

    @mock.patch("pencil.usb_export._run_command")
    def test_does_not_power_off_when_unmount_fails(self, run_command):
        run_command.side_effect = [False, False]

        self.assertFalse(safely_eject_drive(self.drive))
        self.assertEqual(run_command.call_count, 2)

    @mock.patch("pencil.usb_export._run_command")
    def test_mount_only_drive_can_still_be_unmounted(self, run_command):
        drive = USBDrive(Path("/mnt/usb"), "USB")
        run_command.return_value = True

        self.assertTrue(safely_eject_drive(drive))
        run_command.assert_called_once_with(["umount", "/mnt/usb"])


if __name__ == "__main__":
    unittest.main()
