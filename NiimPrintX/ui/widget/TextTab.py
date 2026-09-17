import tkinter as tk
from tkinter import ttk
from tkinter import font as tk_font
import tkinter.messagebox as messagebox

from .TextOperation import TextOperation
from ..component import theme
from ..component.FontList import fonts
from ..component.RoundedButton import RoundedButton

from devtools import debug


class TextTab:
    def __init__(self, parent, config):
        self.parent = parent
        self.config = config
        self.frame = tk.Frame(parent, bg=theme.BG_CARD, padx=20, pady=20)
        self.text_op = TextOperation(self, config)
        self.fonts = fonts()
        self.create_widgets()

    def create_widgets(self):
        default_bg = theme.BG_CARD
        label_style = {"bg": default_bg, "fg": theme.TEXT_MUTED, "font": theme.FONT_LABEL}

        tk.Label(self.frame, text="Text element", bg=default_bg, fg=theme.TEXT_PRIMARY,
                 font=theme.FONT_SECTION_TITLE).grid(row=0, column=0, columnspan=5, sticky='w', pady=(0, 14))

        # Content label and multi-line text entry with scrollbar
        tk.Label(self.frame, text="Content", **label_style).grid(row=1, column=0, sticky='nw')
        
        self.frame.grid_columnconfigure(0, weight=1)

        # Content: multi-line text entry with scrollbar
        tk.Label(self.frame, text="Content", **label_style).grid(row=1, column=0, sticky='w', pady=(0, 4))
        text_frame = tk.Frame(self.frame, bg=default_bg, highlightbackground=theme.BORDER, highlightthickness=1)
        text_frame.grid(row=2, column=0, sticky='ew', pady=(0, 4))

        self.content_entry = tk.Text(text_frame, highlightthickness=0, bd=0, height=3, width=24,
                                     bg=theme.BG_FIELD, fg=theme.TEXT_PRIMARY, font=theme.FONT_BODY)
        self.content_entry.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=6, pady=6)

        # Add scrollbar for longer text
        scrollbar = tk.Scrollbar(text_frame, command=self.content_entry.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.content_entry.config(yscrollcommand=scrollbar.set)

        self.content_entry.insert("1.0", "Text")

        self.sample_text_label = tk.Label(self.frame, text="Sample Text", font=('Arial', 12),
                                          bg=default_bg, fg=theme.TEXT_FAINT, wraplength=250, justify='left')
        self.sample_text_label.grid(row=3, column=0, sticky='w', pady=(0, 10))

        tk.Label(self.frame, text="Font family", **label_style).grid(row=4, column=0, sticky='w', pady=(0, 4))
        self.font_family_dropdown = ttk.Combobox(self.frame, values=list(self.fonts.keys()), style="Pill.TCombobox")
        self.font_family_dropdown.grid(row=5, column=0, sticky='ew', pady=(0, 10))
        font_settings = self.config.settings.get("font", {})
        self.font_family_dropdown.set(font_settings.get("family", "Arial"))
        widget_name = "font_dropdown"
        self.font_family_dropdown.bind("<<ComboboxSelected>>",
                                       lambda event, w=widget_name: self.update_text_properties(event, w))
        self.update_font_list()

        size_row = tk.Frame(self.frame, bg=default_bg)
        size_row.grid(row=6, column=0, sticky='ew', pady=(0, 10))
        size_row.grid_columnconfigure(0, weight=1)
        size_row.grid_columnconfigure(1, weight=1)

        size_col = tk.Frame(size_row, bg=default_bg)
        size_col.grid(row=0, column=0, sticky='ew', padx=(0, 6))
        tk.Label(size_col, text="Size", **label_style).pack(anchor='w', pady=(0, 4))
        self.size_var = tk.IntVar()
        self.size_var.set(font_settings.get("size", 16))
        self.font_size_dropdown = tk.Spinbox(size_col, from_=4, to=100, textvariable=self.size_var,
                                             highlightthickness=1, highlightbackground=theme.BORDER, bd=0,
                                             bg=theme.BG_FIELD, command=self.update_text_properties)
        self.font_size_dropdown.bind('<FocusOut>', self.update_text_properties)
        self.font_size_dropdown.pack(fill='x')

        kerning_col = tk.Frame(size_row, bg=default_bg)
        kerning_col.grid(row=0, column=1, sticky='ew')
        tk.Label(kerning_col, text="Kerning", **label_style).pack(anchor='w', pady=(0, 4))
        self.kerning_var = tk.StringVar()
        self.kerning_var.set(str(font_settings.get("kerning", "0")))
        self.font_kerning_dropdown = tk.Spinbox(kerning_col, from_=0, to=20, increment=0.1, format="%.1f",
                                                textvariable=self.kerning_var, highlightthickness=1,
                                                highlightbackground=theme.BORDER, bd=0, bg=theme.BG_FIELD,
                                                command=self.update_text_properties)
        self.font_kerning_dropdown.bind('<FocusOut>', self.update_text_properties)
        self.font_kerning_dropdown.pack(fill='x')

        style_row = tk.Frame(self.frame, bg=default_bg)
        style_row.grid(row=7, column=0, sticky='w', pady=(0, 16))
        self.bold_var = tk.BooleanVar()
        self.bold_var.set(font_settings.get("weight", "normal") == "bold")
        tk.Checkbutton(style_row, text="Bold", variable=self.bold_var, bg=default_bg,
                      command=self.update_text_properties).pack(side=tk.LEFT)
        self.italic_var = tk.BooleanVar()
        self.italic_var.set(font_settings.get("slant", "roman") == "italic")
        tk.Checkbutton(style_row, text="Italic", variable=self.italic_var, bg=default_bg,
                      command=self.update_text_properties).pack(side=tk.LEFT, padx=(10, 0))
        self.underline_var = tk.BooleanVar()
        self.underline_var.set(font_settings.get("underline", False))
        tk.Checkbutton(style_row, text="Underline", variable=self.underline_var, bg=default_bg,
                      command=self.update_text_properties).pack(side=tk.LEFT, padx=(10, 0))

        button_frame = tk.Frame(self.frame, bg=default_bg)
        button_frame.grid(row=8, column=0, sticky="ew")
        self.add_button = RoundedButton(button_frame, text="Add", variant="primary", bg=default_bg,
                                        command=self.text_op.add_text_to_canvas)
        self.delete_button = RoundedButton(button_frame, text="Delete", variant="outline", bg=default_bg,
                                           command=self.text_op.delete_text)
        self.add_button.pack(side=tk.LEFT)
        self.delete_button.pack(side=tk.LEFT, padx=(8, 0))

    def update_font_list(self, event=None):
        font_family = self.font_family_dropdown.get()
        # self.font_dropdown['values'] = list(self.fonts[font_family]["fonts"].keys())
        # self.font_dropdown.current(0)

        content = self.content_entry.get("1.0", "end-1c")
        label_font = tk_font.Font(family=font_family, size=14)
        self.sample_text_label.config(font=label_font,
                                      text=f"{content} in {font_family}")

    def update_text_properties(self, event=None, widget_name=None):
        font_obj, font_props = self.get_font_properties()
        self.config.settings["font"] = font_props
        self.config.save_settings()
        content = self.content_entry.get("1.0", "end-1c")
        label_font = tk_font.Font(family=font_props['family'], size=14, weight=font_props['weight'],
                                  slant=font_props['slant'])
        self.sample_text_label.config(font=label_font,
                                      text=f"{content} in {font_props['family'].replace('-', ' ')}")
        if self.config.current_selected:
            # self.config.canvas.itemconfig(self.config.current_selected, font=font_obj)
            # self.config.text_items[self.config.current_selected]['font'] = font_obj
            self.config.text_items[self.config.current_selected]['font_props'] = font_props
            self.text_op.update_canvas_text(self.config.current_selected)

        # if widget_name == "font_dropdown":
        #     self.bold_var.set(False)
        #     self.italic_var.set(False)
        #     self.underline_var.set(False)

    def get_font_properties(self):
        family = self.font_family_dropdown.get()
        # font = self.font_dropdown.get()
        size = int(self.font_size_dropdown.get())
        kerning = float(self.font_kerning_dropdown.get())
        weight = 'bold' if self.bold_var.get() else 'normal'
        slant = 'italic' if self.italic_var.get() else 'roman'
        underline = self.underline_var.get()
        # font_base_name = self.fonts[family]["fonts"][font]['name']

        # font_style = None
        # if weight == 'bold' and "Bold" in self.fonts[family]["fonts"][font]["variants"]:
        #     font_style = "Bold"
        #
        # if slant == 'italic':
        #     if "Italic" in self.fonts[family]["fonts"][font]["variants"]:
        #         font_style = "Italic"
        #     elif "Oblique" in self.fonts[family]["fonts"][font]["variants"]:
        #         font_style = "Oblique"
        # if weight == 'bold' and slant == 'italic':
        #     if "Bold-Italic" in self.fonts[family]["fonts"][font]["variants"]:
        #         font_style = "Bold-Italic"
        #
        # if font_style:
        #     font_name = f"{font_base_name}-{font_style}"
        # else:
        #     if self.fonts[family]["fonts"][font]["main"]:
        #         font_name = font_base_name
        #     elif "Regular" in self.fonts[family]["fonts"][font]["variants"]:
        #         font_name = f"{font_base_name}-Regular"
        #     else:
        #         font_name = f"{font_base_name}-{self.fonts[family]['fonts'][font]['variants'][0]}"

        font_props = {
            "family": family,
            # "font": font,
            "size": size,
            "kerning": kerning,
            "weight": weight,
            "slant": slant,
            "underline": underline,
            # "font_name": font_name
        }
        font_obj = tk_font.Font(family=family, size=size, weight=weight, slant=slant, underline=underline)

        return font_obj, font_props

    def get_text_operation(self):
        return self.text_op
