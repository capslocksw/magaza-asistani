"""Grounding guardrail: an answer may only mention SKUs that tools returned in this session."""

from __future__ import annotations

import re
from collections.abc import AsyncGenerator, Callable
from typing import Any

import pytest
from agent_test_helpers import answer_text, chat, client, of_type
from google.adk.models import BaseLlm, LlmRequest, LlmResponse
from google.genai import types
from pydantic import Field, PrivateAttr

from agent_api.callbacks import GROUNDING_FALLBACK, strip_skus

pytestmark = pytest.mark.emulator

FAKE_SKU = "YM-ZZZ-9999"


def _responses(req: LlmRequest) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for content in req.contents:
        for part in content.parts or []:
            if part.function_response and part.function_response.name:
                out[part.function_response.name] = dict(part.function_response.response or {})
    return out


class ScriptedLlm(BaseLlm):
    """Plays a fixed list of steps; each step builds parts from the request (to reuse real tool output)."""

    model: str = "scripted-llm"
    _steps: list[Callable[[LlmRequest], list[types.Part]]] = PrivateAttr(default_factory=list)
    seen: list[LlmRequest] = Field(default_factory=list)

    def with_steps(self, *steps: Callable[[LlmRequest], list[types.Part]]) -> ScriptedLlm:
        self._steps = list(steps)
        self.seen = []
        return self

    async def generate_content_async(
        self, llm_request: LlmRequest, stream: bool = False
    ) -> AsyncGenerator[LlmResponse, None]:
        self.seen.append(llm_request)
        step = self._steps.pop(0) if self._steps else (lambda _r: [types.Part(text="Tamam.")])
        yield LlmResponse(content=types.Content(role="model", parts=step(llm_request)))


def search(_req: LlmRequest) -> list[types.Part]:
    return [
        types.Part(
            function_call=types.FunctionCall(name="search_products", args={"query": "montaj yapıştırıcısı"})
        )
    ]


def hallucinate(_req: LlmRequest) -> list[types.Part]:
    return [types.Part(text=f"Size Süper Yapıştırıcı ({FAKE_SKU}) öneririm.\nAyrıca eldiven kullanın.")]


def hallucinate_lowercase(_req: LlmRequest) -> list[types.Part]:
    return [types.Part(text=f"Deneyin: {FAKE_SKU.lower()} kodlu ürün.\nAyrıca eldiven kullanın.")]


def grounded(req: LlmRequest) -> list[types.Part]:
    sku = _responses(req)["search_products"]["products"][0]["sku"]
    return [types.Part(text=f"Size montaj yapıştırıcısı ({sku}) öneririm.")]


def test_ungrounded_sku_triggers_one_redirect_then_grounded_answer(seeded_project: str) -> None:
    llm = ScriptedLlm().with_steps(search, hallucinate, grounded)
    with client(seeded_project, llm) as (c, deps):
        events = chat(c, "pk_test_yapimarket", "Montaj yapıştırıcısı lazım")
    text = answer_text(events)
    assert FAKE_SKU not in text
    assert re.search(r"YM-[A-Z]{3}-\d{4}", text)
    # The model was redirected through the guardrail tool, with the unknown SKU reported back to it.
    reported = _responses(llm.seen[-1]).get("report_grounding_issue")
    assert reported and FAKE_SKU in reported["error"]
    agent_msg = next(e for e in deps.analytics.events if e.event_type == "agent_message")
    assert agent_msg.payload["guardrails"] == ["grounding_redirect"]
    assert all(p["sku"] != FAKE_SKU for e in of_type(events, "products") for p in e["products"])


def test_second_violation_is_stripped(seeded_project: str) -> None:
    llm = ScriptedLlm().with_steps(search, hallucinate, hallucinate)
    with client(seeded_project, llm) as (c, deps):
        events = chat(c, "pk_test_yapimarket", "Montaj yapıştırıcısı lazım")
    text = answer_text(events)
    assert FAKE_SKU not in text
    assert "eldiven" in text  # unaffected lines survive
    agent_msg = next(e for e in deps.analytics.events if e.event_type == "agent_message")
    assert agent_msg.payload["guardrails"] == ["grounding_redirect", "grounding_stripped"]


def test_strip_skus_falls_back_when_nothing_left() -> None:
    assert strip_skus(f"Öneri: X ({FAKE_SKU})", {FAKE_SKU}) == GROUNDING_FALLBACK
    assert strip_skus(f"Merhaba\nÖneri: X ({FAKE_SKU})", {FAKE_SKU}) == "Merhaba"


def test_sku_in_other_shape_is_also_guarded(seeded_project: str) -> None:
    llm = ScriptedLlm().with_steps(search, hallucinate_lowercase, hallucinate_lowercase)
    with client(seeded_project, llm) as (c, deps):
        events = chat(c, "pk_test_yapimarket", "Montaj yapıştırıcısı lazım")
    text = answer_text(events)
    assert FAKE_SKU.lower() not in text.lower() and "eldiven" in text
    agent_msg = next(e for e in deps.analytics.events if e.event_type == "agent_message")
    assert agent_msg.payload["guardrails"] == ["grounding_redirect", "grounding_stripped"]
