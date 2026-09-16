import tkinter as tk
from tkinter import ttk
from tkinter import messagebox

from .SpoolmanOperation import SpoolmanOperation
from NiimPrintX.spoolman.exception import SpoolmanError
from NiimPrintX.spoolman.label import build_spool_label_image
from NiimPrintX.spoolman import config as spoolman_config


class SpoolmanTab:
    def __init__(self, root, parent, config):
        self.root = root
        self.parent = parent
        self.config = config
        self.frame = ttk.Frame(parent)
        self.spoolman_op = SpoolmanOperation(root)
        self.spools = {}
        self.include_qr = tk.BooleanVar(value=True)
        self.create_widgets()
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

        bottom = tk.Frame(self.frame)
        bottom.pack(side=tk.TOP, fill=tk.X, padx=10, pady=10)
        tk.Checkbutton(bottom, text="Include QR code", variable=self.include_qr).pack(side=tk.LEFT)
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

    def generate_label(self):
        selection = self.tree.selection()
        if not selection:
            messagebox.showerror("Spoolman", "Select a spool first.")
            return
        spool = self.spools.get(int(selection[0]))
        if not spool:
            return

        device = self.config.device
        label_size_key = self.config.current_label_size
        label_size = self.config.label_sizes.get(device, {}).get("size", {}).get(label_size_key)
        if not label_size:
            messagebox.showerror("Spoolman", "Select a device and label size first.")
            return

        width_mm, height_mm = label_size
        print_dpi = self.config.label_sizes[device]["print_dpi"]
        width_px = round(width_mm / 25.4 * print_dpi)
        height_px = round(height_mm / 25.4 * print_dpi)

        base_url = self.spoolman_op.client.root_url if self.spoolman_op.client else None
        image = build_spool_label_image(
            spool, width_px, height_px,
            include_qr=self.include_qr.get(),
            base_url=base_url,
        )
        self.root.print_option.show_image_preview(image)
