"""Temporary BlueIQ API proof-of-concept script."""

import asyncio
import os

from aiohttp import ClientSession

from custom_components.blueiq.api import BlueIQClient


async def main() -> None:
    token = os.environ.get("BLUEIQ_TOKEN")
    if not token:
        raise RuntimeError("Set BLUEIQ_TOKEN before running the script")

    async with ClientSession() as session:
        client = BlueIQClient(session, token)

        devices = await client.get_devices()

        for device in devices:
            print(f"{device.nickname}: " f"{device.status} " f"({device.device_name})")

            modes = await client.get_modes(device.device_name)

            for mode in modes:
                print(f"  {mode.name}: " f"{mode.mode_id} " f"[{mode.preset_type}]")


if __name__ == "__main__":
    asyncio.run(main())
