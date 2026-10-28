"""Spend guard (ADR 007): paid requests are reserved before they are sent and refused past the cap."""

from __future__ import annotations

import threading
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest
from google.genai import errors

from magaza_core.budget import BudgetExceeded, BudgetGuard, SpendLedger, get_budget_guard
from magaza_core.embedding import HashingEmbedder, VertexEmbedder, get_embedder
from magaza_core.llm_config import BudgetConfig, LlmConfig, load_llm_config

MODEL = "gemini-3.8-flash"


def guard(tmp_path: Path, cap: float = 5.0, margin: float = 0.0, run_cap: float | None = None) -> BudgetGuard:
    budget = BudgetConfig(
        hard_cap_usd=cap, safety_margin_usd=margin, max_output_tokens=4096, chars_per_token=2.5
    )
    config = load_llm_config().model_copy(update={"budget": budget})
    return BudgetGuard(config, SpendLedger(tmp_path / "ledger.sqlite"), run_cap)


def test_repo_config_caps_real_spend_at_five_dollars() -> None:
    cfg: LlmConfig = load_llm_config()
    assert 0 < cfg.budget.hard_cap_usd <= 5.0  # agreed hard limit for real Gemini spend
    assert cfg.budget.hard_cap_usd - cfg.budget.safety_margin_usd > 0
    assert cfg.price(cfg.chat.default_model) is not None and cfg.price(cfg.embedding.model) is not None


def test_reserve_settle_and_release(tmp_path: Path) -> None:
    g = guard(tmp_path)
    worst = g.cost(MODEL, 10_000, 4096)
    first = g.reserve(MODEL, "chat", 10_000, 4096)
    assert first.estimate_usd == pytest.approx(worst)
    assert g.ledger.totals().in_flight_usd == pytest.approx(worst)
    assert g.settle(first, 2_000, 300) == pytest.approx(g.cost(MODEL, 2_000, 300))
    rejected = g.reserve(MODEL, "chat", 1_000, 4096)
    g.release(rejected)  # 4xx: not billed
    unknown = g.reserve(MODEL, "chat", 1_000, 4096)
    g.settle_estimate(unknown)  # timeout: worst case stays on the books
    totals = g.ledger.totals()
    assert totals.in_flight_usd == 0
    assert totals.spent_usd == pytest.approx(g.cost(MODEL, 2_000, 300) + unknown.estimate_usd)
    assert g.status()["by_model"][MODEL]["calls"] == 2  # type: ignore[index]


def test_request_past_the_cap_is_refused_and_recorded(tmp_path: Path) -> None:
    worst = guard(tmp_path / "probe").cost(MODEL, 10_000, 4096)
    g = guard(tmp_path, cap=worst * 1.5 + 0.01, margin=0.01)  # room for one worst case, not two
    g.reserve(MODEL, "chat", 10_000, 4096)
    with pytest.raises(BudgetExceeded, match="not sent"):
        g.reserve(MODEL, "chat", 10_000, 4096)
    totals = g.ledger.totals()
    assert totals.refused == 1 and totals.committed_usd <= g.limit_usd
    # the ledger is shared: a fresh guard (another process) sees the same commitment
    with pytest.raises(BudgetExceeded):
        BudgetGuard(g.config, SpendLedger(g.ledger.path)).reserve(MODEL, "chat", 10_000, 4096)


def test_concurrent_reservations_never_exceed_the_limit(tmp_path: Path) -> None:
    g = guard(tmp_path, cap=0.01)
    cost = g.cost(MODEL, 0, 200)  # 0.000825 USD each -> 12 fit under 0.01
    allowed: list[bool] = []

    def worker() -> None:
        try:
            BudgetGuard(g.config, SpendLedger(g.ledger.path)).reserve(MODEL, "chat", 0, 200)
            allowed.append(True)
        except BudgetExceeded:
            allowed.append(False)

    threads = [threading.Thread(target=worker) for _ in range(20)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert allowed.count(True) == int(0.01 // cost) and g.ledger.totals().committed_usd <= 0.01


def test_run_cap_and_unpriced_models(tmp_path: Path) -> None:
    g = guard(tmp_path, run_cap=0.02)
    g.reserve(MODEL, "chat", 10_000, 0)  # ~0.008 USD
    with pytest.raises(BudgetExceeded, match="run cap"):
        g.reserve(MODEL, "chat", 10_000, 4096)
    with pytest.raises(BudgetExceeded, match="no price"):
        g.reserve("gemini-unknown-model", "chat", 1, 1)


def test_cloud_run_refuses_the_local_ledger(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("K_SERVICE", "agent-api")
    with pytest.raises(RuntimeError, match="shared spend ledger"):
        get_budget_guard()


def test_llm_mode_does_not_switch_on_paid_embeddings(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LLM_MODE", "vertex")
    monkeypatch.delenv("EMBEDDING_MODE", raising=False)
    assert isinstance(get_embedder(), HashingEmbedder)
    monkeypatch.setenv("EMBEDDING_MODE", "vertx")
    with pytest.raises(ValueError, match="EMBEDDING_MODE"):
        get_embedder()


class FakeModels:
    def __init__(self, fail: Exception | None = None) -> None:
        self.fail = fail
        self.calls = 0

    async def embed_content(self, *, model: str, contents: list[str], config: Any) -> Any:
        self.calls += 1
        if self.fail:
            raise self.fail
        return SimpleNamespace(
            embeddings=[
                SimpleNamespace(values=[1.0, 0.0], statistics=SimpleNamespace(token_count=7.0))
                for _ in contents
            ]
        )


def fake_client(models: FakeModels) -> Any:
    return SimpleNamespace(aio=SimpleNamespace(models=models))


async def test_vertex_embedder_settles_billed_tokens(tmp_path: Path) -> None:
    g = guard(tmp_path)
    models = FakeModels()
    embedder = VertexEmbedder("demo-project", "europe-west1", g, client=fake_client(models))
    vectors = await embedder.embed(["korniş", "silikon tabancası"], "document")
    assert len(vectors) == 2 and models.calls == 2
    assert g.ledger.totals().spent_usd == pytest.approx(2 * g.cost(embedder.name, 7, 0))


async def test_vertex_embedder_refused_or_rejected(tmp_path: Path) -> None:
    exhausted = guard(tmp_path, cap=1e-9)
    models = FakeModels()
    with pytest.raises(BudgetExceeded):
        await VertexEmbedder("p", "europe-west1", exhausted, client=fake_client(models)).embed(
            ["koli"], "query"
        )
    assert models.calls == 0  # refused before the request was sent

    g = guard(tmp_path / "second")
    rejected = FakeModels(fail=errors.ClientError(400, {"error": {"message": "bad request"}}))
    with pytest.raises(errors.ClientError):
        await VertexEmbedder("p", "europe-west1", g, client=fake_client(rejected)).embed(["koli"], "query")
    assert g.ledger.totals().committed_usd == 0
