"""Tests for the BlueIQ coordinator."""

from __future__ import annotations

from unittest.mock import AsyncMock, Mock

import pytest

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from custom_components.blueiq.api import (
    BlueIQClient,
    BlueIQDevice,
    BlueIQMode,
)
from custom_components.blueiq.coordinator import BlueIQCoordinator


@pytest.mark.asyncio
async def test_coordinator_fetches_devices_and_modes(
    hass: HomeAssistant,
) -> None:
    """The coordinator should fetch devices and their modes."""
    device = BlueIQDevice(
        device_name="TEST-DEVICE-001",
        nickname="Fish Light",
        status="connected",
        firmware_version="0.6.1",
        last_seen=None,
        product_code="OPTIBRIGHT",
    )

    mode = BlueIQMode(
        mode_id=900001,
        name="Day",
        preset_type="DAY",
        device_name=device.device_name,
    )

    client = AsyncMock(spec=BlueIQClient)
    client.get_devices.return_value = [device]
    client.get_modes.return_value = [mode]

    config_entry = Mock(spec=ConfigEntry)
    config_entry.entry_id = "test-entry"

    coordinator = BlueIQCoordinator(
        hass=hass,
        config_entry=config_entry,
        client=client,
    )

    data = await coordinator._async_update_data()

    assert data.devices == {
        device.device_name: device,
    }

    assert data.modes == {
        device.device_name: (mode,),
    }

    client.get_devices.assert_awaited_once_with()
    client.get_modes.assert_awaited_once_with(device.device_name)
