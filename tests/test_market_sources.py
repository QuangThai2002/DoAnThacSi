from __future__ import annotations

import unittest
from pathlib import Path
from unittest.mock import Mock, patch
import sys

SRC_DIR = Path(__file__).resolve().parents[1] / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from agent.market_sources import fetch_configured_sources, fetch_youtube_brief


class MarketSourceTests(unittest.TestCase):
    def test_unconfigured_sources_never_make_network_calls(self) -> None:
        with patch("agent.market_sources.requests.get") as get, patch("agent.market_sources.requests.post") as post:
            results = fetch_configured_sources("hoa quả tươi", {})

        self.assertEqual([item["status"] for item in results], ["Chưa kết nối"] * 3)
        get.assert_not_called()
        post.assert_not_called()

    def test_youtube_result_keeps_platform_label_and_source_link(self) -> None:
        response = Mock()
        response.json.return_value = {
            "items": [
                {
                    "id": {"videoId": "abc123"},
                    "snippet": {"title": "Xu hướng hoa quả", "channelTitle": "Kênh thử nghiệm", "publishedAt": "2026-09-28T00:00:00Z"},
                }
            ]
        }
        with patch("agent.market_sources.requests.get", return_value=response) as get:
            result = fetch_youtube_brief("hoa quả tươi", "test-key")

        self.assertEqual(result["platform"], "YouTube")
        self.assertEqual(result["status"], "Đã kết nối")
        self.assertEqual(result["items"][0]["url"], "https://www.youtube.com/watch?v=abc123")
        self.assertEqual(get.call_args.kwargs["params"]["regionCode"], "VN")


if __name__ == "__main__":
    unittest.main()
