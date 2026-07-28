"""Reusable Tkinter-based widgets for the HMI."""

import tkinter as tk


class NumericKeypad(tk.Toplevel):
    """Simple on-screen keypad for numeric entry."""

    def __init__(self, master: tk.Widget, variable: tk.Variable, allow_negative: bool = False) -> None:
        super().__init__(master)
        self.var = variable
        self.title("Input")
        self.resizable(False, False)
        self.allow_negative = allow_negative
        self.value = tk.StringVar(value=str(variable.get()))
        self._replace_on_next_input = True
        col_span = 4 if allow_negative else 3
        tk.Entry(self, textvariable=self.value, width=10, justify="right").grid(row=0, column=0, columnspan=col_span, pady=5)
        buttons = [
            ("7", 1, 0), ("8", 1, 1), ("9", 1, 2),
            ("4", 2, 0), ("5", 2, 1), ("6", 2, 2),
            ("1", 3, 0), ("2", 3, 1), ("3", 3, 2),
            ("0", 4, 0), (".", 4, 1), ("<-", 4, 2),
        ]
        if allow_negative:
            buttons.append(("-", 4, 3))
        for text, r, c in buttons:
            action = lambda ch=text: self._press(ch)
            tk.Button(self, text=text, width=4, command=action).grid(row=r, column=c, padx=2, pady=2)
        tk.Button(self, text="Clear", width=6, command=self._clear).grid(row=5, column=0, pady=2)
        tk.Button(self, text="Cancel", width=6, command=self.destroy).grid(row=5, column=1, pady=2)
        tk.Button(self, text="OK", width=6, command=self._apply).grid(row=5, column=2, pady=2)
        self.bind("<Return>", lambda _e: self._apply())
        self.bind("<KP_Enter>", lambda _e: self._apply())
        self.attributes("-topmost", True)
        self.transient(master)
        self.focus_set()
        self.wait_visibility()

    def _press(self, char: str) -> None:
        if char == "<-":
            if self._replace_on_next_input:
                self.value.set("")
                self._replace_on_next_input = False
            else:
                self.value.set(self.value.get()[:-1])
        elif char == "-" and self.allow_negative:
            if self._replace_on_next_input:
                self.value.set("-")
                self._replace_on_next_input = False
            else:
                val = self.value.get()
                if val.startswith("-"):
                    self.value.set(val[1:])
                else:
                    self.value.set("-" + val)
        else:
            if self._replace_on_next_input:
                self.value.set(char)
                self._replace_on_next_input = False
            else:
                self.value.set(self.value.get() + char)

    def _clear(self) -> None:
        self.value.set("")
        self._replace_on_next_input = False

    def _apply(self) -> None:
        try:
            if isinstance(self.var, tk.DoubleVar):
                self.var.set(float(self.value.get() or 0))
            elif isinstance(self.var, tk.IntVar):
                self.var.set(int(float(self.value.get() or 0)))
            else:
                self.var.set(self.value.get())
        except Exception:
            pass
        self.destroy()


class NumericEntry(tk.Entry):
    """Entry widget that opens a numeric keypad when clicked."""

    def __init__(self, master: tk.Widget, textvariable: tk.Variable, allow_negative: bool = False, **kw) -> None:
        super().__init__(master, textvariable=textvariable, **kw)
        self._var = textvariable
        self._allow_negative = allow_negative
        self.bind("<Button-1>", self._open_pad)

    def _open_pad(self, _event=None) -> None:
        pad = NumericKeypad(self, self._var, allow_negative=self._allow_negative)
        self.wait_window(pad)


class OnScreenKeyboard(tk.Toplevel):
    """Simple keyboard popup for text entry."""

    def __init__(self, master: tk.Widget, variable: tk.Variable) -> None:
        super().__init__(master)
        self.var = variable
        self.title("Input")
        self.resizable(False, False)
        self.value = tk.StringVar(value=str(variable.get()))
        self._replace_on_next_input = True
        tk.Entry(self, textvariable=self.value, width=20).pack(pady=5)

        keys_frame = tk.Frame(self)
        keys_frame.pack()

        rows = [
            list("1234567890"),
            list("qwertyuiop"),
            list("asdfghjkl"),
            list("zxcvbnm"),
        ]
        for keys in rows:
            row_frame = tk.Frame(keys_frame)
            row_frame.pack(anchor="center")
            for ch in keys:
                tk.Button(row_frame, text=ch, width=3, command=lambda ch=ch: self._press(ch)).pack(side="left", padx=1, pady=1)

        bottom = tk.Frame(keys_frame)
        bottom.pack(anchor="center")
        tk.Button(bottom, text="_", width=3, command=lambda: self._press("_")).pack(side="left", padx=1, pady=1)
        tk.Button(bottom, text="Backspace", width=9, command=lambda: self._press("<-")).pack(side="left", padx=1, pady=1)
        tk.Button(bottom, text="Clear", width=5, command=self._clear).pack(side="left", padx=1, pady=1)
        tk.Button(bottom, text="Cancel", width=5, command=self.destroy).pack(side="left", padx=1, pady=1)
        tk.Button(bottom, text="OK", width=5, command=self._apply).pack(side="left", padx=1, pady=1)

        self.bind("<Return>", lambda _e: self._apply())
        self.bind("<KP_Enter>", lambda _e: self._apply())
        self.attributes("-topmost", True)
        self.transient(master)
        self.focus_set()
        self.wait_visibility()

    def _press(self, char: str) -> None:
        if char == "<-":
            if self._replace_on_next_input:
                self.value.set("")
                self._replace_on_next_input = False
            else:
                self.value.set(self.value.get()[:-1])
        else:
            if self._replace_on_next_input:
                self.value.set(char)
                self._replace_on_next_input = False
            else:
                self.value.set(self.value.get() + char)

    def _clear(self) -> None:
        self.value.set("")
        self._replace_on_next_input = False

    def _apply(self) -> None:
        self.var.set(self.value.get())
        self.destroy()


class KeyboardEntry(tk.Entry):
    """Entry widget that opens an :class:`OnScreenKeyboard` when clicked."""

    def __init__(self, master: tk.Widget, textvariable: tk.Variable, **kw) -> None:
        super().__init__(master, textvariable=textvariable, **kw)
        self._var = textvariable
        self.bind("<Button-1>", self._open_keyboard)

    def _open_keyboard(self, _event=None) -> None:
        kb = OnScreenKeyboard(self, self._var)
        self.wait_window(kb)
