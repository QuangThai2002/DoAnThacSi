from __future__ import annotations

import unittest
from pathlib import Path
import sys

SRC_DIR = Path(__file__).resolve().parents[1] / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from agent.market_intelligence import (
    MARKET_REFERENCE_COUNT,
    market_categories,
    price_comparison,
    reference_listings,
    source_status,
    trend_brief,
)


class MarketIntelligenceTests(unittest.TestCase):
    def test_market_demo_covers_the_same_fifty_shop_categories(self) -> None:
        self.assertEqual(len(market_categories()), 50)
        self.assertEqual(len({str(item["id"]) for item in market_categories()}), 50)

    def test_reference_price_band_is_deterministic_and_ordered(self) -> None:
        self.assertEqual(reference_listings("fresh-fruit"), reference_listings("fresh-fruit"))
        summary = price_comparison("fresh-fruit", own_prices=[240_000, 260_000])
        self.assertEqual(summary["reference_count"], MARKET_REFERENCE_COUNT)
        self.assertLess(summary["lower_price_vnd"], summary["typical_price_vnd"])
        self.assertLess(summary["typical_price_vnd"], summary["upper_price_vnd"])
        self.assertEqual(summary["own_price_vnd"], 250_000)

    def test_market_trends_and_connector_status_are_explicitly_not_live(self) -> None:
        trends = trend_brief("fresh-fruit")
        self.assertEqual(len(trends), 3)
        self.assertTrue(all("mô phỏng" in item["signal"].lower() or "mô phỏng" in item["detail"].lower() for item in trends))
        statuses = source_status()
        self.assertEqual(statuses[0]["status"], "Đang dùng")
        self.assertTrue(any(row["status"] == "Chưa kết nối" for row in statuses))


if __name__ == "__main__":
    unittest.main()
