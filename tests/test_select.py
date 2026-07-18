"""Tests for the BlueIQ select platform."""

from __future__ import annotations

from unittest.mock import AsyncMock, Mock

import pytest

from custom_components.blueiq.api import (
    BlueIQDevice,
    BlueIQMode,
)
from custom_components.blueiq.coordinator import (
    BlueIQCoordinator,
    BlueIQData,
)
from custom_components.blueiq.select import BlueIQModeSelect


@pytest.mark.asyncio
async def test_select_option_applies_mode() -> None:
    """Selecting an option should use the coordinator."""
    device_name = "TEST-DEVICE-001"

    device = BlueIQDevice(
        device_name=device_name,
        nickname="Fish Light",
        status="connected",
        firmware_version="0.6.1",
        last_seen=None,
        product_code="OPTIBRIGHT",
    )

    modes = (
        BlueIQMode(
            mode_id=900001,
            name="Overnight",
            preset_type="OVERNIGHT",
            device_name=device_name,
        ),
        BlueIQMode(
            mode_id=900002,
            name="Predawn",
            preset_type="EARLY_MORNING",
            device_name=device_name,
        ),
    )

    coordinator = Mock()
    coordinator.data = BlueIQData(
        devices={
            device_name: device,
        },
        modes={
            device_name: modes,
        },
        selected_modes={},
    )
    coordinator.last_update_success = True
    coordinator.async_apply_mode = AsyncMock()

    entity = BlueIQModeSelect(
        coordinator=coordinator,
        device_name=device_name,
    )

    assert entity.options == [
        "Overnight",
        "Predawn",
    ]
    assert entity.current_option is None

    await entity.async_select_option("Predawn")

    coordinator.async_apply_mode.assert_awaited_once_with(
        device_name=device_name,
        option="Predawn",
    )
