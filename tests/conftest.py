"""Shared pytest fixtures for BlueIQ tests."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

pytest_plugins = [
    "pytest_homeassistant_custom_component",
]


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(
    enable_custom_integrations: None,
) -> None:
    """Enable custom integrations during tests."""


FIXTURES_DIR = Path(__file__).parent / "fixtures"


def load_json_fixture(filename: str) -> Any:
    """Load a JSON fixture."""
    with (FIXTURES_DIR / filename).open(encoding="utf-8") as file:
        return json.load(file)


@pytest.fixture
def device_payload() -> list[dict[str, Any]]:
    """Return a sanitized device payload."""
    return load_json_fixture("devices.json")


@pytest.fixture
def mode_payload() -> list[dict[str, Any]]:
    """Return a sanitized mode payload."""
    return load_json_fixture("modes.json")
