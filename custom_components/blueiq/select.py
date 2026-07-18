"""BlueIQ mode select entities."""

from __future__ import annotations

from homeassistant.components.select import SelectEntity
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import BlueIQConfigEntry
from .api import BlueIQClient, BlueIQDevice, BlueIQMode
from .const import DOMAIN


async def async_setup_entry(
    hass,
    entry: BlueIQConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up BlueIQ mode selectors."""
    client = entry.runtime_data
    devices = await client.get_devices()

    entities: list[BlueIQModeSelect] = []

    for device in devices:
        modes = await client.get_modes(device.device_name)

        entities.append(
            BlueIQModeSelect(
                client=client,
                device=device,
                modes=modes,
            )
        )

    async_add_entities(entities)


class BlueIQModeSelect(SelectEntity):
    """Select entity for a BlueIQ lighting mode."""

    _attr_has_entity_name = True
    _attr_name = "Mode"
    _attr_icon = "mdi:theme-light-dark"

    def __init__(
        self,
        *,
        client: BlueIQClient,
        device: BlueIQDevice,
        modes: list[BlueIQMode],
    ) -> None:
        self._client = client
        self._device = device
        self._modes = modes

        self._attr_unique_id = f"{device.device_name}_mode"
        self._attr_options = [mode.name for mode in modes]

        self._attr_device_info = DeviceInfo(
            identifiers={
                (DOMAIN, device.device_name),
            },
            name=device.nickname,
            manufacturer="BlueIQ",
            model=device.product_code or "Unknown",
            sw_version=device.firmware_version,
        )

    async def async_select_option(
        self,
        option: str,
    ) -> None:
        """Apply the selected BlueIQ mode."""
        mode = next(
            (mode for mode in self._modes if mode.name == option),
            None,
        )

        if mode is None:
            raise ValueError(f"Unknown BlueIQ mode: {option}")

        await self._client.apply_mode(mode.mode_id)

        self._attr_current_option = option
