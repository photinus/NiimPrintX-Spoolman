import tkinter as tk
from tkinter import ttk
from tkinter import messagebox

from .SpoolmanOperation import SpoolmanOperation
from ..component import theme
from ..component.RoundedButton import RoundedButton
from ..component.DesignStore import save_design
from NiimPrintX.spoolman.exception import SpoolmanError
from NiimPrintX.spoolman.label import build_spool_label_image
from NiimPrintX.spoolman.template import has_template, load_template, render_spool_label_template
from NiimPrintX.spoolman import config as spoolman_config

TEMPLATE_TOKENS = [
    ("Vendor", "vendor"),
    ("Name", "name"),
    ("Material", "material"),
    ("ID", "id"),
    ("Caption", "caption"),
]


class SpoolmanTab:
    def __init__(self, root, parent, config):
        self.root = root
        self.parent = parent
        self.config = config
        self.frame = tk.Frame(parent, bg=theme.BG_CARD, padx=20, pady=20)
        self.spoolman_op = SpoolmanOperation(root)
        self.spools = {}
        self.include_qr = tk.BooleanVar(value=True)
        self.editing_template = False
        self.create_widgets()
        self.load_saved_url()

    def create_widgets(self):
        bg = theme.BG_CARD
        label_style = {"bg": bg, "fg": theme.TEXT_MUTED, "font": theme.FONT_LABEL}

        tk.Label(self.frame, text="Spoolman", bg=bg, fg=theme.TEXT_PRIMARY,
                 font=theme.FONT_SECTION_TITLE).pack(anchor='w', pady=(0, 14))

        tk.Label(self.frame, text="Spoolman URL", **label_style).pack(anchor='w', pady=(0, 4))
        url_row = tk.Frame(self.frame, bg=bg)
        url_row.pack(fill='x', pady=(0, 10))
        self.url_var = tk.StringVar()
        url_entry = tk.Entry(url_row, textvariable=self.url_var, highlightthickness=1,
                             highlightbackground=theme.BORDER, bd=0, bg=theme.BG_FIELD,
                             fg=theme.TEXT_PRIMARY, font=theme.FONT_BODY)
        url_entry.pack(side=tk.LEFT, fill='x', expand=True, ipady=4)
        url_entry.bind("<Return>", lambda event: self.connect())
        RoundedButton(url_row, text="Connect", variant="primary", bg=bg,
                     command=self.connect).pack(side=tk.LEFT, padx=(6, 0))

        tk.Label(self.frame, text="Search", **label_style).pack(anchor='w', pady=(0, 4))
        search_row = tk.Frame(self.frame, bg=bg)
        search_row.pack(fill='x', pady=(0, 10))
        self.search_var = tk.StringVar()
        search_entry = tk.Entry(search_row, textvariable=self.search_var, highlightthickness=1,
                                highlightbackground=theme.BORDER, bd=0, bg=theme.BG_FIELD,
                                fg=theme.TEXT_PRIMARY, font=theme.FONT_BODY)
        search_entry.pack(side=tk.LEFT, fill='x', expand=True, ipady=4)
        search_entry.bind("<Return>", lambda event: self.refresh_spools())
        RoundedButton(search_row, text="Refresh", variant="outline", bg=bg,
                     command=self.refresh_spools).pack(side=tk.LEFT, padx=(6, 0))

        self.status_label = tk.Label(self.frame, text="Not connected", bg=bg, fg=theme.TEXT_FAINT,
                                     font=theme.FONT_LABEL, anchor='w', justify='left', wraplength=250)
        self.status_label.pack(anchor='w', pady=(0, 10))

        self.template_toggle_button = RoundedButton(
            self.frame, text="Edit label template", variant="outline", bg=bg, command=self.toggle_template_edit
        )
        self.template_toggle_button.pack(anchor='w', pady=(0, 4))

        self.template_status_label = tk.Label(self.frame, text="", bg=bg, fg=theme.TEXT_FAINT,
                                              font=theme.FONT_LABEL, anchor='w', justify='left', wraplength=250)
        self.template_status_label.pack(anchor='w', pady=(0, 4))

        self.template_tools = tk.Frame(self.frame, bg=bg)
        tk.Label(self.template_tools, text="Insert:", **label_style).pack(side=tk.LEFT, padx=(0, 4))
        tools_wrap = tk.Frame(self.template_tools, bg=bg)
        tools_wrap.pack(side=tk.LEFT, fill='x')
        for label, token in TEMPLATE_TOKENS:
            RoundedButton(tools_wrap, text=label, variant="secondary", bg=bg,
                         command=lambda t=token: self.insert_template_token(t)).pack(side=tk.LEFT, padx=(0, 4), pady=2)
        RoundedButton(tools_wrap, text="QR code", variant="secondary", bg=bg,
                     command=self.insert_template_qr).pack(side=tk.LEFT, pady=2)
        # template_tools is only packed while editing_template is True (see toggle_template_edit)

        columns = ("id", "vendor", "name", "material", "color", "remaining", "location")
        headings = {
            "id": "ID", "vendor": "Vendor", "name": "Filament", "material": "Material",
            "color": "Color", "remaining": "Remaining", "location": "Location",
        }
        widths = {"id": 30, "vendor": 60, "name": 90, "material": 55, "color": 55, "remaining": 60,
                  "location": 60}

        tree_frame = tk.Frame(self.frame, bg=bg, highlightbackground=theme.BORDER, highlightthickness=1)
        tree_frame.pack(fill='both', expand=True, pady=(10, 10))

        style = ttk.Style()
        style.configure("Spoolman.Treeview", background=theme.BG_CARD, fieldbackground=theme.BG_CARD,
                       foreground=theme.TEXT_PRIMARY, rowheight=24, font=theme.FONT_LABEL)
        style.configure("Spoolman.Treeview.Heading", background=theme.BG_SIDEBAR, foreground=theme.TEXT_MUTED,
                       font=theme.FONT_LABEL_BOLD)
        style.map("Spoolman.Treeview", background=[('selected', theme.ACCENT_LIGHT)],
                 foreground=[('selected', theme.TEXT_PRIMARY)])

        h_scroll = ttk.Scrollbar(tree_frame, orient='horizontal')
        v_scroll = ttk.Scrollbar(tree_frame, orient='vertical')
        self.tree = ttk.Treeview(tree_frame, columns=columns, show="headings", selectmode="browse",
                                 style="Spoolman.Treeview", height=6,
                                 xscrollcommand=h_scroll.set, yscrollcommand=v_scroll.set)
        for col in columns:
            self.tree.heading(col, text=headings[col])
            self.tree.column(col, width=widths[col], anchor="w")
        h_scroll.config(command=self.tree.xview)
        v_scroll.config(command=self.tree.yview)
        v_scroll.pack(side=tk.RIGHT, fill='y')
        h_scroll.pack(side=tk.BOTTOM, fill='x')
        self.tree.pack(side=tk.LEFT, fill='both', expand=True)
        self.tree.bind("<<TreeviewSelect>>", self.on_spool_selected)

        bottom = tk.Frame(self.frame, bg=bg)
        bottom.pack(fill='x')
        qr_row = tk.Frame(bottom, bg=bg)
        qr_row.pack(anchor='w', pady=(0, 8))
        tk.Checkbutton(qr_row, text="Include QR code", variable=self.include_qr, bg=bg,
                      fg=theme.TEXT_PRIMARY, font=theme.FONT_BODY,
                      command=self.on_spool_selected).pack(side=tk.LEFT)
        RoundedButton(bottom, text="Generate label", variant="primary", bg=bg,
                     command=self.generate_label).pack(fill='x')

    def load_saved_url(self):
        base_url = spoolman_config.load_settings().get("base_url")
        if not base_url:
            return
        self.url_var.set(base_url)
        try:
            self.spoolman_op.connect(base_url)
        except SpoolmanError:
            return
        self.refresh_spools(silent=True)

    def connect(self):
        base_url = self.url_var.get().strip()
        if not base_url:
            messagebox.showerror("Spoolman", "Please enter a Spoolman server URL.")
            return
        try:
            client = self.spoolman_op.connect(base_url)
        except SpoolmanError as e:
            messagebox.showerror("Spoolman", str(e))
            return
        spoolman_config.save_settings(base_url=client.root_url)
        self.url_var.set(client.root_url)
        self.refresh_spools()

    def refresh_spools(self, silent=False):
        if not self.spoolman_op.client:
            if not silent:
                messagebox.showerror("Spoolman", "Connect to a Spoolman server first.")
            return
        self.status_label.config(text="Loading spools...", fg=theme.TEXT_FAINT)
        search = self.search_var.get().strip() or None
        self.spoolman_op.fetch_spools(
            self._on_load_success,
            lambda message: self._on_load_error(message, silent),
            name=search,
        )

    def _on_load_error(self, message, silent=False):
        self.status_label.config(text=f"Error: {message}", fg=theme.DANGER_TEXT)
        if not silent:
            messagebox.showerror("Spoolman", message)

    def _on_load_success(self, spools):
        self.spools = {spool["id"]: spool for spool in spools}
        self.tree.delete(*self.tree.get_children())
        for spool in spools:
            filament = spool.get("filament") or {}
            vendor = (filament.get("vendor") or {}).get("name", "")
            remaining = spool.get("remaining_weight")
            remaining_str = f"{remaining:.0f}g" if remaining is not None else "-"
            self.tree.insert("", "end", iid=str(spool["id"]), values=(
                spool["id"], vendor, filament.get("name", ""), filament.get("material", ""),
                filament.get("color_hex") or "-", remaining_str, spool.get("location") or "",
            ))
        self.status_label.config(text=f"{len(spools)} spool(s) loaded", fg=theme.SUCCESS)
        self.root.canvas_selector.clear_static_preview()

    def _selected_spool(self):
        selection = self.tree.selection()
        if not selection:
            return None
        return self.spools.get(int(selection[0]))

    def _render_label_image(self, spool):
        """Build the label image for a spool at the currently selected device/size.

        Shared by the live preview and Generate Label so they never drift -- raises
        ValueError with a user-facing message if a device/label size isn't picked yet.
        """
        device = self.config.device
        label_size_key = self.config.current_label_size
        label_size = self.config.label_sizes.get(device, {}).get("size", {}).get(label_size_key)
        if not label_size:
            raise ValueError("Select a device and label size first.")

        width_mm, height_mm = label_size
        print_dpi = self.config.label_sizes[device]["print_dpi"]
        base_url = self.spoolman_op.client.root_url if self.spoolman_op.client else None

        template_data = load_template(self.config, device, label_size_key)
        if template_data:
            return render_spool_label_template(
                template_data, spool, self.config.os_system, width_mm, height_mm, print_dpi,
                base_url=base_url,
            )
        width_px = round(width_mm / 25.4 * print_dpi)
        height_px = round(height_mm / 25.4 * print_dpi)
        return build_spool_label_image(
            spool, width_px, height_px,
            include_qr=self.include_qr.get(),
            base_url=base_url,
        )

    def generate_label(self):
        spool = self._selected_spool()
        if not spool:
            messagebox.showerror("Spoolman", "Select a spool first.")
            return
        try:
            image = self._render_label_image(spool)
        except ValueError as e:
            messagebox.showerror("Spoolman", str(e))
            return
        self.root.print_option.show_image_preview(image, name=self._spool_display_name(spool))

    @staticmethod
    def _spool_display_name(spool):
        filament = spool.get("filament") or {}
        vendor = (filament.get("vendor") or {}).get("name") or ""
        name = filament.get("name") or ""
        label = " ".join(part for part in (vendor, name) if part).strip()
        return label or f"Spool #{spool.get('id')}"

    def on_spool_selected(self, event=None):
        if self.editing_template:
            # The canvas is the template being edited right now -- don't paper over it.
            return
        spool = self._selected_spool()
        if not spool:
            self.root.canvas_selector.clear_static_preview()
            return
        try:
            image = self._render_label_image(spool)
        except Exception:
            # No device/size picked yet, or a bad template -- just leave the canvas as is.
            self.root.canvas_selector.clear_static_preview()
            return
        self.root.canvas_selector.show_static_preview(image)

    def toggle_template_edit(self):
        if self.config.current_label_size:
            save_design(self.config)

        self.editing_template = not self.editing_template
        self.config.design_kind = "spoolman" if self.editing_template else "design"
        self.root.canvas_selector.update_canvas_size()

        if self.editing_template:
            self.template_toggle_button.config(text="Done editing template")
            self.template_tools.pack(anchor='w', pady=(0, 10))
        else:
            self.template_toggle_button.config(text="Edit label template")
            self.template_tools.pack_forget()
        self._update_template_status()
        # Jumps into/out of the Design section and shows/hides the token +
        # "Done editing template" toolbar there -- see LabelPrinterApp.set_template_editing.
        self.root.set_template_editing(self.editing_template)

    def insert_template_token(self, token):
        self.root.select_design_subtab("text")
        content_entry = self.root.text_tab.content_entry
        content_entry.insert(tk.INSERT, f"{{{token}}}")
        content_entry.focus_set()

    def insert_template_qr(self):
        self.root.icon_tab.image_op.add_qr_placeholder()

    def _update_template_status(self):
        device = self.config.device
        label_size = self.config.current_label_size
        if not device or not label_size:
            self.template_status_label.config(text="")
            return
        if self.editing_template:
            self.template_status_label.config(
                text=f"Editing template for {device.upper()} / {label_size} "
                     f"-- use {{vendor}} {{name}} {{material}} {{id}} {{caption}} tokens in text"
            )
        elif has_template(self.config, device, label_size):
            self.template_status_label.config(text=f"Using custom template for {device.upper()} / {label_size}")
        else:
            self.template_status_label.config(text=f"No template for {device.upper()} / {label_size} (using automatic layout)")

    def on_show(self):
        """Called by the app when the Spoolman section becomes active."""
        self._update_template_status()
        self.on_spool_selected()

    def on_hide(self):
        """Called by the app when leaving the Spoolman section (and not mid
        template-edit): drop the preview overlay so Design shows the real
        editable canvas underneath again."""
        if not self.editing_template:
            self.root.canvas_selector.clear_static_preview()
