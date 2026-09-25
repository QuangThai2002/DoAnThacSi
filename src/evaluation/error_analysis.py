from __future__ import annotations

import argparse
import csv
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_INPUT = PROJECT_ROOT / "data" / "processed" / "retrieval_eval_results.csv"
DEFAULT_OUTPUT = PROJECT_ROOT / "data" / "processed" / "retrieval_error_analysis.md"


def as_bool(value: str) -> bool:
    return str(value).strip().lower() in {"1", "true", "yes"}


def as_float(value: str) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def clean_cell(value: str, limit: int = 180) -> str:
    cleaned = " ".join(str(value or "").split())
    return cleaned[:limit].rstrip() + ("..." if len(cleaned) > limit else "")


def classify(row: dict[str, str]) -> str:
    if not as_bool(row.get("hit_at_5", "")):
        return "relevant_below_top5" if as_bool(row.get("hit_at_10", "")) else "not_retrieved_top10"
    if "|" in row.get("expected_documents", "") and as_float(row.get("unique_document_recall_at_5", "")) < 1.0:
        return "partial_multi_document_retrieval"
    if as_bool(row.get("has_page_ground_truth", "")) and not as_bool(row.get("page_hit_at_5", "")):
        return "wrong_page"
    if not as_bool(row.get("hit_at_1", "")):
        return "ranking_error_top1"
    return "success"


def load_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as file:
        return list(csv.DictReader(file))


def render_report(
    rows: list[dict[str, str]],
    source: Path,
    variant: str | None,
    limit: int,
    include_success: bool,
) -> str:
    selected = [row for row in rows if not variant or row.get("variant") == variant]
    classified = [(classify(row), row) for row in selected]
    counts = Counter(label for label, _row in classified)
    samples = [(label, row) for label, row in classified if include_success or label != "success"]
    priority = {
        "not_retrieved_top10": 0,
        "relevant_below_top5": 1,
        "partial_multi_document_retrieval": 2,
        "wrong_page": 3,
        "ranking_error_top1": 4,
        "success": 5,
    }
    samples.sort(key=lambda pair: (priority[pair[0]], pair[1].get("category", ""), pair[1].get("id", "")))

    meanings = {
        "not_retrieved_top10": "No expected document appeared in the top 10.",
        "relevant_below_top5": "Relevant document appeared in ranks 6–10 only.",
        "partial_multi_document_retrieval": "A multi-document question missed at least one expected document in top 5.",
        "wrong_page": "Expected document was found but no expected page appeared in top 5.",
        "ranking_error_top1": "A relevant document exists in top 5 but not at rank 1.",
        "success": "Top-1 and page criteria passed for this heuristic taxonomy.",
    }
    lines = [
        "# Retrieval error analysis",
        "",
        f"- Generated at (UTC): {datetime.now(timezone.utc).isoformat()}",
        f"- Input: `{source}`",
        f"- Variant filter: `{variant or 'all'}`",
        f"- Rows analyzed: {len(selected)}",
        "",
        "## Error categories",
        "",
        "| Category | Count | Meaning |",
        "| --- | ---: | --- |",
    ]
    for label in sorted(counts, key=lambda item: (priority[item], item)):
        lines.append(f"| {label} | {counts[label]} | {meanings[label]} |")

    lines.extend([
        "",
        "## Review samples",
        "",
        "| ID | Error | Category | Query type | Question | Expected docs | Top docs |",
        "| --- | --- | --- | --- | --- | --- | --- |",
    ])
    for label, row in samples[:limit]:
        values = [
            row.get("id", ""),
            label,
            row.get("category", ""),
            row.get("query_type", ""),
            clean_cell(row.get("question", "")).replace("|", "\\|"),
            clean_cell(row.get("expected_documents", ""), 80),
            clean_cell(row.get("top_unique_documents_10", ""), 100),
        ]
        lines.append("| " + " | ".join(values) + " |")

    lines.extend([
        "",
        "## How to use this report",
        "",
        "Review only DEV records when deciding changes to retrieval. Record the root cause for each sample (bad gold label, chunking, lexical mismatch, embedding mismatch, source filtering, ranking, or page alignment) before changing an algorithm. Do not tune against locked TEST rows.",
    ])
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description="Create a reviewable retrieval error report.")
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--variant", help="Analyze one retrieval variant only.")
    parser.add_argument("--limit", type=int, default=30)
    parser.add_argument("--include-success", action="store_true")
    args = parser.parse_args()

    report = render_report(
        rows=load_csv(args.input),
        source=args.input,
        variant=args.variant,
        limit=max(1, args.limit),
        include_success=args.include_success,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(report, encoding="utf-8")
    print(f"Wrote error analysis to {args.output}")


if __name__ == "__main__":
    main()
