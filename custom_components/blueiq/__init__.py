"""The BlueIQ integration."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME, Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import (
    BlueIQAuthenticationError,
    BlueIQClient,
    BlueIQConnectionError,
)
from .const import CONF_TOKEN
from .coordinator import BlueIQCoordinator

PLATFORMS: list[Platform] = [
    Platform.SELECT,
]


type BlueIQConfigEntry = ConfigEntry[BlueIQCoordinator]


async def async_setup_entry(
    hass: HomeAssistant,
    entry: BlueIQConfigEntry,
) -> bool:
    """Set up BlueIQ from a config entry."""
    session = async_get_clientsession(hass)

    token = entry.data.get(CONF_TOKEN)
    client = BlueIQClient(session, token=token)

    try:
        if token:
            await client.validate_token()
        else:
            token = await client.authenticate(
                entry.data[CONF_USERNAME],
                entry.data[CONF_PASSWORD],
            )

            hass.config_entries.async_update_entry(
                entry,
                data={
                    **entry.data,
                    CONF_TOKEN: token,
                },
            )

    except BlueIQAuthenticationError as error:
        raise ConfigEntryAuthFailed("BlueIQ authentication failed") from error

    except BlueIQConnectionError as error:
        raise RuntimeError("Unable to connect to BlueIQ") from error

    coordinator = BlueIQCoordinator(
        hass=hass,
        config_entry=entry,
        client=client,
    )

    await coordinator.async_config_entry_first_refresh()

    entry.runtime_data = coordinator

    await hass.config_entries.async_forward_entry_setups(
        entry,
        PLATFORMS,
    )

    return True


async def async_unload_entry(
    hass: HomeAssistant,
    entry: BlueIQConfigEntry,
) -> bool:
    """Unload a BlueIQ config entry."""
    return await hass.config_entries.async_unload_platforms(
        entry,
        PLATFORMS,
    )
