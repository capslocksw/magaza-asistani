"""Quota / rate-limit callback and loop guard (pure unit tests, no emulator)."""

from __future__ import annotations

from typing import Any

from agent_api.callbacks import RateLimiter, TurnCallbacks
from agent_api.turn import TurnContext
from magaza_core.contracts import TenantQuotas
from magaza_core.tenancy import TenantContext
from magaza_jobs.demo_data.tenants import tenant_config


class FakeUsage:
    def __init__(self, messages: int = 0) -> None:
        self.messages = messages
        self.increments = 0

    async def get(self, month: str) -> dict[str, int]:
        return {"messages": self.messages, "sessions": 0}

    async def increment(self, month: str, *, messages: int = 0, sessions: int = 0) -> None:
        self.increments += messages


def _callbacks(
    quotas: TenantQuotas, usage: FakeUsage, session_messages: int = 0, limiter: RateLimiter | None = None
) -> TurnCallbacks:
    config = tenant_config("yapi-market").model_copy(update={"quotas": quotas})
    turn = TurnContext(
        tenant=TenantContext.of(config),
        visitor_hash="v" * 32,
        session_id="s1",
        message="x",
        session_messages=session_messages,
    )
    return TurnCallbacks(turn, usage=usage, limiter=limiter or RateLimiter(), max_model_calls=3)  # type: ignore[arg-type]


async def _before(cb: TurnCallbacks) -> Any:
    return await cb.before_model(None, None)  # type: ignore[arg-type]


async def test_rate_limit_blocks_and_reports() -> None:
    limiter = RateLimiter()
    quotas = TenantQuotas(monthly_messages=100, messages_per_session=50, requests_per_minute_per_visitor=2)
    for _ in range(2):
        cb = _callbacks(quotas, FakeUsage(), limiter=limiter)
        assert await _before(cb) is None
    cb = _callbacks(quotas, FakeUsage(), limiter=limiter)
    response = await _before(cb)
    assert response is not None and cb.turn.blocked is not None and cb.turn.blocked.code == "rate_limited"


async def test_monthly_and_session_quotas() -> None:
    quotas = TenantQuotas(monthly_messages=10, messages_per_session=5, requests_per_minute_per_visitor=60)
    cb = _callbacks(quotas, FakeUsage(messages=10))
    await _before(cb)
    assert cb.turn.blocked is not None and cb.turn.blocked.code == "quota_exceeded"
    cb = _callbacks(quotas, FakeUsage(), session_messages=5)
    await _before(cb)
    assert cb.turn.blocked is not None and cb.turn.blocked.code == "quota_exceeded"
    usage = FakeUsage()
    cb = _callbacks(quotas, usage)
    assert await _before(cb) is None and usage.increments == 1


async def test_loop_limit() -> None:
    cb = _callbacks(
        TenantQuotas(monthly_messages=100, messages_per_session=50, requests_per_minute_per_visitor=60),
        FakeUsage(),
    )
    for _ in range(3):
        assert await _before(cb) is None
    assert await _before(cb) is not None and "loop_limit" in cb.turn.guardrails


def test_rate_limiter_window() -> None:
    limiter = RateLimiter()
    assert limiter.allow("t", "v", 1, now=0.0)
    assert not limiter.allow("t", "v", 1, now=30.0)
    assert limiter.allow("t", "v", 1, now=61.0)
