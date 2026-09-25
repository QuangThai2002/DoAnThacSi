from __future__ import annotations

"""Create an immutable benchmark candidate only after review checks pass."""

import argparse
import hashlib
import json
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from audit_gold_benchmark import audit, read_jsonl, write_jsonl


DEFAULT_DATASET = Path(__file__).with_name("gold_benchmark_v1.jsonl")
PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CHUNKS = PROJECT_ROOT / "data" / "processed" / "chunks.jsonl"
DEFAULT_OUTPUT = Path(__file__).with_name("gold_benchmark_v1_locked.jsonl")
DEFAULT_MANIFEST = Path(__file__).with_name("gold_benchmark_v1_locked_manifest.json")
REQUIRED_SPLITS = {"dev", "test", "challenge"}

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file:
        for block in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def validation_errors(dataset: list[dict[str, Any]], chunks: list[dict[str, Any]]) -> list[str]:
    errors: list[str] = []
    if not dataset:
        return ["Dataset is empty."]

    split_counts = Counter(str(item.get("split", "")).strip().lower() for item in dataset)
    missing_splits = sorted(REQUIRED_SPLITS - set(split_counts))
    if missing_splits:
        errors.append("Missing required split(s): " + ", ".join(missing_splits))
    if split_counts.get("test", 0) == 0:
        errors.append("TEST split must contain at least one record.")

    unverified = [str(item.get("id", "")) for item in dataset if not item.get("gold_verified", False)]
    if unverified:
        errors.append(
            f"{len(unverified)} record(s) have gold_verified=false. Examples: {', '.join(unverified[:10])}"
        )

    queue, report = audit(dataset, chunks)
    unresolved = [record for record in queue if record["quality_flags"]]
    if unresolved:
        examples = ", ".join(record["id"] for record in unresolved[:10])
        errors.append(
            f"{len(unresolved)} record(s) still have audit flags. Examples: {examples}"
        )
    return errors


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", type=Path, default=DEFAULT_DATASET)
    parser.add_argument("--chunks", type=Path, default=DEFAULT_CHUNKS)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument(
        "--force",
        action="store_true",
        help="Allow replacing an existing locked candidate after validation passes.",
    )
    args = parser.parse_args()

    if (args.output.exists() or args.manifest.exists()) and not args.force:
        raise FileExistsError(
            "Locked output already exists. Refusing to overwrite it; use --force only for a deliberate re-lock."
        )

    dataset = read_jsonl(args.dataset)
    chunks = read_jsonl(args.chunks)
    errors = validation_errors(dataset, chunks)
    if errors:
        formatted = "\n".join(f"- {error}" for error in errors)
        raise ValueError(f"Benchmark cannot be locked:\n{formatted}")

    write_jsonl(args.output, dataset)
    manifest = {
        "locked_at_utc": datetime.now(timezone.utc).isoformat(),
        "source_dataset": str(args.dataset),
        "source_dataset_sha256": sha256(args.dataset),
        "locked_dataset": str(args.output),
        "locked_dataset_sha256": sha256(args.output),
        "chunks_path": str(args.chunks),
        "chunks_sha256": sha256(args.chunks),
        "total": len(dataset),
        "split": dict(Counter(str(item["split"]) for item in dataset)),
    }
    args.manifest.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Locked {len(dataset)} verified records to {args.output}")
    print(f"Wrote manifest to {args.manifest}")


if __name__ == "__main__":
    main()
