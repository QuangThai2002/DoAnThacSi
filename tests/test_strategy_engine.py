from __future__ import annotations

import unittest
from pathlib import Path
import sys


SRC_DIR = Path(__file__).resolve().parents[1] / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from agent.strategy_engine import action_plan, opportunity_radar, simulate_strategy


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
        plan = action_plan(result)
        self.assertEqual([item["Tuần"] for item in plan], ["Tuần 1", "Tuần 2", "Tuần 3", "Tuần 4"])


if __name__ == "__main__":
    unittest.main()
