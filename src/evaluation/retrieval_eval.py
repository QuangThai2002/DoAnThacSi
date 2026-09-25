from __future__ import annotations

import argparse
import csv
import json
import math
import statistics
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable


PROJECT_ROOT = Path(__file__).resolve().parents[2]
SRC_DIR = PROJECT_ROOT / "src"

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

import hybrid_search_shopee_v2 as retrieval  # noqa: E402


DEFAULT_DATASET_PATH = Path(__file__).with_name("eval_dataset.jsonl")
DEFAULT_OUTPUT_PATH = PROJECT_ROOT / "data" / "processed" / "retrieval_eval_results.csv"
DEFAULT_SUMMARY_PATH = PROJECT_ROOT / "data" / "processed" / "retrieval_eval_summary.csv"

VARIANTS = [
    "bm25",
    "dense",
    "hybrid_without_query_bonus",
    "hybrid_with_heuristic",
]


@dataclass
class EvalItem:
    id: str
    question: str
    category: str
    query_type: str
    expected_documents: list[str]
    expected_pages: list[str]
    answerable: bool
    requires_private_shop_data: bool


def load_dataset(path: Path) -> list[EvalItem]:
    items: list[EvalItem] = []

    with path.open("r", encoding="utf-8") as file:
        for line in file:
            line = line.strip()
            if not line:
                continue

            raw = json.loads(line)
            items.append(
                EvalItem(
                    id=str(raw["id"]),
                    question=str(raw["question"]),
                    category=str(raw.get("category", "")),
                    query_type=str(raw.get("query_type", "")),
                    expected_documents=[
                        str(value) for value in raw.get("expected_documents", [])
                    ],
                    expected_pages=[
                        str(value) for value in raw.get("expected_pages", [])
                    ],
                    answerable=bool(raw.get("answerable", True)),
                    requires_private_shop_data=bool(
                        raw.get("requires_private_shop_data", False)
                    ),
                )
            )

    return items


def document_id(result: Any) -> str:
    return str(result.metadata.get("document_id", "")).strip()


def page(result: Any) -> str:
    return str(result.metadata.get("page", "")).strip()


def unique_in_order(values: list[str]) -> list[str]:
    seen: set[str] = set()
    output: list[str] = []

    for value in values:
        if not value or value in seen:
            continue
        seen.add(value)
        output.append(value)

    return output


def hit_at(results: list[Any], expected_documents: set[str], k: int) -> int:
    return int(any(document_id(result) in expected_documents for result in results[:k]))


def recall_at(results: list[Any], expected_documents: set[str], k: int) -> float:
    retrieved = {document_id(result) for result in results[:k]}
    return len(retrieved & expected_documents) / len(expected_documents)


def unique_document_recall_at(
    results: list[Any],
    expected_documents: set[str],
    k: int,
) -> float:
    retrieved = set(unique_in_order([document_id(result) for result in results])[:k])
    return len(retrieved & expected_documents) / len(expected_documents)


def reciprocal_rank_at(
    results: list[Any],
    expected_documents: set[str],
    k: int,
) -> float:
    for index, result in enumerate(results[:k], start=1):
        if document_id(result) in expected_documents:
            return 1.0 / index

    return 0.0


def ndcg_at(results: list[Any], expected_documents: set[str], k: int) -> float:
    seen_relevant_documents: set[str] = set()
    gains: list[float] = []

    for result in results[:k]:
        current_document_id = document_id(result)
        if (
            current_document_id in expected_documents
            and current_document_id not in seen_relevant_documents
        ):
            gains.append(1.0)
            seen_relevant_documents.add(current_document_id)
        else:
            gains.append(0.0)

    dcg = sum(gain / math.log2(index + 2) for index, gain in enumerate(gains))
    ideal_hits = min(len(expected_documents), k)
    idcg = sum(1.0 / math.log2(index + 2) for index in range(ideal_hits))
    return dcg / idcg if idcg else 0.0


def page_hit_at(
    results: list[Any],
    expected_documents: set[str],
    expected_pages: set[str],
    k: int,
) -> int | None:
    if not expected_pages:
        return None

    return int(
        any(
            document_id(result) in expected_documents and page(result) in expected_pages
            for result in results[:k]
        )
    )


def percentile(values: list[float], percent: float) -> float:
    if not values:
        return 0.0
    if len(values) == 1:
        return values[0]

    ordered = sorted(values)
    position = (len(ordered) - 1) * percent
    lower = math.floor(position)
    upper = math.ceil(position)

    if lower == upper:
        return ordered[int(position)]

    weight = position - lower
    return ordered[lower] * (1 - weight) + ordered[upper] * weight


def run_variant(
    variant: str,
    item: EvalItem,
    embedding_model: Any,
    collection: Any,
    chunks: list[dict],
    bm25_index: Any,
) -> tuple[list[Any], float]:
    source_groups = retrieval.detect_source_groups(item.question)
    started = time.perf_counter()

    if variant == "dense":
        results = retrieval.vector_search(
            query=item.question,
            embedding_model=embedding_model,
            collection=collection,
            source_groups=source_groups,
        )
    elif variant == "bm25":
        results = retrieval.bm25_search(
            query=item.question,
            chunks=chunks,
            bm25_index=bm25_index,
            source_groups=source_groups,
        )
    elif variant == "hybrid_with_heuristic":
        _vector_results, _bm25_results, results, _elapsed = retrieval.hybrid_search(
            query=item.question,
            embedding_model=embedding_model,
            collection=collection,
            chunks=chunks,
            bm25_index=bm25_index,
        )
    elif variant == "hybrid_without_query_bonus":
        original_bonus: Callable[[str, Any], float] = retrieval.query_aware_bonus
        retrieval.query_aware_bonus = lambda _query, _result: 0.0
        try:
            _vector_results, _bm25_results, results, _elapsed = retrieval.hybrid_search(
                query=item.question,
                embedding_model=embedding_model,
                collection=collection,
                chunks=chunks,
                bm25_index=bm25_index,
            )
        finally:
            retrieval.query_aware_bonus = original_bonus
    else:
        raise ValueError(f"Unknown variant: {variant}")

    elapsed = time.perf_counter() - started
    return results, elapsed


def warm_up(
    items: list[EvalItem],
    embedding_model: Any,
    collection: Any,
    chunks: list[dict],
    bm25_index: Any,
) -> None:
    if not items:
        return

    item = items[0]
    for variant in VARIANTS:
        run_variant(variant, item, embedding_model, collection, chunks, bm25_index)


def evaluate(
    dataset_path: Path,
    output_path: Path,
    summary_path: Path,
    repetitions: int,
) -> None:
    all_items = load_dataset(dataset_path)
    items = [item for item in all_items if item.answerable]

    embedding_model, collection, chunks, bm25_index, _chunk_id_to_index = (
        retrieval.load_resources()
    )
    warm_up(items, embedding_model, collection, chunks, bm25_index)

    rows: list[dict[str, Any]] = []

    for item in items:
        expected_documents = set(item.expected_documents)
        expected_pages = set(item.expected_pages)

        if not expected_documents:
            continue

        for variant in VARIANTS:
            results: list[Any] = []
            latencies: list[float] = []

            for attempt in range(repetitions):
                current_results, elapsed = run_variant(
                    variant=variant,
                    item=item,
                    embedding_model=embedding_model,
                    collection=collection,
                    chunks=chunks,
                    bm25_index=bm25_index,
                )
                latencies.append(elapsed)
                if attempt == 0:
                    results = current_results

            top_documents_10 = [document_id(result) for result in results[:10]]
            top_pages_10 = [page(result) for result in results[:10]]
            top_unique_documents_10 = unique_in_order(top_documents_10)
            page_hit_5 = page_hit_at(results, expected_documents, expected_pages, 5)

            rows.append(
                {
                    "id": item.id,
                    "variant": variant,
                    "category": item.category,
                    "query_type": item.query_type,
                    "hit_at_1": hit_at(results, expected_documents, 1),
                    "hit_at_3": hit_at(results, expected_documents, 3),
                    "hit_at_5": hit_at(results, expected_documents, 5),
                    "hit_at_10": hit_at(results, expected_documents, 10),
                    "recall_at_1": recall_at(results, expected_documents, 1),
                    "recall_at_3": recall_at(results, expected_documents, 3),
                    "recall_at_5": recall_at(results, expected_documents, 5),
                    "recall_at_10": recall_at(results, expected_documents, 10),
                    "unique_document_recall_at_1": unique_document_recall_at(
                        results,
                        expected_documents,
                        1,
                    ),
                    "unique_document_recall_at_3": unique_document_recall_at(
                        results,
                        expected_documents,
                        3,
                    ),
                    "unique_document_recall_at_5": unique_document_recall_at(
                        results,
                        expected_documents,
                        5,
                    ),
                    "unique_document_recall_at_10": unique_document_recall_at(
                        results,
                        expected_documents,
                        10,
                    ),
                    "mrr_at_10": reciprocal_rank_at(results, expected_documents, 10),
                    "ndcg_at_5": ndcg_at(results, expected_documents, 5),
                    "page_hit_at_5": "" if page_hit_5 is None else page_hit_5,
                    "has_page_ground_truth": bool(expected_pages),
                    "latency_median_seconds": round(statistics.median(latencies), 6),
                    "latency_p95_seconds": round(percentile(latencies, 0.95), 6),
                    "latency_runs": repetitions,
                    "expected_documents": "|".join(item.expected_documents),
                    "expected_pages": "|".join(item.expected_pages),
                    "top_documents_10": "|".join(top_documents_10),
                    "top_unique_documents_10": "|".join(top_unique_documents_10),
                    "top_pages_10": "|".join(top_pages_10),
                    "question": item.question,
                }
            )

    write_csv(output_path, rows)
    summary_rows = build_summary(rows)
    write_csv(summary_path, summary_rows)

    print(f"Wrote {len(rows)} retrieval rows to {output_path}")
    print(f"Wrote {len(summary_rows)} summary rows to {summary_path}")
    print_overall(summary_rows)


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        return

    with path.open("w", encoding="utf-8-sig", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def average(rows: list[dict[str, Any]], field: str) -> float:
    values = [float(row[field]) for row in rows if row[field] != ""]
    return sum(values) / len(values) if values else 0.0


def build_group_summary(
    rows: list[dict[str, Any]],
    group_name: str,
    group_value: str,
) -> list[dict[str, Any]]:
    output: list[dict[str, Any]] = []
    variants = sorted({str(row["variant"]) for row in rows})

    for variant in variants:
        subset = [row for row in rows if row["variant"] == variant]
        if not subset:
            continue

        page_subset = [row for row in subset if row["has_page_ground_truth"] is True]

        output.append(
            {
                "group_name": group_name,
                "group_value": group_value,
                "variant": variant,
                "count": len(subset),
                "hit_at_1": round(average(subset, "hit_at_1"), 6),
                "hit_at_3": round(average(subset, "hit_at_3"), 6),
                "hit_at_5": round(average(subset, "hit_at_5"), 6),
                "hit_at_10": round(average(subset, "hit_at_10"), 6),
                "recall_at_1": round(average(subset, "recall_at_1"), 6),
                "recall_at_3": round(average(subset, "recall_at_3"), 6),
                "recall_at_5": round(average(subset, "recall_at_5"), 6),
                "recall_at_10": round(average(subset, "recall_at_10"), 6),
                "unique_document_recall_at_5": round(
                    average(subset, "unique_document_recall_at_5"),
                    6,
                ),
                "unique_document_recall_at_10": round(
                    average(subset, "unique_document_recall_at_10"),
                    6,
                ),
                "mrr_at_10": round(average(subset, "mrr_at_10"), 6),
                "ndcg_at_5": round(average(subset, "ndcg_at_5"), 6),
                "page_labeled_count": len(page_subset),
                "page_hit_at_5": (
                    round(average(page_subset, "page_hit_at_5"), 6)
                    if page_subset
                    else ""
                ),
                "latency_median_seconds": round(
                    statistics.median(
                        [float(row["latency_median_seconds"]) for row in subset]
                    ),
                    6,
                ),
                "latency_p95_seconds": round(
                    percentile(
                        [float(row["latency_median_seconds"]) for row in subset],
                        0.95,
                    ),
                    6,
                ),
            }
        )

    return output


def build_summary(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    summary_rows = build_group_summary(rows, "overall", "all")

    for field in ["category", "query_type"]:
        for value in sorted({str(row[field]) for row in rows}):
            subset = [row for row in rows if row[field] == value]
            summary_rows.extend(build_group_summary(subset, field, value))

    return summary_rows


def print_overall(summary_rows: list[dict[str, Any]]) -> None:
    print(
        "\nvariant,count,hit@1,hit@3,hit@5,recall@5,"
        "unique_doc_recall@5,mrr@10,ndcg@5,page_hit@5,median_latency,p95_latency"
    )

    for row in summary_rows:
        if row["group_name"] != "overall":
            continue

        print(
            f"{row['variant']},{row['count']},{row['hit_at_1']:.3f},"
            f"{row['hit_at_3']:.3f},{row['hit_at_5']:.3f},"
            f"{row['recall_at_5']:.3f},"
            f"{row['unique_document_recall_at_5']:.3f},"
            f"{row['mrr_at_10']:.3f},{row['ndcg_at_5']:.3f},"
            f"{row['page_hit_at_5']},{row['latency_median_seconds']:.4f},"
            f"{row['latency_p95_seconds']:.4f}"
        )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", type=Path, default=DEFAULT_DATASET_PATH)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT_PATH)
    parser.add_argument("--summary", type=Path, default=DEFAULT_SUMMARY_PATH)
    parser.add_argument("--repetitions", type=int, default=3)
    args = parser.parse_args()

    evaluate(
        dataset_path=args.dataset,
        output_path=args.output,
        summary_path=args.summary,
        repetitions=max(1, args.repetitions),
    )


if __name__ == "__main__":
    main()
