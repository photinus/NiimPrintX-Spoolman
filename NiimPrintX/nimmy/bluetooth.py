import asyncio
from bleak import BleakClient, BleakScanner

from .exception import BLEException
from .logger_config import get_logger

logger = get_logger()


async def find_device(device_name_prefix=None, timeout=10):
    try:
        devices = await asyncio.wait_for(BleakScanner.discover(timeout=timeout), timeout=timeout + 2)
    except asyncio.TimeoutError as exc:
        raise BLEException("Bluetooth scan timed out. Check Bluetooth permissions and make sure the printer is awake.") from exc
    matching_prefix = device_name_prefix.lower() if device_name_prefix else None
    for device in devices:
        if device.name and (not matching_prefix or device.name.lower().startswith(matching_prefix)):
            return device
    visible_names = ", ".join(device.name for device in devices if device.name) or "no named devices"
    raise BLEException(f"Failed to find device {device_name_prefix}. Visible devices: {visible_names}")


async def scan_devices(device_name=None, timeout=10):
    print("Scanning for devices...")
    try:
        devices = await asyncio.wait_for(BleakScanner.discover(timeout=timeout), timeout=timeout + 2)
    except asyncio.TimeoutError as exc:
        raise BLEException("Bluetooth scan timed out. Check Bluetooth permissions and make sure the printer is awake.") from exc
    for device in devices:
        if device_name:
            if device.name and device_name.lower() in device.name.lower():
                print(f"Found device: {device.name} at {device.address}")
                return device
        else:
            print(f"Found device: {device.name} at {device.address}")
    return None


class BLETransport:
    def __init__(self, address=None):
        self.address = address
        self.client = None

    async def __aenter__(self):
        # Automatically connect if address is provided during initialization
        if self.address:
            self.client = BleakClient(self.address)
            await self.client.connect()
            if self.client.is_connected:
                logger.info(f"Connected to {self.address}")
                return self
            raise BLEException(f"Failed to connect to the BLE device at {self.address}")
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.client:
            await self.client.disconnect()
            logger.info("Disconnected.")

    async def connect(self, address):
        if self.client is None:
            self.client = BleakClient(address)
        if not self.client.is_connected:
            await self.client.connect()
            return self.client.is_connected
        return True

    def is_connected(self):
        return bool(self.client and self.client.is_connected)

    async def disconnect(self):
        if self.client and self.client.is_connected:
            await self.client.disconnect()

    async def write(self, data, char_uuid):
        if self.client and self.client.is_connected:
            await self.client.write_gatt_char(char_uuid, data)
        else:
            raise BLEException("BLE client is not connected.")

    async def start_notification(self, char_uuid, handler):
        if self.client and self.client.is_connected:
            await self.client.start_notify(char_uuid, handler)
        else:
            raise BLEException("BLE client is not connected.")

    async def stop_notification(self, char_uuid):
        if self.client and self.client.is_connected:
            await self.client.stop_notify(char_uuid)
        else:
            raise BLEException("BLE client is not connected.")
