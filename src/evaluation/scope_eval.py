from __future__ import annotations

import argparse
import csv
import json
import sys
from collections import Counter
from dataclasses import dataclass
from pathlib import Path


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
DEFAULT_OUTPUT_PATH = PROJECT_ROOT / "data" / "processed" / "scope_eval_results.csv"
DEFAULT_SUMMARY_PATH = PROJECT_ROOT / "data" / "processed" / "scope_eval_summary.csv"

LABELS = ["answerable", "private_data", "out_of_scope"]


@dataclass
class ScopeItem:
    id: str
    question: str
    category: str
    query_type: str
    expected_label: str


def load_dataset(path: Path) -> list[ScopeItem]:
    items: list[ScopeItem] = []

    with path.open("r", encoding="utf-8") as file:
        for line in file:
            line = line.strip()
            if not line:
                continue

            raw = json.loads(line)
            answerable = bool(raw.get("answerable", True))
            requires_private_shop_data = bool(raw.get("requires_private_shop_data", False))

            if requires_private_shop_data:
                expected_label = "private_data"
            elif not answerable:
                expected_label = "out_of_scope"
            else:
                expected_label = "answerable"

            items.append(
                ScopeItem(
                    id=str(raw["id"]),
                    question=str(raw["question"]),
                    category=str(raw.get("category", "")),
                    query_type=str(raw.get("query_type", "")),
                    expected_label=expected_label,
                )
            )

    return items


def predict_label(question: str) -> str:
    if retrieval.business_private_data_question(question):
        return "private_data"

    if not retrieval.detect_source_groups(question):
        return "out_of_scope"

    return "answerable"


def safe_divide(numerator: float, denominator: float) -> float:
    return numerator / denominator if denominator else 0.0


def evaluate(dataset_path: Path, output_path: Path, summary_path: Path) -> None:
    items = load_dataset(dataset_path)
    rows: list[dict[str, object]] = []

    for item in items:
        predicted_label = predict_label(item.question)
        rows.append(
            {
                "id": item.id,
                "category": item.category,
                "query_type": item.query_type,
                "expected_label": item.expected_label,
                "predicted_label": predicted_label,
                "correct": int(predicted_label == item.expected_label),
                "question": item.question,
            }
        )

    summary_rows = build_summary(rows)
    write_csv(output_path, rows)
    write_csv(summary_path, summary_rows)

    accuracy = safe_divide(sum(int(row["correct"]) for row in rows), len(rows))
    print(f"Wrote {len(rows)} scope rows to {output_path}")
    print(f"Wrote {len(summary_rows)} summary rows to {summary_path}")
    print(f"accuracy,{accuracy:.3f}")


def build_summary(rows: list[dict[str, object]]) -> list[dict[str, object]]:
    output: list[dict[str, object]] = []
    total = len(rows)
    correct = sum(int(row["correct"]) for row in rows)
    output.append(
        {
            "label": "overall",
            "support": total,
            "precision": "",
            "recall": "",
            "f1": "",
            "accuracy": round(safe_divide(correct, total), 6),
        }
    )

    for label in LABELS:
        true_positive = sum(
            1
            for row in rows
            if row["expected_label"] == label and row["predicted_label"] == label
        )
        predicted_positive = sum(1 for row in rows if row["predicted_label"] == label)
        actual_positive = sum(1 for row in rows if row["expected_label"] == label)

        precision = safe_divide(true_positive, predicted_positive)
        recall = safe_divide(true_positive, actual_positive)
        f1 = safe_divide(2 * precision * recall, precision + recall)

        output.append(
            {
                "label": label,
                "support": actual_positive,
                "precision": round(precision, 6),
                "recall": round(recall, 6),
                "f1": round(f1, 6),
                "accuracy": "",
            }
        )

    confusion = Counter(
        (str(row["expected_label"]), str(row["predicted_label"])) for row in rows
    )
    for expected in LABELS:
        for predicted in LABELS:
            output.append(
                {
                    "label": f"confusion:{expected}->{predicted}",
                    "support": confusion[(expected, predicted)],
                    "precision": "",
                    "recall": "",
                    "f1": "",
                    "accuracy": "",
                }
            )

    return output


def write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        return

    with path.open("w", encoding="utf-8-sig", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", type=Path, default=DEFAULT_DATASET_PATH)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT_PATH)
    parser.add_argument("--summary", type=Path, default=DEFAULT_SUMMARY_PATH)
    args = parser.parse_args()

    evaluate(args.dataset, args.output, args.summary)


if __name__ == "__main__":
    main()
