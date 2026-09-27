from __future__ import annotations

import sys
import unittest
from pathlib import Path


EVALUATION_DIR = Path(__file__).resolve().parents[1] / "src" / "evaluation"
if str(EVALUATION_DIR) not in sys.path:
    sys.path.insert(0, str(EVALUATION_DIR))

from agent_annotation_store import (  # noqa: E402
    apply_agent_review,
    official_validation_errors,
    validate_official_records,
)


class AgentAnnotationStoreTests(unittest.TestCase):
    @staticmethod
    def policy_item() -> dict:
        return {
            "id": "policy_001",
            "question": "Phí cố định là gì?",
            "expected_intent": "policy_rag",
            "expected_tools": ["rag"],
            "split": "test",
            "gold_verified": False,
        }

    @staticmethod
    def shop_item() -> dict:
        return {
            "id": "shop_001",
            "question": "GMV tháng 8 là bao nhiêu?",
            "expected_intent": "shop_analysis",
            "expected_tools": ["shop_data", "calculator"],
            "split": "dev",
            "gold_verified": False,
        }

    def test_verified_policy_requires_citation_and_source_confirmation(self) -> None:
        with self.assertRaisesRegex(ValueError, "citation document id"):
            apply_agent_review(
                self.policy_item(),
                reviewer="reviewer",
                status="verified",
                question="Phí cố định là gì?",
                expected_intent="policy_rag",
                expected_tools=["rag"],
                expected_period="",
                expected_citation_document_ids=[],
                expected_answer_markers=[],
                confirmed_reference_source=False,
                note="Đã kiểm tra route và nguồn chính sách.",
            )

        reviewed = apply_agent_review(
            self.policy_item(),
            reviewer="reviewer",
            status="verified",
            question="Phí cố định là gì?",
            expected_intent="policy_rag",
            expected_tools=["rag"],
            expected_period="",
            expected_citation_document_ids=["SHP_FEE_001"],
            expected_answer_markers=[],
            confirmed_reference_source=True,
            note="Đã kiểm tra route và nguồn chính sách.",
        )
        self.assertEqual(official_validation_errors(reviewed), [])

    def test_verified_shop_requires_answer_marker(self) -> None:
        with self.assertRaisesRegex(ValueError, "answer marker"):
            apply_agent_review(
                self.shop_item(),
                reviewer="reviewer",
                status="verified",
                question="GMV tháng 8 là bao nhiêu?",
                expected_intent="shop_analysis",
                expected_tools=["shop_data", "calculator"],
                expected_period="2026-08",
                expected_citation_document_ids=[],
                expected_answer_markers=[],
                confirmed_reference_source=False,
                note="Đã kiểm tra dữ liệu mock và phép tính.",
            )

    def test_official_validation_rejects_unreviewed_item(self) -> None:
        with self.assertRaisesRegex(ValueError, "incomplete"):
            validate_official_records([self.policy_item()])


if __name__ == "__main__":
    unittest.main()
