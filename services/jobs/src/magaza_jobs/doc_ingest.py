"""doc-ingest: technical data sheet PDFs -> text chunks -> embeddings in Firestore (tenant scoped).

python -m magaza_jobs.doc_ingest --tenant yapi-market
"""

from __future__ import annotations

import argparse
import asyncio
import io
import logging
import re
import time
from pathlib import Path
from typing import Any

from google.cloud.firestore import AsyncClient
from pypdf import PdfReader

from magaza_core.contracts import DocChunk
from magaza_core.embedding import Embedder, get_embedder
from magaza_core.repo import KnowledgeRepo, TenantRegistry, get_db
from magaza_core.tenancy import TenantContext
from magaza_core.text import fold

log = logging.getLogger(__name__)
MAX_CHARS = 900
_SKU_IN_NAME = re.compile(r"[A-Z]{2,4}-[A-Z0-9]{2,5}-\d{3,6}")


# Section names common to technical data sheets in general (not sector specific).
KNOWN_SECTIONS = {
    "urun tanimi",
    "kullanim alanlari",
    "teknik ozellikler",
    "uygulama",
    "uygulama adimlari",
    "kuruma",
    "kuruma ve bekleme sureleri",
    "sik sorulan sorular",
    "guvenlik",
    "guvenlik uyarilari",
    "saklama",
    "ambalaj",
    "depolama",
    "uyarilar",
    "notlar",
}


def _is_heading(line: str, nxt: str | None) -> bool:
    """Known section name, or a short title-like line followed by a paragraph (tables have short rows)."""
    line = line.strip()
    if fold(line) in KNOWN_SECTIONS:
        return True
    return (
        3 <= len(line) <= 40
        and line[0].isupper()
        and not line.endswith((".", ",", ":", ";"))
        and not any(ch.isdigit() for ch in line)
        and nxt is not None
        and len(nxt.strip()) > 60
    )


def chunk_pages(pages: list[str], *, doc_id: str, sku: str | None, source_url: str) -> list[DocChunk]:
    """Splits extracted text into section-aware chunks (heading = short title-like line)."""
    lines: list[tuple[int, str]] = [
        (n, ln.rstrip()) for n, text in enumerate(pages, start=1) for ln in text.splitlines() if ln.strip()
    ]
    if not lines:
        return []
    header_end = next((i for i, (_, ln) in enumerate(lines) if ln.startswith("Ürün kodu")), 0)
    title_lines = [ln for _, ln in lines[:header_end] if "TEKNİK FÖY" not in ln.upper() or "—" in ln]
    title = " ".join(title_lines[-2:]).strip() if title_lines else doc_id
    title = re.sub(r"\s+", " ", title)
    chunks: list[DocChunk] = []
    section: str | None = "Genel"
    buffer: list[str] = []
    page_start = lines[0][0]

    def flush() -> None:
        nonlocal buffer
        text = " ".join(buffer).strip()
        if text:
            for part in range(0, len(text), MAX_CHARS):
                chunks.append(
                    DocChunk(
                        chunk_id=f"{doc_id}#{len(chunks)}",
                        doc_id=doc_id,
                        sku=sku,
                        title=title,
                        section=section,
                        text=f"{section}: {text[part : part + MAX_CHARS]}"
                        if section
                        else text[part : part + MAX_CHARS],
                        order=len(chunks),
                        page=page_start,
                        source_url=source_url,
                    )
                )
        buffer = []

    body_start = header_end + 1 if lines[header_end][1].startswith("Ürün kodu") else header_end
    for i, (page, line) in enumerate(lines[body_start:], start=body_start):
        nxt = lines[i + 1][1] if i + 1 < len(lines) else None
        if _is_heading(line, nxt) and not line.startswith("Ürün kodu"):
            flush()
            section, page_start = line.strip(), page
        else:
            if not buffer:
                page_start = page
            buffer.append(line.strip())
    flush()
    return chunks


def extract(path: Path) -> list[str]:
    if path.suffix.lower() == ".pdf":
        reader = PdfReader(io.BytesIO(path.read_bytes()))
        return [page.extract_text() or "" for page in reader.pages]
    # Markdown fallback (e.g. PDFs not rendered): strip markdown syntax.
    text = re.sub(r"[#*_|`]", " ", path.read_text(encoding="utf-8"))
    return [text]


async def ingest_docs(
    db: AsyncClient, ctx: TenantContext, embedder: Embedder, docs_dir: str | None = None
) -> dict[str, Any]:
    started = time.perf_counter()
    folder = Path(docs_dir or ctx.config.catalog.docs_url or "")
    if not folder.is_dir():
        return {"docs": 0, "chunks": 0, "error": f"docs folder not found: {folder}"}
    files: dict[str, Path] = {}
    for path in sorted(folder.iterdir()):
        suffix = path.suffix.lower()
        if suffix == ".pdf":
            files[path.stem] = path  # PDFs win over their Markdown sources
        elif suffix == ".md":
            files.setdefault(path.stem, path)
    repo = KnowledgeRepo(db, ctx)
    total = 0
    for stem, path in files.items():
        sku_match = _SKU_IN_NAME.search(stem)
        sku = sku_match.group(0) if sku_match else None
        doc_id = f"doc-{stem.lower()}"
        chunks = chunk_pages(extract(path), doc_id=doc_id, sku=sku, source_url=f"/docs/{stem}.pdf")
        if not chunks:
            continue
        embeddings = await embedder.embed([f"{c.title}. {c.text}" for c in chunks], "document")
        total += await repo.replace_doc(doc_id, chunks, embeddings)
    return {"docs": len(files), "chunks": total, "seconds": round(time.perf_counter() - started, 2)}


async def _main(tenant_id: str, docs_dir: str | None) -> None:
    db = get_db()
    config = await TenantRegistry(db).get(tenant_id)
    if config is None:
        raise SystemExit(f"unknown tenant {tenant_id}")
    print(await ingest_docs(db, TenantContext.of(config), get_embedder(), docs_dir))


def main() -> None:
    parser = argparse.ArgumentParser(description="Ingest a tenant's technical data sheets")
    parser.add_argument("--tenant", required=True)
    parser.add_argument("--docs", help="override docs folder")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO)
    asyncio.run(_main(args.tenant, args.docs))


if __name__ == "__main__":
    main()
