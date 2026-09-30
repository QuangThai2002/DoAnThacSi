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

    def test_metric_definition_does_not_request_private_shop_data(self) -> None:
        plan = Planner().plan("GMV là gì? GMV có phải lợi nhuận không?")
        self.assertEqual(plan.tools, ("rag",))
        self.assertFalse(plan.needs_private_shop_data)


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

    def test_extended_operational_tables_support_profit_returns_reviews_and_procurement(self) -> None:
        summary = self.tool.profitability_summary("2026-08")
        self.assertEqual(summary["estimated_contribution_vnd"], 1_452_200)
        self.assertEqual(self.tool.returns_summary("2026-08")["return_request_count"], 3)
        self.assertEqual(self.tool.review_summary("2026-08")["average_rating"], 3.6)
        self.assertEqual(self.tool.procurement_summary("2026-08")["open_purchase_order_count"], 2)

    def test_further_operational_tables_support_overhead_stock_and_quality(self) -> None:
        self.assertEqual(
            self.tool.operating_cost_summary("2026-08")["total_operating_cost_vnd"], 840_000
        )
        movement = self.tool.inventory_movement_summary("2026-08")
        self.assertEqual(movement["damaged_unit_count"], 1)
        quality = self.tool.quality_summary("2026-08")
        self.assertEqual(quality["inspected_unit_count"], 62)
        self.assertEqual(quality["defective_unit_count"], 1)
        self.assertEqual(quality["defect_rate_percent"], 1.61)

    def test_business_health_tables_support_cash_supplier_customer_and_funnel(self) -> None:
        cash = self.tool.cash_flow_summary("2026-08")
        self.assertEqual(cash["net_cash_movement_vnd"], 420_000)
        self.assertEqual(
            self.tool.supplier_performance_summary("2026-08")["best_supplier"]["supplier_name"],
            "Nguồn hàng Điện tử A",
        )
        self.assertEqual(self.tool.customer_retention_summary("2026-08")["repeat_order_rate_percent"], 25.0)
        self.assertEqual(self.tool.product_funnel_summary("2026-08")["weak_product"]["sku"], "SKU-003")


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

    def test_gmv_definition_does_not_need_shop_numbers(self) -> None:
        class GuideRAG:
            def search(self, _question: str) -> dict:
                return {
                    "evidence": [
                        {
                            "document_id": "ESLABONG_GUIDE_001",
                            "title": "Sổ tay vận hành Eslabong",
                            "page": "",
                            "excerpt": "GMV là tổng giá trị hàng hóa.",
                        }
                    ]
                }

        result = AgentRunner(rag_tool=GuideRAG()).run("GMV là gì? GMV có phải lợi nhuận không?")
        self.assertIn("GMV là tổng giá trị hàng hóa", result["answer"])
        self.assertIn("không phải lợi nhuận", result["answer"])

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

    def test_runner_uses_review_data_for_a_shop_question(self) -> None:
        result = AgentRunner().run("Đánh giá khách hàng của shop tôi tháng 8 năm 2026 thế nào?")
        self.assertIn("đánh giá, điểm trung bình 3.60/5", result["answer"])
        self.assertIn("2 đánh giá từ 3 sao trở xuống", result["answer"])

    def test_runner_explains_recorded_operating_costs_without_claiming_net_profit(self) -> None:
        result = AgentRunner().run("Chi phí vận hành tháng 8 năm 2026 của shop tôi là bao nhiêu?")
        self.assertIn("Chi phí vận hành đã ghi nhận là 840,000 VND", result["answer"])
        self.assertIn("chưa tự suy ra thuế", result["answer"])

    def test_runner_answers_cash_flow_with_a_clear_accounting_limit(self) -> None:
        result = AgentRunner().run("Dòng tiền tháng 8 năm 2026 của shop tôi thế nào?")
        self.assertIn("dòng tiền tăng ròng 420,000 VND", result["answer"])
        self.assertIn("không thay thế sổ sách kế toán", result["answer"])

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
