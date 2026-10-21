"""ADK callbacks: grounding guardrail, quota / rate limit, loop limit, token accounting."""

from __future__ import annotations

import re
from collections import defaultdict, deque
from datetime import UTC, datetime
from time import monotonic
from typing import Any

from google.adk.agents.callback_context import CallbackContext
from google.adk.models import LlmRequest, LlmResponse
from google.genai import types

from magaza_core.contracts import ErrorEvent
from magaza_core.repo import UsageRepo

from .tools import GROUNDED_KEY, SKU_LIKE
from .turn import TurnContext

GROUNDING_FALLBACK = (
    "Önerebileceğim ürünleri katalogda doğrulayamadım. İhtiyacınızı biraz daha ayrıntılı anlatır mısınız? "
    "Ne yapmak istediğinizi ve kullanılacak yüzeyi ya da ürünü yazarsanız tekrar arayayım."
)


def _text_response(text: str) -> LlmResponse:
    return LlmResponse(content=types.Content(role="model", parts=[types.Part(text=text)]))


def response_text(response: LlmResponse) -> str:
    parts = response.content.parts if response.content and response.content.parts else []
    return "".join(p.text for p in parts if p.text and not p.thought)


def strip_skus(text: str, unknown: set[str]) -> str:
    lowered = {sku.lower() for sku in unknown}
    kept = [line for line in text.splitlines() if not any(sku in line.lower() for sku in lowered)]
    cleaned = "\n".join(kept).strip()
    return cleaned or GROUNDING_FALLBACK


class RateLimiter:
    """Sliding one-minute window per (tenant, visitor). In-process: approximate across Cloud Run instances."""

    def __init__(self) -> None:
        self._hits: dict[tuple[str, str], deque[float]] = defaultdict(deque)

    def allow(self, tenant_id: str, visitor_hash: str, per_minute: int, now: float | None = None) -> bool:
        now = monotonic() if now is None else now
        hits = self._hits[(tenant_id, visitor_hash)]
        while hits and now - hits[0] > 60:
            hits.popleft()
        if len(hits) >= per_minute:
            return False
        hits.append(now)
        return True


class TurnCallbacks:
    def __init__(
        self, turn: TurnContext, *, usage: UsageRepo, limiter: RateLimiter, max_model_calls: int
    ) -> None:
        self.turn = turn
        self.usage = usage
        self.limiter = limiter
        self.max_model_calls = max_model_calls
        self.sku_pattern = re.compile(turn.tenant.config.sku_pattern)

    async def _quota_block(self) -> ErrorEvent | None:
        quotas = self.turn.tenant.config.quotas
        if not self.limiter.allow(
            self.turn.tenant_id, self.turn.visitor_hash, quotas.requests_per_minute_per_visitor
        ):
            return ErrorEvent(
                type="error",
                code="rate_limited",
                message="Çok hızlı mesaj gönderiyorsunuz; lütfen biraz bekleyin.",
            )
        if self.turn.session_messages >= quotas.messages_per_session:
            return ErrorEvent(
                type="error",
                code="quota_exceeded",
                message="Bu sohbetin mesaj sınırına ulaşıldı; yeni bir sohbet başlatın.",
            )
        month = f"{datetime.now(UTC):%Y-%m}"
        if (await self.usage.get(month))["messages"] >= quotas.monthly_messages:
            return ErrorEvent(
                type="error", code="quota_exceeded", message="Asistan bu ay için kullanım sınırına ulaştı."
            )
        await self.usage.increment(month, messages=1, sessions=1 if self.turn.session_messages == 0 else 0)
        return None

    async def before_model(
        self, callback_context: CallbackContext, llm_request: LlmRequest
    ) -> LlmResponse | None:
        self.turn.model_calls += 1
        if self.turn.model_calls == 1:
            blocked = await self._quota_block()
            if blocked:
                self.turn.blocked = blocked
                self.turn.guardrails.append(blocked.code)
                return _text_response(blocked.message)
        if self.turn.model_calls > self.max_model_calls:
            self.turn.guardrails.append("loop_limit")
            return _text_response(
                "Şu anda bu soruya yanıt üretemiyorum; lütfen sorunuzu farklı şekilde sorun."
            )
        return None

    async def after_model(
        self, callback_context: CallbackContext, llm_response: LlmResponse
    ) -> LlmResponse | None:
        usage = llm_response.usage_metadata
        if usage and not llm_response.partial:
            self.turn.tokens_in += usage.prompt_token_count or 0
            self.turn.tokens_out += usage.candidates_token_count or 0
        if llm_response.partial or llm_response.get_function_calls():
            return None
        text = response_text(llm_response)
        mentioned = set(self.sku_pattern.findall(text)) | {m.upper() for m in SKU_LIKE.findall(text)}
        if not mentioned:
            return None
        state_grounded: Any = callback_context.state.get(GROUNDED_KEY, [])
        grounded = set(state_grounded) | self.turn.grounded
        unknown = mentioned - grounded
        if not unknown:
            return None
        if self.turn.grounding_retries == 0:
            # Redirect once: turn the answer into a call of the guardrail tool; the model then rewrites it.
            self.turn.grounding_retries += 1
            self.turn.guardrails.append("grounding_redirect")
            call = types.FunctionCall(name="report_grounding_issue", args={"unknown_skus": sorted(unknown)})
            return LlmResponse(
                content=types.Content(role="model", parts=[types.Part(function_call=call)]),
                usage_metadata=usage,
            )
        self.turn.guardrails.append("grounding_stripped")
        return LlmResponse(
            content=types.Content(role="model", parts=[types.Part(text=strip_skus(text, unknown))]),
            usage_metadata=usage,
        )
