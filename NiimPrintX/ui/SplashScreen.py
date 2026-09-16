import tkinter as tk
from tkinter import font as tk_font

from NiimPrintX import __version__
from NiimPrintX.ui.component import theme
from NiimPrintX.ui.component.RoundedButton import _rounded_rect

WIDTH = 360
HEIGHT = 220
LOGO_SIZE = 64


class SplashScreen(tk.Toplevel):
    """Launch splash: just the app name + version in a rounded card, matching
    the rest of the app's theme -- replaces the old static splash image."""

    def __init__(self, master, app_name="NiimPrintX", version=None, **kwargs):
        super().__init__(master, **kwargs)
        self.overrideredirect(True)
        self.configure(bg=theme.BG_APP)
        self.withdraw()

        canvas = tk.Canvas(self, width=WIDTH, height=HEIGHT, highlightthickness=0, bd=0, bg=theme.BG_APP)
        canvas.pack()

        _rounded_rect(canvas, 1, 1, WIDTH - 1, HEIGHT - 1, 18,
                      fill=theme.BG_CARD, outline=theme.BORDER_STRONG)

        cx = WIDTH / 2
        logo_top = 40
        _rounded_rect(canvas, cx - LOGO_SIZE / 2, logo_top, cx + LOGO_SIZE / 2, logo_top + LOGO_SIZE, 16,
                      fill=theme.ACCENT, outline=theme.ACCENT)
        canvas.create_text(cx, logo_top + LOGO_SIZE / 2, text="N", fill=theme.TEXT_ON_ACCENT,
                           font=(theme.FONT_FAMILY, 26, "bold"))

        name_font = tk_font.Font(family=theme.FONT_FAMILY, size=18, weight="bold")
        canvas.create_text(cx, logo_top + LOGO_SIZE + 30, text=app_name, fill=theme.TEXT_PRIMARY, font=name_font)

        version_font = tk_font.Font(family=theme.FONT_FAMILY, size=10)
        canvas.create_text(cx, logo_top + LOGO_SIZE + 56, text=f"v{version or __version__}",
                           fill=theme.TEXT_MUTED, font=version_font)

        # Center the window
        self.update_idletasks()
        x = (self.winfo_screenwidth() // 2) - (WIDTH // 2)
        y = (self.winfo_screenheight() // 2) - (HEIGHT // 2)
        self.geometry(f"{WIDTH}x{HEIGHT}+{x}+{y}")
        self.deiconify()
