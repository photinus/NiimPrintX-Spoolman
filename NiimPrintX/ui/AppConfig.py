import os
import appdirs
import platform

from NiimPrintX.nimmy.label_sizes import LABEL_SIZES


class AppConfig:
    def __init__(self):
        self.os_system = platform.system()
        self.screen_dpi = 72
        self.text_items = {}
        self.image_items = {}
        self.current_selected = None
        self.current_selected_image = None
        self.current_dir = os.path.dirname(os.path.realpath(__file__))
        self.icon_folder = f"{self.current_dir}/icons"
        self.canvas = None
        self.bounding_box = None
        self.device = None
        self.label_sizes = LABEL_SIZES
        self.current_label_size = None
        self.frames = {}
        self.print_job = False
        self.printer_connected = False
        self.cache_dir = appdirs.user_cache_dir('NiimPrintX')


