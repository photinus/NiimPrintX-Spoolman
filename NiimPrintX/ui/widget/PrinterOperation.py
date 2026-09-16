from tkinter import messagebox

from devtools import debug


class PrinterOperation:
    def __init__(self, config):
        self.config = config
        self.printer = None
        self.last_error = None

    async def printer_connect(self, model):
        self.last_error = None
        try:
            from NiimPrintX.nimmy.bluetooth import find_device
            from NiimPrintX.nimmy.printer import PrinterClient

            device = await find_device(model)
            self.printer = PrinterClient(device, model=model)
            if await self.printer.connect():
                self.config.printer_connected = True
                return True
        except Exception as e:
            # debug(e)
            self.last_error = f"Cannot connect to printer {model}: {e}"
        self.config.printer_connected = False
        self.printer = None
        return False

    async def get_label_size_from_rfid(self):
        if not self.printer:
            return None
        rfid = await self.printer.get_rfid()
        if not rfid:
            return None
        barcode = rfid.get("barcode")
        return self.config.rfid_label_sizes.get(self.config.device, {}).get(barcode)

    async def printer_disconnect(self):
        try:
            if self.config.printer_connected or self.printer:
                await self.printer.disconnect()
            self.config.printer_connected = False
            self.printer = None
            return True
        except Exception as e:
            self.config.printer_connected = False
            messagebox.showerror("Error", f"{str(e)}.")
            return False

    async def print(self, image, density, quantity):
        try:
            if not self.config.printer_connected or not self.printer:
                connected = await self.printer_connect(self.config.device)
                if not connected:
                    return False

            await self.printer.print_image(image, density, quantity)
            return True
        except Exception as e:
            messagebox.showerror("Error", f"{str(e)}.")
            return False

    async def heartbeat(self):
        try:
            if self.printer:
                hb = await self.printer.heartbeat()
                if hb is None:
                    return self.printer.transport.is_connected(), {}
                return True, hb
        except Exception as e:
            # print(f"Error {e}")
            if not self.printer or not self.printer.transport.is_connected():
                self.printer = None
                return False, {}
            return True, {}
        return False, {}
