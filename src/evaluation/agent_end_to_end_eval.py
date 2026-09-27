from __future__ import annotations

"""Evaluate observable behavior of the traceable Agent baseline end to end.

This evaluator is deliberately separate from ``agent_eval.py``. The latter
checks deterministic planning only; this one executes the Agent and measures
whether its declared tools actually completed, policy answers carry citations,
shop answers disclose mock data, and out-of-scope requests are refused.
"""

import argparse
import csv
import json
import math
import sys
from pathlib import Path
from statistics import median
from typing import Any, Protocol


PROJECT_ROOT = Path(__file__).resolve().parents[2]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from agent.agent_runner import AgentRunner  # noqa: E402
from agent_annotation_store import validate_official_records  # noqa: E402
from artifact_provenance import build_manifest, git_is_clean, write_manifest  # noqa: E402


DEFAULT_DATASET = Path(__file__).with_name("agent_benchmark_candidate_v1.jsonl")
DEFAULT_RESULTS = PROJECT_ROOT / "data" / "processed" / "agent_end_to_end_eval_results.csv"
DEFAULT_SUMMARY = PROJECT_ROOT / "data" / "processed" / "agent_end_to_end_eval_summary.csv"
DEFAULT_MANIFEST = PROJECT_ROOT / "data" / "processed" / "agent_end_to_end_eval_manifest.json"


class Runner(Protocol):
    def run(self, question: str) -> dict[str, Any]: ...


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    with path.open("r", encoding="utf-8") as file:
        return [json.loads(line) for line in file if line.strip()]


def percentile_95(values: list[float]) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    return ordered[max(0, math.ceil(len(ordered) * 0.95) - 1)]


def evaluate(
    dataset: list[dict[str, Any]],
    *,
    runner: Runner | None = None,
    require_verified: bool = False,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    if require_verified:
        validate_official_records(dataset)

    active_runner = runner or AgentRunner()
    rows: list[dict[str, Any]] = []
    for item in dataset:
        expected_tools = list(item["expected_tools"])
        result = active_runner.run(str(item["question"]))
        plan = result.get("plan", {})
        planned_tools = list(plan.get("tools", ()))
        trace = result.get("trace", [])
        trace_tools_ok = {
            str(entry.get("tool", ""))
            for entry in trace
            if entry.get("status") == "ok"
        }
        trace_has_error = any(entry.get("status") == "error" for entry in trace)
        citations = result.get("citations", [])
        answer = str(result.get("answer", ""))

        expected_citations = "rag" in expected_tools
        expected_citation_document_ids = {
            str(value).strip()
            for value in item.get("expected_citation_document_ids", [])
            if str(value).strip()
        }
        expected_answer_markers = [
            str(value).strip().lower()
            for value in item.get("expected_answer_markers", [])
            if str(value).strip()
        ]
        expects_mock_disclaimer = "shop_data" in expected_tools
        expects_refusal = item.get("expected_intent") == "out_of_scope"
        expected_period = item.get("expected_period")
        period_correct = plan.get("period") == expected_period if expected_period else True
        tools_executed = all(tool in trace_tools_ok for tool in expected_tools)
        citation_document_check_applicable = bool(expected_citation_document_ids)
        returned_document_ids = {
            str(citation.get("document_id", "")).strip()
            for citation in citations
            if isinstance(citation, dict)
        }
        citations_correct = bool(citations) if expected_citations else not citations
        citation_document_correct = (
            bool(expected_citation_document_ids & returned_document_ids)
            if citation_document_check_applicable
            else True
        )
        answer_marker_check_applicable = bool(expected_answer_markers)
        answer_marker_correct = (
            all(marker in answer.lower() for marker in expected_answer_markers)
            if answer_marker_check_applicable
            else True
        )
        disclaimer_correct = (
            "dữ liệu vận hành mô phỏng" in answer.lower()
            if expects_mock_disclaimer
            else True
        )
        refusal_correct = (
            "ngoài phạm vi" in answer.lower() and not trace
            if expects_refusal
            else True
        )
        plan_tools_correct = planned_tools == expected_tools
        intent_correct = plan.get("intent") == item.get("expected_intent")
        no_trace_error = not trace_has_error
        overall_pass = all(
            (
                intent_correct,
                plan_tools_correct,
                tools_executed,
                citations_correct,
                citation_document_correct,
                answer_marker_correct,
                disclaimer_correct,
                refusal_correct,
                period_correct,
                no_trace_error,
            )
        )
        rows.append(
            {
                "id": item["id"],
                "split": str(item.get("split", "")).strip().lower(),
                "expected_intent": item["expected_intent"],
                "planned_intent": plan.get("intent", ""),
                "intent_correct": int(intent_correct),
                "expected_tools": "|".join(expected_tools),
                "planned_tools": "|".join(planned_tools),
                "plan_tools_correct": int(plan_tools_correct),
                "tools_executed": int(tools_executed),
                "citation_expected": int(expected_citations),
                "citation_count": len(citations),
                "citations_correct": int(citations_correct),
                "citation_document_check_applicable": int(citation_document_check_applicable),
                "expected_citation_document_ids": "|".join(sorted(expected_citation_document_ids)),
                "returned_citation_document_ids": "|".join(sorted(returned_document_ids)),
                "citation_document_correct": int(citation_document_correct),
                "answer_marker_check_applicable": int(answer_marker_check_applicable),
                "expected_answer_markers": "|".join(expected_answer_markers),
                "answer_marker_correct": int(answer_marker_correct),
                "mock_disclaimer_correct": int(disclaimer_correct),
                "refusal_correct": int(refusal_correct),
                "expected_period": expected_period or "",
                "planned_period": plan.get("period") or "",
                "period_correct": int(period_correct),
                "trace_has_error": int(trace_has_error),
                "gold_verified": int(bool(item.get("gold_verified", False))),
                "agent_latency_seconds": round(float(result.get("agent_latency_seconds", 0.0)), 6),
                "overall_pass": int(overall_pass),
            }
        )

    def rate(name: str) -> float:
        return round(sum(int(row[name]) for row in rows) / len(rows), 6) if rows else 0.0

    latencies = [float(row["agent_latency_seconds"]) for row in rows]
    def applicable_rate(name: str, applicability: str) -> float | None:
        applicable = [row for row in rows if int(row[applicability])]
        if not applicable:
            return None
        return round(sum(int(row[name]) for row in applicable) / len(applicable), 6)

    summary = {
        "count": len(rows),
        "overall_pass_rate": rate("overall_pass"),
        "intent_accuracy": rate("intent_correct"),
        "plan_tool_exact_match": rate("plan_tools_correct"),
        "tool_execution_success": rate("tools_executed"),
        "citation_contract_success": rate("citations_correct"),
        "citation_document_correctness": applicable_rate(
            "citation_document_correct", "citation_document_check_applicable"
        ),
        "citation_document_check_count": sum(
            int(row["citation_document_check_applicable"]) for row in rows
        ),
        "answer_marker_correctness": applicable_rate(
            "answer_marker_correct", "answer_marker_check_applicable"
        ),
        "answer_marker_check_count": sum(
            int(row["answer_marker_check_applicable"]) for row in rows
        ),
        "mock_disclaimer_success": rate("mock_disclaimer_correct"),
        "out_of_scope_refusal_success": rate("refusal_correct"),
        "period_accuracy": rate("period_correct"),
        "trace_without_error_rate": round(
            sum(1 - int(row["trace_has_error"]) for row in rows) / len(rows), 6
        ) if rows else 0.0,
        "latency_median_seconds": round(median(latencies), 6) if latencies else 0.0,
        "latency_p95_seconds": round(percentile_95(latencies), 6),
        "verified_item_count": sum(int(row["gold_verified"]) for row in rows),
        "unverified_item_count": sum(1 - int(row["gold_verified"]) for row in rows),
    }
    return rows, summary


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        return
    with path.open("w", encoding="utf-8-sig", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
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
        help="Fail unless every evaluation record has gold_verified=true.",
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
        evaluation_name="agent_end_to_end_evaluation",
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
            "The selected Agent TEST split was independently verified and guarded "
            "by --require-verified in a clean working tree."
            if is_official_candidate
            else (
                "This Agent result is a development or regression run because it "
                "does not select a verified TEST split with --require-verified in a "
                "clean working tree."
            )
        ),
    )
    write_manifest(args.manifest, manifest)
    print(f"Wrote {len(rows)} Agent end-to-end rows to {args.output}")
    print("metric,value")
    for key, value in summary.items():
        print(f"{key},{value}")


if __name__ == "__main__":
    main()
