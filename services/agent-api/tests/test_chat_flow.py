"""End-to-end agent turns through the HTTP API with the deterministic FakeLlm and the Firestore emulator."""

from __future__ import annotations

import pytest
from agent_test_helpers import answer_text, chat, client, of_type

pytestmark = pytest.mark.emulator


def test_kickoff_example_yapi_market(seeded_project: str) -> None:
    with client(seeded_project) as (c, deps):
        events = chat(c, "pk_test_yapimarket", "Kornişim koptu, matkabım yok")
        bundle = of_type(events, "bundle")[0]["bundle"]
        titles = " | ".join(i["title"] for i in bundle["items"])
        assert "Montaj Yapıştırıcısı" in titles
        assert "Silikon Tabancası" in titles
        assert "Yüzey Temizleyici" in titles
        assert all(i["sku"].startswith("YM-") for i in bundle["items"])
        assert bundle["items"][0]["role"] == "main"
        products = of_type(events, "products")[0]["products"]
        assert {p["sku"] for p in products} >= {i["sku"] for i in bundle["items"]}
        sources = of_type(events, "source")[0]["sources"]
        assert sources and sources[0]["url"].endswith(".pdf")
        text = answer_text(events)
        assert "₺" in text and bundle["items"][0]["sku"] in text
        done = events[-1]
        assert done["type"] == "done" and done["usage"]["model"] == "fake-llm"

        kinds = [e.event_type for e in deps.analytics.events]
        for kind in ("user_message", "tool_call", "agent_message", "product_shown"):
            assert kind in kinds
        agent_msg = next(e for e in deps.analytics.events if e.event_type == "agent_message")
        assert (
            agent_msg.tenant_id == "yapi-market"
            and agent_msg.tokens_in > 0
            and agent_msg.latency_ms is not None
        )
        assert agent_msg.payload["topic"] == "montaj_sabitleme"


def test_kickoff_example_ambalaj_and_quote_hint(seeded_project: str) -> None:
    with client(seeded_project) as (c, _):
        events = chat(c, "pk_test_ambalaj", "2 kg seramik kupa göndereceğim, hangi koli?")
        titles = " | ".join(i["title"] for i in of_type(events, "bundle")[0]["bundle"]["items"])
        assert "Çift Oluklu Koli" in titles and "Balonlu Naylon" in titles and "Koli Bandı" in titles

        events = chat(c, "pk_test_ambalaj", "Ayda 1000 koli gönderiyorum, teklif alabilir miyim?")
        assert of_type(events, "action")[0]["action"] == "suggest_quote"


def test_clarifying_question_for_vague_message(seeded_project: str) -> None:
    with client(seeded_project) as (c, _):
        events = chat(c, "pk_test_yapimarket", "merhaba")
        assert "ayrıntı" in answer_text(events)
        assert not of_type(events, "bundle")


def test_session_continues_and_counts_messages(seeded_project: str) -> None:
    with client(seeded_project) as (c, deps):
        first = chat(c, "pk_test_yapimarket", "Banyo derzleri karardı", visitor="v_session_test_01")
        sid = first[-1]["session_id"]
        second = chat(
            c,
            "pk_test_yapimarket",
            "Salonu boyayacağım, neler lazım?",
            visitor="v_session_test_01",
            session_id=sid,
        )
        assert second[-1]["session_id"] == sid
        turns = [e.payload["turn"] for e in deps.analytics.events if e.event_type == "user_message"]
        assert turns[-2:] == [1, 2]


def test_pii_is_masked_in_analytics(seeded_project: str) -> None:
    with client(seeded_project) as (c, deps):
        chat(c, "pk_test_ambalaj", "Koli lazım, bana deniz@example.com veya 0555 123 45 67 üzerinden ulaşın")
        user_msg = next(e for e in deps.analytics.events if e.event_type == "user_message")
        assert "deniz@example.com" not in user_msg.payload["text"]
        assert "[e-posta]" in user_msg.payload["text"] and "[telefon]" in user_msg.payload["text"]
