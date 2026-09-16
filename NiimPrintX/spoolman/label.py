"""Render a printable label image for a Spoolman spool record.

Styled after Spoolman's own spool QR card (vendor / name / material·id),
minus any color swatch -- NiimBot labels print on a monochrome thermal head,
so a color circle just dithers into a gray blob.
"""
from PIL import Image, ImageDraw, ImageFont

try:
    import qrcode
except ImportError:  # pragma: no cover - optional dependency
    qrcode = None

BACKGROUND = "white"
FOREGROUND = "black"

# A label must be at least this much wider than it is tall before the QR code and text
# go side-by-side; anything closer to square stacks the QR above the text instead.
LANDSCAPE_ASPECT_THRESHOLD = 1.5


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
    """Shrink a single line of text until it fits, or bottom out at min_size."""
    size = start_size
    font = _font(size)
    while size > min_size:
        font = _font(size)
        width, height = _text_size(draw, text, font)
        if width <= max_width and height <= max_height:
            break
        size -= 1
    return font


def _wrap_lines(draw, text, font, max_width):
    words = text.split()
    if not words:
        return [text]
    lines = []
    current = words[0]
    for word in words[1:]:
        candidate = f"{current} {word}"
        if _text_size(draw, candidate, font)[0] <= max_width:
            current = candidate
        else:
            lines.append(current)
            current = word
    lines.append(current)
    return lines


def _fit_wrapped(draw, text, max_width, max_height, start_size, min_size, max_lines):
    """Shrink + word-wrap text until it fits within max_lines and max_height."""
    size = start_size
    fallback = None
    while size >= min_size:
        font = _font(size)
        lines = _wrap_lines(draw, text, font, max_width)
        line_height = _text_size(draw, "Ag", font)[1]
        line_gap = max(1, round(line_height * 0.15))
        total_height = line_height * len(lines) + line_gap * max(0, len(lines) - 1)
        if len(lines) <= max_lines and total_height <= max_height:
            return font, lines, total_height
        fallback = (font, lines[:max_lines], line_height * max_lines)
        size -= 1
    return fallback if fallback else (_font(min_size), [text], _text_size(draw, text, _font(min_size))[1])


def _spool_fields(spool):
    filament = spool.get("filament") or {}
    vendor = filament.get("vendor") or {}
    return {
        "id": spool.get("id"),
        "vendor": vendor.get("name") or "",
        "name": filament.get("name") or "",
        "material": filament.get("material") or "",
    }


def _caption_text(fields):
    parts = [fields["material"]] if fields["material"] else []
    parts.append(f"#{fields['id']}")
    return " · ".join(parts)


def _build_qr_image(data, size_px):
    if qrcode is None or not data or size_px < 20:
        return None
    qr = qrcode.QRCode(border=1, box_size=10)
    qr.add_data(data)
    qr.make(fit=True)
    qr_image = qr.make_image(fill_color="black", back_color="white").convert("RGB")
    return qr_image.resize((size_px, size_px), Image.NEAREST)


def _place_qr(fields, base_url, content_box, landscape, margin):
    """Size and position the QR code for the given content box and layout orientation.

    Returns (qr_image_or_None, text_box) where text_box is (left, top, width, height)
    for whatever space remains for the text block.
    """
    content_left, content_top, content_width, content_height = content_box
    text_box = (content_left, content_top, content_width, content_height)

    if fields["id"] is None:
        return None, text_box

    if landscape:
        # Labels only reach this branch when they're clearly wider than tall, so the QR
        # can safely fill the content height without starving the text column.
        qr_size = min(content_height, round(content_width * 0.6))
    else:
        # Stacked layout: keep the QR to half the height so vendor/name/caption keep
        # enough vertical room to wrap instead of shrinking to near-nothing.
        qr_size = min(content_width, round(content_height * 0.5))

    qr_data = (
        f"{base_url.rstrip('/')}/spool/show/{fields['id']}"
        if base_url else f"spoolman:spool:{fields['id']}"
    )
    qr_image = _build_qr_image(qr_data, qr_size)
    if qr_image is None:
        return None, text_box

    qr_size = qr_image.size[0]
    if landscape:
        qr_pos = (content_left, content_top + (content_height - qr_size) // 2)
        text_left = content_left + qr_size + margin
        text_box = (text_left, content_top, max(content_left + content_width - text_left, 10), content_height)
    else:
        qr_pos = (content_left + (content_width - qr_size) // 2, content_top)
        text_top = content_top + qr_size + margin
        text_box = (content_left, text_top, content_width, max(content_top + content_height - text_top, 10))

    return (qr_image, qr_pos), text_box


def build_spool_label_image(spool, width_px, height_px, *, include_qr=True, base_url=None):
    """Render a spool as a label-sized PIL image, ready to hand to the printer pipeline.

    The layout adapts to the label's aspect ratio: clearly wide labels get a QR code
    beside the text, while square-ish or tall labels (e.g. a 40x30mm or 50x80mm B1 roll)
    stack the QR above the text instead -- a side-by-side layout on a near-square label
    leaves the QR eating most of the width and crams the text into a narrow strip.
    """
    fields = _spool_fields(spool)
    width_px = max(int(width_px), 1)
    height_px = max(int(height_px), 1)

    img = Image.new("RGB", (width_px, height_px), BACKGROUND)
    draw = ImageDraw.Draw(img)

    margin = max(2, round(min(width_px, height_px) * 0.08))
    content_left = margin
    content_top = margin
    content_width = max(width_px - 2 * margin, 1)
    content_height = max(height_px - 2 * margin, 1)
    # Side-by-side only pays off once the label is meaningfully wider than it is tall;
    # near-square labels (e.g. 40x30mm) read better with the QR stacked above the text.
    landscape = width_px >= height_px * LANDSCAPE_ASPECT_THRESHOLD

    qr_placement, (text_left, text_top, text_width, text_height) = (
        _place_qr(fields, base_url, (content_left, content_top, content_width, content_height), landscape, margin)
        if include_qr else (None, (content_left, content_top, content_width, content_height))
    )
    if qr_placement is not None:
        qr_image, qr_pos = qr_placement
        img.paste(qr_image, qr_pos)

    text_bottom = text_top + text_height
    gap = max(1, round(text_height * 0.05))
    y = text_top

    if fields["vendor"]:
        vendor_text = fields["vendor"].upper()
        vendor_font = _fit_font(
            draw, vendor_text, text_width, round(text_height * 0.16), start_size=round(text_height * 0.18)
        )
        draw.text((text_left, y), vendor_text, font=vendor_font, fill=FOREGROUND)
        y += _text_size(draw, vendor_text, vendor_font)[1] + gap

    caption = _caption_text(fields)
    caption_font = _fit_font(
        draw, caption, text_width, round(text_height * 0.16), start_size=round(text_height * 0.18)
    )
    caption_height = _text_size(draw, caption, caption_font)[1]

    reserved_bottom = caption_height + gap
    name_max_height = max(text_bottom - y - reserved_bottom, round(text_height * 0.25))

    name_text = fields["name"] or f"Spool #{fields['id']}"
    name_font, name_lines, _ = _fit_wrapped(
        draw, name_text, text_width, name_max_height,
        start_size=round(text_height * 0.32), min_size=max(8, round(text_height * 0.14)), max_lines=3,
    )
    for line in name_lines:
        draw.text((text_left, y), line, font=name_font, fill=FOREGROUND)
        y += _text_size(draw, line, name_font)[1] + max(1, round(gap * 0.5))

    y += gap
    draw.text((text_left, y), caption, font=caption_font, fill=FOREGROUND)

    return img
