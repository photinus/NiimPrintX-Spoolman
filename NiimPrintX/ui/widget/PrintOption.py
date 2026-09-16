import asyncio
import io
import os
import tkinter as tk
from tkinter import ttk
from tkinter import filedialog
from tkinter import messagebox
from PIL import Image, ImageTk
import cairo
import tempfile

from .PrinterOperation import PrinterOperation
from NiimPrintX.nimmy.printer import EXTENDED_PROTOCOL_MODELS

from devtools import debug


class PrintOption:
    def __init__(self, root, parent, config):
        self.root = root
        self.parent = parent
        self.config = config
        self.frame = ttk.Frame(parent)
        self.preview_source = "canvas"
        self.preview_source_image = None
        self.create_widgets()
        self.print_op = PrinterOperation(self.config)
        self.check_heartbeat()

    def check_heartbeat(self):
        asyncio.run_coroutine_threadsafe(self.schedule_heartbeat(), self.root.async_loop)

    async def schedule_heartbeat(self):
        while True:
            # debug(self.config.printer_connected, self.config.print_job)
            if self.print_op.printer and not self.config.print_job:
                # debug("connected")
                state, hb = await self.print_op.heartbeat()
                self.root.after(0, lambda: self.update_status(state, hb))
            elif not self.config.print_job:
                # debug("not connected")
                self.root.after(0, lambda: self.update_status(False))
            await asyncio.sleep(5)

    def update_status(self, connected=False, hb_data=None):
        # debug(hb_data)
        # debug(f"Heartbeat received: {connected}")
        self.config.printer_connected = connected
        if not connected and self.connect_button["state"] != tk.DISABLED:
            self.connect_button.config(text="Connect")
            self.connect_button.config(state=tk.NORMAL)
        self.root.after(0, lambda: self.root.status_bar.update_status(connected))

    def create_widgets(self):
        print_button = tk.Button(self.parent, text="Print", command=self.display_print)
        print_button.pack(side=tk.RIGHT, padx=10)
        save_image_button = tk.Button(self.parent, text="Save Image", command=self.save_image)
        save_image_button.pack(side=tk.RIGHT, padx=10)
        self.connect_button = tk.Button(self.parent, text="Connect", command=self.printer_connect)
        self.connect_button.pack(side=tk.RIGHT, padx=10)

    def printer_connect(self):
        self.connect_button.config(state=tk.DISABLED)
        if not self.config.printer_connected:
            future = asyncio.run_coroutine_threadsafe(
                self.print_op.printer_connect(self.config.device), self.root.async_loop
            )
            future.add_done_callback(lambda f: self.root.after(0, lambda: self._update_device_status(f)))
        else:
            future = asyncio.run_coroutine_threadsafe(
                self.print_op.printer_disconnect(), self.root.async_loop
            )
            future.add_done_callback(lambda f: self.root.after(0, lambda: self._update_device_status(f)))

    def _update_device_status(self, future):
        result = future.result()
        if self.config.printer_connected:
            self.connect_button.config(text="Disconnect")
            self.connect_button.config(state=tk.NORMAL)
            self.detect_label_size()
        else:
            self.connect_button.config(text="Connect")
            self.connect_button.config(state=tk.NORMAL)
            result = False
            if self.print_op.last_error:
                messagebox.showerror("Error", self.print_op.last_error)
        self.root.after(0, lambda: self.root.status_bar.update_status(result))

    def detect_label_size(self):
        future = asyncio.run_coroutine_threadsafe(
            self.print_op.get_label_size_from_rfid(), self.root.async_loop
        )
        future.add_done_callback(lambda f: self.root.after(0, lambda: self._update_label_size(f)))

    def _update_label_size(self, future):
        try:
            label_size = future.result()
        except Exception:
            return
        if label_size:
            self.root.canvas_selector.set_label_size(label_size)

    def display_print(self):
        # Export to PNG and display it in a pop-up window
        if self.config.os_system == "Windows":
            # Windows-specific logic using tempfile.mkstemp()
            fd, tmp_file_path = tempfile.mkstemp(suffix=".png")
            try:
                self.export_to_png(tmp_file_path)  # Save to file
                self.display_image_in_popup(tmp_file_path)  # Display in pop-up window
            finally:
                os.close(fd)  # Close the file descriptor
                os.remove(tmp_file_path)  # Remove the temporary file
        else:
            with tempfile.NamedTemporaryFile(suffix=".png") as tmp_file:
                self.export_to_png(tmp_file.name)  # Save to file
                self.display_image_in_popup(tmp_file.name)

    def save_image(self):
        options = {
            'defaultextension': '.png',
            'filetypes': [('PNG files', '*.png')],
            'initialfile': 'niimprintx.png',  # Specify an initial file name
            'title': 'Save as PNG'
        }
        # Open the save as dialog and get the selected file name
        file_path = filedialog.asksaveasfilename(**options)
        if file_path:
            self.export_to_png(file_path)
            self.display_image_in_popup(file_path)

    def mm_to_pixels(self, mm):
        inches = mm / 25.4
        return int(inches * self.config.label_sizes[self.config.device]["print_dpi"])

    def print_settings_key(self):
        label_size = self.config.current_label_size or self.config.settings.get("label_size", "")
        return f"{self.config.device}:{label_size}"

    def get_print_settings(self):
        max_density = self.config.label_sizes[self.config.device]["density"]
        defaults = {
            "density": min(3, max_density),
            "copies": 1,
            "horizontal_offset": 0.0,
            "vertical_offset": 0.0,
        }
        saved_settings = self.config.settings.get("print", {}).get(self.print_settings_key(), {})
        defaults.update(saved_settings)
        defaults["density"] = max(1, min(self.safe_int(defaults["density"], 3), max_density))
        defaults["copies"] = max(1, min(self.safe_int(defaults["copies"], 1), 100))
        defaults["horizontal_offset"] = max(-5.0, min(self.safe_float(defaults["horizontal_offset"], 0.0), 5.0))
        defaults["vertical_offset"] = max(-5.0, min(self.safe_float(defaults["vertical_offset"], 0.0), 5.0))
        return defaults

    def save_print_settings(self):
        if not all(hasattr(self, attr) for attr in ("print_density", "print_copy", "horizontal_offset", "vertical_offset")):
            return
        current_settings = self.get_print_settings()
        print_settings = self.config.settings.setdefault("print", {})
        print_settings[self.print_settings_key()] = {
            "density": self.read_print_var(self.print_density, current_settings["density"], int),
            "copies": self.read_print_var(self.print_copy, current_settings["copies"], int),
            "horizontal_offset": self.read_print_var(
                self.horizontal_offset, current_settings["horizontal_offset"], float
            ),
            "vertical_offset": self.read_print_var(
                self.vertical_offset, current_settings["vertical_offset"], float
            ),
        }
        self.config.save_settings()

    def read_print_var(self, var, fallback, converter):
        try:
            return converter(var.get())
        except (tk.TclError, TypeError, ValueError):
            return fallback

    def safe_int(self, value, fallback):
        try:
            return int(value)
        except (TypeError, ValueError):
            return fallback

    def safe_float(self, value, fallback):
        try:
            return float(value)
        except (TypeError, ValueError):
            return fallback

    def export_to_png(self, output_filename=None, horizontal_offset=0.0, vertical_offset=0.0):
        width = self.config.canvas.winfo_reqwidth()
        height = self.config.canvas.winfo_reqheight()

        horizontal_offset_pixels = self.mm_to_pixels(horizontal_offset)
        vertical_offset_pixels = self.mm_to_pixels(vertical_offset)

        x1, y1, x2, y2 = self.config.canvas.bbox(self.config.bounding_box)

        x1 += horizontal_offset_pixels
        y1 += vertical_offset_pixels
        x2 += horizontal_offset_pixels
        y2 += vertical_offset_pixels

        bbox_width = x2 - x1
        bbox_height = y2 - y1

        surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, width, height)
        ctx = cairo.Context(surface)
        ctx.set_source_rgb(1, 1, 1)  # White background
        ctx.paint()

        # Drawing images (if any)
        if self.config.image_items:
            for img_id, img_props in self.config.image_items.items():
                coords = self.config.canvas.coords(img_id)
                resized_image = ImageTk.getimage(img_props["image"])
                with io.BytesIO() as buffer:
                    resized_image.save(buffer, format="PNG")
                    buffer.seek(0)
                    img_surface = cairo.ImageSurface.create_from_png(buffer)
                ctx.set_source_surface(img_surface, coords[0], coords[1])
                ctx.paint()

        # Drawing text items
        if self.config.text_items:
            for text_id, text_props in self.config.text_items.items():
                coords = self.config.canvas.coords(text_id)
                resized_image = ImageTk.getimage(text_props["font_image"])
                with io.BytesIO() as buffer:
                    resized_image.save(buffer, format="PNG")
                    buffer.seek(0)
                    img_surface = cairo.ImageSurface.create_from_png(buffer)
                ctx.set_source_surface(img_surface, coords[0], coords[1])
                ctx.paint()

        # Create a cropped surface to save
        cropped_surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, int(bbox_width), int(bbox_height))
        cropped_ctx = cairo.Context(cropped_surface)
        cropped_ctx.set_source_surface(surface, -x1, -y1)
        cropped_ctx.paint()
        if output_filename:
            cropped_surface.write_to_png(output_filename)
        else:
            image_bytes = cropped_surface.get_data()
            img = Image.frombuffer("RGBA", (int(bbox_width), int(bbox_height)), image_bytes, "raw", "BGRA", 0, 1)

            return img

    def display_image_in_popup(self, filename):
        self.print_image = Image.open(filename)
        self.preview_source = "canvas"
        self._show_preview_popup()

    def show_image_preview(self, image):
        """Show the print preview/print dialog for an in-memory PIL image (e.g. a Spoolman label)."""
        self.print_image = image
        self.preview_source_image = image
        self.preview_source = "external"
        self._show_preview_popup()

    def _show_preview_popup(self):
        # Create a new Toplevel window
        popup = tk.Toplevel(self.root)
        popup.title("Preview Image")

        img_tk = ImageTk.PhotoImage(self.print_image)

        # Create a Label to display the image
        self.image_label = tk.Label(popup, image=img_tk)
        self.image_label.image = img_tk  # Keep a reference to avoid garbage collection
        self.image_label.grid(row=0, column=0, columnspan=4, padx=10, pady=10)

        print_settings = self.get_print_settings()

        option_frame = tk.Frame(popup)
        option_frame.grid(row=1, column=0, columnspan=4, padx=20, pady=10, sticky="ew")

        self.print_density = tk.IntVar()
        self.print_density.set(print_settings["density"])
        tk.Label(option_frame, text="Density").grid(row=0, column=0, padx=5, pady=5, sticky="e")
        density_slider = tk.Spinbox(option_frame,
                                    from_=1,
                                    to=self.config.label_sizes[self.config.device]['density'],
                                    textvariable=self.print_density,
                                    width=4,
                                    command=self.save_print_settings
                                    )
        density_slider.grid(row=0, column=1, padx=5, pady=5, sticky="w")
        density_slider.bind("<FocusOut>", lambda event: self.save_print_settings())
        density_slider.bind("<Return>", lambda event: self.save_print_settings())

        tk.Label(option_frame, text="Copies").grid(row=0, column=2, padx=20, pady=5, sticky="e")
        self.print_copy = tk.IntVar()
        self.print_copy.set(print_settings["copies"])
        print_copy_dropdown = tk.Spinbox(option_frame, from_=1, to=100,
                                         textvariable=self.print_copy,
                                         width=4,
                                         command=self.save_print_settings
                                         )
        print_copy_dropdown.grid(row=0, column=3, padx=5, pady=5, sticky="w")
        print_copy_dropdown.bind("<FocusOut>", lambda event: self.save_print_settings())
        print_copy_dropdown.bind("<Return>", lambda event: self.save_print_settings())

        offset_frame = tk.Frame(popup)
        offset_frame.grid(row=2, column=0, columnspan=4, padx=20, pady=10, sticky="ew")

        self.horizontal_offset = tk.DoubleVar()
        self.horizontal_offset.set(print_settings["horizontal_offset"])
        tk.Label(offset_frame, text="Horizontal\nOffset").grid(row=0, column=0, padx=2, pady=5, sticky="e")
        horizontal_offset_dropdown = tk.Spinbox(offset_frame,
                                                from_=-5,
                                                to=5,
                                                textvariable=self.horizontal_offset,
                                                increment=0.5, format="%.1f",
                                                width=4,
                                                command=self.update_image_offset
                                                )
        horizontal_offset_dropdown.grid(row=0, column=1, padx=2, pady=5, sticky="w")
        horizontal_offset_dropdown.bind("<FocusOut>", lambda event: self.update_image_offset())

        tk.Label(offset_frame, text="Vertical\nOffset").grid(row=0, column=2, padx=10, pady=5, sticky="e")
        self.vertical_offset = tk.DoubleVar()
        self.vertical_offset.set(print_settings["vertical_offset"])
        vertical_offset_dropdown = tk.Spinbox(offset_frame, from_=-5, to=5,
                                              textvariable=self.vertical_offset,
                                              increment=0.5, format="%.1f",
                                              width=4,
                                              command=self.update_image_offset
                                              )
        vertical_offset_dropdown.grid(row=0, column=3, padx=2, pady=5, sticky="w")
        vertical_offset_dropdown.bind("<FocusOut>", lambda event: self.update_image_offset())

        button_frame = tk.Frame(popup)
        button_frame.grid(row=3, column=0, columnspan=4, padx=20, pady=10, sticky="ew")

        self.print_button = tk.Button(button_frame, text="Print",
                                      command=self.print_current_label)
        self.print_button.grid(row=0, column=0, padx=5, pady=10, sticky="ew")

        close_button = tk.Button(button_frame, text="Close", command=lambda: self.close_print_popup(popup))
        close_button.grid(row=0, column=1, padx=5, pady=10, sticky="ew")

        # Ensure the buttons are evenly spaced
        button_frame.grid_columnconfigure(0, weight=1)
        button_frame.grid_columnconfigure(1, weight=1)

        # Ensure the frames are evenly spaced
        option_frame.grid_columnconfigure(1, weight=1)
        option_frame.grid_columnconfigure(3, weight=1)
        offset_frame.grid_columnconfigure(1, weight=1)
        offset_frame.grid_columnconfigure(3, weight=1)

        if print_settings["horizontal_offset"] or print_settings["vertical_offset"]:
            self.update_image_offset()

    def close_print_popup(self, popup):
        self.save_print_settings()
        popup.destroy()

    def update_image_offset(self):
        self.save_print_settings()
        print_settings = self.get_print_settings()
        horizontal_offset = print_settings["horizontal_offset"]
        vertical_offset = print_settings["vertical_offset"]
        if self.preview_source == "canvas":
            self.print_image = self.export_to_png(output_filename=None,
                                                  horizontal_offset=horizontal_offset,
                                                  vertical_offset=vertical_offset)
        else:
            self.print_image = self._offset_image(self.preview_source_image, horizontal_offset, vertical_offset)
        img_tk = ImageTk.PhotoImage(self.print_image)
        self.image_label.config(image=img_tk)
        self.image_label.image = img_tk
        self.print_button.config(command=self.print_current_label)

    def _offset_image(self, image, horizontal_offset_mm, vertical_offset_mm):
        """Shift an in-memory (non-canvas) preview image by the given mm offsets."""
        h_px = self.mm_to_pixels(horizontal_offset_mm)
        v_px = self.mm_to_pixels(vertical_offset_mm)
        shifted = Image.new(image.mode, image.size, "white")
        shifted.paste(image, (h_px, v_px))
        return shifted

    def print_current_label(self):
        print_settings = self.get_print_settings()
        self.print_label(self.print_image, print_settings["density"], print_settings["copies"])

    def print_label(self, image, density, quantity):
        self.save_print_settings()
        self.print_button.config(state=tk.DISABLED)
        self.config.print_job = True

        # D-series label presets are stored as (length, roll-width), which is backwards
        # from what SET_DIMENSION wants (rows=length taken from image.height), so those
        # models need the canvas image pre-rotated 90 degrees. B1 presets are stored as
        # (roll-width, length) already in the right order, so it must NOT be rotated here
        # -- rotating it swaps in the wrong axis and both matches what you're seeing
        # (sideways print, feed length wrong).
        if self.config.device not in EXTENDED_PROTOCOL_MODELS:
            image = image.rotate(-90, Image.NEAREST, expand=True)
        future = asyncio.run_coroutine_threadsafe(
            self.print_op.print(image, density, quantity), self.root.async_loop
        )
        future.add_done_callback(lambda f: self.root.after(0, lambda: self._print_handler(f)))

    def _print_handler(self, future):
        self.config.print_job = False
        result = future.result()
        if result:
            # debug("print", result)
            self.root.after(0, lambda: self.root.status_bar.update_status(result))
        self.print_button.config(state=tk.NORMAL)
