"""Agent tools. Every tool is a closure bound to one server-verified tenant (via tenant-scoped repositories),
so a model can never reach another tenant's data whatever arguments it produces."""

from __future__ import annotations

import time
import uuid
from collections.abc import Callable
from typing import Any

from google.adk.tools import ToolContext
from pydantic import ValidationError

from magaza_core.analytics import AnalyticsEmitter
from magaza_core.contracts import Bundle, BundleItem, ComplementRule, Product, QuoteRequest
from magaza_core.embedding import Embedder
from magaza_core.money import format_try
from magaza_core.repo import ComplementRuleRepo, KnowledgeRepo, ProductRepo, QuoteRepo
from magaza_core.text import fold, tokens

from .turn import TurnContext

GROUNDED_KEY = "grounded_skus"


def brief(p: Product) -> dict[str, Any]:
    specs = [f"{s.label}: {s.value}{f' {s.unit}' if s.unit else ''}" for s in p.specs[:6]]
    return {
        "sku": p.sku,
        "title": p.title,
        "brand": p.brand,
        "category": p.category,
        "price": p.price,
        "price_text": format_try(p.price),
        "unit": p.unit,
        "in_stock": p.stock > 0,
        "key_specs": specs,
        "has_datasheet": bool(p.doc_id),
        "complement_count": len(p.complement_skus),
    }


class ToolBox:
    def __init__(
        self,
        turn: TurnContext,
        *,
        products: ProductRepo,
        knowledge: KnowledgeRepo,
        rules: ComplementRuleRepo,
        quotes: QuoteRepo,
        embedder: Embedder,
        analytics: AnalyticsEmitter,
    ) -> None:
        self.turn = turn
        self.products = products
        self.knowledge = knowledge
        self.rules = rules
        self.quotes = quotes
        self.embedder = embedder
        self.analytics = analytics
        self._rules: list[ComplementRule] | None = None

    # ------------------------------------------------------------------ helpers
    def _ground(self, tool_context: ToolContext | None, products: list[Product]) -> None:
        self.turn.remember(products)
        if tool_context is not None:
            tool_context.state[GROUNDED_KEY] = sorted(self.turn.grounded)

    def _log(self, tool: str, started: float, payload: dict[str, Any]) -> None:
        self.analytics.emit(
            "tool_call",
            tenant_id=self.turn.tenant_id,
            visitor_id_hash=self.turn.visitor_hash,
            session_id=self.turn.session_id,
            latency_ms=int((time.perf_counter() - started) * 1000),
            payload={"tool": tool, **payload},
        )

    async def _reasons(self, source: Product, targets: list[Product]) -> dict[str, str]:
        if self._rules is None:
            self._rules = await self.rules.list()
        reasons: dict[str, str] = {}
        for t in targets:
            for r in sorted(self._rules, key=lambda r: r.priority):
                if (
                    r.source_category == source.category
                    and (not r.source_tags or set(r.source_tags) & set(source.tags))
                    and r.target_category == t.category
                    and (not r.target_tags or set(r.target_tags) & set(t.tags))
                ):
                    reasons[t.sku] = r.reason
                    break
        return reasons

    # ------------------------------------------------------------------ tools
    def tools(self) -> list[Callable[..., Any]]:
        box = self

        async def search_products(
            query: str,
            category: str = "",
            brand: str = "",
            max_price: float = 0,
            in_stock_only: bool = True,
            *,
            tool_context: ToolContext,
        ) -> dict[str, Any]:
            """Searches this store's catalog (semantic search). Always use it before recommending products.

            Args:
              query: The customer's need in their own words, e.g. "matkapsız korniş montajı".
              category: Optional category slug filter; leave empty when unsure.
              brand: Optional brand filter.
              max_price: Optional maximum price in TRY (0 means no limit).
              in_stock_only: Only return products that are in stock.
            """
            started = time.perf_counter()
            vector = (await box.embedder.embed([query], "query"))[0]
            hits = await box.products.vector_search(vector, category=category or None, limit=30)
            if not hits and category:
                hits = await box.products.vector_search(vector, limit=30)
            query_tokens = set(tokens(query))

            def score(p: Product, distance: float) -> float:
                text_tokens = set(tokens(f"{p.title} {' '.join(p.tags)} {p.subcategory or ''}"))
                stems = {t[:5] for t in text_tokens}
                overlap = sum(1 for t in query_tokens if t in text_tokens or t[:5] in stems)
                return (1 - distance) + 0.08 * overlap

            floor = box.embedder.min_similarity
            hits = [h for h in hits if 1 - h.distance >= floor]
            ranked = sorted(hits, key=lambda h: score(h.product, h.distance), reverse=True)
            results = [
                h.product
                for h in ranked
                if (not brand or fold(brand) in fold(h.product.brand))
                and (not max_price or h.product.price <= max_price)
                and (not in_stock_only or h.product.stock > 0)
            ][:6]
            box._ground(tool_context, results)
            if not results:
                box.turn.zero_result_queries.append(query)
            box._log(
                "search_products",
                started,
                {
                    "query": query,
                    "result_count": len(results),
                    "skus": [p.sku for p in results],
                    "zero_result": not results,
                },
            )
            return {"count": len(results), "products": [brief(p) for p in results]}

        async def get_product(sku: str, *, tool_context: ToolContext) -> dict[str, Any]:
            """Returns full details (description, all technical specs, data sheet) of one product of this store.

            Args:
              sku: Product code exactly as returned by search_products.
            """
            started = time.perf_counter()
            product = await box.products.get(sku.strip().upper())
            box._log("get_product", started, {"sku": sku, "found": product is not None})
            if product is None:
                return {"error": f"{sku} bu mağazanın kataloğunda yok."}
            box._ground(tool_context, [product])
            return {
                **brief(product),
                "description": product.description,
                "specs": [s.model_dump(mode="json") for s in product.specs],
                "stock": product.stock,
                "datasheet_url": product.doc_url,
                "complement_skus": product.complement_skus,
            }

        async def get_complements(sku: str, *, tool_context: ToolContext) -> dict[str, Any]:
            """Returns complementary products that are usually needed together with the given product.

            Args:
              sku: Product code of the main product.
            """
            started = time.perf_counter()
            product = await box.products.get(sku.strip().upper())
            if product is None:
                box._log("get_complements", started, {"sku": sku, "found": False})
                return {"error": f"{sku} bu mağazanın kataloğunda yok."}
            complements = [c for c in await box.products.get_many(product.complement_skus) if c.stock > 0]
            reasons = await box._reasons(product, complements)
            box._ground(tool_context, [product, *complements])
            box._log("get_complements", started, {"sku": sku, "skus": [c.sku for c in complements]})
            return {
                "main": brief(product),
                "complements": [{**brief(c), "reason": reasons.get(c.sku, "")} for c in complements],
            }

        async def search_knowledge(query: str, sku: str = "", *, tool_context: ToolContext) -> dict[str, Any]:
            """Searches the store's technical data sheets (teknik föy) for facts such as load capacity,
            drying time, surface compatibility or application steps. Cite these facts instead of guessing.

            Args:
              query: The technical question.
              sku: Optional product code to prefer that product's data sheet.
            """
            started = time.perf_counter()
            vector = (await box.embedder.embed([query if not sku else f"{query} {sku}"], "query"))[0]
            chunks = await box.knowledge.vector_search(vector, limit=12)
            if sku:
                chunks.sort(key=lambda c: (c.chunk.sku != sku.upper(), c.distance))
            top = chunks[:4]
            box.turn.knowledge.extend(top)
            box._log(
                "search_knowledge",
                started,
                {"query": query, "result_count": len(top), "doc_ids": [c.chunk.doc_id for c in top]},
            )
            return {
                "passages": [
                    {
                        "doc_id": c.chunk.doc_id,
                        "title": c.chunk.title,
                        "section": c.chunk.section,
                        "sku": c.chunk.sku,
                        "text": c.chunk.text[:700],
                        "source_url": c.chunk.source_url,
                    }
                    for c in top
                ]
            }

        async def propose_bundle(
            skus: list[str], quantities: list[int], title: str, rationale: str, *, tool_context: ToolContext
        ) -> dict[str, Any]:
            """Builds the solution bundle the customer can add to the cart in one click.
            The first SKU is the main product, the rest are complements. Only use SKUs returned by tools.

            Args:
              skus: Product codes, main product first.
              quantities: Quantity per SKU (same order); use 1 when unsure.
              title: Short bundle title in Turkish, e.g. "Matkapsız korniş montaj paketi".
              rationale: One sentence explaining why these products belong together.
            """
            started = time.perf_counter()
            clean = [s.strip().upper() for s in skus][:6]
            ungrounded = [s for s in clean if s not in box.turn.grounded]
            products = {
                p.sku: p for p in await box.products.get_many([s for s in clean if s not in ungrounded])
            }
            missing = [s for s in clean if s not in products]
            out_of_stock = [s for s, p in products.items() if p.stock <= 0]
            if not clean or missing or out_of_stock:
                box._log(
                    "propose_bundle", started, {"ok": False, "missing": missing, "out_of_stock": out_of_stock}
                )
                return {
                    "error": "Paket oluşturulamadı.",
                    "unknown_or_ungrounded_skus": missing,
                    "out_of_stock_skus": out_of_stock,
                    "hint": "Yalnızca search_products / get_complements sonuçlarındaki stoktaki SKU'ları kullan.",
                }
            qty = [max(1, int(q)) for q in quantities] + [1] * len(clean)
            items = [
                BundleItem(
                    sku=s,
                    title=products[s].title,
                    price=products[s].price,
                    qty=qty[i],
                    role="main" if i == 0 else "complement",
                    image_url=products[s].image_url,
                    url=products[s].url,
                )
                for i, s in enumerate(clean)
            ]
            total = round(sum(i.price * i.qty for i in items), 2)
            bundle = Bundle(
                bundle_id=f"b_{uuid.uuid4().hex[:12]}",
                title=title.strip() or "Önerilen paket",
                rationale=rationale.strip() or "Birlikte kullanılması önerilen ürünler.",
                items=items,
                total=total,
                currency="TRY",
            )
            box.turn.bundle = bundle
            box._ground(tool_context, list(products.values()))
            box._log(
                "propose_bundle",
                started,
                {"ok": True, "bundle_id": bundle.bundle_id, "skus": clean, "total": total},
            )
            return {
                "bundle_id": bundle.bundle_id,
                "total": total,
                "total_text": format_try(total),
                "items": [
                    {"sku": i.sku, "title": i.title, "qty": i.qty, "price_text": format_try(i.price)}
                    for i in items
                ],
            }

        async def create_quote_request(
            company_name: str,
            contact_name: str,
            email: str,
            skus: list[str],
            quantities: list[int],
            phone: str = "",
            note: str = "",
            *,
            tool_context: ToolContext,
        ) -> dict[str, Any]:
            """Creates a B2B quote request for the sales team. Only call it after the customer gave their
            company name, contact name and e-mail and agreed to request a quote.

            Args:
              company_name: Customer's company.
              contact_name: Contact person.
              email: Contact e-mail.
              skus: Product codes to quote (from tool results).
              quantities: Requested quantity per SKU.
              phone: Optional phone.
              note: Optional note (delivery frequency, etc.).
            """
            started = time.perf_counter()
            clean = [s.strip().upper() for s in skus]
            ungrounded = [s for s in clean if s not in box.turn.grounded]
            if ungrounded or not clean:
                return {"error": "Teklif için önce ürünleri katalogdan bul.", "ungrounded_skus": ungrounded}
            qty = [max(1, int(q)) for q in quantities] + [1] * len(clean)
            try:
                request = QuoteRequest(
                    visitor_id="agent-session",
                    session_id=box.turn.session_id,
                    company_name=company_name,
                    contact_name=contact_name,
                    email=email,
                    phone=phone or None,
                    note=note or None,
                    items=[{"sku": s, "qty": qty[i]} for i, s in enumerate(clean)],
                )
            except ValidationError as exc:
                return {"error": "Teklif bilgileri geçersiz.", "details": [e["msg"] for e in exc.errors()]}
            products = {p.sku: p for p in await box.products.get_many(clean)}
            lines = [
                {"sku": s, "qty": qty[i], "unit_price": products[s].price if s in products else None}
                for i, s in enumerate(clean)
            ]
            quote_id = await box.quotes.create(
                request, visitor_id_hash=box.turn.visitor_hash, source="agent", lines=lines
            )
            box.turn.quote_id = quote_id
            box._log("create_quote_request", started, {"quote_id": quote_id, "skus": clean})
            box.analytics.emit(
                "quote_request",
                tenant_id=box.turn.tenant_id,
                visitor_id_hash=box.turn.visitor_hash,
                session_id=box.turn.session_id,
                payload={"quote_id": quote_id, "source": "agent", "skus": clean, "email": email},
            )
            return {"quote_id": quote_id, "status": "received"}

        async def report_grounding_issue(
            unknown_skus: list[str], *, tool_context: ToolContext
        ) -> dict[str, Any]:
            """Internal guardrail: reports SKUs that were not returned by any tool in this conversation.

            Args:
              unknown_skus: The SKUs that could not be verified.
            """
            return {
                "error": "Yanıtındaki şu ürün kodları araçlardan gelmedi: " + ", ".join(unknown_skus),
                "instruction": "Yalnızca araç sonuçlarındaki SKU'ları kullan; gerekirse search_products çağır ve yanıtı yeniden yaz.",
                "allowed_skus": sorted(box.turn.grounded)[:40],
            }

        tools: list[Callable[..., Any]] = [
            search_products,
            get_product,
            search_knowledge,
            get_complements,
            propose_bundle,
        ]
        if self.turn.tenant.config.actions.quote_request:
            tools.append(create_quote_request)
        tools.append(report_grounding_issue)
        return tools
