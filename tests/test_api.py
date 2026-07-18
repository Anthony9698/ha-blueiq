"""Tests for the unofficial BlueIQ API client."""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, patch, Mock

from aiohttp import ClientSession
import pytest

from custom_components.blueiq.api import (
    BlueIQAuthenticationError,
    BlueIQClient,
    BlueIQProtocolError,
)

TOKEN = "test-token"
EXISTING_TOKEN = "existing-token"
DEVICE_NAME = "TEST-DEVICE-001"
EMAIL = "test@example.com"
PASSWORD = "test-password"


@pytest.mark.asyncio
async def test_get_devices_parses_device_response(
    device_payload: list[dict[str, Any]],
) -> None:
    """The client should parse a BlueIQ device response."""
    async with ClientSession() as session:
        client = BlueIQClient(session, TOKEN)

        with patch.object(
            client,
            "_request",
            new=AsyncMock(return_value=device_payload),
        ) as request_mock:
            devices = await client.get_devices()

    request_mock.assert_awaited_once_with(
        "GET",
        "/api/device",
    )

    assert len(devices) == 1

    device = devices[0]

    assert device.device_name == DEVICE_NAME
    assert device.nickname == "Fish Light"
    assert device.status == "connected"
    assert device.firmware_version == "0.6.1"
    assert device.product_code == "OPTIBRIGHT"
    assert device.last_seen is not None


@pytest.mark.asyncio
async def test_get_modes_parses_different_modes(
    mode_payload: list[dict[str, Any]],
) -> None:
    """The client should parse modes without relying on real IDs."""
    async with ClientSession() as session:
        client = BlueIQClient(session, TOKEN)

        with patch.object(
            client,
            "_request",
            new=AsyncMock(return_value=mode_payload),
        ) as request_mock:
            modes = await client.get_modes(DEVICE_NAME)

    request_mock.assert_awaited_once_with(
        "GET",
        f"/api/mode/{DEVICE_NAME}",
    )

    assert len(modes) == 6

    modes_by_preset = {mode.preset_type: mode for mode in modes}

    assert modes_by_preset["SUNRISE"].mode_id == 900001
    assert modes_by_preset["DAY"].mode_id == 900002
    assert modes_by_preset["SUNSET"].mode_id == 900003
    assert modes_by_preset["NIGHT"].mode_id == 900004
    assert modes_by_preset["OVERNIGHT"].mode_id == 900005
    assert modes_by_preset["EARLY_MORNING"].mode_id == 900006


@pytest.mark.asyncio
async def test_apply_mode_builds_expected_request() -> None:
    """Applying a mode should send the required request arguments."""
    mode_id = 900002

    async with ClientSession() as session:
        client = BlueIQClient(session, TOKEN)

        with patch.object(
            client,
            "_request",
            new=AsyncMock(return_value=None),
        ) as request_mock:
            await client.apply_mode(mode_id)

    request_mock.assert_awaited_once_with(
        "POST",
        f"/api/mode/{mode_id}/apply",
        data=b"",
        extra_headers={
            "Content-Type": "application/json",
        },
    )


@pytest.mark.asyncio
async def test_get_modes_rejects_invalid_response_shape() -> None:
    """A non-list mode response should raise a protocol error."""
    async with ClientSession() as session:
        client = BlueIQClient(session, TOKEN)

        with patch.object(
            client,
            "_request",
            new=AsyncMock(return_value={"unexpected": "response"}),
        ):
            with pytest.raises(
                BlueIQProtocolError,
                match="Expected a list of modes",
            ):
                await client.get_modes(DEVICE_NAME)


@pytest.mark.asyncio
async def test_validate_token_posts_account_open() -> None:
    """Validating a token should call account-open."""
    async with ClientSession() as session:
        client = BlueIQClient(session, TOKEN)

        with patch.object(
            client,
            "_request",
            new=AsyncMock(return_value=None),
        ) as request_mock:
            result = await client.validate_token()

    assert result is True

    request_mock.assert_awaited_once_with(
        "POST",
        "/api/account/open",
        data=b"",
        extra_headers={
            "Content-Type": "application/json",
        },
    )


@pytest.mark.asyncio
async def test_authenticate_stores_returned_token() -> None:
    """Authentication should return and store the received token."""
    async with ClientSession() as session:
        client = BlueIQClient(session)

        with patch.object(
            client,
            "_request",
            new=AsyncMock(return_value={"token": TOKEN}),
        ) as request_mock:
            returned_token = await client.authenticate(
                EMAIL,
                PASSWORD,
            )

    assert returned_token == TOKEN
    assert client.token == TOKEN
    assert client.is_authenticated is True

    request_mock.assert_awaited_once_with(
        "POST",
        "/api/account/login",
        include_token=False,
        json_data={
            "email": EMAIL,
            "password": PASSWORD,
        },
    )


@pytest.mark.asyncio
async def test_authenticate_replaces_existing_token() -> None:
    """Authentication should replace a previously stored token."""
    async with ClientSession() as session:
        client = BlueIQClient(
            session,
            token=EXISTING_TOKEN,
        )

        with patch.object(
            client,
            "_request",
            new=AsyncMock(return_value={"token": TOKEN}),
        ) as request_mock:
            returned_token = await client.authenticate(
                EMAIL,
                PASSWORD,
            )

    assert returned_token == TOKEN
    assert client.token == TOKEN

    request_mock.assert_awaited_once_with(
        "POST",
        "/api/account/login",
        include_token=False,
        json_data={
            "email": EMAIL,
            "password": PASSWORD,
        },
    )


@pytest.mark.asyncio
async def test_invalid_credentials_raise_authentication_error() -> None:
    """Invalid credentials should raise an authentication error."""
    async with ClientSession() as session:
        client = BlueIQClient(session)

        with patch.object(
            client,
            "_request",
            new=AsyncMock(side_effect=BlueIQAuthenticationError("Invalid credentials")),
        ):
            with pytest.raises(
                BlueIQAuthenticationError,
                match="Invalid credentials",
            ):
                await client.authenticate(
                    EMAIL,
                    PASSWORD,
                )

    assert client.token is None
    assert client.is_authenticated is False


@pytest.mark.asyncio
async def test_set_schedule_override() -> None:
    """The client should send the schedule override request."""
    client = BlueIQClient(
        session=Mock(),
        token="test-token",
    )
    client._request = AsyncMock()

    await client.set_schedule_override(
        device_name="TEST-DEVICE-001",
        duration_minutes=1440,
    )

    client._request.assert_awaited_once_with(
        "PUT",
        "/api/schedule/override/TEST-DEVICE-001/1440",
        data=b"",
        extra_headers={
            "Content-Type": "application/json",
        },
    )
