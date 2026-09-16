import tkinter as tk
from tkinter import font as tk_font

from ..component import theme

NAV_ITEMS = [
    ("design", "Design"),
    ("spoolman", "Spoolman"),
]


class _NavRow(tk.Canvas):
    """A single sidebar nav row: icon glyph + label, pill-highlighted when active."""

    WIDTH = 200
    HEIGHT = 36

    def __init__(self, parent, key, label, on_click):
        super().__init__(parent, width=self.WIDTH, height=self.HEIGHT,
                          highlightthickness=0, bd=0, bg=theme.BG_SIDEBAR)
        self.key = key
        self.label = label
        self._on_click = on_click
        self._active = False
        self._font_active = tk_font.Font(family=theme.FONT_NAV[0], size=theme.FONT_NAV[1], weight="bold")
        self._font_inactive = tk_font.Font(family=theme.FONT_NAV_INACTIVE[0], size=theme.FONT_NAV_INACTIVE[1])
        self.bind("<Button-1>", lambda e: self._on_click(self.key))
        self._draw()

    def set_active(self, active):
        self._active = active
        self._draw()

    def _draw(self):
        self.delete("all")
        if self._active:
            from ..component.RoundedButton import _rounded_rect
            _rounded_rect(self, 0, 0, self.WIDTH, self.HEIGHT, 8, fill=theme.ACCENT_LIGHT, outline=theme.ACCENT_LIGHT)
            fg = theme.ACCENT_DARK
            glyph = theme.ACCENT
            font = self._font_active
        else:
            fg = theme.TEXT_MUTED
            glyph = theme.TEXT_MUTED
            font = self._font_inactive

        cx, cy = 18, self.HEIGHT / 2
        if self.key == "design":
            self.create_rectangle(cx - 8, cy - 8, cx + 8, cy + 8, outline=glyph, width=2)
            self.create_line(cx - 3, cy + 1, cx + 3, cy - 5, fill=glyph, width=2)
        else:
            self.create_oval(cx - 8, cy - 8, cx + 8, cy + 8, outline=glyph, width=2)
            self.create_oval(cx - 2, cy - 2, cx + 2, cy + 2, fill=glyph, outline=glyph)

        self.create_text(36, cy, text=self.label, fill=fg, font=font, anchor="w")


class Sidebar(tk.Frame):
    """Left nav rail: app logo/name + Design/Spoolman section switcher."""

    def __init__(self, parent, on_select):
        super().__init__(parent, bg=theme.BG_SIDEBAR, width=232)
        self.pack_propagate(False)
        self._on_select = on_select
        self._rows = {}
        self._active_key = None
        self._build()

    def _build(self):
        header = tk.Frame(self, bg=theme.BG_SIDEBAR)
        header.pack(side=tk.TOP, fill=tk.X, padx=16, pady=(20, 24))

        logo = tk.Canvas(header, width=30, height=30, highlightthickness=0, bd=0, bg=theme.BG_SIDEBAR)
        logo.pack(side=tk.LEFT)
        from ..component.RoundedButton import _rounded_rect
        _rounded_rect(logo, 0, 0, 30, 30, 8, fill=theme.ACCENT, outline=theme.ACCENT)
        logo.create_text(15, 15, text="N", fill=theme.TEXT_ON_ACCENT,
                         font=(theme.FONT_FAMILY, 14, "bold"))

        text_col = tk.Frame(header, bg=theme.BG_SIDEBAR)
        text_col.pack(side=tk.LEFT, padx=(10, 0))
        tk.Label(text_col, text="NiimPrintX", bg=theme.BG_SIDEBAR, fg=theme.TEXT_PRIMARY,
                 font=theme.FONT_APP_TITLE, anchor="w").pack(anchor="w")
        tk.Label(text_col, text="Label Studio", bg=theme.BG_SIDEBAR, fg=theme.TEXT_MUTED,
                 font=(theme.FONT_FAMILY, 9), anchor="w").pack(anchor="w")

        nav_col = tk.Frame(self, bg=theme.BG_SIDEBAR)
        nav_col.pack(side=tk.TOP, fill=tk.X, padx=16)
        for key, label in NAV_ITEMS:
            row = _NavRow(nav_col, key, label, self.select)
            row.pack(side=tk.TOP, fill=tk.X, pady=2)
            self._rows[key] = row

        # Highlight the default row without firing on_select -- the caller is
        # expected to have already built whatever that default section shows.
        self._active_key = NAV_ITEMS[0][0]
        self._rows[self._active_key].set_active(True)

    def select(self, key):
        if key == self._active_key:
            return
        self._active_key = key
        for row_key, row in self._rows.items():
            row.set_active(row_key == key)
        self._on_select(key)
