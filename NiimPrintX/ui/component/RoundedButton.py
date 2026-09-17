"""A small pill/rounded-rect button drawn on a tk.Canvas.

Plain ttk/tk widgets can't do border-radius, so the "Warm Studio" refresh's
pill buttons (Connect, Print, Add text, nav badges, ...) are drawn by hand.
The public surface intentionally mirrors the bits of tk.Button that the rest
of the app already relies on (`.config(text=..., state=...)`, `widget["state"]`)
so it's a drop-in replacement.
"""

import tkinter as tk
from tkinter import font as tk_font

from . import theme

VARIANTS = {
    "primary": {
        "bg": theme.ACCENT,
        "hover": theme.ACCENT_DARK,
        "fg": theme.TEXT_ON_ACCENT,
        "border": None,
    },
    "secondary": {
        "bg": theme.BG_SIDEBAR,
        "hover": theme.BORDER,
        "fg": theme.TEXT_PRIMARY,
        "border": None,
    },
    "outline": {
        "bg": theme.BG_CONTENT,
        "hover": theme.ACCENT_LIGHT,
        "fg": theme.TEXT_PRIMARY,
        "border": theme.BORDER_STRONG,
    },
}

DISABLED_BG = "#E7E1D5"
DISABLED_FG = theme.TEXT_FAINT


def _rounded_rect(canvas, x1, y1, x2, y2, radius, **kwargs):
    radius = min(radius, (x2 - x1) / 2, (y2 - y1) / 2)
    points = [
        x1 + radius, y1,
        x2 - radius, y1,
        x2, y1,
        x2, y1 + radius,
        x2, y2 - radius,
        x2, y2,
        x2 - radius, y2,
        x1 + radius, y2,
        x1, y2,
        x1, y2 - radius,
        x1, y1 + radius,
        x1, y1,
    ]
    return canvas.create_polygon(points, smooth=True, **kwargs)


class RoundedButton(tk.Canvas):
    def __init__(self, parent, text="", command=None, variant="primary",
                 font=None, padx=16, pady=9, radius=9, min_width=0, bg=None, **kwargs):
        self._parent_bg = bg or self._infer_parent_bg(parent)
        super().__init__(parent, highlightthickness=0, bd=0, bg=self._parent_bg, **kwargs)
        self._text = text
        self._command = command
        self._variant = variant
        self._font = font or tk_font.Font(family=theme.FONT_PILL[0], size=theme.FONT_PILL[1], weight="bold")
        self._padx = padx
        self._pady = pady
        self._radius = radius
        self._min_width = min_width
        self._state = "normal"
        self._hover = False

        self.bind("<Enter>", self._on_enter)
        self.bind("<Leave>", self._on_leave)
        self.bind("<Button-1>", self._on_click)

        self._redraw()

    @staticmethod
    def _infer_parent_bg(parent):
        try:
            return parent.cget("bg")
        except tk.TclError:
            try:
                return parent.cget("background")
            except tk.TclError:
                return theme.BG_CONTENT

    def _colors(self):
        if self._state == "disabled":
            return DISABLED_BG, DISABLED_FG, None
        spec = VARIANTS[self._variant]
        bg = spec["hover"] if self._hover else spec["bg"]
        return bg, spec["fg"], spec["border"]

    def _redraw(self):
        self.delete("all")
        text_w = self._font.measure(self._text)
        text_h = self._font.metrics("linespace")
        width = max(self._min_width, text_w + self._padx * 2)
        height = text_h + self._pady * 2
        self.configure(width=width, height=height)

        bg, fg, border = self._colors()
        outline_kwargs = {"outline": border, "width": 1} if border else {"outline": bg, "width": 0}
        _rounded_rect(self, 1, 1, width - 1, height - 1, self._radius, fill=bg, **outline_kwargs)
        self.create_text(width / 2, height / 2, text=self._text, fill=fg, font=self._font)
        cursor = "hand2" if self._state == "normal" else "arrow"
        self.configure(cursor=cursor)

    def _on_enter(self, _event=None):
        if self._state == "normal":
            self._hover = True
            self._redraw()

    def _on_leave(self, _event=None):
        if self._hover:
            self._hover = False
            self._redraw()

    def _on_click(self, _event=None):
        if self._state == "normal" and self._command:
            self._command()

    # -- tk.Button-compatible surface -------------------------------------------------
    def config(self, **kwargs):
        dirty = False
        if "text" in kwargs:
            self._text = kwargs.pop("text")
            dirty = True
        if "command" in kwargs:
            self._command = kwargs.pop("command")
        if "state" in kwargs:
            self._state = kwargs.pop("state")
            dirty = True
        if "variant" in kwargs:
            self._variant = kwargs.pop("variant")
            dirty = True
        if kwargs:
            super().config(**kwargs)
        if dirty:
            self._redraw()

    configure = config

    def cget(self, key):
        if key == "text":
            return self._text
        if key == "state":
            return self._state
        if key == "command":
            return self._command
        return super().cget(key)

    def __getitem__(self, key):
        return self.cget(key)

    def __setitem__(self, key, value):
        self.config(**{key: value})
