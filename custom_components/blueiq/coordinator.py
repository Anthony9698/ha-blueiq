"""Data coordinator for the BlueIQ integration."""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import timedelta
import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import (
    DataUpdateCoordinator,
    UpdateFailed,
)

from .api import (
    BlueIQAuthenticationError,
    BlueIQClient,
    BlueIQConnectionError,
    BlueIQDevice,
    BlueIQMode,
)

from .const import SCHEDULE_OVERRIDE_MINUTES

_LOGGER = logging.getLogger(__name__)

UPDATE_INTERVAL = timedelta(minutes=5)


@dataclass(frozen=True, slots=True)
class BlueIQData:
    """Runtime data fetched from BlueIQ."""

    devices: dict[str, BlueIQDevice]
    modes: dict[str, tuple[BlueIQMode, ...]]
    selected_modes: dict[str, str]


class BlueIQCoordinator(DataUpdateCoordinator[BlueIQData]):
    """Coordinate BlueIQ API updates."""

    config_entry: ConfigEntry

    def __init__(
        self,
        hass: HomeAssistant,
        config_entry: ConfigEntry,
        client: BlueIQClient,
    ) -> None:
        """Initialize the BlueIQ coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            config_entry=config_entry,
            name="BlueIQ",
            update_interval=UPDATE_INTERVAL,
        )

        self.client = client

    async def _async_update_data(self) -> BlueIQData:
        """Fetch devices and modes from BlueIQ."""
        try:
            devices = await self.client.get_devices()

            _LOGGER.debug(
                "BlueIQ devices response: %s",
                devices,
            )

            devices_by_name = {device.device_name: device for device in devices}

            modes_by_device: dict[str, tuple[BlueIQMode, ...]] = {}

            for device in devices:
                modes = await self.client.get_modes(device.device_name)

                _LOGGER.debug(
                    "BlueIQ modes for %s: %s",
                    device.device_name,
                    modes,
                )

                modes_by_device[device.device_name] = tuple(modes)

        except BlueIQAuthenticationError as error:
            raise ConfigEntryAuthFailed("BlueIQ authentication failed") from error

        except BlueIQConnectionError as error:
            raise UpdateFailed(f"Unable to communicate with BlueIQ: {error}") from error

        except Exception as error:
            raise UpdateFailed(
                f"Unexpected error while updating BlueIQ: {error}"
            ) from error

        previous_selected_modes = (
            self.data.selected_modes if self.data is not None else {}
        )

        selected_modes: dict[str, str] = {}

        for device_name, selected_mode in previous_selected_modes.items():
            available_mode_names = {
                mode.name for mode in modes_by_device.get(device_name, ())
            }

            if selected_mode in available_mode_names:
                selected_modes[device_name] = selected_mode

        return BlueIQData(
            devices=devices_by_name,
            modes=modes_by_device,
            selected_modes=selected_modes,
        )

    async def async_apply_mode(
        self,
        device_name: str,
        option: str,
    ) -> None:
        """Apply a mode and update coordinator state."""
        if self.data is None:
            raise UpdateFailed("BlueIQ data has not been loaded")

        modes = self.data.modes.get(device_name, ())

        mode = next(
            (candidate for candidate in modes if candidate.name == option),
            None,
        )

        if mode is None:
            raise ValueError(
                f"Unknown BlueIQ mode {option!r} " f"for device {device_name!r}"
            )

        try:
            await self.client.apply_mode(mode.mode_id)
            await self.client.set_schedule_override(
                device_name=device_name,
                duration_minutes=SCHEDULE_OVERRIDE_MINUTES,
            )

        except BlueIQAuthenticationError as error:
            raise ConfigEntryAuthFailed("BlueIQ authentication failed") from error

        except BlueIQConnectionError as error:
            raise UpdateFailed(f"Unable to apply BlueIQ mode: {error}") from error

        selected_modes = {
            **self.data.selected_modes,
            device_name: option,
        }

        self.async_set_updated_data(
            replace(
                self.data,
                selected_modes=selected_modes,
            )
        )
