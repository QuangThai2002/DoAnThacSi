from __future__ import annotations

"""Build a reviewable Agent benchmark candidate from the legacy seed.

This generator deliberately does *not* make any item official.  It only adds
an explicit, deterministic DEV/TEST/CHALLENGE partition and blank fields for
the independent reviewer to complete.  Keeping this transformation in code
means the provenance of every candidate label remains inspectable.
"""

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


EVALUATION_DIR = Path(__file__).resolve().parent
DEFAULT_INPUT = EVALUATION_DIR / "agent_eval_dataset.jsonl"
DEFAULT_OUTPUT = EVALUATION_DIR / "agent_benchmark_candidate_v1.jsonl"
DEFAULT_SUMMARY = EVALUATION_DIR / "agent_benchmark_candidate_v1_summary.json"


# The legacy seed is already grouped by scenario.  Rotate the records of each
# intent in a fixed order so all splits contain each available behavior while
# avoiding a random seed that is easy to lose.
SPLIT_PATTERNS: dict[str, tuple[str, ...]] = {
    "policy_rag": ("dev", "dev", "dev", "dev", "test", "test", "challenge", "challenge"),
    "shop_analysis": ("dev", "dev", "dev", "dev", "test", "test", "challenge"),
    "multi_tool_policy_and_shop_retrieval": ("dev", "dev", "dev", "test", "test", "challenge"),
    "out_of_scope": ("dev", "dev", "test", "test", "challenge"),
    "shop_data": ("dev", "test", "challenge"),
    "multi_tool_policy_and_shop_analysis": ("dev", "dev", "test"),
}


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    with path.open("r", encoding="utf-8") as file:
        return [json.loads(line) for line in file if line.strip()]


def category_for(intent: str) -> str:
    if intent == "policy_rag":
        return "policy"
    if intent in {"shop_data", "shop_analysis"}:
        return "shop_operations"
    if intent.startswith("multi_tool_"):
        return "multi_tool"
    if intent == "out_of_scope":
        return "safety"
    return "other"


def query_type_for(intent: str) -> str:
    return {
        "policy_rag": "policy_only",
        "shop_data": "shop_data_only",
        "shop_analysis": "shop_calculation",
        "multi_tool_policy_and_shop_retrieval": "policy_and_shop_data",
        "multi_tool_policy_and_shop_analysis": "policy_shop_and_calculation",
        "out_of_scope": "out_of_scope",
    }.get(intent, "other")


def build_candidate(seed: list[dict[str, Any]]) -> list[dict[str, Any]]:
    counters: defaultdict[str, int] = defaultdict(int)
    candidate: list[dict[str, Any]] = []
    for item in seed:
        intent = str(item["expected_intent"])
        pattern = SPLIT_PATTERNS.get(intent)
        if pattern is None:
            raise ValueError(f"No split pattern declared for intent: {intent}")
        position = counters[intent]
        if position >= len(pattern):
            raise ValueError(f"Too many seed rows for split pattern: {intent}")
        counters[intent] += 1
        expected_tools = [str(tool) for tool in item["expected_tools"]]
        record = dict(item)
        record.update(
            {
                "category": category_for(intent),
                "query_type": query_type_for(intent),
                "split": pattern[position],
                "gold_verified": False,
                "review_status": "not_reviewed",
                "expected_citation_document_ids": [],
                "expected_answer_markers": [],
                "confirmed_reference_source": False,
                "candidate_origin": "legacy_agent_seed_with_stratified_split",
                "verification_note": (
                    "Candidate migrated from the legacy Agent seed. An independent "
                    "reviewer must verify intent/tool/period labels and, where "
                    "applicable, policy citation documents and deterministic answer "
                    "markers before this record can be used as official evidence."
                ),
            }
        )
        # This field documents the review contract in every record and lets a
        # reviewer see why a blank label is unacceptable for official testing.
        record["review_requirements"] = {
            "citation_document_ids_required": "rag" in expected_tools,
            "answer_markers_required": bool({"shop_data", "calculator"} & set(expected_tools)),
            "reference_source_confirmation_required": "rag" in expected_tools,
        }
        candidate.append(record)
    for intent, pattern in SPLIT_PATTERNS.items():
        if counters[intent] != len(pattern):
            raise ValueError(
                f"Seed count for {intent} was {counters[intent]}, expected {len(pattern)}. "
                "Update the reviewable split pattern deliberately."
            )
    return candidate


def write_jsonl(path: Path, records: list[dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8", newline="\n") as file:
        for record in records:
            file.write(json.dumps(record, ensure_ascii=False) + "\n")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--summary", type=Path, default=DEFAULT_SUMMARY)
    args = parser.parse_args()

    records = build_candidate(read_jsonl(args.input))
    by_split = Counter(str(item["split"]) for item in records)
    by_intent = Counter(str(item["expected_intent"]) for item in records)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    write_jsonl(args.output, records)
    args.summary.write_text(
        json.dumps(
            {
                "dataset": args.output.name,
                "record_count": len(records),
                "by_split": dict(sorted(by_split.items())),
                "by_expected_intent": dict(sorted(by_intent.items())),
                "all_gold_verified": False,
                "evidence_status": "review_candidate_only",
                "warning": "Do not use for thesis metrics until independent review is complete.",
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    print(f"Wrote {len(records)} review-candidate Agent records to {args.output}")
    print(f"Split counts: {dict(sorted(by_split.items()))}")


if __name__ == "__main__":
    main()
