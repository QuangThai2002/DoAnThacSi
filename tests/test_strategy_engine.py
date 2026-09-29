from __future__ import annotations

import unittest
from pathlib import Path
import sys


SRC_DIR = Path(__file__).resolve().parents[1] / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from agent.strategy_engine import action_plan, inventory_risk_analysis, opportunity_radar, simulate_strategy


class StrategyEngineTests(unittest.TestCase):
    def test_radar_covers_all_demo_categories(self) -> None:
        radar = opportunity_radar()
        self.assertEqual(len(radar), 50)
        self.assertEqual([item["rank"] for item in radar], list(range(1, 51)))
        self.assertTrue(all(item["recommendation"] for item in radar))

    def test_simulation_outputs_a_measurable_experiment_and_plan(self) -> None:
        result = simulate_strategy(
            "fresh-fruit", scenario_seed=42, price_change_percent=-5,
            use_bundle=True, ad_budget_change_percent=20, restock_units=30,
        )
        self.assertGreater(int(result["baseline_gmv_vnd"]), 0)
        self.assertGreater(int(result["estimated_gmv_vnd"]), 0)
        self.assertIn("14 ngày", str(result["action"]))
        self.assertLess(int(result["evidence_score"]), 90)
        self.assertIn("Không đủ bằng chứng", str(result["language_policy"]))
        self.assertTrue(result["requires_human_approval"])
        self.assertEqual(len(result["stop_conditions"]), 3)
        plan = action_plan(result)
        self.assertEqual([item["Tuần"] for item in plan], ["Tuần 1", "Tuần 2", "Tuần 3", "Tuần 4"])

    def test_inventory_risk_analysis_is_deterministic_and_has_reorder_guardrails(self) -> None:
        result = inventory_risk_analysis("fresh-fruit", scenario_seed=42, target_stock_months=2.0)
        rows = result["rows"]

        self.assertGreaterEqual(len(rows), 5)
        self.assertLessEqual(len(rows), 12)
        self.assertTrue(any("không nhập thêm" in str(row["status"]).lower() for row in rows))
        self.assertTrue(any(int(row["recommended_order_qty"]) > 0 for row in rows))
        self.assertTrue(all(int(row["capital_in_stock_demo_vnd"]) > 0 for row in rows))
        self.assertTrue(all(str(row["repeat_purchase_signal_demo"]) for row in rows))
        self.assertLess(int(result["evidence_score"]), 90)


if __name__ == "__main__":
    unittest.main()
