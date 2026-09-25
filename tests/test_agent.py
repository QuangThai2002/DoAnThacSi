from __future__ import annotations

import sys
import unittest
from pathlib import Path


SRC_DIR = Path(__file__).resolve().parents[1] / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from agent.agent_runner import AgentRunner
from agent.calculator_tool import CalculatorTool
from agent.planner import Planner
from agent.shop_data_tool import ShopDataTool


class PlannerTests(unittest.TestCase):
    def test_multi_tool_plan_has_period(self) -> None:
        plan = Planner().plan(
            "Tháng 8 năm 2026 shop tôi có doanh thu bao nhiêu và theo chính sách Shopee phí nào cần đối chiếu?"
        )
        self.assertEqual(plan.period, "2026-08")
        self.assertEqual(plan.intent, "multi_tool_policy_and_shop_analysis")
        self.assertEqual(plan.tools, ("shop_data", "rag", "calculator"))

    def test_out_of_scope_plan_does_not_call_tools(self) -> None:
        plan = Planner().plan("Thời tiết Hà Nội ngày mai thế nào?")
        self.assertEqual(plan.intent, "out_of_scope")
        self.assertEqual(plan.tools, ())


class ShopDataToolTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tool = ShopDataTool()

    def test_august_sales_summary_is_deterministic(self) -> None:
        summary = self.tool.sales_summary("2026-08")
        self.assertEqual(summary["completed_order_count"], 6)
        self.assertEqual(summary["gross_merchandise_value_vnd"], 3_980_000)
        self.assertEqual(summary["estimated_platform_fees_vnd"], 237_800)
        self.assertEqual(summary["net_revenue_after_estimated_fees_vnd"], 3_537_200)

    def test_inventory_alerts_use_available_quantity(self) -> None:
        alerts = self.tool.inventory_alerts()
        self.assertEqual(alerts["alert_count"], 4)
        self.assertEqual(alerts["alerts"][0]["sku"], "SKU-003")


class CalculatorAndRunnerTests(unittest.TestCase):
    def test_rank_costs_returns_largest_item(self) -> None:
        ranking = CalculatorTool().rank_costs({"fee": 100, "discount": 150})
        self.assertEqual(ranking["cost_ranking"][0]["name"], "discount")
        self.assertEqual(ranking["cost_ranking"][0]["share_of_ranked_costs"], 0.6)

    def test_runner_keeps_mock_data_disclaimer(self) -> None:
        result = AgentRunner().run("Tháng 8 năm 2026 shop tôi có doanh thu bao nhiêu?")
        self.assertIn("dữ liệu vận hành mô phỏng", result["answer"])
        self.assertEqual(result["plan"]["tools"], ("shop_data", "calculator"))


if __name__ == "__main__":
    unittest.main()
