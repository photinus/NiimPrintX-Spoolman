import platform
import tkinter as tk
from tkinter import ttk
from tkinter import messagebox

from .AppConfig import AppConfig
from .widget.TextTab import TextTab
from .widget.IconTab import IconTab
from .widget.SpoolmanTab import SpoolmanTab, TEMPLATE_TOKENS
from .widget.StatusBar import StatusBar
from .widget.PrintOption import PrintOption
from .widget.Sidebar import Sidebar
from .widget.TitleBar import TitleBar
from .component import theme
from .component import RecentLabels
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

_RESIZE_BORDER = 6
_MIN_WIDTH = 760
_MIN_HEIGHT = 560


class LabelPrinterApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title('NiimPrintX')
        width=1100
        height=800
        x = (self.winfo_screenwidth() // 2) - (width // 2)
        y = (self.winfo_screenheight() // 2) - (height // 2)
        self.geometry(f"{width}x{height}+{x}+{y}")
        self.minsize(_MIN_WIDTH, _MIN_HEIGHT)
        self.protocol("WM_DELETE_WINDOW", self.on_close)
        self.configure(bg=theme.BG_APP, highlightthickness=1, highlightbackground=theme.BORDER_STRONG)
        # Custom title bar replaces the OS one, so the window is frameless:
        # no native caption/border, minimize/maximize/close, or resize grips
        # -- all of that is rebuilt below (TitleBar + the resize-grip frames
        # in _make_resize_grips) and native ones no longer apply.
        self.overrideredirect(True)
        self._maximized = False
        self._restore_geometry = None
        self._resize_edge = None
        self.bind("<Map>", self._on_map)
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
        self._apply_windows_taskbar_fix()
        self.deiconify()
        self.lift()

    def create_menu(self):
        self.file_menu = FileMenu(self, self.app_config)

    def create_widgets(self):
        self.title_bar = TitleBar(
            self,
            on_file_menu=lambda x, y: self.file_menu.show(x, y),
            on_minimize=self._minimize,
            on_toggle_maximize=self._toggle_maximize,
            on_close=self.on_close,
        )
        self.title_bar.pack(side=tk.TOP, fill=tk.X)

        body_row = tk.Frame(self, bg=theme.BG_APP)
        body_row.pack(side=tk.TOP, fill=tk.BOTH, expand=True)
        self._make_resize_grips()

        # Left nav rail: replaces the old Text/Icon/Spoolman Notebook tabs with
        # a persistent sidebar (Design merges Text+Icon; Spoolman stays separate).
        self.sidebar = Sidebar(body_row, on_select=self.show_section, config=self.app_config,
                               on_recent_select=self.open_recent_label)
        self.sidebar.pack(side=tk.LEFT, fill=tk.Y)

        right_col = tk.Frame(body_row, bg=theme.BG_CONTENT)
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
        toolbar_row1 = tk.Frame(self.design_toolbar, bg=theme.BG_CONTENT)
        toolbar_row1.pack(side=tk.TOP, fill=tk.X)
        self.add_text_button = RoundedButton(toolbar_row1, text="+ Add text", variant="primary",
                                             bg=theme.BG_CONTENT,
                                             command=lambda: self.select_design_subtab("text"))
        self.add_icon_button = RoundedButton(toolbar_row1, text="+ Add icon", variant="secondary",
                                             bg=theme.BG_CONTENT,
                                             command=lambda: self.select_design_subtab("icon"))
        self.add_text_button.pack(side=tk.LEFT)
        self.add_icon_button.pack(side=tk.LEFT, padx=(8, 0))

        # Shown only while editing a Spoolman label template (see
        # set_template_editing) -- gives an obvious way to insert tokens and,
        # crucially, to finish/save and get back to the Spoolman panel.
        self.template_controls = tk.Frame(self.design_toolbar, bg=theme.BG_CONTENT)
        tk.Label(self.template_controls, text="Editing template -- insert:", bg=theme.BG_CONTENT,
                fg=theme.TEXT_MUTED, font=theme.FONT_LABEL).pack(side=tk.LEFT, padx=(0, 8))
        for label, token in TEMPLATE_TOKENS:
            RoundedButton(self.template_controls, text=label, variant="secondary", bg=theme.BG_CONTENT,
                         command=lambda t=token: self.spoolman_tab.insert_template_token(t)).pack(side=tk.LEFT, padx=(0, 6))
        RoundedButton(self.template_controls, text="QR code", variant="secondary", bg=theme.BG_CONTENT,
                     command=lambda: self.spoolman_tab.insert_template_qr()).pack(side=tk.LEFT, padx=(0, 14))
        RoundedButton(self.template_controls, text="Done editing template", variant="primary", bg=theme.BG_CONTENT,
                     command=lambda: self.spoolman_tab.toggle_template_edit()).pack(side=tk.LEFT)

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

    def set_template_editing(self, active):
        """Called by SpoolmanTab when entering/leaving Spoolman label-template
        editing. Jumps into the Design section (where the canvas + token
        toolbar live) while editing, and back to the Spoolman panel once
        done -- so there's always an obvious "Done" button and an obvious
        way back, instead of the editor opening with no visible exit."""
        if active:
            self.select_design_subtab("text")
            self.show_section("design")
            self.template_controls.pack(side=tk.TOP, fill=tk.X, pady=(10, 0))
        else:
            self.template_controls.pack_forget()
            self.show_section("spoolman")

    def open_recent_label(self, entry):
        """Reopen a previously-printed label (sidebar 'Recent labels' click) in
        the print-preview popup so it can be viewed and reprinted."""
        image = RecentLabels.load_recent_label_image(self.app_config, entry)
        if image is None:
            messagebox.showerror("Recent labels", "That label's image is no longer available.")
            return
        self.print_option.show_image_preview(image, name=entry.get("name"))

    # -- Frameless-window chrome: resize grips, minimize/maximize, close --------------

    @staticmethod
    def _set_resize_cursor(widget, windows_name, x11_name):
        """Cursor names aren't portable: 'size_ns' etc. are Windows-only Tk
        names (this app's actual target), 'sb_v_double_arrow' etc. are the
        X11 fallback this dev sandbox needs. Try native-Windows first."""
        try:
            widget.config(cursor=windows_name)
        except tk.TclError:
            try:
                widget.config(cursor=x11_name)
            except tk.TclError:
                pass

    def _make_resize_grips(self):
        """Thin invisible frames along each edge/corner that drag-resize the
        window, replacing the native resize border overrideredirect removes."""
        b = _RESIZE_BORDER
        edges = [
            ("n", dict(relx=0, rely=0, relwidth=1, height=b, anchor="nw"), "size_ns", "sb_v_double_arrow"),
            ("s", dict(relx=0, rely=1, relwidth=1, height=b, anchor="sw"), "size_ns", "sb_v_double_arrow"),
            ("w", dict(relx=0, rely=0, relheight=1, width=b, anchor="nw"), "size_we", "sb_h_double_arrow"),
            ("e", dict(relx=1, rely=0, relheight=1, width=b, anchor="ne"), "size_we", "sb_h_double_arrow"),
        ]
        corners = [
            ("nw", dict(relx=0, rely=0, width=b * 2, height=b * 2, anchor="nw"), "size_nw_se", "top_left_corner"),
            ("se", dict(relx=1, rely=1, width=b * 2, height=b * 2, anchor="se"), "size_nw_se", "bottom_right_corner"),
            ("ne", dict(relx=1, rely=0, width=b * 2, height=b * 2, anchor="ne"), "size_ne_sw", "top_right_corner"),
            ("sw", dict(relx=0, rely=1, width=b * 2, height=b * 2, anchor="sw"), "size_ne_sw", "bottom_left_corner"),
        ]
        # Corners are created after (so stacked above) the edges they overlap,
        # so a corner drag takes priority over the edge underneath it.
        for edge, place_kwargs, win_cursor, x11_cursor in edges + corners:
            grip = tk.Frame(self, bg=theme.BG_APP)
            self._set_resize_cursor(grip, win_cursor, x11_cursor)
            grip.place(**place_kwargs)
            grip.bind("<ButtonPress-1>", lambda e, edge=edge: self._start_resize(e, edge))
            grip.bind("<B1-Motion>", self._do_resize)
            grip.bind("<ButtonRelease-1>", self._end_resize)

    def _start_resize(self, event, edge):
        self._resize_edge = edge
        self._resize_start = (
            event.x_root, event.y_root,
            self.winfo_x(), self.winfo_y(),
            self.winfo_width(), self.winfo_height(),
        )

    def _do_resize(self, event):
        if not self._resize_edge:
            return
        start_x_root, start_y_root, orig_x, orig_y, orig_w, orig_h = self._resize_start
        dx = event.x_root - start_x_root
        dy = event.y_root - start_y_root
        edge = self._resize_edge

        x, y, w, h = orig_x, orig_y, orig_w, orig_h
        if "e" in edge:
            w = max(_MIN_WIDTH, orig_w + dx)
        if "s" in edge:
            h = max(_MIN_HEIGHT, orig_h + dy)
        if "w" in edge:
            w = max(_MIN_WIDTH, orig_w - dx)
            x = orig_x + (orig_w - w)
        if "n" in edge:
            h = max(_MIN_HEIGHT, orig_h - dy)
            y = orig_y + (orig_h - h)
        self.geometry(f"{w}x{h}+{x}+{y}")

    def _end_resize(self, _event=None):
        self._resize_edge = None

    def _minimize(self):
        # overrideredirect windows can't just iconify() reliably on Windows --
        # the standard workaround is to drop back to a normal frame right
        # before minimizing, then restore it once the window is mapped again.
        self.overrideredirect(False)
        self.iconify()

    def _on_map(self, event):
        if event.widget is self and self.state() == "normal":
            self.overrideredirect(True)

    def _get_work_area(self):
        """Screen bounds excluding the taskbar, so maximize doesn't cover it."""
        if platform.system() == "Windows":
            try:
                import ctypes
                import ctypes.wintypes
                rect = ctypes.wintypes.RECT()
                SPI_GETWORKAREA = 0x0030
                ctypes.windll.user32.SystemParametersInfoW(SPI_GETWORKAREA, 0, ctypes.byref(rect), 0)
                return rect.left, rect.top, rect.right - rect.left, rect.bottom - rect.top
            except Exception:
                pass
        return 0, 0, self.winfo_screenwidth(), self.winfo_screenheight()

    def _toggle_maximize(self):
        if self._maximized:
            self.geometry(self._restore_geometry)
            self._maximized = False
        else:
            self._restore_geometry = self.geometry()
            x, y, w, h = self._get_work_area()
            self.geometry(f"{w}x{h}+{x}+{y}")
            self._maximized = True
        self.title_bar.set_maximized(self._maximized)

    def _apply_windows_taskbar_fix(self):
        """overrideredirect windows are invisible to the Windows taskbar/Alt-Tab
        by default (WS_EX_TOOLWINDOW-like behavior); force the "app window"
        extended style back on so it still shows up normally. No-ops safely
        everywhere else, or if anything about this fails."""
        if platform.system() != "Windows":
            return
        try:
            import ctypes
            hwnd = ctypes.windll.user32.GetParent(self.winfo_id())
            GWL_EXSTYLE = -20
            WS_EX_APPWINDOW = 0x00040000
            WS_EX_TOOLWINDOW = 0x00000080
            style = ctypes.windll.user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
            style = (style & ~WS_EX_TOOLWINDOW) | WS_EX_APPWINDOW
            ctypes.windll.user32.SetWindowLongW(hwnd, GWL_EXSTYLE, style)
            SWP_NOMOVE, SWP_NOSIZE, SWP_NOZORDER, SWP_FRAMECHANGED = 0x0002, 0x0001, 0x0004, 0x0020
            ctypes.windll.user32.SetWindowPos(
                hwnd, 0, 0, 0, 0, 0, SWP_NOMOVE | SWP_NOSIZE | SWP_NOZORDER | SWP_FRAMECHANGED
            )
        except Exception:
            pass

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
