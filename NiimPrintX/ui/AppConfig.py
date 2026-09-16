import os
import json
import appdirs
import platform

from NiimPrintX.nimmy.label_sizes import LABEL_SIZES, RFID_LABEL_SIZES


class AppConfig:
    def __init__(self):
        self.os_system = platform.system()
        self.cache_dir = appdirs.user_cache_dir('NiimPrintX')
        self.design_dir = os.path.join(self.cache_dir, "designs")
        self.settings_file = os.path.join(self.cache_dir, "settings.json")
        os.makedirs(self.design_dir, exist_ok=True)
        self.settings = self.load_settings()
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
        # "design" (default) is the regular per-device/label-size canvas design;
        # "spoolman" is the Spoolman label template, saved/loaded separately by
        # DesignStore so editing one never clobbers the other.
        self.design_kind = "design"
        self.label_sizes = LABEL_SIZES
        self.rfid_label_sizes = RFID_LABEL_SIZES
        self.current_label_size = None
        self.frames = {}
        self.print_job = False
        self.printer_connected = False

    def load_settings(self):
        defaults = {
            "device": "d110",
            "label_size": "30mm x 15mm",
            "font": {
                "family": "Arial",
                "size": 16,
                "kerning": "0",
                "weight": "normal",
                "slant": "roman",
                "underline": False
            },
            "print": {}
        }
        if not os.path.exists(self.settings_file):
            return defaults
        try:
            with open(self.settings_file, "r", encoding="utf-8") as settings:
                loaded_settings = json.load(settings)
            font_settings = defaults["font"].copy()
            font_settings.update(loaded_settings.get("font", {}))
            defaults.update({key: value for key, value in loaded_settings.items() if key != "font"})
            defaults["font"] = font_settings
        except (OSError, json.JSONDecodeError):
            pass
        return defaults

    def save_settings(self):
        try:
            with open(self.settings_file, "w", encoding="utf-8") as settings:
                json.dump(self.settings, settings, indent=2)
        except OSError:
            pass


