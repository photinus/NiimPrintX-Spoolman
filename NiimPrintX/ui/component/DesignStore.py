import base64
import io
import os
import pickle
import re

from PIL import Image, ImageTk


def design_path(config, device=None, label_size=None, kind=None):
    device = device or config.device
    label_size = label_size or config.current_label_size
    if not device or not label_size:
        return None
    kind = kind or getattr(config, "design_kind", "design")
    safe_label_size = re.sub(r"[^A-Za-z0-9_.-]+", "_", label_size).strip("_")
    suffix = "" if kind == "design" else f".{kind}"
    return os.path.join(config.design_dir, f"{device}_{safe_label_size}{suffix}.niim")


def serialize_design(config):
    data = {
        "device": config.device,
        "current_label_size": config.current_label_size,
        "text": {},
        "image": {}
    }

    for text_id, properties in config.text_items.items():
        font_image = ImageTk.getimage(properties["font_image"])
        with io.BytesIO() as buffer:
            font_image.save(buffer, format="PNG")
            font_img_str = base64.b64encode(buffer.getvalue()).decode("utf-8")

        data["text"][str(text_id)] = {
            "content": properties["content"],
            "coords": config.canvas.coords(text_id),
            "font_props": properties["font_props"],
            "font_image": font_img_str
        }

    for image_id, properties in config.image_items.items():
        resized_image = ImageTk.getimage(properties["image"])
        with io.BytesIO() as buffer:
            resized_image.save(buffer, format="PNG")
            resize_img_str = base64.b64encode(buffer.getvalue()).decode("utf-8")

        with io.BytesIO() as buffer:
            properties["original_image"].save(buffer, format="PNG")
            original_img_str = base64.b64encode(buffer.getvalue()).decode("utf-8")

        data["image"][str(image_id)] = {
            "image": resize_img_str,
            "original_image": original_img_str,
            "coords": config.canvas.coords(image_id),
            "qr": bool(properties.get("qr"))
        }

    return data


def save_design(config, device=None, label_size=None, kind=None):
    path = design_path(config, device, label_size, kind)
    if not path or not config.canvas:
        return
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "wb") as design:
        pickle.dump(serialize_design(config), design)


def read_design_data(config, device=None, label_size=None, kind=None):
    """Read a saved design's raw dict (text/image items + coords) without touching the
    live canvas -- used for headless rendering, e.g. the Spoolman template renderer."""
    path = design_path(config, device, label_size, kind)
    if not path or not os.path.exists(path):
        return None
    with open(path, "rb") as design:
        return pickle.load(design)


def load_design(config, root, device=None, label_size=None, kind=None):
    data = read_design_data(config, device, label_size, kind)
    if data is None:
        return False

    config.text_items = {}
    config.image_items = {}

    for item_data in data.get("text", {}).values():
        font_img_data = base64.b64decode(item_data["font_image"])
        font_image = Image.open(io.BytesIO(font_img_data))
        font_img_tk = ImageTk.PhotoImage(font_image)
        text_id = config.canvas.create_image(item_data["coords"][0], item_data["coords"][1],
                                             image=font_img_tk, anchor="nw")
        config.canvas.tag_bind(text_id, "<Button-1>",
                               lambda event, tid=text_id: root.text_tab.text_op.select_text(event, tid))
        config.canvas.tag_bind(text_id, "<ButtonRelease-1>", lambda event: save_design(config))
        config.text_items[text_id] = {
            "font_image": font_img_tk,
            "font_props": item_data["font_props"],
            "content": item_data["content"],
            "handle": None,
            "bbox": None
        }

    for item_data in data.get("image", {}).values():
        original_image_data = base64.b64decode(item_data["original_image"])
        original_image = Image.open(io.BytesIO(original_image_data))
        image_data = base64.b64decode(item_data["image"])
        image = Image.open(io.BytesIO(image_data))
        img_tk = ImageTk.PhotoImage(image)
        image_id = config.canvas.create_image(item_data["coords"][0], item_data["coords"][1],
                                              image=img_tk, anchor="nw")
        config.image_items[image_id] = {
            "image": img_tk,
            "original_image": original_image,
            "bbox": None,
            "handle": None,
            "qr": bool(item_data.get("qr"))
        }
        config.canvas.tag_bind(image_id, "<Button-1>",
                               lambda event, img_id=image_id: root.icon_tab.image_op.select_image(event, img_id))
        config.canvas.tag_bind(image_id, "<Button1-Motion>",
                               lambda event, img_id=image_id: root.icon_tab.image_op.move_image(event, img_id))
        config.canvas.tag_bind(image_id, "<ButtonRelease-1>", lambda event: save_design(config))

    return True
