from __future__ import annotations

import math

import pytest

from magaza_core.embedding import HashingEmbedder
from magaza_core.llm_config import load_llm_config
from magaza_core.pii import mask_payload, mask_pii
from magaza_core.tenancy import assign_group, hash_visitor
from magaza_core.text import fold, label_topic, tokens
from magaza_jobs.demo_data.tenants import tenant_config


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("mail: deniz.kaya+test@example.com.tr", "mail: [e-posta]"),
        ("tel 0555 123 45 67", "tel [telefon]"),
        ("tel +90 532 123 4567", "tel [telefon]"),
        ("TC 10000000146", "TC [tc-kimlik]"),
        ("kart 4111 1111 1111 1111", "kart [kart]"),
        (
            "2 kg seramik kupa, 290 ml, 1000 koli, sipariş 12345678901",
            "2 kg seramik kupa, 290 ml, 1000 koli, sipariş 12345678901",
        ),
    ],
)
def test_mask_pii(raw: str, expected: str) -> None:
    assert mask_pii(raw) == expected


def test_mask_payload_recurses() -> None:
    assert mask_payload({"a": ["x@y.co"], "n": 5}) == {"a": ["[e-posta]"], "n": 5}


def test_turkish_folding_and_tokens() -> None:
    assert fold("KORNİŞİM Çatlak ığdır") == "kornisim catlak igdir"
    assert tokens("Kornişim koptu ve matkabım yok") == ["kornisim", "koptu", "matkabim", "yok"]


def test_topic_labelling_from_tenant_taxonomy() -> None:
    taxonomy = tenant_config("ambalaj").topic_taxonomy
    assert label_topic("2 kg seramik kupa göndereceğim", taxonomy) == "kirilacak_urun"
    assert label_topic("merhaba", taxonomy) is None


def test_hashing_embedder_is_deterministic_and_lexical() -> None:
    emb = HashingEmbedder(768)
    a, b, c = (
        emb.embed_one("matkapsız korniş montajı"),
        emb.embed_one("korniş montaj yapıştırıcısı"),
        emb.embed_one("çift oluklu koli"),
    )
    assert len(a) == 768 and math.isclose(sum(x * x for x in a), 1.0, rel_tol=1e-6)
    assert a == emb.embed_one("matkapsız korniş montajı")
    cos = lambda x, y: sum(i * j for i, j in zip(x, y, strict=True))  # noqa: E731
    assert cos(a, b) > cos(a, c)


def test_visitor_hash_and_group() -> None:
    assert hash_visitor("a", "v1") != hash_visitor("b", "v1")
    assert assign_group("t", "v", 0) == "assistant" and assign_group("t", "v", 100) == "control"


def test_llm_config_prices_and_ids() -> None:
    cfg = load_llm_config()
    assert cfg.chat.default_model == "gemini-3.8-flash"
    assert cfg.embedding.dimension == 768
    from datetime import date

    assert cfg.estimate_cost_usd("gemini-3.8-flash", 1_000_000, 0, date(2026, 10, 1)) == pytest.approx(0.825)
    assert cfg.estimate_cost_usd("gemini-3.8-flash", 0, 1_000_000, date(2027, 2, 1)) == pytest.approx(8.25)
    assert cfg.estimate_cost_usd("fake-llm", 10_000, 10_000) == 0
