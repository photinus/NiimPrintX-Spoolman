import tkinter as tk
import tkinter.messagebox as messagebox
from PIL import ImageTk

from NiimPrintX.nimmy.text_render import render_text_image
from ..component.DesignStore import save_design
from devtools import debug


class TextOperation:
    def __init__(self, parent, config):
        self.parent = parent
        self.config = config

    # Function to add text to canvas and make it draggable
    def create_text_image(self, font_props, text):
        image = render_text_image(self.config.os_system, font_props, text)
        return ImageTk.PhotoImage(image)

    def add_text_to_canvas(self):
        # Get the current text in the content_entry Text widget
        text = self.parent.content_entry.get("1.0", "end-1c")

        font_obj, font_props = self.parent.get_font_properties()
        if not text:
            messagebox.showerror("Error", f"Please enter text in content to add.")
            return

        tk_image = self.create_text_image(font_props, text)
        text_id = self.config.canvas.create_image(0, 0, image=tk_image, anchor="nw", )

        self.config.canvas.tag_bind(text_id, "<Button-1>", lambda event, tid=text_id: self.select_text(event, tid))
        self.config.text_items[text_id] = {
            "font_props": font_props,
            "font_image": tk_image,
            "content": text,
            "handle": None,
            "bbox": None,

        }
        save_design(self.config)

    def delete_text(self):
        if self.config.current_selected:
            self.config.canvas.delete(self.config.current_selected)
            self.config.canvas.delete(self.config.text_items[self.config.current_selected]['bbox'])
            self.config.canvas.delete(self.config.text_items[self.config.current_selected]['handle'])
            del self.config.text_items[self.config.current_selected]
            self.config.current_selected = None
            self.parent.add_button.config(text="Add", command=self.add_text_to_canvas)
            save_design(self.config)

    def select_text(self, event, text_id):
        self.deselect_text()
        self.config.current_selected = text_id
        self.update_widgets(text_id)
        self.draw_bounding_box(event, text_id)

    def update_widgets(self, text_id):
        font_prop = self.config.text_items[text_id]['font_props']
        text = self.config.text_items[text_id]['content']

        self.parent.content_entry.delete("1.0", tk.END)
        self.parent.content_entry.insert("1.0", text)

        self.parent.font_family_dropdown.set(font_prop["family"])
        # self.parent.font_dropdown.set(font_prop["font"])
        self.parent.size_var.set(font_prop["size"])
        self.parent.kerning_var.set(font_prop["kerning"])

        if font_prop["slant"] == "roman":
            self.parent.italic_var.set(False)
        else:
            self.parent.italic_var.set(True)

        if font_prop["weight"] == "normal":
            self.parent.bold_var.set(False)
        else:
            self.parent.bold_var.set(True)

        if not font_prop["underline"]:
            self.parent.underline_var.set(False)
        else:
            self.parent.underline_var.set(True)

        self.parent.add_button.config(text="Update", command=lambda t_id=text_id: self.update_canvas_text(t_id))

    def update_canvas_text(self, text_id):
        text = self.parent.content_entry.get("1.0", "end-1c")
        self.config.text_items[text_id]['content'] = text
        font_props = self.config.text_items[text_id]['font_props']
        tk_image = self.create_text_image(font_props, text)
        self.config.canvas.itemconfig(text_id, image=tk_image)
        self.config.text_items[text_id]['font_image'] = tk_image
        self.update_bbox_and_handle(text_id)
        save_design(self.config)

    def draw_bounding_box(self, event, text_id):
        bbox = self.config.canvas.create_rectangle(self.config.canvas.bbox(text_id),
                                                   outline="blue", width=2, tags="bounding_box")
        handle = self.config.canvas.create_oval(self.config.canvas.bbox(text_id)[2] - 5,
                                                self.config.canvas.bbox(text_id)[3] - 5,
                                                self.config.canvas.bbox(text_id)[2] + 5,
                                                self.config.canvas.bbox(text_id)[3] + 5,
                                                outline="blue", fill="gray")
        self.config.text_items[text_id].update({
            "bbox": bbox,
            "handle": handle,
            "initial_x": event.x,
            "initial_y": event.y,
        })

        self.config.canvas.tag_bind(text_id, "<Button1-Motion>", lambda e, tid=text_id: self.move_text(e, tid))
        self.config.canvas.tag_bind(text_id, "<ButtonRelease-1>", lambda e: save_design(self.config))
        self.config.canvas.tag_bind(handle, "<Button1-Motion>", lambda e, tid=text_id: self.resize_text(e, tid))
        self.config.canvas.tag_bind(handle, "<Button-1>", lambda e: self.start_resize(e, text_id))
        self.config.canvas.tag_bind(handle, "<ButtonRelease-1>", lambda e: save_design(self.config))

    def move_text(self, event, text_id):
        dx = event.x - self.config.text_items[text_id]["initial_x"]
        dy = event.y - self.config.text_items[text_id]["initial_y"]
        self.config.canvas.move(text_id, dx, dy)
        self.config.canvas.move(self.config.text_items[text_id]['bbox'], dx, dy)
        self.config.canvas.move(self.config.text_items[text_id]['handle'], dx, dy)
        self.config.text_items[text_id]["initial_x"] = event.x
        self.config.text_items[text_id]["initial_y"] = event.y

    def start_resize(self, event, text_id):
        self.config.text_items[text_id]['initial_x'] = event.x
        self.config.text_items[text_id]['initial_y'] = event.y
        self.config.text_items[text_id]['initial_size'] = self.config.text_items[text_id]['font_props']['size']

    def resize_text(self, event, text_id):
        dy = event.y - self.config.text_items[text_id]['initial_y']
        new_size = max(8, self.config.text_items[text_id]['initial_size'] + dy // 10)
        tk_image = self.create_text_image(self.config.text_items[text_id]["font_props"],
                                          self.config.text_items[text_id]['content'])
        self.config.canvas.itemconfig(text_id, image=tk_image)
        self.config.text_items[text_id]['font_image'] = tk_image
        self.config.text_items[text_id]["font_props"]['size'] = new_size
        self.update_bbox_and_handle(text_id)

        self.parent.size_var.set(new_size)

    def update_bbox_and_handle(self, text_id):
        bbox_coords = self.config.canvas.bbox(text_id)
        self.config.canvas.coords(self.config.text_items[text_id]["bbox"], bbox_coords)
        self.config.canvas.coords(
            self.config.text_items[text_id]["handle"],
            bbox_coords[2] - 5,
            bbox_coords[3] - 5,
            bbox_coords[2] + 5,
            bbox_coords[3] + 5
        )

    def deselect_text(self):
        if self.config.current_selected:
            self.delete_bounding_box(self.config.current_selected)
            self.config.current_selected = None
            self.parent.add_button.config(text="Add", command=self.add_text_to_canvas)

    def delete_bounding_box(self, text_id):
        if 'bbox' in self.config.text_items[text_id]:
            self.config.canvas.delete(self.config.text_items[text_id]['bbox'])
            self.config.canvas.delete(self.config.text_items[text_id]['handle'])
