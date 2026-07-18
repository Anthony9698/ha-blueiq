"""Tests for the BlueIQ select platform."""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from homeassistant.core import HomeAssistant

from custom_components.blueiq.api import (
    BlueIQClient,
    BlueIQDevice,
    BlueIQMode,
)
from custom_components.blueiq.select import BlueIQModeSelect


@pytest.mark.asyncio
async def test_select_option_applies_mode(
    hass: HomeAssistant,
) -> None:
    """Selecting an option should apply its BlueIQ mode."""
    client = AsyncMock(spec=BlueIQClient)

    device = BlueIQDevice(
        device_name="TEST-DEVICE-001",
        nickname="Fish Light",
        status="connected",
        firmware_version="0.6.1",
        last_seen=None,
        product_code="OPTIBRIGHT",
    )

    modes = [
        BlueIQMode(
            mode_id=900001,
            name="Overnight",
            preset_type="OVERNIGHT",
            device_name=device.device_name,
        ),
        BlueIQMode(
            mode_id=900002,
            name="Predawn",
            preset_type="EARLY_MORNING",
            device_name=device.device_name,
        ),
    ]

    entity = BlueIQModeSelect(
        client=client,
        device=device,
        modes=modes,
    )

    entity.hass = hass

    await entity.async_select_option("Predawn")

    client.apply_mode.assert_awaited_once_with(900002)
    assert entity.current_option == "Predawn"
