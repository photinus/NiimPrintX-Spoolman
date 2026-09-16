"""A rounded-corner container: real widgets (a Combobox, Labels, a whole
panel of them) can't have border-radius themselves, so this draws the
rounded background on a Canvas and hosts them in a normal `.inner` Frame
placed on top of it via `create_window`.

Two usage modes:
- Content-sized (the default): pack/place widgets into `.inner`, then call
  `.finalize()` once -- the canvas sizes itself to fit and draws the
  rounded rect behind them. Used for fixed-content chrome like pills.
- `fill_parent=True`: the canvas instead sizes to whatever its own parent
  gives it (via pack/place `fill`/`expand`) and redraws on every resize.
  Used for panels that should grow/shrink, e.g. a draggable splitter.
"""

import tkinter as tk

from .RoundedButton import _rounded_rect


def _infer_bg(widget):
    try:
        return widget.cget("bg")
    except tk.TclError:
        try:
            return widget.cget("background")
        except tk.TclError:
            return "#FFFFFF"


class RoundedFrame(tk.Canvas):
    def __init__(self, parent, bg_color, radius=12, border_color=None, outer_bg=None,
                 fill_parent=False, **kwargs):
        outer_bg = outer_bg if outer_bg is not None else _infer_bg(parent)
        super().__init__(parent, highlightthickness=0, bd=0, bg=outer_bg, **kwargs)
        self.bg_color = bg_color
        self.radius = radius
        self.border_color = border_color
        self.fill_parent = fill_parent

        self.inner = tk.Frame(self, bg=bg_color)
        self._window_id = self.create_window(0, 0, window=self.inner, anchor="nw")

        if fill_parent:
            self.bind("<Configure>", lambda e: self._redraw(e.width, e.height))

    def _redraw(self, w, h):
        if w <= 1 or h <= 1:
            return
        self.delete("bg")
        outline = self.border_color or self.bg_color
        rect_id = _rounded_rect(self, 0, 0, w, h, self.radius, fill=self.bg_color, outline=outline, tags="bg")
        self.tag_lower(rect_id, self._window_id)
        self.itemconfig(self._window_id, width=w, height=h)

    def finalize(self):
        """One-shot sizing for content-driven (non-fill_parent) usage --
        call once after everything has been packed/placed into `.inner`."""
        self.update_idletasks()
        w = max(1, self.inner.winfo_reqwidth())
        h = max(1, self.inner.winfo_reqheight())
        self.configure(width=w, height=h)
        self._redraw(w, h)
        return self
