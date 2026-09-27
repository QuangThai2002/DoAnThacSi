from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[2]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from agent.planner import Planner  # noqa: E402
from artifact_provenance import build_manifest, git_is_clean, write_manifest  # noqa: E402


DEFAULT_DATASET = Path(__file__).with_name("agent_eval_dataset.jsonl")
DEFAULT_RESULTS = PROJECT_ROOT / "data" / "processed" / "agent_plan_eval_results.csv"
DEFAULT_SUMMARY = PROJECT_ROOT / "data" / "processed" / "agent_plan_eval_summary.csv"
DEFAULT_MANIFEST = PROJECT_ROOT / "data" / "processed" / "agent_plan_eval_manifest.json"


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    with path.open("r", encoding="utf-8") as file:
        return [json.loads(line) for line in file if line.strip()]


def safe_divide(numerator: float, denominator: float) -> float:
    return numerator / denominator if denominator else 0.0


def evaluate(
    dataset: list[dict[str, Any]],
    require_verified: bool = False,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    if require_verified:
        unverified = [
            str(item.get("id", ""))
            for item in dataset
            if not bool(item.get("gold_verified", False))
        ]
        if unverified:
            raise ValueError(
                "Refusing official Agent evaluation because "
                f"{len(unverified)} item(s) have gold_verified=false. "
                f"Examples: {', '.join(unverified[:10])}"
            )

    planner = Planner()
    rows: list[dict[str, Any]] = []
    for item in dataset:
        plan = planner.plan(str(item["question"]))
        expected_tools = list(item["expected_tools"])
        planned_tools = list(plan.tools)
        expected_set = set(expected_tools)
        planned_set = set(planned_tools)
        overlap = len(expected_set & planned_set)
        if not expected_set and not planned_set:
            precision = recall = f1 = 1.0
        else:
            precision = safe_divide(overlap, len(planned_set))
            recall = safe_divide(overlap, len(expected_set))
            f1 = safe_divide(2 * precision * recall, precision + recall)
        rows.append(
            {
                "id": item["id"],
                "split": str(item.get("split", "")).strip().lower(),
                "question": item["question"],
                "expected_intent": item["expected_intent"],
                "planned_intent": plan.intent,
                "intent_correct": int(plan.intent == item["expected_intent"]),
                "expected_tools": "|".join(expected_tools),
                "planned_tools": "|".join(planned_tools),
                "tool_exact_match": int(expected_tools == planned_tools),
                "tool_precision": round(precision, 6),
                "tool_recall": round(recall, 6),
                "tool_f1": round(f1, 6),
                "planned_period": plan.period or "",
            }
        )

    count = len(rows)
    summary = {
        "count": count,
        "intent_accuracy": round(sum(row["intent_correct"] for row in rows) / count, 6) if count else 0.0,
        "tool_exact_match": round(sum(row["tool_exact_match"] for row in rows) / count, 6) if count else 0.0,
        "tool_precision": round(sum(float(row["tool_precision"]) for row in rows) / count, 6) if count else 0.0,
        "tool_recall": round(sum(float(row["tool_recall"]) for row in rows) / count, 6) if count else 0.0,
        "tool_f1": round(sum(float(row["tool_f1"]) for row in rows) / count, 6) if count else 0.0,
        "verified_item_count": sum(
            bool(item.get("gold_verified", False)) for item in dataset
        ),
        "unverified_item_count": sum(
            not bool(item.get("gold_verified", False)) for item in dataset
        ),
    }
    return rows, summary


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate deterministic Agent planning.")
    parser.add_argument("--dataset", type=Path, default=DEFAULT_DATASET)
    parser.add_argument("--output", type=Path, default=DEFAULT_RESULTS)
    parser.add_argument("--summary", type=Path, default=DEFAULT_SUMMARY)
    parser.add_argument(
        "--split",
        action="append",
        choices=["dev", "test", "challenge"],
        help="Evaluate only one or more labelled splits. Repeat this flag as needed.",
    )
    parser.add_argument(
        "--manifest",
        type=Path,
        default=DEFAULT_MANIFEST,
        help="Write dataset/code/output provenance next to the evaluation artefacts.",
    )
    parser.add_argument(
        "--require-verified",
        action="store_true",
        help="Fail if any Agent evaluation record has gold_verified=false.",
    )
    args = parser.parse_args()

    selected_splits = set(args.split) if args.split else None
    dataset = [
        item
        for item in load_jsonl(args.dataset)
        if not selected_splits
        or str(item.get("split", "")).strip().lower() in selected_splits
    ]
    if not dataset:
        raise ValueError("No Agent evaluation items match the selected split(s).")
    rows, summary = evaluate(
        dataset,
        require_verified=args.require_verified,
    )
    write_csv(args.output, rows)
    write_csv(args.summary, [summary])
    verified_count = sum(int(bool(item.get("gold_verified", False))) for item in dataset)
    selected_split_names = sorted(
        {str(item.get("split", "")).strip().lower() for item in dataset if item.get("split")}
    )
    is_official_candidate = (
        args.require_verified
        and verified_count == len(dataset)
        and selected_split_names == ["test"]
        and git_is_clean(PROJECT_ROOT)
    )
    manifest = build_manifest(
        evaluation_name="agent_planner_evaluation",
        project_root=PROJECT_ROOT,
        dataset_path=args.dataset,
        output_paths=[args.output, args.summary],
        configuration={
            "require_verified": args.require_verified,
            "selected_splits": selected_split_names,
        },
        dataset_counts={
            "total_records": len(dataset),
            "verified_selected_records": verified_count,
            "unverified_selected_records": len(dataset) - verified_count,
        },
        evidence_status=(
            "official_test_candidate"
            if is_official_candidate
            else "development_or_regression_only"
        ),
        evidence_status_reason=(
            "The selected planner TEST split was independently verified and guarded "
            "by --require-verified in a clean working tree."
            if is_official_candidate
            else (
                "This planner result is a development or regression run because it "
                "does not select a verified TEST split with --require-verified in a "
                "clean working tree."
            )
        ),
    )
    write_manifest(args.manifest, manifest)
    print(f"Wrote {len(rows)} Agent planning rows to {args.output}")
    print("metric,value")
    for key, value in summary.items():
        print(f"{key},{value}")


if __name__ == "__main__":
    main()
