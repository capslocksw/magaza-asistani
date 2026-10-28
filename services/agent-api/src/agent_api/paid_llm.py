"""Gemini behind the spend guard (ADR 007): every request reserves its worst case before it leaves the process."""

from __future__ import annotations

from collections.abc import AsyncGenerator
from typing import Any

from google.adk.models import Gemini, LlmRequest, LlmResponse
from google.genai import errors, types
from pydantic import PrivateAttr

from magaza_core.budget import BudgetGuard


def request_chars(llm_request: LlmRequest) -> int:
    """Size of everything sent to the model (contents, system instruction, tool declarations) as JSON text."""
    size = sum(len(c.model_dump_json(exclude_none=True)) for c in llm_request.contents)
    if llm_request.config is not None:
        size += len(llm_request.config.model_dump_json(exclude_none=True, exclude={"http_options"}))
    return size


def billed_tokens(usage: types.GenerateContentResponseUsageMetadata) -> tuple[int, int]:
    """(input, output) as billed: tool-use prompt counts as input, thinking tokens as output."""
    tokens_in = (usage.prompt_token_count or 0) + (usage.tool_use_prompt_token_count or 0)
    tokens_out = (usage.candidates_token_count or 0) + (usage.thoughts_token_count or 0)
    return tokens_in, tokens_out


class BudgetedGemini(Gemini):
    """ADK Gemini model whose requests are reserved and settled in the shared spend ledger."""

    _guard: BudgetGuard = PrivateAttr()

    def __init__(self, *, guard: BudgetGuard, **data: Any) -> None:
        super().__init__(**data)
        self._guard = guard

    async def generate_content_async(
        self, llm_request: LlmRequest, stream: bool = False
    ) -> AsyncGenerator[LlmResponse, None]:
        cap = self._guard.config.budget.max_output_tokens
        config = llm_request.config or types.GenerateContentConfig()
        config.max_output_tokens = min(config.max_output_tokens or cap, cap)  # bounds the worst case
        llm_request.config = config
        reservation = self._guard.reserve(
            self.model, "chat", self._guard.estimate_tokens(request_chars(llm_request)), cap
        )
        usage: types.GenerateContentResponseUsageMetadata | None = None
        try:
            async for response in super().generate_content_async(llm_request, stream):
                if response.usage_metadata is not None:
                    usage = response.usage_metadata
                yield response
        except errors.ClientError:
            self._guard.release(reservation)  # rejected requests (4xx, incl. 429) are not billed
            raise
        except BaseException:
            self._guard.settle_estimate(reservation)  # includes a consumer closing the stream early
            raise
        if usage is None:
            self._guard.settle_estimate(reservation)
        else:
            self._guard.settle(reservation, *billed_tokens(usage))
