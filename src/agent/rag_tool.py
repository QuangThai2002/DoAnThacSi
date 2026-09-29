from __future__ import annotations

from functools import lru_cache
from time import perf_counter
from typing import Any

import hybrid_search_shopee_v2 as retrieval


@lru_cache(maxsize=1)
def load_bm25_resources() -> tuple[list[dict[str, Any]], Any]:
    """Load the lightweight local policy index without starting the embedding model."""
    if not retrieval.CHUNKS_PATH.exists():
        raise FileNotFoundError(f"Không tìm thấy: {retrieval.CHUNKS_PATH}")

    chunks = retrieval.load_jsonl(retrieval.CHUNKS_PATH)
    documents = [
        retrieval.tokenize(
            f"{chunk.get('title', '')}\n{chunk.get('source_group', '')}\n{chunk.get('text', '')}"
        )
        for chunk in chunks
    ]
    return chunks, retrieval.BM25Index(documents)


@lru_cache(maxsize=1)
def load_rag_resources() -> tuple[Any, Any, list[dict[str, Any]], Any]:
    """Load the slower semantic resources only for questions that need them."""
    if not retrieval.VECTOR_DB_DIR.exists():
        raise FileNotFoundError(f"Không tìm thấy Vector DB: {retrieval.VECTOR_DB_DIR}")
    chunks, bm25_index = load_bm25_resources()
    embedding_model = retrieval.SentenceTransformer(retrieval.EMBEDDING_MODEL)
    chroma_client = retrieval.chromadb.PersistentClient(path=str(retrieval.VECTOR_DB_DIR))
    collection = chroma_client.get_collection(name=retrieval.COLLECTION_NAME)
    return embedding_model, collection, chunks, bm25_index


class RAGTool:
    """Retrieve policy evidence without calling a generative model."""

    def search(self, question: str, top_k: int = 3) -> dict[str, Any]:
        source_groups = retrieval.detect_source_groups(question)
        if source_groups == ["shopee_policy"]:
            return self._fast_policy_search(question, top_k)

        # Community Cloud receives the tracked text corpus but not the local
        # Chroma directory. Keep public demos useful by falling back to BM25
        # instead of returning an internal setup error.
        if not retrieval.VECTOR_DB_DIR.exists():
            return self._fallback_bm25_search(question, top_k, tuple(source_groups))

        embedding_model, collection, chunks, bm25_index = load_rag_resources()
        _dense, _bm25, hybrid, elapsed = retrieval.hybrid_search(
            query=question,
            embedding_model=embedding_model,
            collection=collection,
            chunks=chunks,
            bm25_index=bm25_index,
        )
        return self._result_from_ranked(
            hybrid[:top_k], elapsed, retrieval_mode="hybrid_with_heuristic"
        )

    @staticmethod
    @lru_cache(maxsize=128)
    def _fast_policy_search(question: str, top_k: int) -> dict[str, Any]:
        """Answer common Shopee-policy questions from the local text index first."""
        started = perf_counter()
        chunks, bm25_index = load_bm25_resources()
        source_groups = retrieval.detect_source_groups(question)
        bm25_results = retrieval.bm25_search(
            query=question,
            chunks=chunks,
            bm25_index=bm25_index,
            source_groups=source_groups,
        )
        ranked = retrieval.fuse_results(question, [], bm25_results)
        return RAGTool._result_from_ranked(
            ranked[:top_k], perf_counter() - started, retrieval_mode="bm25_fast_path"
        )

    @staticmethod
    @lru_cache(maxsize=128)
    def _fallback_bm25_search(
        question: str,
        top_k: int,
        source_groups: tuple[str, ...],
    ) -> dict[str, Any]:
        """Search tracked source text when the optional vector index is absent."""
        started = perf_counter()
        chunks, bm25_index = load_bm25_resources()
        bm25_results = retrieval.bm25_search(
            query=question,
            chunks=chunks,
            bm25_index=bm25_index,
            source_groups=list(source_groups),
        )
        ranked = retrieval.fuse_results(question, [], bm25_results)
        return RAGTool._result_from_ranked(
            ranked[:top_k],
            perf_counter() - started,
            retrieval_mode="bm25_without_vector_db",
        )

    @staticmethod
    def _result_from_ranked(
        ranked: list[Any], elapsed: float, retrieval_mode: str
    ) -> dict[str, Any]:
        evidence = []
        for result in ranked:
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
            "retrieval_mode": retrieval_mode,
            "latency_seconds": round(elapsed, 6),
            "evidence": evidence,
        }
