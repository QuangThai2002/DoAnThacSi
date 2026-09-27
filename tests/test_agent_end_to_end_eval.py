from __future__ import annotations

import sys
import unittest
from pathlib import Path


EVALUATION_DIR = Path(__file__).resolve().parents[1] / "src" / "evaluation"
if str(EVALUATION_DIR) not in sys.path:
    sys.path.insert(0, str(EVALUATION_DIR))

from agent_end_to_end_eval import evaluate  # noqa: E402


class FakeRunner:
    def run(self, question: str) -> dict:
        if question == "outside":
            return {
                "plan": {"intent": "out_of_scope", "tools": (), "period": None},
                "answer": "Câu hỏi này nằm ngoài phạm vi Agent hiện tại.",
                "citations": [],
                "trace": [],
                "agent_latency_seconds": 0.01,
            }
        return {
            "plan": {"intent": "multi", "tools": ("shop_data", "rag", "calculator"), "period": "2026-08"},
            "answer": "Kết quả dùng dữ liệu vận hành mô phỏng. Có nguồn chính sách.",
            "citations": [{"document_id": "SHP_FEE_001", "page": "1"}],
            "trace": [
                {"tool": "shop_data", "status": "ok"},
                {"tool": "rag", "status": "ok"},
                {"tool": "calculator", "status": "ok"},
            ],
            "agent_latency_seconds": 0.02,
        }


class AgentEndToEndEvaluationTests(unittest.TestCase):
    def test_evaluator_measures_contracts(self) -> None:
        dataset = [
            {
                "id": "multi_001",
                "question": "multi",
                "expected_intent": "multi",
                "expected_tools": ["shop_data", "rag", "calculator"],
                "expected_period": "2026-08",
                "gold_verified": True,
                "review_status": "verified",
                "reviewer": "reviewer",
                "review_note": "Đã kiểm tra đủ route và output.",
                "expected_citation_document_ids": ["SHP_FEE_001"],
                "expected_answer_markers": ["dữ liệu vận hành mô phỏng"],
                "confirmed_reference_source": True,
                "split": "test",
            },
            {
                "id": "outside_001",
                "question": "outside",
                "expected_intent": "out_of_scope",
                "expected_tools": [],
                "gold_verified": True,
                "review_status": "verified",
                "reviewer": "reviewer",
                "review_note": "Đã kiểm tra xử lý ngoài phạm vi.",
                "expected_citation_document_ids": [],
                "expected_answer_markers": [],
                "confirmed_reference_source": False,
                "split": "test",
            },
        ]
        rows, summary = evaluate(dataset, runner=FakeRunner(), require_verified=True)

        self.assertEqual(len(rows), 2)
        self.assertEqual(summary["overall_pass_rate"], 1.0)
        self.assertEqual(summary["citation_contract_success"], 1.0)
        self.assertEqual(summary["out_of_scope_refusal_success"], 1.0)

    def test_official_mode_rejects_unverified_rows(self) -> None:
        dataset = [
            {
                "id": "unverified_001",
                "question": "outside",
                "expected_intent": "out_of_scope",
                "expected_tools": [],
                "gold_verified": False,
            }
        ]
        with self.assertRaisesRegex(ValueError, "gold_verified"):
            evaluate(dataset, runner=FakeRunner(), require_verified=True)


if __name__ == "__main__":
    unittest.main()
