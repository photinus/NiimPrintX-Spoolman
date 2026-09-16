"""Render a printable label image for a Spoolman spool record."""
from PIL import Image, ImageDraw, ImageFont

try:
    import qrcode
except ImportError:  # pragma: no cover - optional dependency
    qrcode = None

BACKGROUND = "white"
FOREGROUND = "black"


def _font(size):
    size = max(int(size), 6)
    try:
        return ImageFont.load_default(size=size)
    except TypeError:  # Pillow < 10.1 fallback
        return ImageFont.load_default()


def _text_size(draw, text, font):
    bbox = draw.textbbox((0, 0), text, font=font)
    return bbox[2] - bbox[0], bbox[3] - bbox[1]


def _fit_font(draw, text, max_width, max_height, start_size, min_size=8):
    size = start_size
    font = _font(size)
    while size > min_size:
        font = _font(size)
        width, height = _text_size(draw, text, font)
        if width <= max_width and height <= max_height:
            break
        size -= 1
    return font


def _parse_hex(value):
    if not value:
        return None
    value = value.strip().lstrip("#")
    if len(value) != 6:
        return None
    try:
        return tuple(int(value[i:i + 2], 16) for i in (0, 2, 4))
    except ValueError:
        return None


def _spool_fields(spool):
    filament = spool.get("filament") or {}
    vendor = filament.get("vendor") or {}
    return {
        "id": spool.get("id"),
        "vendor": vendor.get("name") or "",
        "name": filament.get("name") or "",
        "material": filament.get("material") or "",
        "color_hex": filament.get("color_hex"),
        "multi_color_hexes": filament.get("multi_color_hexes"),
        "remaining_weight": spool.get("remaining_weight"),
        "location": spool.get("location") or "",
    }


def _draw_color_swatch(img, draw, box, fields):
    x1, y1, x2, y2 = box
    width, height = x2 - x1, y2 - y1
    if width <= 0 or height <= 0:
        return

    multi = fields["multi_color_hexes"]
    if multi:
        colors = [c for c in (_parse_hex(h) for h in multi.split(",")) if c]
    else:
        colors = [c for c in (_parse_hex(fields["color_hex"]),) if c]

    if colors:
        mask = Image.new("L", (width, height), 0)
        ImageDraw.Draw(mask).ellipse((0, 0, width - 1, height - 1), fill=255)

        swatch = Image.new("RGB", (width, height), colors[0])
        swatch_draw = ImageDraw.Draw(swatch)
        stripe_width = width / len(colors)
        for i, color in enumerate(colors):
            swatch_draw.rectangle((i * stripe_width, 0, (i + 1) * stripe_width, height), fill=color)

        img.paste(swatch, (x1, y1), mask)

    draw.ellipse(box, outline=FOREGROUND, width=1)


def _build_qr_image(data, size_px):
    if qrcode is None or not data or size_px < 20:
        return None
    qr = qrcode.QRCode(border=1, box_size=10)
    qr.add_data(data)
    qr.make(fit=True)
    qr_image = qr.make_image(fill_color="black", back_color="white").convert("RGB")
    return qr_image.resize((size_px, size_px), Image.NEAREST)


def build_spool_label_image(spool, width_px, height_px, *, include_qr=True, base_url=None):
    """Render a spool as a label-sized PIL image, ready to hand to the printer pipeline."""
    fields = _spool_fields(spool)
    width_px = max(int(width_px), 1)
    height_px = max(int(height_px), 1)

    img = Image.new("RGB", (width_px, height_px), BACKGROUND)
    draw = ImageDraw.Draw(img)

    margin = max(2, round(height_px * 0.06))
    content_height = max(height_px - margin * 2, 1)
    swatch_size = min(content_height, max(round(width_px * 0.22), 10))

    swatch_box = (margin, margin, margin + swatch_size, margin + swatch_size)
    _draw_color_swatch(img, draw, swatch_box, fields)

    text_left = swatch_box[2] + margin
    text_right = width_px - margin

    if include_qr and fields["id"] is not None:
        qr_size = min(content_height, swatch_size)
        candidate_text_width = text_right - text_left - qr_size - margin
        if candidate_text_width >= max(width_px * 0.3, 40):
            qr_data = (
                f"{base_url.rstrip('/')}/spool/show/{fields['id']}"
                if base_url else f"spoolman:spool:{fields['id']}"
            )
            qr_image = _build_qr_image(qr_data, qr_size)
            if qr_image is not None:
                img.paste(qr_image, (text_right - qr_size, margin))
                text_right -= qr_size + margin

    text_width = max(text_right - text_left, 10)

    title = " ".join(part for part in (fields["vendor"], fields["name"]) if part) or f"Spool #{fields['id']}"
    subtitle_parts = [fields["material"]]
    if fields["remaining_weight"] is not None:
        subtitle_parts.append(f"{fields['remaining_weight']:.0f}g left")
    else:
        subtitle_parts.append(f"#{fields['id']}")
    subtitle = " · ".join(part for part in subtitle_parts if part)

    title_font = _fit_font(draw, title, text_width, content_height * 0.6, start_size=round(content_height * 0.55))
    subtitle_font = _fit_font(
        draw, subtitle, text_width, content_height * 0.35, start_size=round(content_height * 0.32)
    )

    title_width, title_height = _text_size(draw, title, title_font)
    subtitle_width, subtitle_height = _text_size(draw, subtitle, subtitle_font)
    total_text_height = title_height + subtitle_height + 4
    text_top = margin + max((content_height - total_text_height) // 2, 0)

    draw.text((text_left, text_top), title, font=title_font, fill=FOREGROUND)
    draw.text((text_left, text_top + title_height + 4), subtitle, font=subtitle_font, fill=FOREGROUND)

    return img
