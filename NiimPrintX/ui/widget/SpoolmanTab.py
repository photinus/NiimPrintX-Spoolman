import tkinter as tk
from tkinter import ttk
from tkinter import messagebox

from .SpoolmanOperation import SpoolmanOperation
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
        self.frame = ttk.Frame(parent)
        self.spoolman_op = SpoolmanOperation(root)
        self.spools = {}
        self.include_qr = tk.BooleanVar(value=True)
        self.editing_template = False
        self.create_widgets()
        self.parent.bind("<<NotebookTabChanged>>", self._on_tab_changed)
        self.load_saved_url()

    def create_widgets(self):
        top = tk.Frame(self.frame)
        top.pack(side=tk.TOP, fill=tk.X, padx=10, pady=10)

        tk.Label(top, text="Spoolman URL").pack(side=tk.LEFT)
        self.url_var = tk.StringVar()
        url_entry = tk.Entry(top, textvariable=self.url_var, width=32)
        url_entry.pack(side=tk.LEFT, padx=5)
        url_entry.bind("<Return>", lambda event: self.connect())

        tk.Button(top, text="Connect", command=self.connect).pack(side=tk.LEFT, padx=5)

        tk.Label(top, text="Search").pack(side=tk.LEFT, padx=(20, 0))
        self.search_var = tk.StringVar()
        search_entry = tk.Entry(top, textvariable=self.search_var, width=18)
        search_entry.pack(side=tk.LEFT, padx=5)
        search_entry.bind("<Return>", lambda event: self.refresh_spools())

        tk.Button(top, text="Refresh", command=self.refresh_spools).pack(side=tk.LEFT, padx=5)

        self.status_label = tk.Label(self.frame, text="Not connected", fg="gray")
        self.status_label.pack(side=tk.TOP, anchor="w", padx=10)

        template_row = tk.Frame(self.frame)
        template_row.pack(side=tk.TOP, fill=tk.X, padx=10, pady=(0, 5))

        self.template_toggle_button = tk.Button(
            template_row, text="Edit Label Template", command=self.toggle_template_edit
        )
        self.template_toggle_button.pack(side=tk.LEFT)

        self.template_status_label = tk.Label(template_row, text="", fg="gray")
        self.template_status_label.pack(side=tk.LEFT, padx=10)

        self.template_tools = tk.Frame(template_row)
        tk.Label(self.template_tools, text="Insert:").pack(side=tk.LEFT, padx=(10, 2))
        for label, token in TEMPLATE_TOKENS:
            tk.Button(
                self.template_tools, text=label, command=lambda t=token: self.insert_template_token(t)
            ).pack(side=tk.LEFT, padx=2)
        tk.Button(self.template_tools, text="QR Code", command=self.insert_template_qr).pack(side=tk.LEFT, padx=(8, 2))
        # template_tools is only packed while editing_template is True (see toggle_template_edit)

        columns = ("id", "vendor", "name", "material", "color", "remaining", "location")
        headings = {
            "id": "ID", "vendor": "Vendor", "name": "Filament", "material": "Material",
            "color": "Color", "remaining": "Remaining", "location": "Location",
        }
        widths = {"id": 50, "vendor": 110, "name": 170, "material": 80, "color": 80, "remaining": 90,
                  "location": 100}

        self.tree = ttk.Treeview(self.frame, columns=columns, show="headings", selectmode="browse")
        for col in columns:
            self.tree.heading(col, text=headings[col])
            self.tree.column(col, width=widths[col], anchor="w")
        self.tree.pack(side=tk.TOP, fill=tk.BOTH, expand=True, padx=10, pady=5)
        self.tree.bind("<<TreeviewSelect>>", self.on_spool_selected)

        bottom = tk.Frame(self.frame)
        bottom.pack(side=tk.TOP, fill=tk.X, padx=10, pady=10)
        tk.Checkbutton(bottom, text="Include QR code", variable=self.include_qr,
                      command=self.on_spool_selected).pack(side=tk.LEFT)
        tk.Button(bottom, text="Generate Label", command=self.generate_label).pack(side=tk.RIGHT)

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
        self.status_label.config(text="Loading spools...", fg="gray")
        search = self.search_var.get().strip() or None
        self.spoolman_op.fetch_spools(
            self._on_load_success,
            lambda message: self._on_load_error(message, silent),
            name=search,
        )

    def _on_load_error(self, message, silent=False):
        self.status_label.config(text=f"Error: {message}", fg="red")
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
        self.status_label.config(text=f"{len(spools)} spool(s) loaded", fg="green")
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
        self.root.print_option.show_image_preview(image)

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
            self.template_toggle_button.config(text="Done Editing Template")
            self.template_tools.pack(side=tk.LEFT)
            self.root.tab_control.select(self.root.text_tab.frame)
        else:
            self.template_toggle_button.config(text="Edit Label Template")
            self.template_tools.pack_forget()
        self._update_template_status()
        if not self.editing_template:
            self.on_spool_selected()

    def insert_template_token(self, token):
        self.root.tab_control.select(self.root.text_tab.frame)
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

    def _on_tab_changed(self, event=None):
        try:
            current = self.parent.select()
        except tk.TclError:
            return
        if current == str(self.frame):
            self._update_template_status()
            self.on_spool_selected()
        elif not self.editing_template:
            # Leaving the Spoolman tab (and not mid-template-edit): drop the preview
            # overlay so Text/Icon show the real editable canvas underneath again.
            self.root.canvas_selector.clear_static_preview()
