from __future__ import annotations

import json
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from typing import Any

from fastapi.testclient import TestClient
from google.adk.models import BaseLlm

from agent_api.deps import Deps
from agent_api.main import create_app
from agent_api.settings import Settings
from magaza_core.analytics import AnalyticsEmitter
from magaza_core.contracts import SSE_EVENT_ADAPTER
from magaza_core.embedding import HashingEmbedder
from magaza_core.repo import TenantRegistry, get_db
from magaza_core.tenancy import TenantContext

ORIGINS = {"pk_test_yapimarket": "http://localhost:3101", "pk_test_ambalaj": "http://localhost:3102"}


def make_deps(project: str, llm: BaseLlm | None = None) -> Deps:
    return Deps(
        settings=Settings(llm_mode="fake"),
        db=get_db(project),
        embedder=HashingEmbedder(),
        analytics=AnalyticsEmitter(None),
        llm_override=llm,
    )


@contextmanager
def client(project: str, llm: BaseLlm | None = None) -> Iterator[tuple[TestClient, Deps]]:
    deps = make_deps(project, llm)
    with TestClient(create_app(deps)) as c:
        yield c, deps


def parse_sse(body: str) -> list[dict[str, Any]]:
    events = []
    for block in body.split("\n\n"):
        data = "\n".join(line[5:].lstrip() for line in block.splitlines() if line.startswith("data:"))
        if data:
            event = json.loads(data)
            SSE_EVENT_ADAPTER.validate_python(event)  # every event must satisfy the contract
            events.append(event)
    return events


def chat(
    c: TestClient,
    key: str,
    message: str,
    *,
    visitor: str = "v_test_visitor_01",
    session_id: str | None = None,
) -> list[dict[str, Any]]:
    body: dict[str, Any] = {"message": message, "visitor_id": visitor}
    if session_id:
        body["session_id"] = session_id
    res = c.post(f"/v1/t/{key}/chat", json=body, headers={"origin": ORIGINS[key]})
    assert res.status_code == 200, res.text
    return parse_sse(res.text)


def of_type(events: list[dict[str, Any]], kind: str) -> list[dict[str, Any]]:
    return [e for e in events if e["type"] == kind]


def answer_text(events: list[dict[str, Any]]) -> str:
    return "".join(e["text"] for e in of_type(events, "token"))


Script = Callable[[Any], list[Any]]


async def tenant_ctx(project: str, tenant_id: str) -> TenantContext:
    config = await TenantRegistry(get_db(project)).get(tenant_id)
    assert config is not None, tenant_id
    return TenantContext.of(config)
