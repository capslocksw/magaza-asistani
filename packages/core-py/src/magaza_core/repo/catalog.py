from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from google.cloud.firestore_v1.base_query import FieldFilter
from google.cloud.firestore_v1.base_vector_query import DistanceMeasure
from google.cloud.firestore_v1.vector import Vector

from magaza_core.contracts import ComplementRule, DocChunk, Product

from .base import Collections, TenantScopedRepo, strip_internal

_PRODUCT_INTERNAL = ("embedding", "in_stock", "search_text", "synced_at")


@dataclass(frozen=True)
class ScoredProduct:
    product: Product
    distance: float


@dataclass(frozen=True)
class ScoredChunk:
    chunk: DocChunk
    distance: float


def product_search_text(p: Product) -> str:
    """Text that is embedded for a product (title weighted twice, specs flattened)."""
    specs = "; ".join(f"{s.label}: {s.value} {s.unit or ''}".strip() for s in p.specs)
    return (
        f"{p.title}. {p.title}. {p.brand}. {p.category_name} {p.subcategory or ''}. {p.description} "
        f"Etiketler: {' '.join(p.tags)}. {specs}"
    )


class ProductRepo(TenantScopedRepo):
    @property
    def _col(self):  # type: ignore[no-untyped-def]
        return self.col(Collections.PRODUCTS)

    @staticmethod
    def _to_product(data: dict[str, Any]) -> Product:
        return Product.model_validate(strip_internal(data, *_PRODUCT_INTERNAL))

    async def upsert_many(
        self, products: list[Product], embeddings: list[list[float]], synced_at: str | None = None
    ) -> int:
        if len(products) != len(embeddings):
            raise ValueError("products and embeddings length mismatch")
        written = 0
        for start in range(0, len(products), 400):
            batch = self.db.batch()
            for p, emb in zip(products[start : start + 400], embeddings[start : start + 400], strict=True):
                doc = p.model_dump(mode="json")
                doc.update(
                    {"embedding": Vector(emb), "in_stock": p.stock > 0, "search_text": product_search_text(p)}
                )
                if synced_at:
                    doc["synced_at"] = synced_at
                batch.set(self._col.document(p.sku), doc)
                written += 1
            await batch.commit()
        return written

    async def get(self, sku: str) -> Product | None:
        snap = await self._col.document(sku).get()
        return self._to_product(snap.to_dict() or {}) if snap.exists else None

    async def get_many(self, skus: list[str]) -> list[Product]:
        if not skus:
            return []
        refs = [self._col.document(s) for s in dict.fromkeys(skus)]
        found = {s.id: self._to_product(s.to_dict() or {}) async for s in self.db.get_all(refs) if s.exists}
        return [found[s] for s in dict.fromkeys(skus) if s in found]

    async def list_all(self) -> list[Product]:
        return [self._to_product(d.to_dict() or {}) async for d in self._col.stream()]

    async def count(self) -> int:
        result = await self._col.count().get()
        return int(result[0][0].value)

    async def delete_missing(self, keep: set[str]) -> int:
        removed = 0
        async for d in self._col.select([]).stream():
            if d.id not in keep:
                await d.reference.delete()
                removed += 1
        return removed

    async def vector_search(
        self, vector: list[float], *, category: str | None = None, limit: int = 20
    ) -> list[ScoredProduct]:
        query = self._col
        if category:
            query = query.where(filter=FieldFilter("category", "==", category))
        vq = query.find_nearest(
            vector_field="embedding",
            query_vector=Vector(vector),
            distance_measure=DistanceMeasure.COSINE,
            limit=limit,
            distance_result_field="_distance",
        )
        out: list[ScoredProduct] = []
        async for snap in vq.stream():
            data = snap.to_dict() or {}
            out.append(ScoredProduct(self._to_product(data), float(data.get("_distance", 1.0))))
        return out


class KnowledgeRepo(TenantScopedRepo):
    @property
    def _col(self):  # type: ignore[no-untyped-def]
        return self.col(Collections.DOC_CHUNKS)

    async def replace_doc(self, doc_id: str, chunks: list[DocChunk], embeddings: list[list[float]]) -> int:
        await self.delete_doc(doc_id)
        batch = self.db.batch()
        for chunk, emb in zip(chunks, embeddings, strict=True):
            data = chunk.model_dump(mode="json")
            data["embedding"] = Vector(emb)
            batch.set(self._col.document(chunk.chunk_id.replace("/", "_")), data)
        await batch.commit()
        return len(chunks)

    async def delete_doc(self, doc_id: str) -> None:
        async for d in self._col.where(filter=FieldFilter("doc_id", "==", doc_id)).stream():
            await d.reference.delete()

    async def count(self) -> int:
        result = await self._col.count().get()
        return int(result[0][0].value)

    async def vector_search(self, vector: list[float], *, limit: int = 4) -> list[ScoredChunk]:
        vq = self._col.find_nearest(
            vector_field="embedding",
            query_vector=Vector(vector),
            distance_measure=DistanceMeasure.COSINE,
            limit=limit,
            distance_result_field="_distance",
        )
        out: list[ScoredChunk] = []
        async for snap in vq.stream():
            data = snap.to_dict() or {}
            out.append(
                ScoredChunk(
                    DocChunk.model_validate(strip_internal(data, "embedding")),
                    float(data.get("_distance", 1.0)),
                )
            )
        return out


class ComplementRuleRepo(TenantScopedRepo):
    async def replace_all(self, rules: list[ComplementRule]) -> None:
        col = self.col(Collections.COMPLEMENT_RULES)
        await self._delete_collection(col)
        batch = self.db.batch()
        for rule in rules:
            batch.set(col.document(rule.rule_id), rule.model_dump(mode="json"))
        await batch.commit()

    async def list(self) -> list[ComplementRule]:
        return [
            ComplementRule.model_validate(d.to_dict())
            async for d in self.col(Collections.COMPLEMENT_RULES).stream()
        ]
