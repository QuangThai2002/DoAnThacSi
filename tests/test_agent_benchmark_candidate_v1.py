from __future__ import annotations

import sys
import unittest
from collections import Counter
from pathlib import Path


EVALUATION_DIR = Path(__file__).resolve().parents[1] / "src" / "evaluation"
if str(EVALUATION_DIR) not in sys.path:
    sys.path.insert(0, str(EVALUATION_DIR))

from generate_agent_benchmark_candidate_v1 import build_candidate, read_jsonl  # noqa: E402


class AgentBenchmarkCandidateTests(unittest.TestCase):
    def test_candidate_is_stratified_and_explicitly_unverified(self) -> None:
        seed = read_jsonl(EVALUATION_DIR / "agent_eval_dataset.jsonl")
        candidate = build_candidate(seed)

        self.assertEqual(len(candidate), 32)
        self.assertEqual(Counter(item["split"] for item in candidate), {"dev": 16, "test": 10, "challenge": 6})
        self.assertTrue(all(not item["gold_verified"] for item in candidate))
        self.assertTrue(all(item["review_status"] == "not_reviewed" for item in candidate))
        self.assertTrue(all("review_requirements" in item for item in candidate))

    def test_rag_and_shop_review_requirements_are_visible(self) -> None:
        candidate = build_candidate(read_jsonl(EVALUATION_DIR / "agent_eval_dataset.jsonl"))
        policy = next(item for item in candidate if item["id"] == "agent_001")
        shop = next(item for item in candidate if item["id"] == "agent_006")

        self.assertTrue(policy["review_requirements"]["citation_document_ids_required"])
        self.assertTrue(policy["review_requirements"]["reference_source_confirmation_required"])
        self.assertTrue(shop["review_requirements"]["answer_markers_required"])


if __name__ == "__main__":
    unittest.main()
