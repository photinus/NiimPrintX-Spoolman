import asyncio
import sys

from bleak import BleakClient

from NiimPrintX.nimmy.bluetooth import find_device


async def main():
    model = sys.argv[1] if len(sys.argv) > 1 else "b1"
    device = await find_device(model)
    print(f"{device.name} {device.address}")
    async with BleakClient(device.address) as client:
        for service in client.services:
            print(f"service {service.uuid}")
            for char in service.characteristics:
                print(f"  char {char.uuid} {','.join(char.properties)}")


if __name__ == "__main__":
    asyncio.run(main())
