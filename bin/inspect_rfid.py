import asyncio
import json
import sys

from NiimPrintX.nimmy.bluetooth import find_device
from NiimPrintX.nimmy.printer import PrinterClient


async def main():
    model = sys.argv[1] if len(sys.argv) > 1 else "b1"
    device = await find_device(model)
    printer = PrinterClient(device, model=model)
    try:
        if not await printer.connect():
            print("connect failed")
            return
        print(json.dumps(await printer.get_rfid(), indent=2))
    finally:
        await printer.disconnect()


if __name__ == "__main__":
    asyncio.run(main())
