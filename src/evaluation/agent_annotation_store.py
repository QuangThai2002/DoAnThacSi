from __future__ import annotations

"""Audit-safe manual annotation helpers for the Agent benchmark candidate.

Unlike the retrieval benchmark, an Agent item has several independently
checkable labels: intent, ordered tools, a period, policy source documents, and
deterministic markers for mock-shop calculations.  This module refuses to call
an item verified when the labels required by its declared task are absent.
"""

from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from annotation_store import (
    VALID_REVIEW_STATUSES,
    append_review_event,
    atomic_write_jsonl,
    read_jsonl,
    record_digest,
    replace_record,
    reviewed_or_draft,
)


VALID_SPLITS = {"dev", "test", "challenge"}
VALID_TOOLS = {"shop_data", "rag", "calculator"}


def parse_delimited_values(value: str) -> list[str]:
    """Parse reviewer input while preserving the order needed for answer checks."""
    return [part.strip() for part in value.replace("\n", ",").split(",") if part.strip()]


def requirements_for(item: dict[str, Any]) -> dict[str, bool]:
    expected_tools = {str(tool) for tool in item.get("expected_tools", [])}
    return {
        "citation_document_ids_required": "rag" in expected_tools,
        "answer_markers_required": bool(expected_tools & {"shop_data", "calculator"}),
        "reference_source_confirmation_required": "rag" in expected_tools,
    }


def _base_errors(item: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if not str(item.get("id", "")).strip():
        errors.append("Record is missing id.")
    if not str(item.get("question", "")).strip():
        errors.append("Question cannot be blank.")
    if not str(item.get("expected_intent", "")).strip():
        errors.append("Expected intent cannot be blank.")
    tools = item.get("expected_tools")
    if not isinstance(tools, list) or any(str(tool) not in VALID_TOOLS for tool in tools):
        errors.append("Expected tools must be a list containing only supported tool names.")
    split = str(item.get("split", "")).strip().lower()
    if split not in VALID_SPLITS:
        errors.append("Split must be one of dev, test, challenge.")
    return errors


def official_validation_errors(item: dict[str, Any]) -> list[str]:
    """Return all missing conditions before a record may enter official runs."""
    errors = _base_errors(item)
    if not bool(item.get("gold_verified", False)):
        errors.append("gold_verified must be true.")
    if str(item.get("review_status", "")) != "verified":
        errors.append("review_status must be verified.")
    if not str(item.get("reviewer", "")).strip():
        errors.append("Reviewer name is required.")
    if len(str(item.get("review_note", "")).strip()) < 10:
        errors.append("Review note must contain at least 10 characters.")
    requirements = requirements_for(item)
    citation_ids = item.get("expected_citation_document_ids", [])
    if not isinstance(citation_ids, list):
        errors.append("Expected citation document ids must be a list.")
    elif requirements["citation_document_ids_required"] and not citation_ids:
        errors.append("RAG tasks require at least one expected citation document id.")
    answer_markers = item.get("expected_answer_markers", [])
    if not isinstance(answer_markers, list):
        errors.append("Expected answer markers must be a list.")
    elif requirements["answer_markers_required"] and not answer_markers:
        errors.append("Shop/calculation tasks require at least one expected answer marker.")
    if requirements["reference_source_confirmation_required"] and not bool(
        item.get("confirmed_reference_source", False)
    ):
        errors.append("RAG tasks require reviewer confirmation of the reference source.")
    return errors


def validate_official_records(records: list[dict[str, Any]]) -> None:
    invalid: list[str] = []
    for item in records:
        errors = official_validation_errors(item)
        if errors:
            invalid.append(f"{item.get('id', '?')}: {' '.join(errors)}")
    if invalid:
        examples = " | ".join(invalid[:5])
        raise ValueError(
            "Refusing official Agent evaluation because review labels are incomplete. "
            f"Examples: {examples}"
        )


def apply_agent_review(
    item: dict[str, Any],
    *,
    reviewer: str,
    status: str,
    question: str,
    expected_intent: str,
    expected_tools: list[str],
    expected_period: str,
    expected_citation_document_ids: list[str],
    expected_answer_markers: list[str],
    confirmed_reference_source: bool,
    note: str,
) -> dict[str, Any]:
    """Apply a human review decision without mutating the input candidate."""
    reviewer = reviewer.strip()
    status = status.strip()
    question = question.strip()
    expected_intent = expected_intent.strip()
    expected_period = expected_period.strip()
    note = note.strip()
    if status not in VALID_REVIEW_STATUSES:
        raise ValueError(f"Unknown review status: {status}")
    if not reviewer:
        raise ValueError("Reviewer name is required.")
    if not question:
        raise ValueError("Question cannot be blank.")
    if not expected_intent:
        raise ValueError("Expected intent cannot be blank.")
    if not isinstance(expected_tools, list) or any(tool not in VALID_TOOLS for tool in expected_tools):
        raise ValueError("Expected tools contain an unsupported tool name.")
    if len(note) < 10:
        raise ValueError("Review note must contain at least 10 characters.")

    reviewed = deepcopy(item)
    reviewed.update(
        {
            "question": question,
            "expected_intent": expected_intent,
            "expected_tools": list(expected_tools),
            "expected_period": expected_period or None,
            "expected_citation_document_ids": list(expected_citation_document_ids),
            "expected_answer_markers": list(expected_answer_markers),
            "confirmed_reference_source": bool(confirmed_reference_source),
            "review_requirements": requirements_for({"expected_tools": expected_tools}),
            "gold_verified": status == "verified",
            "review_status": status,
            "reviewer": reviewer,
            "reviewed_at_utc": datetime.now(timezone.utc).isoformat(),
            "review_note": note,
            "verification_note": (
                f"Independent Agent annotation by {reviewer}: {note}"
                if status == "verified"
                else f"Agent annotation by {reviewer} ({status}): {note}"
            ),
        }
    )
    if status == "verified":
        errors = official_validation_errors(reviewed)
        if errors:
            raise ValueError("Cannot save verified record: " + " ".join(errors))
    return reviewed


__all__ = [
    "append_review_event",
    "apply_agent_review",
    "atomic_write_jsonl",
    "official_validation_errors",
    "parse_delimited_values",
    "read_jsonl",
    "record_digest",
    "replace_record",
    "reviewed_or_draft",
    "validate_official_records",
]
