"""Shared pytest fixtures for BlueIQ tests."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

FIXTURES_DIR = Path(__file__).parent / "fixtures"


def load_json_fixture(filename: str) -> Any:
    """Load a JSON fixture by filename."""
    fixture_path = FIXTURES_DIR / filename

    with fixture_path.open(encoding="utf-8") as fixture_file:
        return json.load(fixture_file)


@pytest.fixture
def device_payload() -> list[dict[str, Any]]:
    """Return the sanitized BlueIQ device response."""
    return load_json_fixture("devices.json")


@pytest.fixture
def mode_payload() -> list[dict[str, Any]]:
    """Return the sanitized BlueIQ mode response."""
    return load_json_fixture("modes.json")
