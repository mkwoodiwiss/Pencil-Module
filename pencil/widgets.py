"""Reusable Tkinter-based widgets for the HMI."""

import tkinter as tk


def _center_on_screen(window: tk.Toplevel) -> None:
    """Center a popup on screen and keep it inside the visible work area."""
    window.update_idletasks()
    width = window.winfo_reqwidth()
    height = window.winfo_reqheight()
    screen_width = window.winfo_screenwidth()
    screen_height = window.winfo_screenheight()

    width = min(width, max(200, screen_width - 20))
    height = min(height, max(200, screen_height - 30))
    x = max(0, (screen_width - width) // 2)
    y = max(0, (screen_height - height) // 2)
    window.geometry(f"{width}x{height}+{x}+{y}")


class NumericKeypad(tk.Toplevel):
    """Large on-screen keypad for numeric entry."""

    def __init__(self, master: tk.Widget, variable: tk.Variable, allow_negative: bool = False) -> None:
        super().__init__(master)
        self.var = variable
        self.title("Input")
        self.resizable(False, False)
        self.allow_negative = allow_negative
        self.value = tk.StringVar(value=str(variable.get()))
        self._replace_on_next_input = True
        col_span = 4 if allow_negative else 3

        tk.Entry(
            self,
            textvariable=self.value,
            width=12,
            justify="right",
            font=("Arial", 19),
        ).grid(row=0, column=0, columnspan=col_span, padx=8, pady=(7, 5), sticky="ew")

        buttons = [
            ("7", 1, 0), ("8", 1, 1), ("9", 1, 2),
            ("4", 2, 0), ("5", 2, 1), ("6", 2, 2),
            ("1", 3, 0), ("2", 3, 1), ("3", 3, 2),
            ("0", 4, 0), (".", 4, 1), ("<-", 4, 2),
        ]
        if allow_negative:
            buttons.append(("-", 4, 3))

        for text, row, column in buttons:
            tk.Button(
                self,
                text=text,
                width=5,
                height=1,
                font=("Arial", 17),
                command=lambda ch=text: self._press(ch),
            ).grid(row=row, column=column, padx=4, pady=3, ipadx=5, ipady=7)

        action_frame = tk.Frame(self)
        action_frame.grid(row=5, column=0, columnspan=col_span, pady=(3, 7))
        for text, command in (
            ("Clear", self._clear),
            ("Cancel", self.destroy),
            ("OK", self._apply),
        ):
            tk.Button(
                action_frame,
                text=text,
                width=7,
                height=1,
                font=("Arial", 14),
                command=command,
            ).pack(side="left", padx=4, ipady=6)

        self.bind("<Return>", lambda _e: self._apply())
        self.bind("<KP_Enter>", lambda _e: self._apply())
        self.attributes("-topmost", True)
        self.transient(master.winfo_toplevel())
        _center_on_screen(self)
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
                value = self.value.get()
                self.value.set(value[1:] if value.startswith("-") else "-" + value)
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
    """Large keyboard popup for text entry."""

    def __init__(self, master: tk.Widget, variable: tk.Variable) -> None:
        super().__init__(master)
        self.var = variable
        self.title("Input")
        self.resizable(False, False)
        self.value = tk.StringVar(value=str(variable.get()))
        self._replace_on_next_input = True

        tk.Entry(self, textvariable=self.value, width=28, font=("Arial", 17)).pack(padx=8, pady=(7, 5))

        keys_frame = tk.Frame(self)
        keys_frame.pack(padx=6, pady=(0, 5))

        rows = [
            list("1234567890"),
            list("qwertyuiop"),
            list("asdfghjkl"),
            list("zxcvbnm"),
        ]
        for keys in rows:
            row_frame = tk.Frame(keys_frame)
            row_frame.pack(anchor="center")
            for char in keys:
                tk.Button(
                    row_frame,
                    text=char,
                    width=3,
                    height=1,
                    font=("Arial", 13),
                    command=lambda ch=char: self._press(ch),
                ).pack(side="left", padx=2, pady=2, ipady=5)

        bottom = tk.Frame(keys_frame)
        bottom.pack(anchor="center", pady=(2, 0))
        controls = (
            ("_", 4, lambda: self._press("_")),
            ("Backspace", 10, lambda: self._press("<-")),
            ("Clear", 7, self._clear),
            ("Cancel", 7, self.destroy),
            ("OK", 7, self._apply),
        )
        for text, width, command in controls:
            tk.Button(
                bottom,
                text=text,
                width=width,
                height=1,
                font=("Arial", 12),
                command=command,
            ).pack(side="left", padx=2, pady=2, ipady=5)

        self.bind("<Return>", lambda _e: self._apply())
        self.bind("<KP_Enter>", lambda _e: self._apply())
        self.attributes("-topmost", True)
        self.transient(master.winfo_toplevel())
        _center_on_screen(self)
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
        keyboard = OnScreenKeyboard(self, self._var)
        self.wait_window(keyboard)
