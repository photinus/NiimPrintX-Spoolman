"""Recent-labels history: a small "what did I just print" list, shown in the
sidebar and recalled through the existing print-preview popup.

Every successful print (Design canvas or Spoolman) is snapshotted as the flat
PNG that was actually sent to the printer, plus a short display name and the
device/label-size it was printed at. Recalling an entry just reopens that PNG
in the normal print-preview dialog -- it isn't a full undo/version history of
editable text/icon items, just a fast way to reprint something recent.
"""

import json
import os
import time
import uuid

from PIL import Image

INDEX_FILENAME = "recent_labels.json"
IMAGE_SUBDIR = "recent"
MAX_ENTRIES = 20


def _index_path(config):
    return os.path.join(config.cache_dir, INDEX_FILENAME)


def _image_dir(config):
    path = os.path.join(config.cache_dir, IMAGE_SUBDIR)
    os.makedirs(path, exist_ok=True)
    return path


def list_recent_labels(config):
    """Newest-first list of {id, name, device, label_size, timestamp, image,
    _image_path}. `_image_path` is resolved to an absolute path here so
    callers (e.g. the sidebar) don't need to know the on-disk layout."""
    try:
        with open(_index_path(config), "r", encoding="utf-8") as f:
            entries = json.load(f)
    except (OSError, json.JSONDecodeError):
        return []
    image_dir = _image_dir(config)
    for entry in entries:
        entry["_image_path"] = os.path.join(image_dir, entry.get("image", ""))
    return entries


def _save_index(config, entries):
    # entries may carry the derived "_image_path" that list_recent_labels()
    # attaches -- never persist it, since it's an absolute path recomputed
    # from `image` on every read (and would go stale if cache_dir moved).
    on_disk = [{k: v for k, v in entry.items() if not k.startswith("_")} for entry in entries]
    with open(_index_path(config), "w", encoding="utf-8") as f:
        json.dump(on_disk, f, indent=2)


def add_recent_label(config, image, name, device=None, label_size=None, limit=MAX_ENTRIES):
    """Save `image` (a PIL Image) as a new most-recent entry and prune old ones."""
    entries = list_recent_labels(config)
    image_name = f"{uuid.uuid4().hex}.png"
    image.convert("RGB").save(os.path.join(_image_dir(config), image_name), format="PNG")

    entries.insert(0, {
        "id": uuid.uuid4().hex,
        "name": (name or "Label").strip()[:60],
        "device": device,
        "label_size": label_size,
        "timestamp": time.time(),
        "image": image_name,
    })

    while len(entries) > limit:
        dropped = entries.pop()
        dropped_path = os.path.join(_image_dir(config), dropped.get("image", ""))
        if os.path.exists(dropped_path):
            os.remove(dropped_path)

    _save_index(config, entries)
    return entries


def load_recent_label_image(config, entry):
    path = entry.get("_image_path") or os.path.join(_image_dir(config), entry.get("image", ""))
    if not os.path.exists(path):
        return None
    return Image.open(path).copy()


def load_thumbnail(entry, size):
    """Small preview of a recent-label entry for the sidebar row, scaled to fit
    `size` (w, h) while keeping aspect ratio. `entry` must carry the absolute
    `_image_path` that `list_recent_labels` attaches."""
    path = entry.get("_image_path")
    if not path or not os.path.exists(path):
        return None
    image = Image.open(path).convert("RGB")
    image.thumbnail(size, Image.Resampling.LANCZOS)
    return image
