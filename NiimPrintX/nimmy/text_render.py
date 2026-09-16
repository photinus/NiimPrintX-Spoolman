"""Shared PIL text rendering: font lookup + multi-line drawing with letter-spacing.

Used by TextOperation (live canvas text) and the Spoolman template renderer
(headless), so both draw text identically without duplicating font-search logic.
"""
import os

from PIL import Image, ImageDraw, ImageFont


def font_dirs(os_system):
    if os_system == "Windows":
        return [os.path.join(os.environ.get("WINDIR", "C:\\Windows"), "Fonts")]
    if os_system == "Linux":
        return [
            "/usr/share/fonts",
            "/usr/local/share/fonts",
            os.path.expanduser("~/.fonts"),
            os.path.expanduser("~/.local/share/fonts"),
        ]
    return [
        "/System/Library/Fonts",
        "/System/Library/Fonts/Supplemental",
        "/Library/Fonts",
        os.path.expanduser("~/Library/Fonts"),
    ]


def load_font(os_system, font_props):
    family = font_props["family"].replace(" ", "")
    suffixes = []
    if font_props["weight"] == "bold" and font_props["slant"] == "italic":
        suffixes = ["BoldItalic", "BoldOblique"]
    elif font_props["weight"] == "bold":
        suffixes = ["Bold"]
    elif font_props["slant"] == "italic":
        suffixes = ["Italic", "Oblique"]
    suffixes.extend(["Regular", ""])

    extensions = (".ttf", ".ttc", ".otf")
    for font_dir in font_dirs(os_system):
        if not os.path.isdir(font_dir):
            continue
        for root, _, files in os.walk(font_dir):
            for suffix in suffixes:
                for filename in files:
                    normalized = filename.replace(" ", "").replace("-", "")
                    if (normalized.lower().startswith(family.lower())
                            and suffix.lower() in normalized.lower()
                            and filename.lower().endswith(extensions)):
                        return ImageFont.truetype(os.path.join(root, filename), font_props["size"])
    try:
        return ImageFont.truetype("arial.ttf", font_props["size"])
    except OSError:
        return ImageFont.load_default()


def text_bbox(text, font, spacing, stroke_width):
    if spacing <= 0:
        return ImageDraw.Draw(Image.new("RGBA", (1, 1))).textbbox((0, 0), text, font=font, stroke_width=stroke_width)
    width = sum(font.getlength(character) + spacing for character in text)
    _, top, _, bottom = ImageDraw.Draw(Image.new("RGBA", (1, 1))).textbbox((0, 0), text, font=font, stroke_width=stroke_width)
    return 0, top, int(width), bottom


def draw_text(draw, position, text, font, spacing, stroke_width):
    x, y = position
    if spacing <= 0:
        draw.text((x, y), text, font=font, fill="black", stroke_width=stroke_width, stroke_fill="black")
        return
    for character in text:
        draw.text((x, y), character, font=font, fill="black", stroke_width=stroke_width, stroke_fill="black")
        x += font.getlength(character) + spacing


def render_text_image(os_system, font_props, text):
    """Render multi-line text (with kerning/underline) to an RGBA PIL image, top-left padded by 3px."""
    font = load_font(os_system, font_props)
    spacing = int(float(font_props["kerning"]))
    stroke_width = 1 if font_props["weight"] == "bold" else 0
    lines = text.splitlines() or [text]
    line_boxes = [text_bbox(line or " ", font, spacing, stroke_width) for line in lines]
    width = max(box[2] - box[0] for box in line_boxes) + 6
    line_height = max(font_props["size"] + 4, max(box[3] - box[1] for box in line_boxes) + 4)
    height = line_height * len(lines) + 6

    image = Image.new("RGBA", (width, height), (255, 255, 255, 0))
    draw = ImageDraw.Draw(image)
    for index, line in enumerate(lines):
        y = 3 + index * line_height
        draw_text(draw, (3, y), line, font, spacing, stroke_width)
        if font_props["underline"]:
            _, _, line_width, _ = text_bbox(line or " ", font, spacing, stroke_width)
            underline_y = y + line_height - 3
            draw.line((3, underline_y, 3 + line_width, underline_y), fill="black", width=1)

    return image
