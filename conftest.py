"""Shared pytest configuration for every Python package in the workspace."""

from __future__ import annotations

import asyncio
import os
import tempfile
import uuid
from pathlib import Path

import pytest


def pytest_configure(config: pytest.Config) -> None:
    config.addinivalue_line("markers", "emulator: needs the Firestore emulator")
    os.environ.setdefault("PYTHONUTF8", "1")
    # Tests never reach paid APIs and never touch the real spend ledger (ADR 007).
    os.environ["LLM_MODE"] = "fake"
    os.environ["EMBEDDING_MODE"] = "fake"
    os.environ["LLM_SPEND_LEDGER"] = os.path.join(tempfile.mkdtemp(prefix="llm-spend-"), "ledger.sqlite")


def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    if os.environ.get("FIRESTORE_EMULATOR_HOST"):
        return
    skip = pytest.mark.skip(reason="FIRESTORE_EMULATOR_HOST not set (run via `make test`)")
    for item in items:
        if "emulator" in item.keywords:
            item.add_marker(skip)


@pytest.fixture(autouse=True)
def _no_real_genai_clients(monkeypatch: pytest.MonkeyPatch) -> None:
    """Any attempt to build a real google-genai client (Gemini or Vertex embeddings) fails the test."""
    from google import genai

    def refuse(*_args: object, **_kwargs: object) -> None:
        raise RuntimeError("real google-genai clients are disabled in tests; inject a fake client")

    monkeypatch.setattr(genai.Client, "__init__", refuse)


@pytest.fixture(scope="session")
def demo_data_dir(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """Fresh deterministic demo dataset (without PDF rendering; doc-ingest falls back to Markdown)."""
    from magaza_jobs.demo_data import write_all

    out = tmp_path_factory.mktemp("demo")
    write_all(out, pdf=False, data_dir=out.as_posix())
    return out


@pytest.fixture(scope="session")
def seeded_project(demo_data_dir: Path) -> str:
    """An isolated emulator project (demo-test-*) seeded with both demo tenants, shared by the test session."""
    if not os.environ.get("FIRESTORE_EMULATOR_HOST"):
        pytest.skip("FIRESTORE_EMULATOR_HOST not set")
    from magaza_core.repo import get_db
    from magaza_jobs.seed import seed

    project = f"demo-test-{uuid.uuid4().hex[:8]}"

    async def run() -> None:
        await seed(get_db(project), demo_data_dir)

    asyncio.run(run())
    return project
