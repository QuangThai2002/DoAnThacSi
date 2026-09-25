from __future__ import annotations

"""Audit a draft retrieval benchmark before it is used in a thesis experiment.

This script deliberately does not change gold labels. It validates their link to
the processed chunks and emits review flags so that a human can verify every
record against the original PDF/page before the TEST split is locked.
"""

import argparse
import json
import re
import unicodedata
from collections import Counter
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DATASET = Path(__file__).with_name("gold_benchmark_v1.jsonl")
DEFAULT_CHUNKS = PROJECT_ROOT / "data" / "processed" / "chunks.jsonl"
DEFAULT_REPORT = PROJECT_ROOT / "data" / "processed" / "gold_benchmark_v1_audit.json"
DEFAULT_REVIEW_QUEUE = (
    PROJECT_ROOT / "data" / "processed" / "gold_benchmark_v1_review_queue.jsonl"
)

NAVIGATION_MARKERS = (
    "xin chao",
    "shopee co the giup gi cho ban",
    "mua sam cung shopee",
    "khuyen mai uu dai",
    "thanh toan don hang",
    "thong tin chung",
    "language supported",
    "last updated",
)
PAGE_REFERENCE = re.compile(r"\b(trang|page)\s*\d+\b", re.IGNORECASE)
TITLE_PREFIX = re.compile(r"^(theo|trong|bao cao|van ban phap luat)\s+", re.IGNORECASE)
WORD = re.compile(r"[0-9A-Za-zÀ-ỹ_/-]+")


def normalize(text: str) -> str:
    text = unicodedata.normalize("NFD", str(text or ""))
    text = "".join(ch for ch in text if unicodedata.category(ch) != "Mn")
    text = text.replace("đ", "d").replace("Đ", "D")
    return re.sub(r"\s+", " ", text).strip().lower()


def tokens(text: str) -> set[str]:
    return {
        token
        for token in WORD.findall(normalize(text))
        if len(token) >= 3 and not token.isdigit()
    }


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


def chunk_lookup(chunks: list[dict[str, Any]]) -> dict[tuple[str, str], list[str]]:
    lookup: dict[tuple[str, str], list[str]] = {}
    for chunk in chunks:
        document_id = str(chunk.get("document_id", "")).strip()
        page = str(chunk.get("page", "") or chunk.get("location", "")).strip()
        text = str(chunk.get("text", "")).strip()
        if document_id and text:
            lookup.setdefault((document_id, page), []).append(text)
    return lookup


def support_matches_chunk(support: str, chunk_texts: list[str]) -> bool:
    support_normalized = normalize(support).replace("...", "").strip()
    if len(support_normalized) < 40:
        return False

    support_tokens = tokens(support)
    if not support_tokens:
        return False

    for chunk_text in chunk_texts:
        chunk_normalized = normalize(chunk_text)
        if support_normalized in chunk_normalized:
            return True
        overlap = len(support_tokens & tokens(chunk_text)) / len(support_tokens)
        if overlap >= 0.85:
            return True
    return False


def quality_flags(item: dict[str, Any], chunks_by_source: dict[tuple[str, str], list[str]]) -> list[str]:
    flags: list[str] = []
    question = str(item.get("question", "")).strip()
    expected_documents = [str(value).strip() for value in item.get("expected_documents", [])]
    expected_pages = [str(value).strip() for value in item.get("expected_pages", [])]
    evidence = item.get("evidence", [])

    if not str(item.get("id", "")).strip():
        flags.append("missing_id")
    if len(tokens(question)) < 5:
        flags.append("question_too_short")
    if PAGE_REFERENCE.search(question):
        flags.append("question_leaks_page_number")
    if TITLE_PREFIX.match(question):
        flags.append("question_likely_mentions_source_title")
    if not item.get("gold_verified", False):
        flags.append("gold_not_human_verified")
    if not expected_documents:
        flags.append("missing_expected_document")
    if item.get("answerable", True) and not evidence:
        flags.append("answerable_without_evidence")
    if not isinstance(evidence, list):
        flags.append("invalid_evidence_type")
        evidence = []

    evidence_documents: set[str] = set()
    evidence_pages: set[str] = set()
    for source in evidence:
        if not isinstance(source, dict):
            flags.append("invalid_evidence_record")
            continue
        document_id = str(source.get("document_id", "")).strip()
        page = str(source.get("page", "")).strip()
        support = str(source.get("support", "")).strip()
        if not document_id or not support:
            flags.append("incomplete_evidence_record")
            continue
        evidence_documents.add(document_id)
        if page:
            evidence_pages.add(page)

        linked_chunks = chunks_by_source.get((document_id, page), [])
        if not linked_chunks:
            flags.append("evidence_source_not_found_in_chunks")
        elif not support_matches_chunk(support, linked_chunks):
            flags.append("evidence_support_not_confirmed_in_chunks")

        support_normalized = normalize(support)
        if any(marker in support_normalized for marker in NAVIGATION_MARKERS):
            flags.append("evidence_contains_navigation_or_header_boilerplate")

    if expected_documents and not set(expected_documents).issubset(evidence_documents):
        flags.append("expected_document_missing_from_evidence")
    if expected_pages and not set(expected_pages).issubset(evidence_pages):
        flags.append("expected_page_missing_from_evidence")

    question_tokens = tokens(question)
    evidence_tokens = tokens(" ".join(str(source.get("support", "")) for source in evidence if isinstance(source, dict)))
    if question_tokens and evidence_tokens:
        overlap = len(question_tokens & evidence_tokens) / len(question_tokens)
        if overlap >= 0.55:
            flags.append("question_has_high_lexical_overlap_with_evidence")

    return sorted(set(flags))


def reviewer_actions(flags: list[str]) -> list[str]:
    actions = ["verify_original_pdf_and_page"]
    if any("question" in flag for flag in flags):
        actions.append("rewrite_question_in_natural_user_language")
    if "evidence_contains_navigation_or_header_boilerplate" in flags:
        actions.append("replace_boilerplate_with_substantive_evidence")
    link_flags = {
        "evidence_source_not_found_in_chunks",
        "evidence_support_not_confirmed_in_chunks",
        "expected_document_missing_from_evidence",
        "expected_page_missing_from_evidence",
    }
    if any(flag in link_flags for flag in flags):
        actions.append("repair_document_page_or_evidence_link")
    if "gold_not_human_verified" in flags:
        actions.append("set_gold_verified_only_after_human_review")
    return actions


def audit(dataset: list[dict[str, Any]], chunks: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    chunks_by_source = chunk_lookup(chunks)
    ids = Counter(str(item.get("id", "")).strip() for item in dataset)
    queue: list[dict[str, Any]] = []
    flag_counts: Counter[str] = Counter()
    split_counts: Counter[str] = Counter()
    lockable_counts: Counter[str] = Counter()

    for item in dataset:
        item_id = str(item.get("id", "")).strip()
        flags = quality_flags(item, chunks_by_source)
        if item_id and ids[item_id] > 1:
            flags = sorted(set(flags + ["duplicate_id"]))
        lockable = not flags
        review_record = {
            "id": item_id,
            "split": str(item.get("split", "")),
            "category": str(item.get("category", "")),
            "query_type": str(item.get("query_type", "")),
            "question": str(item.get("question", "")),
            "expected_documents": item.get("expected_documents", []),
            "expected_pages": item.get("expected_pages", []),
            "gold_verified": bool(item.get("gold_verified", False)),
            "review_status": "ready_to_lock" if lockable else "needs_manual_review",
            "quality_flags": flags,
            "reviewer_actions": reviewer_actions(flags),
        }
        queue.append(review_record)
        flag_counts.update(flags)
        split_counts[review_record["split"]] += 1
        lockable_counts[review_record["split"]] += int(lockable)

    report = {
        "dataset_total": len(dataset),
        "chunks_total": len(chunks),
        "records_by_split": dict(sorted(split_counts.items())),
        "ready_to_lock_by_split": dict(sorted(lockable_counts.items())),
        "needs_manual_review": sum(
            record["review_status"] == "needs_manual_review" for record in queue
        ),
        "flag_counts": dict(flag_counts.most_common()),
        "lock_rule": "A record is ready_to_lock only when it has no automated flags. It still requires human PDF/page verification before final TEST locking.",
    }
    return queue, report


def write_jsonl(path: Path, records: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as file:
        for record in records:
            file.write(json.dumps(record, ensure_ascii=False) + "\n")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", type=Path, default=DEFAULT_DATASET)
    parser.add_argument("--chunks", type=Path, default=DEFAULT_CHUNKS)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    parser.add_argument("--review-queue", type=Path, default=DEFAULT_REVIEW_QUEUE)
    args = parser.parse_args()

    dataset = read_jsonl(args.dataset)
    chunks = read_jsonl(args.chunks)
    queue, report = audit(dataset, chunks)

    write_jsonl(args.review_queue, queue)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"Wrote {len(queue)} review records to {args.review_queue}")
    print(f"Wrote audit report to {args.report}")
    print(f"Needs manual review: {report['needs_manual_review']}/{report['dataset_total']}")
    for flag, count in report["flag_counts"].items():
        print(f"{flag},{count}")


if __name__ == "__main__":
    main()
