import time
import tkinter as tk
from tkinter import font as tk_font

from PIL import Image, ImageTk

from ..component import theme
from ..component import RecentLabels
from ..component.RoundedButton import _rounded_rect

NAV_ITEMS = [
    ("design", "Design"),
    ("spoolman", "Spoolman"),
]

EXPANDED_WIDTH = 232
COLLAPSED_WIDTH = 64


class _NavRow(tk.Canvas):
    """A single sidebar nav row: icon glyph + label, pill-highlighted when
    active. Auto-sizes to whatever width it's packed/stretched to (rather
    than a fixed pixel width) so it stays correct as the sidebar
    collapses/expands; `set_collapsed` hides the label and centers the icon."""

    HEIGHT = 36

    def __init__(self, parent, key, label, on_click):
        super().__init__(parent, height=self.HEIGHT, highlightthickness=0, bd=0, bg=theme.BG_SIDEBAR)
        self.key = key
        self.label = label
        self._on_click = on_click
        self._active = False
        self._collapsed = False
        self._width = 200
        self._font_active = tk_font.Font(family=theme.FONT_NAV[0], size=theme.FONT_NAV[1], weight="bold")
        self._font_inactive = tk_font.Font(family=theme.FONT_NAV_INACTIVE[0], size=theme.FONT_NAV_INACTIVE[1])
        self.bind("<Button-1>", lambda e: self._on_click(self.key))
        self.bind("<Configure>", lambda e: self._on_configure(e.width))
        self._draw()

    def _on_configure(self, width):
        self._width = width
        self._draw()

    def set_active(self, active):
        self._active = active
        self._draw()

    def set_collapsed(self, collapsed):
        self._collapsed = collapsed
        self._draw()

    def _draw(self):
        self.delete("all")
        w = self._width
        if self._active:
            _rounded_rect(self, 0, 0, w, self.HEIGHT, 8, fill=theme.ACCENT_LIGHT, outline=theme.ACCENT_LIGHT)
            fg = theme.ACCENT_DARK
            glyph = theme.ACCENT
            font = self._font_active
        else:
            fg = theme.TEXT_MUTED
            glyph = theme.TEXT_MUTED
            font = self._font_inactive

        cx = w / 2 if self._collapsed else 18
        cy = self.HEIGHT / 2
        if self.key == "design":
            self.create_rectangle(cx - 8, cy - 8, cx + 8, cy + 8, outline=glyph, width=2)
            self.create_line(cx - 3, cy + 1, cx + 3, cy - 5, fill=glyph, width=2)
        else:
            self.create_oval(cx - 8, cy - 8, cx + 8, cy + 8, outline=glyph, width=2)
            self.create_oval(cx - 2, cy - 2, cx + 2, cy + 2, fill=glyph, outline=glyph)

        if not self._collapsed:
            self.create_text(36, cy, text=self.label, fill=fg, font=font, anchor="w")


class _CollapseToggle(tk.Canvas):
    """Small round chevron button, pinned to the sidebar's bottom-right
    corner, that collapses it to an icon rail or expands it back."""

    SIZE = 24

    def __init__(self, parent, on_click):
        super().__init__(parent, width=self.SIZE, height=self.SIZE, highlightthickness=0,
                         bd=0, bg=theme.BG_SIDEBAR, cursor="hand2")
        self._on_click = on_click
        self._collapsed = False
        self._hover = False
        self.bind("<Button-1>", lambda e: self._on_click())
        self.bind("<Enter>", self._enter)
        self.bind("<Leave>", self._leave)
        self._draw()

    def _enter(self, _event=None):
        self._hover = True
        self._draw()

    def _leave(self, _event=None):
        self._hover = False
        self._draw()

    def set_collapsed(self, collapsed):
        self._collapsed = collapsed
        self._draw()

    def _draw(self):
        self.delete("all")
        bg = theme.ACCENT_LIGHT if self._hover else theme.BG_CONTENT
        _rounded_rect(self, 0, 0, self.SIZE, self.SIZE, self.SIZE / 2, fill=bg, outline=theme.BORDER)
        cx, cy = self.SIZE / 2, self.SIZE / 2
        fg = theme.TEXT_PRIMARY
        if self._collapsed:
            self.create_line(cx - 3, cy - 5, cx + 3, cy, fill=fg, width=2)
            self.create_line(cx + 3, cy, cx - 3, cy + 5, fill=fg, width=2)
        else:
            self.create_line(cx + 3, cy - 5, cx - 3, cy, fill=fg, width=2)
            self.create_line(cx - 3, cy, cx + 3, cy + 5, fill=fg, width=2)


def _relative_time(timestamp):
    delta = max(0, time.time() - timestamp)
    if delta < 90:
        return "Just now"
    minutes = delta / 60
    if minutes < 60:
        return f"{int(minutes)}m ago"
    hours = minutes / 60
    if hours < 24:
        return f"{int(hours)}h ago"
    days = hours / 24
    if days < 2:
        return "Yesterday"
    if days < 7:
        return f"{int(days)}d ago"
    weeks = days / 7
    return f"{int(weeks)}w ago"


class _RecentRow(tk.Frame):
    """Thumbnail + name + relative time for one recently-printed label."""

    THUMB_SIZE = (30, 24)

    def __init__(self, parent, entry, on_click):
        super().__init__(parent, bg=theme.BG_SIDEBAR, cursor="hand2")
        self._thumb_photo = None

        thumb_holder = tk.Label(self, bg=theme.RECENT_THUMB_BG, width=self.THUMB_SIZE[0],
                                height=self.THUMB_SIZE[1])
        thumb_holder.pack(side=tk.LEFT)
        thumb_holder.pack_propagate(False)

        text_col = tk.Frame(self, bg=theme.BG_SIDEBAR)
        text_col.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(8, 0))
        name_label = tk.Label(text_col, text=entry.get("name") or "Label", bg=theme.BG_SIDEBAR,
                              fg=theme.TEXT_PRIMARY, font=(theme.FONT_FAMILY, 9, "bold"),
                              anchor="w", justify="left")
        name_label.pack(fill=tk.X, anchor="w")
        size_bits = " · ".join(filter(None, [entry.get("label_size"), _relative_time(entry.get("timestamp", 0))]))
        meta_label = tk.Label(text_col, text=size_bits, bg=theme.BG_SIDEBAR, fg=theme.TEXT_FAINT,
                              font=(theme.FONT_FAMILY, 8), anchor="w", justify="left")
        meta_label.pack(fill=tk.X, anchor="w")

        for widget in (self, thumb_holder, text_col, name_label, meta_label):
            widget.bind("<Button-1>", lambda e: on_click(entry))

        self._load_thumbnail(entry, thumb_holder)

    def _load_thumbnail(self, entry, holder):
        image = RecentLabels.load_thumbnail(entry, self.THUMB_SIZE)
        if image is None:
            return
        self._thumb_photo = ImageTk.PhotoImage(image)
        holder.config(image=self._thumb_photo, text="")


class Sidebar(tk.Frame):
    """Left nav rail: Design/Spoolman section switcher plus a Recent labels
    history (populated from prints, clicking reopens one). Collapsible to an
    icon-only rail via the chevron pinned at its bottom-right corner."""

    def __init__(self, parent, on_select, config=None, on_recent_select=None):
        super().__init__(parent, bg=theme.BG_SIDEBAR, width=EXPANDED_WIDTH)
        self.pack_propagate(False)
        self._on_select = on_select
        self._config = config
        self._on_recent_select = on_recent_select
        self._rows = {}
        self._active_key = None
        self._recent_rows_frame = None
        self._recent_col = None
        self._collapsed = False
        self._build()

    def _build(self):
        nav_col = tk.Frame(self, bg=theme.BG_SIDEBAR)
        nav_col.pack(side=tk.TOP, fill=tk.X, padx=16, pady=(20, 22))
        for key, label in NAV_ITEMS:
            row = _NavRow(nav_col, key, label, self.select)
            row.pack(side=tk.TOP, fill=tk.X, pady=2)
            self._rows[key] = row

        # Highlight the default row without firing on_select -- the caller is
        # expected to have already built whatever that default section shows.
        self._active_key = NAV_ITEMS[0][0]
        self._rows[self._active_key].set_active(True)

        self._recent_col = tk.Frame(self, bg=theme.BG_SIDEBAR)
        self._recent_col.pack(side=tk.TOP, fill=tk.BOTH, expand=True, padx=16)
        self._recent_heading = tk.Label(self._recent_col, text="RECENT LABELS", bg=theme.BG_SIDEBAR,
                                        fg=theme.TEXT_FAINT, font=(theme.FONT_FAMILY, 9, "bold"),
                                        anchor="w")
        self._recent_heading.pack(fill=tk.X, pady=(0, 10))
        self._recent_rows_frame = tk.Frame(self._recent_col, bg=theme.BG_SIDEBAR)
        self._recent_rows_frame.pack(fill=tk.BOTH, expand=True)

        self.refresh_recent()

        self._toggle = _CollapseToggle(self, self.toggle_collapsed)
        self._toggle.place(relx=1.0, rely=1.0, anchor="se", x=-10, y=-10)

    def select(self, key):
        if key == self._active_key:
            return
        self._active_key = key
        for row_key, row in self._rows.items():
            row.set_active(row_key == key)
        self._on_select(key)

    def toggle_collapsed(self):
        self.set_collapsed(not self._collapsed)

    def set_collapsed(self, collapsed):
        self._collapsed = collapsed
        self.configure(width=COLLAPSED_WIDTH if collapsed else EXPANDED_WIDTH)
        for row in self._rows.values():
            row.set_collapsed(collapsed)
        if collapsed:
            self._recent_col.pack_forget()
        else:
            self._recent_col.pack(side=tk.TOP, fill=tk.BOTH, expand=True, padx=16)
        self._toggle.set_collapsed(collapsed)

    def refresh_recent(self):
        """Re-read the recent-labels history from disk and redraw the list."""
        for child in self._recent_rows_frame.winfo_children():
            child.destroy()
        if self._config is None:
            return
        entries = RecentLabels.list_recent_labels(self._config)
        if not entries:
            tk.Label(self._recent_rows_frame, text="Nothing printed yet", bg=theme.BG_SIDEBAR,
                     fg=theme.TEXT_FAINT, font=(theme.FONT_FAMILY, 9), anchor="w",
                     wraplength=190, justify="left").pack(fill=tk.X, anchor="w")
            return
        for entry in entries[:12]:
            row = _RecentRow(self._recent_rows_frame, entry, self._handle_recent_click)
            row.pack(fill=tk.X, pady=4)

    def _handle_recent_click(self, entry):
        if self._on_recent_select:
            self._on_recent_select(entry)
