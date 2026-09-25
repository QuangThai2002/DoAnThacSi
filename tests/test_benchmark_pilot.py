from __future__ import annotations

import sys
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
EVALUATION_DIR = PROJECT_ROOT / "src" / "evaluation"
if str(EVALUATION_DIR) not in sys.path:
    sys.path.insert(0, str(EVALUATION_DIR))

from audit_gold_benchmark import audit, read_jsonl
from lock_gold_benchmark import validation_errors


class VerifiedPilotTests(unittest.TestCase):
    def test_pilot_passes_automated_quality_and_lock_validation(self) -> None:
        pilot = read_jsonl(EVALUATION_DIR / "gold_pilot_verified.jsonl")
        chunks = read_jsonl(PROJECT_ROOT / "data" / "processed" / "chunks.jsonl")
        _queue, report = audit(pilot, chunks)

        self.assertEqual(report["dataset_total"], 6)
        self.assertEqual(report["needs_manual_review"], 0)
        self.assertEqual(validation_errors(pilot, chunks), [])


if __name__ == "__main__":
    unittest.main()
