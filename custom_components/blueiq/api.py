"""Async client for the unofficial BlueIQ cloud API."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from aiohttp import (
    ClientError,
    ClientResponseError,
    ClientSession,
    ClientTimeout,
)

from .const import (
    API_BASE_URL,
    DEFAULT_APP_BUILD,
    DEFAULT_APP_PLATFORM,
    DEFAULT_APP_VERSION,
    HEADER_APP_BUILD,
    HEADER_APP_PLATFORM,
    HEADER_APP_VERSION,
    CONF_TOKEN,
    SCHEDULE_OVERRIDE_MINUTES,
)

DEFAULT_TIMEOUT = ClientTimeout(total=15)

# Replace this with the exact login endpoint you captured.
LOGIN_PATH = "/api/account/login"


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
        token: str | None = None,
        *,
        base_url: str = API_BASE_URL,
    ) -> None:
        self._session = session
        self._token = token
        self._base_url = base_url.rstrip("/")

    @property
    def token(self) -> str | None:
        """Return the current authentication token."""
        return self._token

    @property
    def is_authenticated(self) -> bool:
        """Return whether the client currently has a token."""
        return bool(self._token)

    def _build_headers(
        self,
        *,
        include_token: bool,
        extra_headers: dict[str, str] | None = None,
    ) -> dict[str, str]:
        """Build headers for a BlueIQ request."""
        headers = {
            HEADER_APP_VERSION: DEFAULT_APP_VERSION,
            HEADER_APP_PLATFORM: DEFAULT_APP_PLATFORM,
            HEADER_APP_BUILD: DEFAULT_APP_BUILD,
            "Accept": "application/json",
        }

        if include_token and self._token:
            headers[CONF_TOKEN] = self._token

        if extra_headers:
            headers.update(extra_headers)

        return headers

    async def _request(
        self,
        method: str,
        path: str,
        *,
        data: bytes | None = None,
        json_data: dict[str, Any] | None = None,
        include_token: bool = True,
        extra_headers: dict[str, str] | None = None,
    ) -> Any:
        """Send a request to the BlueIQ API."""
        if data is not None and json_data is not None:
            raise ValueError("Provide either data or json_data, not both")

        url = f"{self._base_url}{path}"

        headers = self._build_headers(
            include_token=include_token,
            extra_headers=extra_headers,
        )

        try:
            async with self._session.request(
                method,
                url,
                headers=headers,
                data=data,
                json=json_data,
                timeout=DEFAULT_TIMEOUT,
            ) as response:
                body = await response.read()
                body_text = body.decode(errors="replace") if body else ""

                if response.status in {401, 403}:
                    raise BlueIQAuthenticationError(
                        body_text or "BlueIQ rejected the supplied authentication"
                    )

                if response.status >= 400:
                    raise BlueIQError(
                        f"BlueIQ returned HTTP {response.status}"
                        + (f": {body_text}" if body_text else "")
                    )

                if not body:
                    return None

                content_type = response.headers.get("Content-Type", "")

                if "application/json" in content_type:
                    try:
                        return await response.json()
                    except (ValueError, TypeError) as error:
                        raise BlueIQProtocolError(
                            "BlueIQ returned invalid JSON"
                        ) from error

                return body_text

        except BlueIQError:
            raise
        except ClientResponseError as error:
            raise BlueIQError(f"BlueIQ returned HTTP {error.status}") from error
        except ClientError as error:
            raise BlueIQConnectionError("Could not connect to BlueIQ") from error

    async def authenticate(
        self,
        email: str,
        password: str,
    ) -> str:
        """Authenticate with BlueIQ and store the returned token.

        Update the login path, request field names, and response parsing
        to match the successful request captured from the BlueIQ app.
        """
        payload = await self._request(
            "POST",
            LOGIN_PATH,
            include_token=False,
            json_data={
                # Replace these field names if the captured request differs.
                "email": email,
                "password": password,
            },
        )

        token = self._extract_token(payload)

        self._token = token
        return token

    @staticmethod
    def _extract_token(payload: Any) -> str:
        """Extract the BlueIQ JWT from a login response."""
        if not isinstance(payload, dict):
            raise BlueIQProtocolError("Expected the login response to be a JSON object")

        # Keep only the variants actually seen in the captured response.
        possible_fields = (
            "token",
            "accessToken",
            "access_token",
            "jwt",
        )

        for field in possible_fields:
            value = payload.get(field)

            if isinstance(value, str) and value:
                return value

        # Sometimes APIs nest session information.
        session = payload.get("session")

        if isinstance(session, dict):
            for field in possible_fields:
                value = session.get(field)

                if isinstance(value, str) and value:
                    return value

        raise BlueIQProtocolError(
            "The login response did not contain an authentication token"
        )

    def _require_token(self) -> None:
        """Raise if an authenticated operation is attempted without a token."""
        if not self._token:
            raise BlueIQAuthenticationError("BlueIQ authentication is required")

    async def get_devices(self) -> list[BlueIQDevice]:
        """Return devices available to the account."""
        self._require_token()

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

            nickname = raw.get("nickname")
            status = raw.get("status")
            firmware_version = raw.get("firmwareVersion")
            last_seen = raw.get("lastSeen")
            product_code = product.get("productCode")

            devices.append(
                BlueIQDevice(
                    device_name=device_name,
                    nickname=(
                        nickname
                        if isinstance(nickname, str) and nickname
                        else device_name
                    ),
                    status=(
                        status if isinstance(status, str) and status else "unknown"
                    ),
                    firmware_version=(
                        firmware_version if isinstance(firmware_version, str) else None
                    ),
                    last_seen=(last_seen if isinstance(last_seen, str) else None),
                    product_code=(
                        product_code if isinstance(product_code, str) else None
                    ),
                )
            )

        return devices

    async def get_modes(
        self,
        device_name: str,
    ) -> list[BlueIQMode]:
        """Return available modes for a device."""
        self._require_token()

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
            preset_type = raw.get("presetType")
            raw_device_name = raw.get("deviceName")

            if not isinstance(mode_id, int):
                continue

            if not isinstance(name, str) or not name:
                continue

            modes.append(
                BlueIQMode(
                    mode_id=mode_id,
                    name=name,
                    preset_type=(preset_type if isinstance(preset_type, str) else None),
                    device_name=(
                        raw_device_name
                        if isinstance(raw_device_name, str)
                        else device_name
                    ),
                )
            )

        return modes

    async def apply_mode(self, mode_id: int) -> None:
        """Apply a mode."""
        self._require_token()

        await self._request(
            "POST",
            f"/api/mode/{mode_id}/apply",
            data=b"",
            extra_headers={
                "Content-Type": "application/json",
            },
        )

    async def validate_token(self) -> bool:
        """Validate the current BlueIQ token."""
        self._require_token()

        await self._request(
            "POST",
            "/api/account/open",
            data=b"",
            extra_headers={
                "Content-Type": "application/json",
            },
        )

        return True

    async def set_schedule_override(
        self,
        device_name: str,
        duration_minutes: int,
    ) -> None:
        """Override the device schedule for a number of minutes."""
        if duration_minutes <= 0:
            raise ValueError("Override duration must be greater than zero")

        await self._request(
            "PUT",
            f"/api/schedule/override/{device_name}/{duration_minutes}",
            data=b"",
            extra_headers={
                "Content-Type": "application/json",
            },
        )
