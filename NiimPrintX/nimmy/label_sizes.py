"""Supported Niimbot devices, their label presets, and print DPI."""

LABEL_SIZES = {
    "d110": {
        "size": {
            "30mm x 15mm": (30, 15),
            "40mm x 12mm": (40, 12),
            "50mm x 14mm": (50, 14),
            "75mm x 12mm": (75, 12),
            "109mm x 12.5mm": (109, 12.5),
        },
        "density": 3,
        "print_dpi": 203
    },
    "d11": {
        "size": {
            "30mm x 14mm": (30, 14),
            "40mm x 12mm": (40, 12),
            "50mm x 14mm": (50, 14),
            "75mm x 12mm": (75, 12),
            "109mm x 12.5mm": (109, 12.5),
        },
        "density": 3,
        "print_dpi": 203

    },
    "d11_h": {
        "size": {
            "30mm x 14mm": (30, 14),
            "40mm x 12mm": (40, 12),
            "50mm x 14mm": (50, 14),
            "75mm x 12mm": (75, 12),
            "109mm x 12.5mm": (109, 12.5),
        },
        "density": 3,
        "print_dpi": 300
    },
    "d101": {
        "size": {
            "30mm x 14mm": (30, 14),
            "40mm x 12mm": (40, 12),
            "50mm x 14mm": (50, 14),
            "75mm x 12mm": (75, 12),
            "109mm x 12.5mm": (109, 12.5),
        },
        "density": 3,
        "print_dpi": 203

    },
    "b18": {
        "size": {
            "40mm x 14mm": (40, 14),
            "50mm x 14mm": (50, 14),
            "120mm x 14mm": (120, 14),
        },
        "density": 3,
        "print_dpi": 203

    },
    "b1": {
        "size": {
            "30mm x 15mm": (30, 15),
            "40mm x 30mm": (40, 30),
            "50mm x 30mm": (50, 30),
            "50mm x 80mm": (50, 80),
        },
        "density": 5,
        "print_dpi": 203
    },
    "b21": {
        "size": {
            "30mm x 15mm": (30, 15),
            "40mm x 30mm": (40, 30),
            "50mm x 30mm": (50, 30),
            "50mm x 80mm": (50, 80),
        },
        "density": 5,
        "print_dpi": 203
    }
}

# Known RFID roll barcodes, per device, mapped to the matching label-size preset.
# Used to auto-select the label size in the GUI after connecting.
RFID_LABEL_SIZES = {
    "b1": {
        "10262260": "50mm x 30mm"
    },
    "b21": {
        "10262260": "50mm x 30mm"
    }
}
