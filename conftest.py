"""Shared pytest configuration for every Python package in the workspace."""

from __future__ import annotations

import os

import pytest


def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    if os.environ.get("FIRESTORE_EMULATOR_HOST"):
        return
    skip = pytest.mark.skip(reason="FIRESTORE_EMULATOR_HOST not set (run via `make test`)")
    for item in items:
        if "emulator" in item.keywords:
            item.add_marker(skip)


def pytest_configure(config: pytest.Config) -> None:
    config.addinivalue_line("markers", "emulator: needs the Firestore emulator")
