"""Config flow for the BlueIQ integration."""

from __future__ import annotations

from typing import Any

from aiohttp import ClientSession
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME
from homeassistant.data_entry_flow import FlowResult

from homeassistant.helpers.aiohttp_client import (
    async_get_clientsession,
)

from .api import (
    BlueIQAuthenticationError,
    BlueIQConnectionError,
    BlueIQError,
    BlueIQClient,
)
from .const import CONF_TOKEN, DOMAIN

STEP_USER_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_USERNAME): str,
        vol.Required(CONF_PASSWORD): str,
    }
)


class BlueIQConfigFlow(
    config_entries.ConfigFlow,
    domain=DOMAIN,
):
    """Handle a config flow for BlueIQ."""

    VERSION = 1

    async def async_step_user(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> FlowResult:
        """Handle the initial user setup step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            username = user_input[CONF_USERNAME]
            password = user_input[CONF_PASSWORD]

            session = async_get_clientsession(self.hass)
            client = BlueIQClient(session)

            try:
                client = BlueIQClient(session)

                token = await client.authenticate(
                    username,
                    password,
                )

                devices = await client.get_devices()

                if not devices:
                    errors["base"] = "no_devices"
                else:
                    await self.async_set_unique_id(username.lower())
                    self._abort_if_unique_id_configured()

                    return self.async_create_entry(
                        title="BlueIQ",
                        data={
                            CONF_USERNAME: username,
                            CONF_PASSWORD: password,
                            CONF_TOKEN: token,
                        },
                    )

            except BlueIQAuthenticationError:
                errors["base"] = "invalid_auth"
            except BlueIQConnectionError:
                errors["base"] = "cannot_connect"
            except BlueIQError:
                errors["base"] = "unknown"
            finally:
                await session.close()

        return self.async_show_form(
            step_id="user",
            data_schema=STEP_USER_SCHEMA,
            errors=errors,
        )
