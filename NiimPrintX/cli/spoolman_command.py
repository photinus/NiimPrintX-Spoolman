import asyncio
import os

import click

from NiimPrintX.nimmy.bluetooth import find_device
from NiimPrintX.nimmy.printer import PrinterClient
from NiimPrintX.nimmy.helper import print_info, print_error, print_success
from NiimPrintX.nimmy.label_sizes import LABEL_SIZES
from NiimPrintX.spoolman.client import SpoolmanClient
from NiimPrintX.spoolman.exception import SpoolmanError
from NiimPrintX.spoolman.label import build_spool_label_image
from NiimPrintX.spoolman.config import load_settings, save_settings

MODEL_CHOICES = click.Choice(list(LABEL_SIZES.keys()), case_sensitive=False)


def _resolve_base_url(base_url):
    if base_url:
        return base_url
    env_url = os.environ.get("SPOOLMAN_URL")
    if env_url:
        return env_url
    return load_settings().get("base_url")


@click.group("spoolman")
def spoolman_cli():
    """Print labels for filament spools tracked in Spoolman."""


@spoolman_cli.command("config")
@click.option("--base-url", required=True, help="Spoolman server URL, e.g. http://spoolman.local:7912")
def config_command(base_url):
    """Save a default Spoolman server URL for future commands."""
    try:
        client = SpoolmanClient(base_url)
        client.test_connection()
    except SpoolmanError as e:
        print_error(str(e))
        return
    save_settings(base_url=client.root_url)
    print_success(f"Saved Spoolman server URL: {client.root_url}")


@spoolman_cli.command("list")
@click.option("--base-url", default=None, help="Spoolman server URL (overrides saved config)")
@click.option("--material", default=None, help="Filter by filament material")
@click.option("--vendor", default=None, help="Filter by vendor name")
@click.option("--location", default=None, help="Filter by spool location")
@click.option("--archived", is_flag=True, default=False, help="Include archived spools")
def list_command(base_url, material, vendor, location, archived):
    """List spools available on the configured Spoolman server."""
    base_url = _resolve_base_url(base_url)
    if not base_url:
        print_error("No Spoolman server URL configured. Use --base-url or `spoolman config --base-url`.")
        return

    try:
        client = SpoolmanClient(base_url)
        spools = client.get_spools(material=material, vendor=vendor, location=location, archived=archived)
    except SpoolmanError as e:
        print_error(str(e))
        return

    if not spools:
        print_info("No spools found.")
        return

    for spool in spools:
        filament = spool.get("filament") or {}
        vendor_name = (filament.get("vendor") or {}).get("name", "")
        name = filament.get("name", "")
        material_name = filament.get("material", "")
        remaining = spool.get("remaining_weight")
        remaining_str = f"{remaining:.0f}g" if remaining is not None else "?"
        print(f"[{spool['id']:>4}] {vendor_name} {name} ({material_name}) - {remaining_str} remaining")


@spoolman_cli.command("sizes")
@click.option("-m", "--model", type=MODEL_CHOICES, default="d110", show_default=True, help="Niimbot printer model")
def sizes_command(model):
    """List the label size presets available for a printer model."""
    for label_size in LABEL_SIZES[model.lower()]["size"]:
        print(label_size)


@spoolman_cli.command("print")
@click.option("--base-url", default=None, help="Spoolman server URL (overrides saved config)")
@click.option("--spool-id", "spool_id", type=int, required=True, help="Spoolman spool ID to print a label for")
@click.option("-m", "--model", type=MODEL_CHOICES, default="d110", show_default=True, help="Niimbot printer model")
@click.option("--label-size", default=None, help='Preset label size, e.g. "50mm x 14mm" (see `spoolman sizes`)')
@click.option("--width", "label_width_mm", type=float, default=None, help="Custom label width in mm")
@click.option("--height", "label_height_mm", type=float, default=None, help="Custom label height in mm")
@click.option("-d", "--density", type=click.IntRange(1, 5), default=3, show_default=True, help="Print density")
@click.option("-n", "--quantity", default=1, show_default=True, help="Print quantity")
@click.option("--qrcode/--no-qrcode", "include_qr", default=True, help="Include a QR code linking back to the spool")
def print_command(base_url, spool_id, model, label_size, label_width_mm, label_height_mm, density, quantity,
                   include_qr):
    """Fetch a spool from Spoolman and print a label for it."""
    base_url = _resolve_base_url(base_url)
    if not base_url:
        print_error("No Spoolman server URL configured. Use --base-url or `spoolman config --base-url`.")
        return

    model = model.lower()
    model_sizes = LABEL_SIZES[model]

    if label_size:
        if label_size not in model_sizes["size"]:
            print_error(f"Unknown label size '{label_size}' for {model}. "
                        f"Available: {', '.join(model_sizes['size'])}")
            return
        label_width_mm, label_height_mm = model_sizes["size"][label_size]

    if label_width_mm is None or label_height_mm is None:
        print_error("Specify --label-size or both --width and --height.")
        return

    if model in ("b18", "d11", "d11_h", "d110") and density > 3:
        density = 3

    try:
        client = SpoolmanClient(base_url)
        spool = client.get_spool(spool_id)
    except SpoolmanError as e:
        print_error(str(e))
        return

    print_dpi = model_sizes["print_dpi"]
    width_px = round(label_width_mm / 25.4 * print_dpi)
    height_px = round(label_height_mm / 25.4 * print_dpi)

    image = build_spool_label_image(spool, width_px, height_px, include_qr=include_qr, base_url=client.root_url)
    # PIL rotates counterclockwise, so a clockwise print orientation needs a negative angle.
    image = image.rotate(-90, expand=True)

    asyncio.run(_print(model, density, image, quantity))


async def _print(model, density, image, quantity):
    printer = None
    try:
        print_info("Starting print job")
        device = await find_device(model)
        printer = PrinterClient(device)
        if await printer.connect():
            print(f"Connected to {device.name}")
        await printer.print_image(image, density=density, quantity=quantity)
        print_success("Print job completed")
    except Exception as e:
        print_error(str(e))
    finally:
        if printer:
            await printer.disconnect()
