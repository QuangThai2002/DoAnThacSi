from __future__ import annotations

import sys
import unittest
from pathlib import Path


EVALUATION_DIR = Path(__file__).resolve().parents[1] / "src" / "evaluation"
if str(EVALUATION_DIR) not in sys.path:
    sys.path.insert(0, str(EVALUATION_DIR))

from lock_agent_benchmark import validation_errors  # noqa: E402


class LockAgentBenchmarkTests(unittest.TestCase):
    @staticmethod
    def reviewed_rag_record() -> dict:
        return {
            "id": "agent_test_001",
            "question": "Phí cố định là gì?",
            "expected_intent": "policy_rag",
            "expected_tools": ["rag"],
            "split": "test",
            "gold_verified": True,
            "review_status": "verified",
            "reviewer": "independent reviewer",
            "review_note": "Đã kiểm tra tài liệu nguồn và route.",
            "expected_citation_document_ids": ["SHP_FEE_001"],
            "expected_answer_markers": [],
            "confirmed_reference_source": True,
        }

    def test_valid_reviewed_test_record_can_lock(self) -> None:
        errors = validation_errors([self.reviewed_rag_record()], {"SHP_FEE_001"})
        self.assertEqual(errors, [])

    def test_lock_rejects_document_not_in_corpus(self) -> None:
        errors = validation_errors([self.reviewed_rag_record()], {"OTHER_DOC"})
        self.assertTrue(any("absent from current chunks" in error for error in errors))

    def test_lock_rejects_non_test_record(self) -> None:
        record = self.reviewed_rag_record()
        record["split"] = "dev"
        errors = validation_errors([record], {"SHP_FEE_001"})
        self.assertTrue(any("TEST records only" in error for error in errors))


if __name__ == "__main__":
    unittest.main()
