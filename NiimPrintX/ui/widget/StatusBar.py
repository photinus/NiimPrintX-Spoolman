import tkinter as tk
from tkinter import font as tk_font

from ..component import theme
from ..component.RoundedButton import _rounded_rect

CONNECTED_BG = "#E3EEDD"
CONNECTED_TEXT = theme.SUCCESS
CONNECTED_DOT = theme.SUCCESS

DISCONNECTED_BG = theme.DANGER_BG
DISCONNECTED_TEXT = theme.DANGER_TEXT
DISCONNECTED_DOT = theme.DANGER_DOT


class StatusBar(tk.Canvas):
    """Connection-status pill (dot + label), meant to live in the persistent top bar."""

    HEIGHT = 30

    def __init__(self, parent, config):
        self.parent = parent
        self.config = config
        bg = self._parent_bg(parent)
        super().__init__(parent, height=self.HEIGHT, highlightthickness=0, bd=0, bg=bg)
        self._font = tk_font.Font(family=theme.FONT_BADGE[0], size=theme.FONT_BADGE[1], weight="bold")
        self._connected = False
        self.pack(side=tk.RIGHT, padx=(10, 0))
        self._draw()

    @staticmethod
    def _parent_bg(parent):
        try:
            return parent.cget("bg")
        except tk.TclError:
            return theme.BG_CONTENT

    def _draw(self):
        self.delete("all")
        text = "Connected" if self._connected else "Not connected"
        bg = CONNECTED_BG if self._connected else DISCONNECTED_BG
        fg = CONNECTED_TEXT if self._connected else DISCONNECTED_TEXT
        dot = CONNECTED_DOT if self._connected else DISCONNECTED_DOT

        text_w = self._font.measure(text)
        width = 12 + 8 + 6 + text_w + 14
        self.configure(width=width)

        _rounded_rect(self, 0, 0, width, self.HEIGHT, self.HEIGHT / 2, fill=bg, outline=bg)
        dot_r = 3.5
        self.create_oval(12 - dot_r, self.HEIGHT / 2 - dot_r, 12 + dot_r, self.HEIGHT / 2 + dot_r,
                         fill=dot, outline=dot)
        self.create_text(12 + dot_r + 6, self.HEIGHT / 2, text=text, fill=fg, font=self._font, anchor="w")

    def update_status(self, connection=True):
        """Update the pill to reflect the connection state."""
        self._connected = bool(connection)
        self._draw()
