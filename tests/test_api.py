"""Tests for the unofficial BlueIQ API client."""

from __future__ import annotations

from typing import Any

import pytest
from aiohttp import ClientSession
from aioresponses import aioresponses
from yarl import URL

from custom_components.blueiq.api import (
    BlueIQAuthenticationError,
    BlueIQClient,
    BlueIQProtocolError,
)

BASE_URL = "https://central.nobleapplications.com"
TOKEN = "test-token"
DEVICE_NAME = "TEST-DEVICE-001"


@pytest.mark.asyncio
async def test_get_devices_parses_device_response(
    device_payload: list[dict[str, Any]],
) -> None:
    """The client should parse a BlueIQ device response."""
    with aioresponses() as mocked:
        mocked.get(
            f"{BASE_URL}/api/device",
            payload=device_payload,
            status=200,
        )

        async with ClientSession() as session:
            client = BlueIQClient(session, TOKEN)
            devices = await client.get_devices()

    assert len(devices) == 1

    device = devices[0]

    assert device.device_name == DEVICE_NAME
    assert device.nickname == "Fish Light"
    assert device.status == "connected"
    assert device.firmware_version == "0.6.1"
    assert device.product_code == "OPTIBRIGHT"
    assert device.last_seen is not None


@pytest.mark.asyncio
async def test_get_modes_parses_diff_modes(
    mode_payload: list[dict[str, Any]],
) -> None:
    """The client should parse modes without relying on real IDs."""
    with aioresponses() as mocked:
        mocked.get(
            f"{BASE_URL}/api/mode/{DEVICE_NAME}",
            payload=mode_payload,
            status=200,
        )

        async with ClientSession() as session:
            client = BlueIQClient(session, TOKEN)
            modes = await client.get_modes(DEVICE_NAME)

    assert len(modes) == 6

    modes_by_preset = {mode.preset_type: mode for mode in modes}

    sunrise = modes_by_preset["SUNRISE"]
    day = modes_by_preset["DAY"]
    sunset = modes_by_preset["SUNSET"]
    night = modes_by_preset["NIGHT"]
    overnight = modes_by_preset["OVERNIGHT"]
    predawn = modes_by_preset["EARLY_MORNING"]

    assert sunrise.name == "Sunrise"
    assert sunrise.mode_id == 900001

    assert day.name == "Day"
    assert day.mode_id == 900002

    assert sunset.name == "Sunset"
    assert sunset.mode_id == 900003

    assert night.name == "Night"
    assert night.mode_id == 900004

    assert overnight.name == "Overnight"
    assert overnight.mode_id == 900005

    assert predawn.name == "Predawn"
    assert predawn.mode_id == 900006


@pytest.mark.asyncio
async def test_apply_mode_posts_empty_json_request() -> None:
    """Applying a mode should match the request BlueIQ expects."""
    mode_id = 900002

    with aioresponses() as mocked:
        mocked.post(
            f"{BASE_URL}/api/mode/{mode_id}/apply",
            status=200,
            body="",
        )

        async with ClientSession() as session:
            client = BlueIQClient(session, TOKEN)
            await client.apply_mode(mode_id)

        request_key = (
            "POST",
            URL(f"{BASE_URL}/api/mode/{mode_id}/apply"),
        )

        requests = mocked.requests[request_key]

    assert len(requests) == 1

    request = requests[0]

    assert request.kwargs["data"] == b""
    assert request.kwargs["headers"]["Content-Type"] == "application/json"


@pytest.mark.asyncio
async def test_get_devices_raises_authentication_error() -> None:
    """The client should distinguish authentication failures."""
    with aioresponses() as mocked:
        mocked.get(
            f"{BASE_URL}/api/device",
            status=401,
            body="Unauthorized",
        )

        async with ClientSession() as session:
            client = BlueIQClient(session, TOKEN)

            with pytest.raises(BlueIQAuthenticationError):
                await client.get_devices()


@pytest.mark.asyncio
async def test_get_modes_rejects_invalid_response_shape() -> None:
    """A non-list mode response should raise a protocol error."""
    with aioresponses() as mocked:
        mocked.get(
            f"{BASE_URL}/api/mode/{DEVICE_NAME}",
            payload={"unexpected": "response"},
            status=200,
        )

        async with ClientSession() as session:
            client = BlueIQClient(session, TOKEN)

            with pytest.raises(
                BlueIQProtocolError,
                match="Expected a list of modes",
            ):
                await client.get_modes(DEVICE_NAME)
