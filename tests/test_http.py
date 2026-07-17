"""HTTP contract tests for the BlueIQ API client."""

from __future__ import annotations

from typing import Any

from aiohttp import ClientSession, web
import pytest

from custom_components.blueiq.api import BlueIQClient
from custom_components.blueiq.const import HEADER_TOKEN

TOKEN = "test-token"
EMAIL = "test@example.com"
PASSWORD = "test-password"


@pytest.mark.asyncio
async def test_login_omits_token_and_later_requests_include_it(
    aiohttp_server: Any,
    socket_enabled: None,
) -> None:
    """Login should omit the token; later requests should include it."""
    received: dict[str, Any] = {}

    async def login_handler(
        request: web.Request,
    ) -> web.Response:
        received["login_headers"] = dict(request.headers)
        received["login_body"] = await request.json()

        return web.json_response(
            {
                "token": TOKEN,
            }
        )

    async def devices_handler(
        request: web.Request,
    ) -> web.Response:
        received["device_headers"] = dict(request.headers)

        return web.json_response([])

    app = web.Application()
    app.router.add_post(
        "/api/account/login",
        login_handler,
    )
    app.router.add_get(
        "/api/device",
        devices_handler,
    )

    server = await aiohttp_server(app)

    async with ClientSession() as session:
        client = BlueIQClient(
            session,
            base_url=str(server.make_url("")).rstrip("/"),
        )

        returned_token = await client.authenticate(
            EMAIL,
            PASSWORD,
        )
        await client.get_devices()

    assert returned_token == TOKEN

    assert HEADER_TOKEN not in received["login_headers"]

    assert received["login_body"] == {
        "email": EMAIL,
        "password": PASSWORD,
    }

    assert received["device_headers"][HEADER_TOKEN] == TOKEN


@pytest.mark.asyncio
async def test_apply_mode_sends_empty_json_request(
    aiohttp_server: Any,
    socket_enabled: None,
) -> None:
    """Applying a mode should send the expected request."""
    received: dict[str, Any] = {}
    mode_id = 900002

    async def apply_handler(
        request: web.Request,
    ) -> web.Response:
        received["method"] = request.method
        received["headers"] = dict(request.headers)
        received["body"] = await request.read()

        return web.Response(status=200)

    app = web.Application()
    app.router.add_post(
        f"/api/mode/{mode_id}/apply",
        apply_handler,
    )

    server = await aiohttp_server(app)

    async with ClientSession() as session:
        client = BlueIQClient(
            session,
            token=TOKEN,
            base_url=str(server.make_url("")).rstrip("/"),
        )

        await client.apply_mode(mode_id)

    assert received["method"] == "POST"
    assert received["body"] == b""

    assert received["headers"]["Content-Type"] == "application/json"
    assert received["headers"][HEADER_TOKEN] == TOKEN
