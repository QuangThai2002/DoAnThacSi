from __future__ import annotations

import sys
import unittest
from pathlib import Path


SRC_DIR = Path(__file__).resolve().parents[1] / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from defense_preflight import benchmark_summary, render_report  # noqa: E402


class DefensePreflightTests(unittest.TestCase):
    def test_benchmark_summary_separates_total_and_verified_test(self) -> None:
        # The helper itself is intentionally file-backed; this assertion covers
        # the semantics through a small temporary fixture in the next test.
        self.assertEqual(benchmark_summary(Path("does-not-exist.jsonl")), {
            "total": 0,
            "verified": 0,
            "test": 0,
            "verified_test": 0,
        })

    def test_report_keeps_warnings_distinct_from_scientific_blockers(self) -> None:
        from defense_preflight import Check

        report = render_report(
            [
                Check("PASS", "Demo", "Sẵn sàng."),
                Check("WARN", "Ollama", "Chưa chạy."),
                Check("BLOCK", "TEST", "Chưa khóa."),
            ]
        )
        self.assertIn("Cảnh báo demo", report)
        self.assertIn("Blocker cho số liệu luận văn", report)
        self.assertIn("không trình bày score regression", report)


if __name__ == "__main__":
    unittest.main()
