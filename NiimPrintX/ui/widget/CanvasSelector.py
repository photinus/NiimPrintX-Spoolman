import tkinter as tk
from tkinter import ttk

from PIL import ImageTk

from .CanvasOperation import CanvasOperation
from ..component.DesignStore import load_design, save_design
from NiimPrintX.nimmy.canvas_geometry import label_geometry

PREVIEW_TAG = "static_preview"


class CanvasSelector:
    def __init__(self, parent, config, text_op, img_op):
        self.parent = parent
        self.config = config
        self.frame = ttk.Frame(parent)
        self.canvas_op = CanvasOperation(config, text_op, img_op)
        self._preview_photo = None
        self.create_widgets()

    def create_widgets(self):
        device_label = tk.Label(self.frame, text="Device")
        device_label.pack(side=tk.LEFT, padx=10)
        saved_device = self.config.settings.get("device", "d110")
        self.selected_device = tk.StringVar(value=saved_device.upper())
        device_option = ttk.Combobox(self.frame, textvariable=self.selected_device,
                                     values=list(map(lambda x: x.upper(), self.config.label_sizes.keys())),
                                     state="readonly")
        device_option.pack(side=tk.LEFT, padx=10)
        device_option.bind("<<ComboboxSelected>>", self.update_device_label_size)
        label_size_label = tk.Label(self.frame, text="Label size")
        label_size_label.pack(side=tk.LEFT, padx=10)
        self.selected_label_size = tk.StringVar()
        self.label_size_option = ttk.Combobox(self.frame, textvariable=self.selected_label_size,
                                              state="readonly")
        self.update_device_label_size()
        self.label_size_option.pack(side=tk.LEFT, padx=10)
        self.label_size_option.bind("<<ComboboxSelected>>", self.update_canvas_size)
        self.update_canvas_size()
        self.frame.pack(side=tk.LEFT)

        # print_button = tk.Button(self.frame, text="Print")
        # print_button.pack(side=tk.RIGHT, padx=10)

    def update_device_label_size(self, event=None):
        if self.config.current_label_size:
            save_design(self.config)
        device = self.selected_device.get().lower()
        if device:
            label_sizes = list(self.config.label_sizes[device]['size'].keys())
            self.config.device = device
        else:
            label_sizes = []
        self.label_size_option['values'] = label_sizes
        if label_sizes:
            saved_label_size = self.config.settings.get("label_size")
            if saved_label_size in label_sizes:
                self.selected_label_size.set(saved_label_size)
            else:
                self.label_size_option.current(0)
        else:
            self.selected_label_size.set('')
        self.update_canvas_size()

    def update_canvas_size(self, event=None, restore_design=True):
        """Update the canvas size based on the selected label size."""
        previous_device = self.config.device
        previous_label_size = self.config.current_label_size
        if event is not None and previous_label_size:
            save_design(self.config, previous_device, previous_label_size)

        self.config.device = self.selected_device.get().lower()
        self.config.current_label_size = self.selected_label_size.get()
        self.config.settings["device"] = self.config.device
        self.config.settings["label_size"] = self.config.current_label_size
        self.config.save_settings()
        label_width_mm, label_height_mm = self.config.label_sizes[self.config.device]['size'][self.config.current_label_size]
        print_dpi = self.config.label_sizes[self.config.device]["print_dpi"]

        geometry = label_geometry(label_width_mm, label_height_mm, print_dpi)
        self.bounding_box_width = geometry["bbox_width"]
        self.bounding_box_height = geometry["bbox_height"]
        self.canvas_width = geometry["canvas_width"]
        self.canvas_height = geometry["canvas_height"]

        self.print_area_width = self.bounding_box_width - self.mm_to_pixels(2)
        self.print_area_height = self.bounding_box_height - self.mm_to_pixels(4)

        # If a canvas exists, destroy it before creating a new one
        if hasattr(self.config, "canvas") and self.config.canvas is not None:
            self.config.canvas.destroy()
            self.config.text_items = {}
            self.config.image_items = {}
            self.config.current_selected = None
            self.config.current_selected_image = None

        # Create a new canvas with updated dimensions
        self.config.canvas = tk.Canvas(
            self.config.frames["top_frame"], width=self.canvas_width, height=self.canvas_height,
            highlightthickness=0, bg="lightgray"
        )
        self.config.canvas.pack(padx=0, pady=0)

        # Create a centered bounding box
        self.bbox_left = geometry["bbox_left"]
        self.bbox_top = geometry["bbox_top"]
        x_center = self.canvas_width // 2
        y_center = self.canvas_height // 2
        self._preview_photo = None  # old canvas (and any preview overlay on it) is gone

        self.config.bounding_box = self.config.canvas.create_rectangle(
            self.bbox_left,
            self.bbox_top,
            self.bbox_left + self.bounding_box_width,
            self.bbox_top + self.bounding_box_height,
            outline="blue",
            width=1,
            # dash=(4, 4),
            fill="white",
            tags="label_box"
        )

        self.config.print_area_box = self.config.canvas.create_rectangle(
            x_center - self.print_area_width // 2,
            y_center - self.print_area_height // 2,
            x_center + self.print_area_width // 2,
            y_center + self.print_area_height // 2,
            outline="red",
            width=1,
            dash=(4, 4),
            fill="white",
            tags="label_box"
        )

        self.config.canvas.bind("<Button-1>", self.canvas_op.canvas_click_handler)
        if restore_design:
            load_design(self.config, self.parent.master, self.config.device, self.config.current_label_size)

    def show_static_preview(self, image):
        """Overlay a flattened, non-editable preview image (e.g. a rendered Spoolman
        label) on the canvas at the label's position -- used by the Spoolman tab so it
        can reuse the same large canvas the Text/Icon tabs use instead of a side panel.
        Doesn't touch config.text_items/image_items, so the underlying editable design
        is untouched and reappears as soon as the overlay is cleared."""
        if not self.config.canvas:
            return
        self.config.canvas.delete(PREVIEW_TAG)
        self._preview_photo = ImageTk.PhotoImage(image)
        self.config.canvas.create_image(
            self.bbox_left, self.bbox_top, image=self._preview_photo, anchor="nw", tags=PREVIEW_TAG
        )
        self.config.canvas.tag_raise(PREVIEW_TAG)

    def clear_static_preview(self):
        if self.config.canvas:
            self.config.canvas.delete(PREVIEW_TAG)
        self._preview_photo = None

    def set_label_size(self, label_size):
        label_sizes = self.label_size_option["values"]
        if label_size not in label_sizes:
            return False
        if self.config.current_label_size:
            save_design(self.config)
        self.selected_label_size.set(label_size)
        self.update_canvas_size()
        return True

    def mm_to_pixels(self, mm):
        inches = mm / 25.4
        return int(inches * self.config.label_sizes[self.config.device]["print_dpi"])
