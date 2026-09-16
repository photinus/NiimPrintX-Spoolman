"""Render a printable label image for a Spoolman spool record.

Styled after Spoolman's own spool QR card (vendor / name / material·id / a
remaining-weight bar), minus any color swatch -- NiimBot labels print on a
monochrome thermal head, so a color circle just dithers into a gray blob.
"""
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


def _remaining_percent(spool):
    remaining = spool.get("remaining_weight")
    initial = spool.get("initial_weight")
    if remaining is None or not initial:
        return None
    return max(0.0, min(100.0, (remaining / initial) * 100))


def _caption_text(fields):
    parts = [fields["material"]] if fields["material"] else []
    parts.append(f"#{fields['id']}")
    return " · ".join(parts)


def _draw_progress_bar(draw, box, percent):
    x1, y1, x2, y2 = box
    if x2 <= x1 or y2 <= y1:
        return
    radius = max(1, (y2 - y1) // 2)
    draw.rounded_rectangle(box, radius=radius, outline=FOREGROUND, width=1)
    if percent and percent > 0:
        fill_width = min(round((x2 - x1) * (percent / 100)), x2 - x1)
        fill_width = max(fill_width, y2 - y1)  # at least one full "pill" so the cap doesn't look clipped
        fill_width = min(fill_width, x2 - x1)
        draw.rounded_rectangle((x1, y1, x1 + fill_width, y2), radius=radius, fill=FOREGROUND)


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

    margin = max(2, round(height_px * 0.08))
    top = margin
    bottom = height_px - margin
    content_height = max(bottom - top, 1)

    text_left = margin
    text_right = width_px - margin

    if include_qr and fields["id"] is not None:
        qr_size = content_height
        qr_data = (
            f"{base_url.rstrip('/')}/spool/show/{fields['id']}"
            if base_url else f"spoolman:spool:{fields['id']}"
        )
        qr_image = _build_qr_image(qr_data, qr_size)
        if qr_image is not None:
            img.paste(qr_image, (margin, top))
            text_left += qr_size + margin

    text_width = max(text_right - text_left, 10)
    gap = max(1, round(content_height * 0.05))
    y = top

    if fields["vendor"]:
        vendor_text = fields["vendor"].upper()
        vendor_font = _fit_font(
            draw, vendor_text, text_width, round(content_height * 0.16), start_size=round(content_height * 0.18)
        )
        draw.text((text_left, y), vendor_text, font=vendor_font, fill=FOREGROUND)
        y += _text_size(draw, vendor_text, vendor_font)[1] + gap

    percent = _remaining_percent(spool)
    bar_height = max(3, round(content_height * 0.12)) if percent is not None else 0

    caption = _caption_text(fields)
    caption_font = _fit_font(
        draw, caption, text_width, round(content_height * 0.16), start_size=round(content_height * 0.18)
    )
    caption_height = _text_size(draw, caption, caption_font)[1]

    reserved_bottom = caption_height + gap + (bar_height + gap if bar_height else 0)
    name_max_height = max(bottom - y - reserved_bottom, round(content_height * 0.25))

    name_text = fields["name"] or f"Spool #{fields['id']}"
    name_font, name_lines, _ = _fit_wrapped(
        draw, name_text, text_width, name_max_height,
        start_size=round(content_height * 0.32), min_size=max(8, round(content_height * 0.14)), max_lines=3,
    )
    for line in name_lines:
        draw.text((text_left, y), line, font=name_font, fill=FOREGROUND)
        y += _text_size(draw, line, name_font)[1] + max(1, round(gap * 0.5))

    y += gap
    draw.text((text_left, y), caption, font=caption_font, fill=FOREGROUND)
    y += caption_height + gap

    if bar_height:
        bar_bottom = min(y + bar_height, bottom)
        _draw_progress_bar(draw, (text_left, y, text_right, bar_bottom), percent)

    return img
