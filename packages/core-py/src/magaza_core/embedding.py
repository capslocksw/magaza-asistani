"""Text embeddings: Vertex Gemini embeddings in production, a deterministic hashing embedder locally/tests.

The hashing embedder (word + stem + character 4-gram features, signed feature hashing) gives useful
lexical similarity for Turkish without any network access, so local demos and tests behave sensibly.
"""

from __future__ import annotations

import asyncio
import hashlib
import math
import os
from typing import Any, Literal, Protocol

from magaza_core.budget import BudgetGuard, get_budget_guard
from magaza_core.llm_config import load_llm_config
from magaza_core.text import tokens

Task = Literal["query", "document"]


class Embedder(Protocol):
    name: str
    dim: int
    min_similarity: float

    async def embed(self, texts: list[str], task: Task) -> list[list[float]]: ...


def _normalize(vec: list[float]) -> list[float]:
    norm = math.sqrt(sum(v * v for v in vec)) or 1.0
    return [v / norm for v in vec]


class HashingEmbedder:
    name = "hashing-embedder"
    # Feature hashing gives unrelated texts 0.1-0.2 similarity too, so no cut-off is applied locally.
    min_similarity = 0.0

    def __init__(self, dim: int = 768) -> None:
        self.dim = dim

    def _features(self, text: str) -> list[tuple[str, float]]:
        feats: list[tuple[str, float]] = []
        for word in tokens(text):
            feats.append((f"w:{word}", 1.0))
            if len(word) > 5:
                feats.append((f"s:{word[:5]}", 0.9))  # crude stem: Turkish is suffixing
            padded = f"#{word}#"
            feats.extend((f"g:{padded[i : i + 4]}", 0.3) for i in range(len(padded) - 3))
        return feats

    def embed_one(self, text: str) -> list[float]:
        vec = [0.0] * self.dim
        for feature, weight in self._features(text):
            h = int.from_bytes(hashlib.blake2b(feature.encode(), digest_size=8).digest(), "big")
            vec[h % self.dim] += weight if (h >> 63) & 1 else -weight
        return _normalize(vec)

    async def embed(self, texts: list[str], task: Task) -> list[list[float]]:
        return [self.embed_one(t) for t in texts]


class VertexEmbedder:
    """Gemini embeddings on Vertex AI (model + dimension from config/llm.yaml), every request behind the spend guard."""

    def __init__(self, project: str, location: str, guard: BudgetGuard, client: Any | None = None) -> None:
        cfg = load_llm_config().embedding
        self.name = cfg.model
        self.dim = cfg.dimension
        self._batch = max(1, cfg.batch_size)
        self._sem = asyncio.Semaphore(cfg.concurrency)
        self.min_similarity = cfg.min_similarity
        self._guard = guard
        if client is None:
            from google import genai

            client = genai.Client(vertexai=True, project=project, location=location)
        self._client: Any = client  # genai.Client, or a fake in tests

    async def _embed_batch(self, batch: list[str], task: Task) -> list[list[float]]:
        from google.genai import errors, types

        async with self._sem:  # reserve only when the request is about to be sent
            reservation = self._guard.reserve(
                self.name, "embedding", sum(self._guard.estimate_tokens(len(t)) for t in batch), 0
            )
            try:
                res = await self._client.aio.models.embed_content(
                    model=self.name,
                    contents=batch,
                    config=types.EmbedContentConfig(
                        output_dimensionality=self.dim,
                        task_type="RETRIEVAL_QUERY" if task == "query" else "RETRIEVAL_DOCUMENT",
                    ),
                )
            except errors.ClientError:
                self._guard.release(reservation)  # rejected requests are not billed
                raise
            except BaseException:
                self._guard.settle_estimate(reservation)
                raise
        embeddings = res.embeddings or []
        counts = [e.statistics.token_count if e.statistics else None for e in embeddings]
        if embeddings and all(c is not None for c in counts):
            self._guard.settle(reservation, int(sum(c or 0 for c in counts)), 0)
        else:
            self._guard.settle_estimate(reservation)
        return [_normalize(list(e.values or [])) for e in embeddings]

    async def embed(self, texts: list[str], task: Task) -> list[list[float]]:
        batches = [texts[i : i + self._batch] for i in range(0, len(texts), self._batch)]
        results = await asyncio.gather(*(self._embed_batch(b, task) for b in batches))
        return [vec for batch in results for vec in batch]


def get_embedder() -> Embedder:
    """EMBEDDING_MODE=vertex opts into paid Vertex embeddings. LLM_MODE does not switch it on: seeding and feed-sync
    would silently re-embed the whole catalog on every start (and hashing vectors must not be mixed with Vertex ones).
    """
    mode = os.environ.get("EMBEDDING_MODE") or "fake"
    if mode == "vertex":
        cfg = load_llm_config()
        return VertexEmbedder(
            os.environ["GOOGLE_CLOUD_PROJECT"],
            os.environ.get("GOOGLE_CLOUD_LOCATION", cfg.region),
            get_budget_guard(),
        )
    if mode != "fake":
        raise ValueError(f"EMBEDDING_MODE must be 'fake' or 'vertex', got {mode!r}")
    return HashingEmbedder(load_llm_config().embedding.dimension)
