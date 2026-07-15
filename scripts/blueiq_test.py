"""BlueIQ API proof-of-concept script."""

import asyncio
import os
import sys

from aiohttp import ClientSession

from custom_components.blueiq.api import BlueIQClient, BlueIQMode

SUPPORTED_MODES = {
    "predawn": "EARLY_MORNING",
    "overnight": "OVERNIGHT",
}


def find_mode(
    modes: list[BlueIQMode],
    requested_mode: str,
) -> BlueIQMode:
    """Find a mode using its stable preset type."""
    preset_type = SUPPORTED_MODES[requested_mode]

    for mode in modes:
        if mode.preset_type == preset_type:
            return mode

    raise RuntimeError(f"Could not find BlueIQ preset type {preset_type!r}")


async def main() -> None:
    token = os.environ.get("BLUEIQ_TOKEN")
    if not token:
        raise RuntimeError(
            "BLUEIQ_TOKEN is not set. " "Run: export BLUEIQ_TOKEN='your-token'"
        )

    if len(sys.argv) != 2 or sys.argv[1].lower() not in SUPPORTED_MODES:
        valid_modes = ", ".join(SUPPORTED_MODES)
        raise RuntimeError(f"Usage: python -m scripts.blueiq_test " f"<{valid_modes}>")

    requested_mode = sys.argv[1].lower()

    async with ClientSession() as session:
        client = BlueIQClient(session, token)

        devices = await client.get_devices()
        if not devices:
            raise RuntimeError("No BlueIQ devices were found")

        device = devices[0]

        print(
            f"Device: {device.nickname}\n"
            f"Status: {device.status}\n"
            f"Device ID: {device.device_name}"
        )

        if device.status != "connected":
            raise RuntimeError(f"{device.nickname} is not connected")

        modes = await client.get_modes(device.device_name)
        mode = find_mode(modes, requested_mode)

        print(
            f"\nAbout to apply:\n"
            f"  Name: {mode.name}\n"
            f"  Preset type: {mode.preset_type}\n"
            f"  Mode ID: {mode.mode_id}"
        )

        confirmation = input("\nApply this mode? [y/N]: ").strip().lower()
        if confirmation not in {"y", "yes"}:
            print("Cancelled.")
            return

        await client.apply_mode(mode.mode_id)

        print(f"\nSuccessfully applied {mode.name}.")


if __name__ == "__main__":
    asyncio.run(main())
