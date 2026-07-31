"""Regression tests for touchscreen-aware settings entries."""

import tkinter as tk
import unittest
from unittest import mock

from pencil.hmi_touch_entries import TouchEntryMixin
from pencil.hmi_v2_integrated import HMI


class TestTouchEntryMixin(unittest.TestCase):
    def setUp(self):
        self.interpreter = tk.Tcl()

    def _assert_entry_class(self, variable, expected_name):
        label_widget = mock.Mock()
        entry_widget = mock.Mock()
        with mock.patch("pencil.hmi_touch_entries.tk.Label", return_value=label_widget), mock.patch(
            "pencil.hmi_touch_entries.NumericEntry",
            return_value=entry_widget,
        ) as numeric_entry, mock.patch(
            "pencil.hmi_touch_entries.KeyboardEntry",
            return_value=entry_widget,
        ) as keyboard_entry:
            TouchEntryMixin._entry(mock.Mock(), 2, "Value", variable)

        selected = keyboard_entry if expected_name == "keyboard" else numeric_entry
        other = numeric_entry if expected_name == "keyboard" else keyboard_entry
        selected.assert_called_once_with(
            mock.ANY,
            textvariable=variable,
            width=16,
        )
        other.assert_not_called()
        entry_widget.grid.assert_called_once_with(
            row=2,
            column=1,
            sticky="w",
            padx=6,
            pady=4,
        )

    def test_double_variable_uses_numeric_keypad_entry(self):
        self._assert_entry_class(tk.DoubleVar(master=self.interpreter, value=1.5), "numeric")

    def test_integer_variable_uses_numeric_keypad_entry(self):
        self._assert_entry_class(tk.IntVar(master=self.interpreter, value=2), "numeric")

    def test_string_variable_uses_on_screen_keyboard_entry(self):
        self._assert_entry_class(tk.StringVar(master=self.interpreter, value="abc"), "keyboard")

    def test_production_hmi_composes_touch_entry_override(self):
        self.assertIn(TouchEntryMixin, HMI.__mro__)


if __name__ == "__main__":
    unittest.main()
