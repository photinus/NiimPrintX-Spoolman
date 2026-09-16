import tkinter as tk

from ..component import theme

HEIGHT = 40
BUTTON_WIDTH = 46


class _CaptionButton(tk.Canvas):
    """One of the minimize/maximize/close glyph buttons on the right."""

    def __init__(self, parent, draw_glyph, on_click, hover_bg=theme.BORDER, hover_fg=None):
        super().__init__(parent, width=BUTTON_WIDTH, height=HEIGHT, highlightthickness=0,
                         bd=0, bg=theme.BG_SIDEBAR, cursor="arrow")
        self._draw_glyph = draw_glyph
        self._on_click = on_click
        self._hover_bg = hover_bg
        self._hover_fg = hover_fg
        self._hover = False
        self.bind("<Enter>", self._enter)
        self.bind("<Leave>", self._leave)
        self.bind("<Button-1>", lambda e: self._on_click())
        self.redraw()

    def _enter(self, _event=None):
        self._hover = True
        self.redraw()

    def _leave(self, _event=None):
        self._hover = False
        self.redraw()

    def redraw(self):
        self.delete("all")
        bg = self._hover_bg if self._hover else theme.BG_SIDEBAR
        self.create_rectangle(0, 0, BUTTON_WIDTH, HEIGHT, fill=bg, outline=bg)
        fg = (self._hover_fg if self._hover and self._hover_fg else theme.TEXT_PRIMARY)
        self._draw_glyph(self, BUTTON_WIDTH / 2, HEIGHT / 2, fg)


def _draw_minimize(canvas, cx, cy, fg):
    canvas.create_line(cx - 5, cy + 4, cx + 5, cy + 4, fill=fg, width=1.4)


def _draw_maximize(canvas, cx, cy, fg):
    canvas.create_rectangle(cx - 5, cy - 5, cx + 5, cy + 5, outline=fg, width=1.2)


def _draw_restore(canvas, cx, cy, fg):
    canvas.create_rectangle(cx - 3, cy - 5, cx + 5, cy + 3, outline=fg, width=1.2)
    canvas.create_rectangle(cx - 5, cy - 3, cx + 3, cy + 5, fill=theme.BG_SIDEBAR, outline=fg, width=1.2)


def _draw_close(canvas, cx, cy, fg):
    canvas.create_line(cx - 5, cy - 5, cx + 5, cy + 5, fill=fg, width=1.4)
    canvas.create_line(cx - 5, cy + 5, cx + 5, cy - 5, fill=fg, width=1.4)


class TitleBar(tk.Frame):
    """Custom-drawn title bar replacing the OS caption/border -- app logo +
    name, a File menu button, and minimize/maximize/close glyph buttons.
    Dragging the empty background moves the window; double-clicking it
    toggles maximize, matching normal OS title-bar conventions."""

    def __init__(self, parent, on_file_menu, on_minimize, on_toggle_maximize, on_close):
        super().__init__(parent, bg=theme.BG_SIDEBAR, height=HEIGHT,
                         highlightbackground=theme.BORDER_STRONG, highlightthickness=0)
        self.pack_propagate(False)
        self._on_toggle_maximize = on_toggle_maximize

        left = tk.Frame(self, bg=theme.BG_SIDEBAR)
        left.pack(side=tk.LEFT, fill=tk.Y, padx=(12, 0))

        logo = tk.Canvas(left, width=20, height=20, highlightthickness=0, bd=0, bg=theme.BG_SIDEBAR)
        logo.pack(side=tk.LEFT, pady=(0, 1))
        from ..component.RoundedButton import _rounded_rect
        _rounded_rect(logo, 0, 0, 20, 20, 5, fill=theme.ACCENT, outline=theme.ACCENT)
        logo.create_text(10, 10, text="N", fill=theme.TEXT_ON_ACCENT, font=(theme.FONT_FAMILY, 9, "bold"))

        tk.Label(left, text="NiimPrintX", bg=theme.BG_SIDEBAR, fg=theme.TEXT_PRIMARY,
                 font=(theme.FONT_FAMILY, 10, "bold")).pack(side=tk.LEFT, padx=(8, 0))

        self._file_button = tk.Label(left, text="File", bg=theme.BG_SIDEBAR, fg=theme.TEXT_MUTED,
                                     font=theme.FONT_LABEL, cursor="arrow", padx=10)
        self._file_button.pack(side=tk.LEFT, padx=(14, 0))
        self._file_button.bind("<Enter>", lambda e: self._file_button.config(fg=theme.TEXT_PRIMARY))
        self._file_button.bind("<Leave>", lambda e: self._file_button.config(fg=theme.TEXT_MUTED))
        self._file_button.bind(
            "<Button-1>", lambda e: on_file_menu(e.widget.winfo_rootx(), e.widget.winfo_rooty() + e.widget.winfo_height())
        )

        right = tk.Frame(self, bg=theme.BG_SIDEBAR)
        right.pack(side=tk.RIGHT)
        self._maximize_button = _CaptionButton(right, _draw_maximize, on_toggle_maximize)
        _CaptionButton(right, _draw_minimize, on_minimize).pack(side=tk.LEFT)
        self._maximize_button.pack(side=tk.LEFT)
        _CaptionButton(right, _draw_close, on_close, hover_bg=theme.DANGER_DOT,
                      hover_fg=theme.TEXT_ON_ACCENT).pack(side=tk.LEFT)

        # Draggable background: the bar itself, plus the left spacer (the
        # logo/name/File cluster keeps its own bindings so clicks there still work).
        for widget in (self, left):
            widget.bind("<ButtonPress-1>", self._start_drag)
            widget.bind("<B1-Motion>", self._drag)
            widget.bind("<Double-Button-1>", lambda e: on_toggle_maximize())

    def set_maximized(self, maximized):
        self._maximize_button._draw_glyph = _draw_restore if maximized else _draw_maximize
        self._maximize_button.redraw()

    def _start_drag(self, event):
        self._drag_start = (event.x_root, event.y_root,
                            self.winfo_toplevel().winfo_x(), self.winfo_toplevel().winfo_y())

    def _drag(self, event):
        if not hasattr(self, "_drag_start"):
            return
        start_x, start_y, win_x, win_y = self._drag_start
        dx = event.x_root - start_x
        dy = event.y_root - start_y
        self.winfo_toplevel().geometry(f"+{win_x + dx}+{win_y + dy}")
