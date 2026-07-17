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


def get_requested_mode() -> str:
    """Read and validate the requested mode from the command line."""
    if len(sys.argv) != 2:
        valid_modes = ", ".join(SUPPORTED_MODES)
        raise RuntimeError(
            "Usage: poetry run python -m scripts.blueiq_test " f"<{valid_modes}>"
        )

    requested_mode = sys.argv[1].lower()

    if requested_mode not in SUPPORTED_MODES:
        valid_modes = ", ".join(SUPPORTED_MODES)
        raise RuntimeError(
            f"Unsupported mode {requested_mode!r}. " f"Choose one of: {valid_modes}"
        )

    return requested_mode


async def authenticate_client(
    session: ClientSession,
) -> BlueIQClient:
    """Create and authenticate a BlueIQ client.

    A preexisting token is used when BLUEIQ_TOKEN is set. Otherwise,
    the script signs in using BLUEIQ_EMAIL and BLUEIQ_PASSWORD.
    """
    token = os.environ.get("BLUEIQ_TOKEN")

    if token:
        client = BlueIQClient(session, token=token)
        await client.validate_token()
        print("Authenticated using BLUEIQ_TOKEN.")
        return client

    email = os.environ.get("BLUEIQ_EMAIL")
    password = os.environ.get("BLUEIQ_PASSWORD")

    if not email or not password:
        raise RuntimeError(
            "Authentication is not configured.\n\n"
            "Either set an existing token:\n"
            "  export BLUEIQ_TOKEN='your-token'\n\n"
            "Or set BlueIQ credentials:\n"
            "  export BLUEIQ_EMAIL='your-email'\n"
            "  export BLUEIQ_PASSWORD='your-password'"
        )

    client = BlueIQClient(session)
    await client.authenticate(email, password)

    print("Authenticated using BlueIQ account credentials.")
    return client


async def main() -> None:
    """Run the BlueIQ mode test."""
    requested_mode = get_requested_mode()

    async with ClientSession() as session:
        client = await authenticate_client(session)

        devices = await client.get_devices()

        if not devices:
            raise RuntimeError("No BlueIQ devices were found")

        device = devices[0]

        print(
            "\n"
            f"Device: {device.nickname}\n"
            f"Status: {device.status}\n"
            f"Device ID: {device.device_name}"
        )

        if device.status.lower() != "connected":
            raise RuntimeError(f"{device.nickname} is not connected")

        modes = await client.get_modes(device.device_name)
        mode = find_mode(modes, requested_mode)

        print(
            "\nAbout to apply:\n"
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
