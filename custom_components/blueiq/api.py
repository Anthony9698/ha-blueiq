"""Async client for the unofficial BlueIQ cloud API."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from aiohttp import ClientError, ClientResponseError, ClientSession

from .const import (
    API_BASE_URL,
    DEFAULT_APP_BUILD,
    DEFAULT_APP_PLATFORM,
    DEFAULT_APP_VERSION,
    HEADER_APP_BUILD,
    HEADER_APP_PLATFORM,
    HEADER_APP_VERSION,
    HEADER_TOKEN,
)


class BlueIQError(Exception):
    """Base exception for BlueIQ API errors."""


class BlueIQAuthenticationError(BlueIQError):
    """Raised when authentication fails."""


class BlueIQConnectionError(BlueIQError):
    """Raised when BlueIQ cannot be reached."""


class BlueIQProtocolError(BlueIQError):
    """Raised when BlueIQ returns an unexpected response."""


@dataclass(frozen=True, slots=True)
class BlueIQDevice:
    """A BlueIQ device."""

    device_name: str
    nickname: str
    status: str
    firmware_version: str | None
    last_seen: str | None
    product_code: str | None


@dataclass(frozen=True, slots=True)
class BlueIQMode:
    """A BlueIQ lighting mode."""

    mode_id: int
    name: str
    preset_type: str | None
    device_name: str


class BlueIQClient:
    """Client for the unofficial BlueIQ cloud API."""

    def __init__(
        self,
        session: ClientSession,
        token: str,
        *,
        base_url: str = API_BASE_URL,
    ) -> None:
        self._session = session
        self._token = token
        self._base_url = base_url.rstrip("/")

    @property
    def headers(self) -> dict[str, str]:
        """Return headers used by the BlueIQ mobile API."""
        return {
            HEADER_TOKEN: self._token,
            HEADER_APP_VERSION: DEFAULT_APP_VERSION,
            HEADER_APP_PLATFORM: DEFAULT_APP_PLATFORM,
            HEADER_APP_BUILD: DEFAULT_APP_BUILD,
            "Accept": "application/json",
        }

    async def _request(
        self,
        method: str,
        path: str,
        *,
        data: bytes | None = None,
        extra_headers: dict[str, str] | None = None,
    ) -> Any:
        url = f"{self._base_url}{path}"

        headers = self.headers.copy()

        if extra_headers:
            headers.update(extra_headers)

        try:
            async with self._session.request(
                method,
                url,
                headers=headers,
                data=data,
                timeout=15,
            ) as response:
                if response.status in {401, 403}:
                    raise BlueIQAuthenticationError(
                        "BlueIQ rejected the authentication token"
                    )

                response.raise_for_status()

                body = await response.read()

                if not body:
                    return None

                content_type = response.headers.get("Content-Type", "")

                if "application/json" in content_type:
                    return await response.json()

                return body.decode(errors="replace")

        except BlueIQAuthenticationError:
            raise
        except ClientResponseError as error:
            raise BlueIQError(f"BlueIQ returned HTTP {error.status}") from error
        except ClientError as error:
            raise BlueIQConnectionError("Could not connect to BlueIQ") from error

    async def get_devices(self) -> list[BlueIQDevice]:
        """Return devices available to the account."""
        payload = await self._request("GET", "/api/device")

        if not isinstance(payload, list):
            raise BlueIQProtocolError("Expected a list of devices")

        devices: list[BlueIQDevice] = []

        for raw in payload:
            if not isinstance(raw, dict):
                continue

            device_name = raw.get("deviceName")
            if not isinstance(device_name, str):
                continue

            product = raw.get("product")
            if not isinstance(product, dict):
                product = {}

            devices.append(
                BlueIQDevice(
                    device_name=device_name,
                    nickname=raw.get("nickname") or device_name,
                    status=raw.get("status") or "unknown",
                    firmware_version=raw.get("firmwareVersion"),
                    last_seen=raw.get("lastSeen"),
                    product_code=product.get("productCode"),
                )
            )

        return devices

    async def get_modes(self, device_name: str) -> list[BlueIQMode]:
        """Return available modes for a device."""
        payload = await self._request(
            "GET",
            f"/api/mode/{device_name}",
        )

        if not isinstance(payload, list):
            raise BlueIQProtocolError("Expected a list of modes")

        modes: list[BlueIQMode] = []

        for raw in payload:
            if not isinstance(raw, dict):
                continue

            mode_id = raw.get("modeId")
            name = raw.get("modeName") or raw.get("presetName")

            if not isinstance(mode_id, int) or not isinstance(name, str):
                continue

            modes.append(
                BlueIQMode(
                    mode_id=mode_id,
                    name=name,
                    preset_type=raw.get("presetType"),
                    device_name=raw.get("deviceName") or device_name,
                )
            )

        return modes

    async def apply_mode(self, mode_id: int) -> None:
        """Apply a mode."""
        await self._request(
            "POST",
            f"/api/mode/{mode_id}/apply",
            data=b"",
            extra_headers={
                "Content-Type": "application/json",
            },
        )
