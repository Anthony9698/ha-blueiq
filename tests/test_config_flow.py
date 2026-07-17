"""Tests for the BlueIQ config flow."""

from unittest.mock import AsyncMock, patch

import pytest

from homeassistant import config_entries
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType

from custom_components.blueiq.api import (
    BlueIQAuthenticationError,
    BlueIQDevice,
)
from custom_components.blueiq.const import CONF_TOKEN, DOMAIN

MOCK_USERNAME = "test@example.com"
MOCK_PASSWORD = "test-password"
MOCK_TOKEN = "test-token"


@pytest.mark.asyncio
async def test_user_flow_success(
    hass: HomeAssistant,
) -> None:
    """Test successful BlueIQ setup."""
    device = BlueIQDevice(
        device_name="TEST-DEVICE-001",
        nickname="Fish Light",
        status="connected",
        firmware_version="0.6.1",
        last_seen=None,
        product_code="OPTIBRIGHT",
    )

    with patch(
        "custom_components.blueiq.config_flow.BlueIQClient"
    ) as mock_client_class:
        mock_client = mock_client_class.return_value
        mock_client.authenticate = AsyncMock(return_value=MOCK_TOKEN)
        mock_client.get_devices = AsyncMock(return_value=[device])

        result = await hass.config_entries.flow.async_init(
            DOMAIN,
            context={
                "source": config_entries.SOURCE_USER,
            },
        )

        assert result["type"] is FlowResultType.FORM
        assert result["step_id"] == "user"

        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {
                CONF_USERNAME: MOCK_USERNAME,
                CONF_PASSWORD: MOCK_PASSWORD,
            },
        )

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == "BlueIQ"
    assert result["data"] == {
        CONF_USERNAME: MOCK_USERNAME,
        CONF_PASSWORD: MOCK_PASSWORD,
        CONF_TOKEN: MOCK_TOKEN,
    }


@pytest.mark.asyncio
async def test_user_flow_invalid_auth(
    hass: HomeAssistant,
) -> None:
    """Test invalid BlueIQ credentials."""
    with patch(
        "custom_components.blueiq.config_flow.BlueIQClient"
    ) as mock_client_class:
        mock_client = mock_client_class.return_value
        mock_client.authenticate = AsyncMock(
            side_effect=BlueIQAuthenticationError("Invalid credentials")
        )

        result = await hass.config_entries.flow.async_init(
            DOMAIN,
            context={
                "source": config_entries.SOURCE_USER,
            },
        )

        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {
                CONF_USERNAME: MOCK_USERNAME,
                CONF_PASSWORD: MOCK_PASSWORD,
            },
        )

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"
    assert result["errors"] == {
        "base": "invalid_auth",
    }
