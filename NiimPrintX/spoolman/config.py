"""Persistence for Spoolman connection settings, shared by the CLI and GUI."""
import json
import os

import appdirs

CONFIG_DIR = appdirs.user_config_dir("NiimPrintX")
CONFIG_FILE = os.path.join(CONFIG_DIR, "spoolman.json")


def load_settings():
    if os.path.isfile(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            return {}
    return {}


def save_settings(**kwargs):
    settings = load_settings()
    settings.update({k: v for k, v in kwargs.items() if v is not None})
    os.makedirs(CONFIG_DIR, exist_ok=True)
    with open(CONFIG_FILE, "w") as f:
        json.dump(settings, f, indent=2)
    return settings
