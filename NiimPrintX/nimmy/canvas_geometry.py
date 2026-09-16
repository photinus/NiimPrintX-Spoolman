"""Canvas <-> label pixel geometry, shared between the live Tkinter canvas
(CanvasSelector) and the headless Spoolman template renderer.

The canvas centers a label-sized bounding box inside extra padding (so items can be
dragged slightly outside the label edge while designing). Anything reading saved
canvas-absolute item coordinates back out as label-relative pixels needs this same
padding/centering math -- kept here once so it can't drift between the two.
"""

PADDING = 150  # matches CanvasSelector's original inline padding


def mm_to_pixels(mm, print_dpi):
    inches = mm / 25.4
    return int(inches * print_dpi)


def label_geometry(width_mm, height_mm, print_dpi):
    """Return the canvas size and the label bounding box's offset/size within it."""
    bbox_width = mm_to_pixels(width_mm, print_dpi)
    bbox_height = mm_to_pixels(height_mm, print_dpi)
    canvas_width = bbox_width + PADDING
    canvas_height = bbox_height + PADDING
    x_center = canvas_width // 2
    y_center = canvas_height // 2
    return {
        "canvas_width": canvas_width,
        "canvas_height": canvas_height,
        "bbox_left": x_center - bbox_width // 2,
        "bbox_top": y_center - bbox_height // 2,
        "bbox_width": bbox_width,
        "bbox_height": bbox_height,
    }
