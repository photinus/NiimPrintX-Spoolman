"""Render a Spoolman label from a user-designed canvas template.

Users design these on the same canvas used for regular text/icon labels (see the
Spoolman tab's "Edit Label Template" mode), with `{field}` tokens in text content and
a QR placeholder image. This module substitutes real spool data into a saved template
and composes the final printable image -- no live Tkinter canvas required, so it can
run from the same code path as the algorithmic fallback in label.py.
"""
import base64
import io
import os
import re

from PIL import Image

try:
    import qrcode
except ImportError:  # pragma: no cover - optional dependency
    qrcode = None

from NiimPrintX.nimmy.canvas_geometry import label_geometry
from NiimPrintX.nimmy.text_render import render_text_image
from NiimPrintX.ui.component.DesignStore import design_path, read_design_data
from .label import BACKGROUND, _spool_fields, _caption_text

_TOKEN_RE = re.compile(r"\{(\w+)\}")


def has_template(config, device=None, label_size=None):
    path = design_path(config, device, label_size, kind="spoolman")
    return bool(path) and os.path.exists(path)


def load_template(config, device=None, label_size=None):
    """Raw saved-template dict, or None if this device/label-size has no template."""
    return read_design_data(config, device, label_size, kind="spoolman")


def _template_fields(spool):
    fields = _spool_fields(spool)
    return {
        "id": fields["id"] if fields["id"] is not None else "",
        "vendor": fields["vendor"],
        "name": fields["name"],
        "material": fields["material"],
        "caption": _caption_text(fields),
    }, fields["id"]


def _substitute(text, fields):
    """Replace {field} tokens; unknown/malformed tokens are left as literal text."""
    return _TOKEN_RE.sub(lambda m: str(fields.get(m.group(1), m.group(0))), text)


def _build_qr(data, size_px):
    if qrcode is None or not data or size_px < 20:
        return None
    qr = qrcode.QRCode(border=1, box_size=10)
    qr.add_data(data)
    qr.make(fit=True)
    qr_image = qr.make_image(fill_color="black", back_color="white").convert("RGBA")
    return qr_image.resize((size_px, size_px), Image.NEAREST)


def render_spool_label_template(design_data, spool, os_system, width_mm, height_mm, print_dpi,
                                 *, base_url=None):
    """Render a spool label from a saved Spoolman canvas template (see DesignStore)."""
    geometry = label_geometry(width_mm, height_mm, print_dpi)
    offset_x, offset_y = geometry["bbox_left"], geometry["bbox_top"]

    img = Image.new("RGB", (geometry["bbox_width"], geometry["bbox_height"]), BACKGROUND)

    fields, spool_id = _template_fields(spool)
    has_id = spool_id is not None
    qr_data = None
    if has_id:
        qr_data = (
            f"{base_url.rstrip('/')}/spool/show/{spool_id}"
            if base_url else f"spoolman:spool:{spool_id}"
        )

    for item in design_data.get("text", {}).values():
        content = _substitute(item["content"], fields)
        if not content.strip():
            continue
        text_image = render_text_image(os_system, item["font_props"], content)
        x, y = item["coords"]
        img.paste(text_image, (round(x - offset_x), round(y - offset_y)), text_image)

    for item in design_data.get("image", {}).values():
        x, y = item["coords"]
        pos = (round(x - offset_x), round(y - offset_y))
        if item.get("qr"):
            if not has_id:
                continue
            size = Image.open(io.BytesIO(base64.b64decode(item["image"]))).size
            qr_image = _build_qr(qr_data, max(20, min(size)))
            if qr_image is not None:
                img.paste(qr_image, pos, qr_image)
        else:
            static_image = Image.open(io.BytesIO(base64.b64decode(item["image"]))).convert("RGBA")
            img.paste(static_image, pos, static_image)

    return img
