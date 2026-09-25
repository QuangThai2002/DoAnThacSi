from __future__ import annotations

from functools import lru_cache
from typing import Any

import hybrid_search_shopee_v2 as retrieval


@lru_cache(maxsize=1)
def load_rag_resources() -> tuple[Any, Any, list[dict[str, Any]], Any]:
    embedding_model, collection, chunks, bm25_index, _chunk_id_to_index = (
        retrieval.load_resources()
    )
    return embedding_model, collection, chunks, bm25_index


class RAGTool:
    """Retrieve policy evidence without calling a generative model."""

    def search(self, question: str, top_k: int = 3) -> dict[str, Any]:
        embedding_model, collection, chunks, bm25_index = load_rag_resources()
        _dense, _bm25, hybrid, elapsed = retrieval.hybrid_search(
            query=question,
            embedding_model=embedding_model,
            collection=collection,
            chunks=chunks,
            bm25_index=bm25_index,
        )
        evidence = []
        for result in hybrid[:top_k]:
            metadata = result.metadata or {}
            text = " ".join(str(result.text or "").split())
            evidence.append(
                {
                    "document_id": str(metadata.get("document_id", "")),
                    "title": str(metadata.get("title", "") or "Tài liệu chưa xác định"),
                    "page": str(metadata.get("page", "")),
                    "source_group": str(metadata.get("source_group", "")),
                    "excerpt": text[:480].rstrip() + ("..." if len(text) > 480 else ""),
                }
            )
        return {
            "tool": "rag.search",
            "retrieval_mode": "hybrid_with_heuristic",
            "latency_seconds": round(elapsed, 6),
            "evidence": evidence,
        }
