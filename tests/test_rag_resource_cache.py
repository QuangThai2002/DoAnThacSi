from __future__ import annotations

import sys
import unittest
from pathlib import Path


SRC_DIR = Path(__file__).resolve().parents[1] / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

import hybrid_search_shopee_v2 as retrieval  # noqa: E402


class ResourceCacheTests(unittest.TestCase):
    def test_retrieval_resources_are_cached_per_process(self) -> None:
        """RAG UI and Agent RAG Tool must be able to reuse one local model/index."""
        self.assertTrue(hasattr(retrieval.load_resources, "cache_info"))
        self.assertEqual(retrieval.load_resources.cache_info().maxsize, 1)


if __name__ == "__main__":
    unittest.main()
