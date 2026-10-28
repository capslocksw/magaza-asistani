"""One chat turn: run the ADK agent to completion, then stream a grounded answer as contract SSE events.

The answer is only streamed after the grounding guardrail has accepted it (see docs/adr/005-grounded-streaming.md),
so an ungrounded SKU can never reach the customer, even transiently.
"""

from __future__ import annotations

import logging
import re
import uuid
from collections.abc import AsyncIterator

from google.adk.agents.run_config import RunConfig
from google.adk.runners import Runner
from google.genai import types

from magaza_core.budget import BudgetExceeded
from magaza_core.contracts import (
    ActionEvent,
    BundleEvent,
    ChatRequest,
    ChatUsage,
    DoneEvent,
    ErrorEvent,
    ProductCard,
    ProductsEvent,
    SourceEvent,
    SourceRef,
    TokenEvent,
)
from magaza_core.repo import ComplementRuleRepo, KnowledgeRepo, ProductRepo, QuoteRepo, SessionRepo, UsageRepo
from magaza_core.tenancy import TenantContext, hash_visitor
from magaza_core.text import fold, label_topic

from .agent import APP_NAME, build_agent
from .callbacks import TurnCallbacks
from .deps import Deps
from .session_service import FirestoreSessionService
from .tools import GROUNDED_KEY, ToolBox
from .turn import TurnContext

log = logging.getLogger(__name__)
SseEvent = TokenEvent | ProductsEvent | BundleEvent | ActionEvent | SourceEvent | DoneEvent | ErrorEvent
DONT_KNOW = (
    "bilmiyorum",
    "bulamadım",
    "föyde bu bilgi yok",
    "emin değilim",
    "doğrulayamadım",
    "ayrıntı verir misiniz",
)
_QUOTE_HINT = re.compile(r"\b(teklif|toplu)\b|\b\d{3,}\b")


def _budget_refusal(exc: BaseException | None) -> bool:
    """True when the spend guard refused a paid request, even if ADK re-raised it wrapped."""
    for _ in range(8):
        if exc is None:
            return False
        if isinstance(exc, BudgetExceeded):
            return True
        exc = exc.__cause__ or exc.__context__
    return False


def chunk_text(text: str, words_per_chunk: int = 3) -> list[str]:
    pieces = re.findall(r"\S+\s*", text)
    return ["".join(pieces[i : i + words_per_chunk]) for i in range(0, len(pieces), words_per_chunk)]


async def run_turn(deps: Deps, ctx: TenantContext, req: ChatRequest) -> AsyncIterator[SseEvent]:
    visitor_hash = hash_visitor(ctx.tenant_id, req.visitor_id)
    sessions = FirestoreSessionService(SessionRepo(deps.db, ctx))
    session = None
    if req.session_id:
        session = await sessions.get_session(
            app_name=APP_NAME, user_id=visitor_hash, session_id=req.session_id
        )
    if session is None:
        session = await sessions.create_session(
            app_name=APP_NAME, user_id=visitor_hash, state={GROUNDED_KEY: [], "message_count": 0}
        )

    turn = TurnContext(
        tenant=ctx,
        visitor_hash=visitor_hash,
        session_id=session.id,
        message=req.message,
        session_messages=int(session.state.get("message_count", 0)),
        grounded=set(session.state.get(GROUNDED_KEY, [])),
    )
    topic = label_topic(req.message, ctx.config.topic_taxonomy)
    deps.analytics.emit(
        "user_message",
        tenant_id=ctx.tenant_id,
        visitor_id_hash=visitor_hash,
        session_id=session.id,
        payload={
            "text": req.message,
            "topic": topic,
            "page_url": req.page_url,
            "turn": turn.session_messages + 1,
        },
    )

    products_repo = ProductRepo(deps.db, ctx)
    toolbox = ToolBox(
        turn,
        products=products_repo,
        knowledge=KnowledgeRepo(deps.db, ctx),
        rules=ComplementRuleRepo(deps.db, ctx),
        quotes=QuoteRepo(deps.db, ctx),
        embedder=deps.embedder,
        analytics=deps.analytics,
    )
    llm_cfg = deps.settings.llm.chat
    callbacks = TurnCallbacks(
        turn,
        usage=UsageRepo(deps.db, ctx),
        limiter=deps.limiter,
        max_model_calls=llm_cfg.max_llm_calls_per_turn,
    )
    agent = build_agent(
        template=await deps.persona_template(ctx.config.persona.template_id),
        config=ctx.config,
        toolbox=toolbox,
        callbacks=callbacks,
        model=deps.model(),
        thinking_level=llm_cfg.thinking_level,
    )
    runner = Runner(app_name=APP_NAME, agent=agent, session_service=sessions)

    final_text = ""
    try:
        async for event in runner.run_async(
            user_id=visitor_hash,
            session_id=session.id,
            new_message=types.Content(role="user", parts=[types.Part(text=req.message)]),
            state_delta={"message_count": turn.session_messages + 1},
            run_config=RunConfig(max_llm_calls=llm_cfg.max_llm_calls_per_turn + 2),
        ):
            if event.is_final_response() and event.content and event.content.parts:
                text = "".join(p.text for p in event.content.parts if p.text and not p.thought)
                if text:
                    final_text = text
    except Exception as exc:
        if _budget_refusal(exc):
            log.warning("paid model request refused by the spend guard: %s", exc)
            yield ErrorEvent(type="error", code="budget_exceeded", message="Asistan şu anda yanıt veremiyor.")
            return
        log.exception("agent turn failed")
        yield ErrorEvent(type="error", code="internal", message="Asistan şu anda yanıt veremiyor.")
        return

    message_id = f"m_{uuid.uuid4().hex[:16]}"
    model_name = deps.model_name
    if turn.blocked:
        deps.analytics.emit(
            "agent_message",
            tenant_id=ctx.tenant_id,
            visitor_id_hash=visitor_hash,
            session_id=session.id,
            latency_ms=turn.elapsed_ms(),
            payload={"guardrail": turn.blocked.code, "guardrails": turn.guardrails, "message_id": message_id},
        )
        yield turn.blocked
        return

    for piece in chunk_text(final_text):
        yield TokenEvent(type="token", text=piece)

    mentioned = [
        m for m in dict.fromkeys(re.findall(ctx.config.sku_pattern, final_text)) if m in turn.grounded
    ]
    bundle = turn.bundle
    shown = list(dict.fromkeys([*(i.sku for i in bundle.items)] if bundle else []) | dict.fromkeys(mentioned))
    missing = [s for s in shown if s not in turn.products]
    for p in await products_repo.get_many(missing):
        turn.products[p.sku] = p
    cards = [
        ProductCard(
            sku=p.sku,
            title=p.title,
            brand=p.brand,
            price=p.price,
            list_price=p.list_price,
            currency="TRY",
            image_url=p.image_url,
            url=p.url,
            in_stock=p.stock > 0,
            reason=(
                "Ana ürün" if bundle and bundle.items[0].sku == p.sku else "Tamamlayıcı" if bundle else None
            ),
        )
        for p in (turn.products[s] for s in shown if s in turn.products)
    ]

    sources: list[SourceRef] = []
    if final_text and turn.knowledge:
        # Cite data sheets of the recommended products; otherwise only the single best passage.
        relevant = [
            c for c in sorted(turn.knowledge, key=lambda c: c.distance) if c.chunk.sku in shown
        ] or sorted(turn.knowledge, key=lambda c: c.distance)[:1]
        for c in relevant:
            if c.chunk.doc_id in {s.doc_id for s in sources}:
                continue
            sources.append(
                SourceRef(
                    doc_id=c.chunk.doc_id,
                    title=c.chunk.title,
                    url=c.chunk.source_url,
                    section=c.chunk.section,
                    snippet=c.chunk.text[:160],
                )
            )
            if len(sources) == 2:
                break
    if sources:
        yield SourceEvent(type="source", sources=sources)
    if cards:
        yield ProductsEvent(type="products", products=cards)
    if bundle:
        yield BundleEvent(type="bundle", bundle=bundle)
    if turn.quote_id:
        yield ActionEvent(
            type="action",
            action="quote_created",
            label="Teklif talebiniz alındı",
            payload={"quote_id": turn.quote_id},
        )
    elif ctx.config.actions.quote_request and bundle and _QUOTE_HINT.search(fold(req.message)):
        yield ActionEvent(type="action", action="suggest_quote", label="Teklif talebi oluştur", payload={})

    latency = turn.elapsed_ms()
    usage = ChatUsage(
        model=model_name, tokens_in=turn.tokens_in, tokens_out=turn.tokens_out, latency_ms=latency
    )
    folded = fold(final_text)
    deps.analytics.emit(
        "agent_message",
        tenant_id=ctx.tenant_id,
        visitor_id_hash=visitor_hash,
        session_id=session.id,
        model=model_name,
        tokens_in=turn.tokens_in,
        tokens_out=turn.tokens_out,
        latency_ms=latency,
        payload={
            "message_id": message_id,
            "text": final_text,
            "skus": shown,
            "bundle_id": bundle.bundle_id if bundle else None,
            "bundle_skus": [i.sku for i in bundle.items] if bundle else [],
            "bundle_total": bundle.total if bundle else None,
            "sources": [s.doc_id for s in sources],
            "dont_know": any(fold(p) in folded for p in DONT_KNOW),
            "unmet": bool(turn.zero_result_queries) and not shown,
            "unmet_reason": "not_in_catalog" if turn.zero_result_queries and not shown else None,
            "unmet_query": turn.zero_result_queries[0] if turn.zero_result_queries and not shown else None,
            "zero_result_queries": turn.zero_result_queries,
            "guardrails": turn.guardrails,
            "topic": topic,
            "model_calls": turn.model_calls,
        },
    )
    if shown:
        deps.analytics.emit(
            "product_shown",
            tenant_id=ctx.tenant_id,
            visitor_id_hash=visitor_hash,
            session_id=session.id,
            payload={
                "skus": shown,
                "bundle_id": bundle.bundle_id if bundle else None,
                "message_id": message_id,
            },
        )
    yield DoneEvent(type="done", session_id=session.id, message_id=message_id, usage=usage)
