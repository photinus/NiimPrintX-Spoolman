import tkinter as tk
from tkinter import ttk
from tkinter import messagebox

from .AppConfig import AppConfig
from .widget.TextTab import TextTab
from .widget.IconTab import IconTab
from .widget.SpoolmanTab import SpoolmanTab
from .widget.StatusBar import StatusBar
from .widget.PrintOption import PrintOption
from .widget.Sidebar import Sidebar
from .component import theme
from .component.RoundedButton import RoundedButton

from NiimPrintX.ui.widget.CanvasSelector import CanvasSelector
from NiimPrintX.ui.widget.FileMenu import FileMenu
from NiimPrintX.ui.component.DesignStore import save_design

import asyncio
import threading

from loguru import logger


logger.disable('NiimPrintX.nimmy')

# import sys
# import logging
#
# logging.basicConfig(level=logging.DEBUG, filename='/Users/dhivah/Documents/Personal/repos/NiimPrintX/logfile.log', filemode='w',
#                     format='%(name)s - %(levelname)s - %(message)s')

# def handle_exception(exc_type, exc_value, exc_traceback):
#     if issubclass(exc_type, KeyboardInterrupt):
#         sys.__exit__(0)
#     else:
#         logging.error("Uncaught exception", exc_info=(exc_type, exc_value, exc_traceback))
#
# sys.excepthook = handle_exception

from devtools import debug
class LabelPrinterApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title('NiimPrintX')
        width=1100
        height=800
        x = (self.winfo_screenwidth() // 2) - (width // 2)
        y = (self.winfo_screenheight() // 2) - (height // 2)
        self.geometry(f"{width}x{height}+{x}+{y}")
        self.resizable(width=True, height=True)  # Allow window to be resizable
        self.protocol("WM_DELETE_WINDOW", self.on_close)
        self.configure(bg=theme.BG_APP)
        self.withdraw()

        # self.async_loop = asyncio.new_event_loop()
        # threading.Thread(target=self.start_asyncio_loop, daemon=True).start()
        #
        # self.app_config = AppConfig()
        # self.create_widgets()
        # self.create_menu()
        # self.printer = None
        # self.load_resources()

    def load_resources(self):
        self.async_loop = asyncio.new_event_loop()
        threading.Thread(target=self.start_asyncio_loop, daemon=True).start()

        self.app_config = AppConfig()
        self._setup_style()

        self.create_widgets()
        self.create_menu()
        self.printer = None
        self.after(5000, self.show_main_window)

    def _setup_style(self):
        """Base ttk theme + a flat 'pill' Combobox style used throughout the refresh.

        ttk can't do border-radius, but 'clam' at least lets every color be
        overridden (unlike the native aqua/xpnative themes), which keeps the
        dropdowns from clashing with the hand-drawn RoundedButton pills.
        """
        style = ttk.Style(self)
        try:
            style.theme_use('clam')
        except tk.TclError:
            pass
        style.configure(
            "Pill.TCombobox",
            fieldbackground=theme.BG_FIELD,
            background=theme.BG_FIELD,
            foreground=theme.TEXT_PRIMARY,
            arrowcolor=theme.TEXT_MUTED,
            bordercolor=theme.BORDER,
            lightcolor=theme.BG_FIELD,
            darkcolor=theme.BG_FIELD,
            borderwidth=0,
            relief='flat',
            padding=4,
        )
        style.map(
            "Pill.TCombobox",
            fieldbackground=[('readonly', theme.BG_FIELD)],
            foreground=[('readonly', theme.TEXT_PRIMARY)],
        )

    def show_main_window(self):
        self.deiconify()
        self.lift()

    def create_menu(self):
        menu_bar = tk.Menu(self)
        self.config(menu=menu_bar)
        self.file_menu = FileMenu(self, menu_bar, self.app_config)

    def create_widgets(self):
        # Left nav rail: replaces the old Text/Icon/Spoolman Notebook tabs with
        # a persistent sidebar (Design merges Text+Icon; Spoolman stays separate).
        self.sidebar = Sidebar(self, on_select=self.show_section)
        self.sidebar.pack(side=tk.LEFT, fill=tk.Y)

        right_col = tk.Frame(self, bg=theme.BG_CONTENT)
        right_col.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # -- Persistent top bar: section title + label-size pill + connection pill --
        self.top_bar = tk.Frame(right_col, bg=theme.BG_CONTENT, height=64)
        self.top_bar.pack(side=tk.TOP, fill=tk.X)
        self.top_bar.pack_propagate(False)

        self.section_title_label = tk.Label(self.top_bar, text="Design", bg=theme.BG_CONTENT,
                                            fg=theme.TEXT_PRIMARY, font=theme.FONT_SECTION_TITLE)
        self.section_title_label.pack(side=tk.LEFT, padx=28)

        top_bar_right = tk.Frame(self.top_bar, bg=theme.BG_CONTENT)
        top_bar_right.pack(side=tk.RIGHT, padx=28)

        # -- Persistent bottom bar: device pill + Save image/Print --
        bottom_bar = tk.Frame(right_col, bg=theme.BG_CONTENT, height=64)
        bottom_bar.pack(side=tk.BOTTOM, fill=tk.X)
        bottom_bar.pack_propagate(False)

        bottom_bar_left = tk.Frame(bottom_bar, bg=theme.BG_CONTENT)
        bottom_bar_left.pack(side=tk.LEFT, padx=28)
        bottom_bar_right = tk.Frame(bottom_bar, bg=theme.BG_CONTENT)
        bottom_bar_right.pack(side=tk.RIGHT, padx=28)

        # -- Body: one shared canvas (never destroyed/reparented -- it's the same
        # editable/previewable surface Design and Spoolman have always shared) plus
        # a 296px side panel whose *contents* swap with the active section. --
        self.design_toolbar = tk.Frame(right_col, bg=theme.BG_CONTENT)
        self.add_text_button = RoundedButton(self.design_toolbar, text="+ Add text", variant="primary",
                                             bg=theme.BG_CONTENT,
                                             command=lambda: self.select_design_subtab("text"))
        self.add_icon_button = RoundedButton(self.design_toolbar, text="+ Add icon", variant="secondary",
                                             bg=theme.BG_CONTENT,
                                             command=lambda: self.select_design_subtab("icon"))
        self.add_text_button.pack(side=tk.LEFT)
        self.add_icon_button.pack(side=tk.LEFT, padx=(8, 0))

        self.body = tk.Frame(right_col, bg=theme.BG_CONTENT)
        body = self.body
        self.design_toolbar.pack(side=tk.TOP, fill=tk.X, padx=28, pady=(20, 12))
        body.pack(side=tk.TOP, fill=tk.BOTH, expand=True, padx=28, pady=(0, 20))

        # Canvas host -- CanvasSelector creates/destroys the actual tk.Canvas here
        # whenever the device/label size changes. Stays mounted for both sections.
        self.app_config.frames["top_frame"] = tk.Frame(body, bg=theme.BG_CANVAS_AREA)
        self.app_config.screen_dpi = int(self.app_config.frames["top_frame"].winfo_fpixels('1i'))
        self.app_config.frames["top_frame"].pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        side_panel = tk.Frame(body, bg=theme.BG_CARD, width=296,
                              highlightbackground=theme.BORDER, highlightthickness=1)
        side_panel.pack(side=tk.LEFT, fill=tk.Y, padx=(24, 0))
        side_panel.pack_propagate(False)

        self.text_tab = TextTab(side_panel, self.app_config)
        self.icon_tab = IconTab(side_panel, self.app_config)
        self.text_tab.frame.place(x=0, y=0, relwidth=1, relheight=1)
        self.icon_tab.frame.place(x=0, y=0, relwidth=1, relheight=1)
        self._design_subtab = None
        self.select_design_subtab("text")

        self.spoolman_tab = SpoolmanTab(self, side_panel, self.app_config)
        self.spoolman_tab.frame.place(x=0, y=0, relwidth=1, relheight=1)
        # Newly-created siblings default to the top of the stacking order --
        # re-raise whichever Design sub-tab is active so it isn't hidden by it.
        self.select_design_subtab(self._design_subtab)

        # Top-bar / bottom-bar widgets that depend on text_tab/icon_tab existing.
        self.canvas_selector = CanvasSelector(top_bar_right, self.app_config,
                                              self.text_tab.get_text_operation(),
                                              self.icon_tab.get_image_operation(),
                                              self, device_parent=bottom_bar_left)
        self.status_bar = StatusBar(top_bar_right, self.app_config)

        self.print_option = PrintOption(self, bottom_bar_right, self.app_config)

    def show_section(self, key):
        """Swap the side panel between Design (Text+Icon merged) and Spoolman, keep
        the sidebar highlight, top-bar title and Spoolman's live preview in sync.
        The canvas itself never moves -- only the panel beside it changes."""
        if key == "spoolman":
            self.spoolman_tab.frame.tkraise()
            self.design_toolbar.pack_forget()
            self.section_title_label.config(text="Spoolman")
            self.spoolman_tab.on_show()
        else:
            key = "design"
            self.design_toolbar.pack(side=tk.TOP, fill=tk.X, padx=28, pady=(20, 12), before=self.body)
            (self.icon_tab.frame if self._design_subtab == "icon" else self.text_tab.frame).tkraise()
            self.section_title_label.config(text="Design")
            if hasattr(self, "spoolman_tab"):
                self.spoolman_tab.on_hide()
        self.sidebar.select(key)

    def select_design_subtab(self, name):
        """Switch the Design section's right-hand property panel between the
        Text and Icon editors (the mockup's '+ Add text' / '+ Add icon' pills)."""
        self._design_subtab = "icon" if name == "icon" else "text"
        if self._design_subtab == "icon":
            self.icon_tab.frame.tkraise()
            self.add_text_button.config(variant="secondary")
            self.add_icon_button.config(variant="primary")
        else:
            self.text_tab.frame.tkraise()
            self.add_text_button.config(variant="primary")
            self.add_icon_button.config(variant="secondary")

    def start_asyncio_loop(self):
        asyncio.set_event_loop(self.async_loop)
        self.async_loop.run_forever()

    def on_close(self):
        if messagebox.askokcancel("Quit", "Do you want to quit?"):
            save_design(self.app_config)
            self.app_config.save_settings()
            self.destroy()

if __name__ == "__main__":
    try:
        app = LabelPrinterApp()
        app.load_resources()
        app.mainloop()
    except Exception as e:
        raise e
