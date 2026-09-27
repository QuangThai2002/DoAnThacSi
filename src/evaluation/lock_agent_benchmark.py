from __future__ import annotations

"""Lock a human-reviewed Agent TEST split with data and corpus provenance.

The source review file is never modified.  This command writes a separate,
TEST-only JSONL and refuses to overwrite it by default.  It is intentionally a
last step: the regular Agent evaluators still require ``--require-verified``.
"""

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[2]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from artifact_provenance import git_is_clean, git_revision, sha256_file  # noqa: E402
from agent_annotation_store import atomic_write_jsonl, read_jsonl, validate_official_records  # noqa: E402


DEFAULT_DATASET = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "agent_benchmark_review"
    / "agent_benchmark_candidate_v1_reviewed.jsonl"
)
DEFAULT_CHUNKS = PROJECT_ROOT / "data" / "processed" / "chunks.jsonl"
DEFAULT_SHOP_MOCK_DIR = PROJECT_ROOT / "data" / "shop_mock"
DEFAULT_OUTPUT = Path(__file__).with_name("agent_benchmark_test_locked.jsonl")
DEFAULT_MANIFEST = Path(__file__).with_name("agent_benchmark_test_locked_manifest.json")


def source_document_ids(chunks_path: Path) -> set[str]:
    return {
        str(record.get("document_id", "")).strip()
        for record in read_jsonl(chunks_path)
        if str(record.get("document_id", "")).strip()
    }


def validation_errors(records: list[dict[str, Any]], available_document_ids: set[str]) -> list[str]:
    if not records:
        return ["No TEST records were selected."]
    split_errors = [
        str(record.get("id", "?"))
        for record in records
        if str(record.get("split", "")).strip().lower() != "test"
    ]
    errors: list[str] = []
    if split_errors:
        errors.append("Locked Agent output must contain TEST records only: " + ", ".join(split_errors[:5]))
    try:
        validate_official_records(records)
    except ValueError as exc:
        errors.append(str(exc))
    unknown_citation_docs: list[str] = []
    for record in records:
        for document_id in record.get("expected_citation_document_ids", []):
            if str(document_id) not in available_document_ids:
                unknown_citation_docs.append(f"{record.get('id', '?')}:{document_id}")
    if unknown_citation_docs:
        errors.append(
            "Expected citation document id is absent from current chunks.jsonl: "
            + ", ".join(unknown_citation_docs[:10])
        )
    return errors


def mock_data_snapshot(directory: Path) -> dict[str, str]:
    if not directory.is_dir():
        raise FileNotFoundError(f"Mock shop data directory does not exist: {directory}")
    files = sorted(path for path in directory.rglob("*.csv") if path.is_file())
    if not files:
        raise ValueError(f"No CSV file exists in mock shop data directory: {directory}")
    return {str(path.relative_to(directory)).replace("\\", "/"): sha256_file(path) for path in files}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", type=Path, default=DEFAULT_DATASET)
    parser.add_argument("--chunks", type=Path, default=DEFAULT_CHUNKS)
    parser.add_argument("--shop-mock-dir", type=Path, default=DEFAULT_SHOP_MOCK_DIR)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument(
        "--force",
        action="store_true",
        help="Allow replacing an existing locked Agent TEST output after validation passes.",
    )
    args = parser.parse_args()

    if (args.output.exists() or args.manifest.exists()) and not args.force:
        raise FileExistsError(
            "Locked output already exists. Refusing to overwrite it; use --force only for a deliberate re-lock."
        )
    if not args.dataset.is_file():
        raise FileNotFoundError(f"Reviewed Agent dataset does not exist: {args.dataset}")
    if not args.chunks.is_file():
        raise FileNotFoundError(f"Current chunks file does not exist: {args.chunks}")

    all_records = read_jsonl(args.dataset)
    test_records = [
        record for record in all_records if str(record.get("split", "")).strip().lower() == "test"
    ]
    errors = validation_errors(test_records, source_document_ids(args.chunks))
    if errors:
        formatted = "\n".join(f"- {error}" for error in errors)
        raise ValueError(f"Agent TEST benchmark cannot be locked:\n{formatted}")

    atomic_write_jsonl(args.output, test_records)
    manifest = {
        "schema_version": 1,
        "locked_at_utc": datetime.now(timezone.utc).isoformat(),
        "lock_type": "agent_test_only",
        "source_dataset": {"path": str(args.dataset.resolve()), "sha256": sha256_file(args.dataset)},
        "locked_dataset": {"path": str(args.output.resolve()), "sha256": sha256_file(args.output)},
        "selected_split": "test",
        "record_count": len(test_records),
        "chunks": {"path": str(args.chunks.resolve()), "sha256": sha256_file(args.chunks)},
        "shop_mock_csv_sha256": mock_data_snapshot(args.shop_mock_dir),
        "project_git_revision": git_revision(PROJECT_ROOT),
        "project_git_is_clean": git_is_clean(PROJECT_ROOT),
        "validation": "validate_official_records + citation document ids present in chunks",
    }
    args.manifest.parent.mkdir(parents=True, exist_ok=True)
    args.manifest.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Locked {len(test_records)} independently reviewed Agent TEST records to {args.output}")
    print(f"Wrote manifest to {args.manifest}")


if __name__ == "__main__":
    main()
