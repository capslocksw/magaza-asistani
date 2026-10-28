"""Paid Gemini behind the spend guard (ADR 007); the real API is never called (parent model is stubbed)."""

from __future__ import annotations

from collections.abc import AsyncGenerator
from pathlib import Path

import pytest
from agent_test_helpers import chat, client, of_type
from google.adk.models import Gemini, LlmRequest, LlmResponse
from google.genai import errors, types

from agent_api.paid_llm import BudgetedGemini, billed_tokens
from magaza_core.budget import BudgetExceeded, BudgetGuard, SpendLedger
from magaza_core.llm_config import BudgetConfig, load_llm_config

MODEL = load_llm_config().chat.default_model
USAGE = types.GenerateContentResponseUsageMetadata(
    prompt_token_count=1200,
    candidates_token_count=150,
    thoughts_token_count=90,
    tool_use_prompt_token_count=30,
)


def guard(tmp_path: Path, cap: float = 5.0) -> BudgetGuard:
    budget = BudgetConfig(hard_cap_usd=cap, safety_margin_usd=0, max_output_tokens=4096, chars_per_token=2.5)
    return BudgetGuard(
        load_llm_config().model_copy(update={"budget": budget}), SpendLedger(tmp_path / "ledger.sqlite")
    )


def request() -> LlmRequest:
    return LlmRequest(
        model=MODEL,
        contents=[types.Content(role="user", parts=[types.Part(text="Kornişim koptu, matkabım yok")])],
        config=types.GenerateContentConfig(system_instruction="Teknik Usta", max_output_tokens=60_000),
    )


@pytest.fixture
def upstream(monkeypatch: pytest.MonkeyPatch) -> list[LlmRequest]:
    """Stands in for the network call of ADK's Gemini; records what would have been sent."""
    sent: list[LlmRequest] = []

    async def fake(
        self: Gemini, llm_request: LlmRequest, stream: bool = False
    ) -> AsyncGenerator[LlmResponse, None]:
        sent.append(llm_request)
        if "reddet" in str(llm_request.contents):
            raise errors.ClientError(400, {"error": {"message": "invalid"}})
        yield LlmResponse(
            content=types.Content(role="model", parts=[types.Part(text="Montaj yapıştırıcısı öneririm.")]),
            usage_metadata=USAGE,
        )

    monkeypatch.setattr(Gemini, "generate_content_async", fake)
    return sent


async def drain(model: BudgetedGemini, req: LlmRequest) -> list[LlmResponse]:
    return [r async for r in model.generate_content_async(req)]


async def test_request_is_reserved_capped_and_settled(tmp_path: Path, upstream: list[LlmRequest]) -> None:
    g = guard(tmp_path)
    await drain(BudgetedGemini(model=MODEL, guard=g), request())
    assert upstream[0].config is not None and upstream[0].config.max_output_tokens == 4096
    totals = g.ledger.totals()
    assert totals.in_flight_usd == 0 and totals.calls == 1
    assert totals.spent_usd == pytest.approx(g.cost(MODEL, *billed_tokens(USAGE)))
    assert billed_tokens(USAGE) == (1230, 240)


async def test_refused_request_never_leaves_the_process(tmp_path: Path, upstream: list[LlmRequest]) -> None:
    g = guard(tmp_path, cap=1e-6)
    with pytest.raises(BudgetExceeded):
        await drain(BudgetedGemini(model=MODEL, guard=g), request())
    assert upstream == [] and g.ledger.totals().refused == 1


async def test_rejected_request_is_released(tmp_path: Path, upstream: list[LlmRequest]) -> None:
    g = guard(tmp_path)
    req = request()
    req.contents[0].parts = [types.Part(text="reddet")]
    with pytest.raises(errors.ClientError):
        await drain(BudgetedGemini(model=MODEL, guard=g), req)
    assert len(upstream) == 1 and g.ledger.totals().committed_usd == 0


@pytest.mark.emulator
def test_chat_reports_budget_exhaustion(
    seeded_project: str, tmp_path: Path, upstream: list[LlmRequest]
) -> None:
    exhausted = BudgetedGemini(model=MODEL, guard=guard(tmp_path, cap=1e-6))
    with client(seeded_project, exhausted) as (c, _deps):
        events = chat(c, "pk_test_yapimarket", "Kornişim koptu, matkabım yok")
    errors_ = of_type(events, "error")
    assert [e["code"] for e in errors_] == ["budget_exceeded"] and upstream == []
