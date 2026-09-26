from __future__ import annotations

"""Durable, auditable storage helpers for manual benchmark annotation.

The draft benchmark is never modified in place. Review decisions are written to
a separate JSONL file and every save also appends a compact event to a journal.
This keeps the difference between auto-derived material and human review
traceable for a thesis experiment.
"""

import hashlib
import json
import os
import tempfile
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


VALID_REVIEW_STATUSES = {"verified", "needs_rewrite", "rejected"}


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as file:
        for line_number, line in enumerate(file, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                record = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(f"Invalid JSON at {path}:{line_number}: {exc}") from exc
            if not isinstance(record, dict):
                raise ValueError(f"Expected an object at {path}:{line_number}")
            records.append(record)
    return records


def atomic_write_jsonl(path: Path, records: list[dict[str, Any]]) -> None:
    """Write JSONL atomically so a crashed review session cannot corrupt it."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        mode="w",
        encoding="utf-8",
        newline="\n",
        dir=path.parent,
        prefix=f".{path.name}.",
        suffix=".tmp",
        delete=False,
    ) as temporary:
        for record in records:
            temporary.write(json.dumps(record, ensure_ascii=False) + "\n")
        temporary_path = Path(temporary.name)
    try:
        os.replace(temporary_path, path)
    finally:
        if temporary_path.exists():
            temporary_path.unlink(missing_ok=True)


def record_digest(record: dict[str, Any]) -> str:
    serialized = json.dumps(record, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def reviewed_or_draft(draft_path: Path, reviewed_path: Path) -> list[dict[str, Any]]:
    """Open an existing review copy, or return a copy of the untouched draft."""
    if reviewed_path.exists():
        return read_jsonl(reviewed_path)
    return deepcopy(read_jsonl(draft_path))


def apply_review(
    item: dict[str, Any],
    *,
    reviewer: str,
    status: str,
    confirmed_original_pdf_page: bool,
    question: str,
    reference_answer: str,
    evidence: list[dict[str, Any]],
    expected_documents: list[str],
    expected_pages: list[str],
    note: str,
) -> dict[str, Any]:
    """Return a reviewed record, rejecting claims that are not auditable."""
    reviewer = reviewer.strip()
    note = note.strip()
    question = question.strip()
    reference_answer = reference_answer.strip()
    if status not in VALID_REVIEW_STATUSES:
        raise ValueError(f"Unknown review status: {status}")
    if not reviewer:
        raise ValueError("Reviewer name is required.")
    if len(note) < 10:
        raise ValueError("Review note must contain at least 10 characters.")
    if not question:
        raise ValueError("Question cannot be blank.")
    if not reference_answer:
        raise ValueError("Reference answer cannot be blank.")
    if not isinstance(evidence, list) or not evidence:
        raise ValueError("At least one evidence record is required.")
    if status == "verified" and not confirmed_original_pdf_page:
        raise ValueError("Verification requires confirmation that the original PDF page was checked.")

    reviewed = deepcopy(item)
    reviewed.update(
        {
            "question": question,
            "reference_answer": reference_answer,
            "evidence": evidence,
            "expected_documents": [value.strip() for value in expected_documents if value.strip()],
            "expected_pages": [value.strip() for value in expected_pages if value.strip()],
            "gold_verified": status == "verified",
            "review_status": status,
            "reviewer": reviewer,
            "reviewed_at_utc": datetime.now(timezone.utc).isoformat(),
            "review_note": note,
            "verification_note": (
                f"Manual PDF/page review by {reviewer}: {note}"
                if status == "verified"
                else f"Review by {reviewer} ({status}): {note}"
            ),
        }
    )
    return reviewed


def replace_record(records: list[dict[str, Any]], reviewed: dict[str, Any]) -> list[dict[str, Any]]:
    item_id = str(reviewed.get("id", "")).strip()
    if not item_id:
        raise ValueError("Reviewed record is missing its id.")
    replacement_count = 0
    updated: list[dict[str, Any]] = []
    for item in records:
        if str(item.get("id", "")).strip() == item_id:
            updated.append(reviewed)
            replacement_count += 1
        else:
            updated.append(item)
    if replacement_count != 1:
        raise ValueError(f"Expected exactly one matching record for {item_id}, found {replacement_count}.")
    return updated


def append_review_event(
    journal_path: Path,
    *,
    before: dict[str, Any],
    after: dict[str, Any],
) -> None:
    """Append a minimal change record without copying evidence contents into the log."""
    journal_path.parent.mkdir(parents=True, exist_ok=True)
    event = {
        "event_at_utc": datetime.now(timezone.utc).isoformat(),
        "record_id": after.get("id"),
        "reviewer": after.get("reviewer"),
        "review_status": after.get("review_status"),
        "gold_verified": after.get("gold_verified", False),
        "before_sha256": record_digest(before),
        "after_sha256": record_digest(after),
    }
    with journal_path.open("a", encoding="utf-8", newline="\n") as file:
        file.write(json.dumps(event, ensure_ascii=False) + "\n")
