from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path


EVALUATION_DIR = Path(__file__).resolve().parents[1] / "src" / "evaluation"
if str(EVALUATION_DIR) not in sys.path:
    sys.path.insert(0, str(EVALUATION_DIR))

from annotation_store import (  # noqa: E402
    apply_review,
    append_review_event,
    atomic_write_jsonl,
    read_jsonl,
    replace_record,
)


class AnnotationStoreTests(unittest.TestCase):
    def setUp(self) -> None:
        self.item = {
            "id": "fee_001",
            "question": "Phí nào được áp dụng?",
            "reference_answer": "Một đáp án tham chiếu.",
            "evidence": [{"document_id": "SHP_FEE_001", "page": "1", "support": "Nội dung gốc đủ dài."}],
            "expected_documents": ["SHP_FEE_001"],
            "expected_pages": ["1"],
            "gold_verified": False,
        }

    def test_verified_review_requires_source_confirmation(self) -> None:
        with self.assertRaisesRegex(ValueError, "requires confirmation"):
            apply_review(
                self.item,
                reviewer="Reviewer A",
                status="verified",
                confirmed_original_pdf_page=False,
                question=self.item["question"],
                reference_answer=self.item["reference_answer"],
                evidence=self.item["evidence"],
                expected_documents=self.item["expected_documents"],
                expected_pages=self.item["expected_pages"],
                note="Đã đọc đầy đủ tài liệu nguồn.",
            )

    def test_review_is_written_atomically_and_journaled(self) -> None:
        reviewed = apply_review(
            self.item,
            reviewer="Reviewer A",
            status="verified",
            confirmed_original_pdf_page=True,
            question=self.item["question"],
            reference_answer=self.item["reference_answer"],
            evidence=self.item["evidence"],
            expected_documents=self.item["expected_documents"],
            expected_pages=self.item["expected_pages"],
            note="Đã đọc và đối chiếu trang nguồn gốc.",
        )
        self.assertTrue(reviewed["gold_verified"])
        self.assertEqual(reviewed["review_status"], "verified")

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            reviewed_path = root / "reviewed.jsonl"
            journal_path = root / "journal.jsonl"
            records = replace_record([self.item], reviewed)
            atomic_write_jsonl(reviewed_path, records)
            append_review_event(journal_path, before=self.item, after=reviewed)

            self.assertEqual(read_jsonl(reviewed_path)[0]["id"], "fee_001")
            event = json.loads(journal_path.read_text(encoding="utf-8").strip())
            self.assertEqual(event["record_id"], "fee_001")
            self.assertEqual(event["review_status"], "verified")


if __name__ == "__main__":
    unittest.main()
