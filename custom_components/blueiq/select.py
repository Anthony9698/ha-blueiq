"""BlueIQ mode select entities."""

from __future__ import annotations

from homeassistant.components.select import SelectEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import BlueIQConfigEntry
from .const import DOMAIN
from .coordinator import BlueIQCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    entry: BlueIQConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up BlueIQ mode select entities."""
    coordinator = entry.runtime_data

    async_add_entities(
        BlueIQModeSelect(
            coordinator=coordinator,
            device_name=device_name,
        )
        for device_name in coordinator.data.devices
    )


class BlueIQModeSelect(
    CoordinatorEntity[BlueIQCoordinator],
    SelectEntity,
):
    """Select entity for a BlueIQ lighting mode."""

    _attr_has_entity_name = True
    _attr_name = "Mode"
    _attr_icon = "mdi:theme-light-dark"

    def __init__(
        self,
        coordinator: BlueIQCoordinator,
        device_name: str,
    ) -> None:
        """Initialize the mode selector."""
        super().__init__(
            coordinator,
            context=device_name,
        )

        self._device_name = device_name
        self._attr_unique_id = f"{device_name}_mode"

        device = coordinator.data.devices[device_name]

        device_display_name = getattr(device, "nickname", None) or device_name

        product_code = getattr(device, "product_code", None)
        firmware_version = getattr(device, "firmware_version", None)

        device_info: dict = {
            "identifiers": {
                (DOMAIN, device_name),
            },
            "name": device_display_name,
            "manufacturer": "Aqueon / BlueIQ",
        }

        if product_code:
            device_info["model"] = product_code

        if firmware_version:
            device_info["sw_version"] = firmware_version

        self._attr_device_info = DeviceInfo(**device_info)

    @property
    def options(self) -> list[str]:
        """Return available BlueIQ modes."""
        modes = self.coordinator.data.modes.get(
            self._device_name,
            (),
        )

        return [mode.name for mode in modes]

    @property
    def current_option(self) -> str | None:
        """Return the currently selected mode."""
        return self.coordinator.data.selected_modes.get(self._device_name)

    async def async_select_option(
        self,
        option: str,
    ) -> None:
        """Apply the selected BlueIQ mode."""
        await self.coordinator.async_apply_mode(
            device_name=self._device_name,
            option=option,
        )
