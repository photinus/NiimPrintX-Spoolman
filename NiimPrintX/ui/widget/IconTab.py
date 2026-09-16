import tkinter as tk
from tkinter import ttk
from tkinter import filedialog
import tkinter.messagebox as messagebox

from .ImageOperation import ImageOperation
from .TabbedIconGrid import TabbedIconGrid
from ..component import theme
from ..component.RoundedButton import RoundedButton

class IconTab:
    def __init__(self, parent, config):
        self.parent = parent
        self.config = config
        self.frame = tk.Frame(parent, bg=theme.BG_CARD, padx=20, pady=20)
        self.image_op = ImageOperation(config)
        self.create_widgets()


    def create_widgets(self):
        default_bg = theme.BG_CARD
        tk.Label(self.frame, text="Icon", bg=default_bg, fg=theme.TEXT_PRIMARY,
                 font=theme.FONT_SECTION_TITLE).pack(anchor='w', pady=(0, 14))

        button_frame = tk.Frame(self.frame, bg=default_bg)
        button_frame.pack(fill='x', pady=(0, 12))
        load_image = RoundedButton(button_frame, text="Add image", variant="primary", bg=default_bg,
                                   command=self.import_image)
        delete_image = RoundedButton(button_frame, text="Delete", variant="outline", bg=default_bg,
                                     command=self.image_op.delete_image)
        load_image.pack(side=tk.LEFT)
        delete_image.pack(side=tk.LEFT, padx=(8, 0))

        # Create the TabbedIconGrid below the buttons
        tabbed_icon_grid = TabbedIconGrid(
            self.frame, self.config.icon_folder, columns=4,
            on_icon_selected=lambda sub_path: self.image_op.load_image(f"{self.config.icon_folder}/{sub_path}")
        )
        tabbed_icon_grid.pack(fill='both', expand=True)


    def import_image(self):
        """Load an image into the canvas."""
        file_path = filedialog.askopenfilename(filetypes=[("Image Files", "*.png *.jpg *.jpeg *.bmp *.gif")])

        if not file_path:
            return
        self.image_op.load_image(file_path)

    def get_image_operation(self):
        return self.image_op

