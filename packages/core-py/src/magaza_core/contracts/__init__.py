"""Contract models generated from ``packages/contracts/schemas`` (run ``make contracts``).

Only ``generated.py`` is produced by the generator; this module adds the few aliases JSON Schema
cannot express as a named Python type (the discriminated SSE union, the event-type literal).
"""

from __future__ import annotations

from typing import Annotated, Any, Literal, get_args

from pydantic import Field, TypeAdapter

from .generated import (
    ActionEvent,
    AddToCartDetail,
    AnalyticsEvent,
    Bundle,
    BundleEvent,
    BundleItem,
    CartLine,
    CatalogSource,
    ChatRequest,
    ChatUsage,
    ClientEvent,
    ComplementRule,
    DocChunk,
    DoneEvent,
    ErrorEvent,
    Order,
    OrderLine,
    PersonaSettings,
    PersonaTemplate,
    Product,
    ProductCard,
    ProductsEvent,
    ProductSpec,
    QuoteItem,
    QuoteRequest,
    QuoteResponse,
    SourceEvent,
    SourceRef,
    TenantActions,
    TenantConfig,
    TenantQuotas,
    TenantTheme,
    TokenEvent,
    TopicDefinition,
    WidgetPublicConfig,
)

SseEvent = Annotated[
    TokenEvent | ProductsEvent | BundleEvent | ActionEvent | SourceEvent | DoneEvent | ErrorEvent,
    Field(discriminator="type"),
]
SSE_EVENT_ADAPTER: TypeAdapter[Any] = TypeAdapter(SseEvent)

AnalyticsEventType = Literal[
    "visit",
    "widget_open",
    "user_message",
    "agent_message",
    "tool_call",
    "product_shown",
    "add_to_cart",
    "quote_request",
    "order",
    "feedback",
]
ANALYTICS_EVENT_TYPES: tuple[str, ...] = get_args(AnalyticsEventType)

__all__ = [
    "ANALYTICS_EVENT_TYPES",
    "SSE_EVENT_ADAPTER",
    "ActionEvent",
    "AddToCartDetail",
    "AnalyticsEvent",
    "AnalyticsEventType",
    "Bundle",
    "BundleEvent",
    "BundleItem",
    "CartLine",
    "CatalogSource",
    "ChatRequest",
    "ChatUsage",
    "ClientEvent",
    "ComplementRule",
    "DocChunk",
    "DoneEvent",
    "ErrorEvent",
    "Order",
    "OrderLine",
    "PersonaSettings",
    "PersonaTemplate",
    "Product",
    "ProductCard",
    "ProductSpec",
    "ProductsEvent",
    "QuoteItem",
    "QuoteRequest",
    "QuoteResponse",
    "SourceEvent",
    "SourceRef",
    "SseEvent",
    "TenantActions",
    "TenantConfig",
    "TenantQuotas",
    "TenantTheme",
    "TokenEvent",
    "TopicDefinition",
    "WidgetPublicConfig",
]
