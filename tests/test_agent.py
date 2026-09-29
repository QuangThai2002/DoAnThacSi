from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest.mock import patch


SRC_DIR = Path(__file__).resolve().parents[1] / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from agent.agent_runner import AgentRunner
from agent.calculator_tool import CalculatorTool
from agent.planner import Planner
from agent.rag_tool import RAGTool
from agent.shop_data_tool import ShopDataTool, ShopDataValidationError


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

    def test_cost_question_routes_to_shop_data_and_calculator(self) -> None:
        plan = Planner().plan("Khoản chi phí nào ảnh hưởng nhiều nhất trong tháng 8 năm 2026?")
        self.assertEqual(plan.period, "2026-08")
        self.assertEqual(plan.tools, ("shop_data", "calculator"))


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

    def test_uploaded_csv_data_is_used_without_falling_back_to_mock_data(self) -> None:
        upload_files = {
            name: (SRC_DIR.parent / "data" / "shop_mock" / name).read_bytes()
            for name in ("orders.csv", "products.csv", "inventory.csv", "ads.csv")
        }

        uploaded_tool = ShopDataTool.from_uploaded_csvs(upload_files)
        summary = uploaded_tool.sales_summary("2026-08")

        self.assertEqual(uploaded_tool.data_scope, "uploaded_csv")
        self.assertEqual(summary["data_scope"], "uploaded_csv")
        self.assertEqual(summary["completed_order_count"], 6)
        self.assertEqual(uploaded_tool.advertising_summary("2026-08")["campaign_count"], 3)

    def test_invalid_uploaded_csv_schema_is_rejected(self) -> None:
        with self.assertRaises(ShopDataValidationError):
            ShopDataTool.from_uploaded_csvs(
                {
                    "orders.csv": b"order_id\nORD-001\n",
                    "products.csv": b"sku,product_name,category,cost_per_unit_vnd,list_price_vnd\nSKU-1,A,B,1,2\n",
                    "inventory.csv": b"sku,on_hand,reserved,reorder_point,last_updated\nSKU-1,1,0,1,2026-08-01\n",
                }
            )

    def test_uploaded_ads_accept_month_year_export_format(self) -> None:
        upload_files = {
            name: (SRC_DIR.parent / "data" / "shop_mock" / name).read_bytes()
            for name in ("orders.csv", "products.csv", "inventory.csv", "ads.csv")
        }
        upload_files["ads.csv"] = upload_files["ads.csv"].replace(
            b"2026-08", b"8/2026"
        )

        summary = ShopDataTool.from_uploaded_csvs(upload_files).advertising_summary("2026-08")

        self.assertEqual(summary["campaign_count"], 3)
        self.assertEqual(summary["ad_spend_vnd"], 360_000)


class CalculatorAndRunnerTests(unittest.TestCase):
    def test_common_policy_question_uses_the_cached_fast_retrieval_path(self) -> None:
        result = RAGTool().search("Phí cố định của Shopee áp dụng theo nguyên tắc nào?")

        self.assertEqual(result["retrieval_mode"], "bm25_fast_path")
        self.assertGreaterEqual(len(result["evidence"]), 1)

    def test_missing_vector_db_falls_back_to_tracked_text_search(self) -> None:
        missing_vector_db = SRC_DIR.parent / "missing-vector-db-for-test"
        with patch("agent.rag_tool.retrieval.VECTOR_DB_DIR", missing_vector_db):
            result = RAGTool().search("Shopee Open Platform cần access token thế nào?")

        self.assertEqual(result["retrieval_mode"], "bm25_without_vector_db")
        self.assertGreaterEqual(len(result["evidence"]), 1)

    def test_operations_guide_answers_sku_without_claiming_shopee_policy(self) -> None:
        missing_vector_db = SRC_DIR.parent / "missing-vector-db-for-test"
        with patch("agent.rag_tool.retrieval.VECTOR_DB_DIR", missing_vector_db):
            result = RAGTool().search("SKU là gì và dùng để làm gì?")

        self.assertEqual(result["retrieval_mode"], "bm25_without_vector_db")
        self.assertEqual(result["evidence"][0]["document_id"], "ESLABONG_GUIDE_001")

    def test_sku_definition_is_short_and_cautious(self) -> None:
        class GuideRAG:
            def search(self, _question: str) -> dict:
                return {"evidence": [{"document_id": "ESLABONG_GUIDE_001", "title": "Sổ tay vận hành Eslabong", "page": "", "excerpt": "SKU là mã định danh."}]}

        result = AgentRunner(rag_tool=GuideRAG()).run("SKU là gì?")
        self.assertIn("SKU là mã riêng", result["answer"])
        self.assertNotIn("chính sách Shopee", result["answer"])

    def test_contract_guidance_does_not_present_itself_as_legal_advice(self) -> None:
        class LegalRAG:
            def search(self, _question: str) -> dict:
                return {"evidence": [{"document_id": "LAW_TRANSACTION_001", "title": "Luật Giao dịch điện tử 2023", "page": "", "excerpt": "Giao dịch điện tử."}]}

        result = AgentRunner(rag_tool=LegalRAG()).run("Hợp đồng với nhà cung cấp cần có gì?")
        self.assertIn("chuyên gia pháp lý", result["answer"])
        self.assertNotIn("chắc chắn", result["answer"])

    def test_rank_costs_returns_largest_item(self) -> None:
        ranking = CalculatorTool().rank_costs({"fee": 100, "discount": 150})
        self.assertEqual(ranking["cost_ranking"][0]["name"], "discount")
        self.assertEqual(ranking["cost_ranking"][0]["share_of_ranked_costs"], 0.6)

    def test_runner_marks_mock_data_source(self) -> None:
        result = AgentRunner().run("Tháng 8 năm 2026 shop tôi có doanh thu bao nhiêu?")
        self.assertEqual(result["data_source"], "mock_shop_data")
        self.assertEqual(result["plan"]["tools"], ("shop_data", "calculator"))

    def test_runner_labels_uploaded_csv_data(self) -> None:
        upload_files = {
            name: (SRC_DIR.parent / "data" / "shop_mock" / name).read_bytes()
            for name in ("orders.csv", "products.csv", "inventory.csv")
        }
        runner = AgentRunner(
            shop_data_tool=ShopDataTool.from_uploaded_csvs(upload_files)
        )

        result = runner.run("Tháng 8 năm 2026 shop tôi có doanh thu bao nhiêu?")

        self.assertEqual(result["data_source"], "uploaded_csv")
        self.assertIn("uploaded in the current session", result["limitations"][0])

    def test_runner_calculates_largest_cost_from_shop_data(self) -> None:
        result = AgentRunner().run(
            "Khoản chi phí nào ảnh hưởng nhiều nhất trong tháng 8 năm 2026?"
        )

        self.assertEqual(result["plan"]["tools"], ("shop_data", "calculator"))
        self.assertIn("seller discount (205,000 VND, 46.3%)", result["answer"])

    def test_policy_answer_is_direct_and_does_not_claim_csv_use(self) -> None:
        class FixedFeeRAG:
            def search(self, _question: str) -> dict:
                return {
                    "evidence": [
                        {
                            "document_id": "fee-1",
                            "title": "Biểu phí cố định",
                            "page": "7",
                            "excerpt": "Phí Cố Định được cấn trừ trên từng đơn hàng.",
                        }
                    ]
                }

        result = AgentRunner(rag_tool=FixedFeeRAG()).run(
            "Phí cố định của Shopee áp dụng theo nguyên tắc nào?"
        )

        self.assertIn("Phí cố định được tính bằng", result["answer"])
        self.assertNotIn("dữ liệu CSV", result["answer"])


if __name__ == "__main__":
    unittest.main()
