from __future__ import annotations

import sys
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
EVALUATION_DIR = PROJECT_ROOT / "src" / "evaluation"
if str(EVALUATION_DIR) not in sys.path:
    sys.path.insert(0, str(EVALUATION_DIR))

from audit_gold_benchmark import audit, read_jsonl  # noqa: E402
from generate_benchmark_candidate_v2 import build_candidate  # noqa: E402


class CandidateBenchmarkV2Tests(unittest.TestCase):
    def test_candidate_has_no_mechanical_flags_except_human_verification(self) -> None:
        chunks = read_jsonl(PROJECT_ROOT / "data" / "processed" / "chunks.jsonl")
        candidate = build_candidate(chunks)
        queue, report = audit(candidate, chunks)

        self.assertEqual(len(candidate), 34)
        self.assertEqual(report["needs_manual_review"], 34)
        all_flags = {flag for item in queue for flag in item["quality_flags"]}
        self.assertEqual(all_flags, {"gold_not_human_verified"})
        self.assertEqual(
            {item["split"] for item in candidate},
            {"dev", "test", "challenge"},
        )


if __name__ == "__main__":
    unittest.main()
