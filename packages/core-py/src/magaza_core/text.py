"""Turkish-aware text helpers (folding, tokenisation, topic labelling)."""

from __future__ import annotations

import re

from magaza_core.contracts import TopicDefinition

_FOLD = str.maketrans("çğıöşüâîûÇĞİIÖŞÜ", "cgiosuaiucgiiosu")
STOPWORDS = frozenset(
    [
        "ve",
        "ile",
        "icin",
        "bir",
        "bu",
        "su",
        "o",
        "da",
        "de",
        "mi",
        "mu",
        "ne",
        "hangi",
        "nasil",
        "gibi",
        "olan",
        "olarak",
        "cok",
        "en",
        "daha",
        "ben",
        "sen",
        "biz",
        "siz",
        "ama",
        "ki",
        "bana",
        "bize",
        "sana",
        "icin",
        "lazim",
        "var",
        "mi",
        "mı",
        "acaba",
    ]
)


def fold(text: str) -> str:
    """Lower-case with Turkish rules and strip diacritics: 'KORNİŞİM' -> 'kornisim'."""
    return text.replace("İ", "i").replace("I", "ı").lower().translate(_FOLD)


def tokens(text: str, *, drop_stopwords: bool = True) -> list[str]:
    words = re.findall(r"[a-z0-9]+", fold(text))
    return [w for w in words if not (drop_stopwords and w in STOPWORDS)]


def label_topic(text: str, taxonomy: list[TopicDefinition]) -> str | None:
    """Keyword topic classifier driven entirely by the tenant's taxonomy (no sector logic in code)."""
    folded = fold(text)
    best: tuple[int, str] | None = None
    for topic in taxonomy:
        hits = sum(1 for kw in topic.keywords if fold(kw) in folded)
        if hits and (best is None or hits > best[0]):
            best = (hits, topic.topic_id)
    return best[1] if best else None
