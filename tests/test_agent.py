from __future__ import annotations

import sys
import unittest
from io import BytesIO
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

    def test_cancelled_order_rule_does_not_request_private_shop_data(self) -> None:
        plan = Planner().plan("Nếu đơn bị hủy thì có được tính doanh thu không?")
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

    def test_excel_with_vietnamese_no_accent_headers_is_accepted(self) -> None:
        import pandas as pd

        header_maps = {
            "orders.csv": {
                "order_id": "ma_don_hang", "order_date": "ngay_dat_hang", "status": "trang_thai",
                "sku": "ma_san_pham", "quantity": "so_luong", "gross_merchandise_value_vnd": "gia_tri_hang_hoa_vnd",
                "seller_discount_vnd": "giam_gia_nguoi_ban_vnd", "platform_discount_vnd": "tro_gia_san_vnd",
                "estimated_transaction_fee_vnd": "phi_giao_dich_uoc_tinh_vnd", "estimated_service_fee_vnd": "phi_dich_vu_uoc_tinh_vnd",
            },
            "products.csv": {
                "sku": "ma_san_pham", "product_name": "ten_san_pham", "category": "nganh_hang",
                "cost_per_unit_vnd": "gia_von_don_vi_vnd", "list_price_vnd": "gia_niem_yet_vnd",
            },
            "inventory.csv": {
                "sku": "ma_san_pham", "on_hand": "ton_thuc_te", "reserved": "da_giu_cho",
                "reorder_point": "nguong_nhap_them", "last_updated": "ngay_cap_nhat",
            },
        }
        files: dict[str, bytes] = {}
        for name, rename_map in header_maps.items():
            frame = pd.read_csv(SRC_DIR.parent / "data" / "shop_mock" / name).rename(columns=rename_map)
            output = BytesIO()
            frame.to_excel(output, index=False, engine="openpyxl")
            files[name] = output.getvalue()

        tool = ShopDataTool.from_uploaded_files(files)

        self.assertEqual(tool.data_scope, "uploaded_csv")
        self.assertEqual(tool.sales_summary("2026-08")["completed_order_count"], 6)

    def test_exported_multisheet_workbook_can_be_loaded_again(self) -> None:
        import pandas as pd

        output = BytesIO()
        sheet_names = {
            "orders.csv": "Don hang",
            "products.csv": "San pham",
            "inventory.csv": "Ton kho",
        }
        with pd.ExcelWriter(output, engine="openpyxl") as writer:
            for file_name, sheet_name in sheet_names.items():
                pd.read_csv(SRC_DIR.parent / "data" / "shop_mock" / file_name).to_excel(
                    writer, sheet_name=sheet_name, index=False
                )

        tool = ShopDataTool.from_uploaded_workbook(output.getvalue())

        self.assertEqual(tool.data_scope, "uploaded_csv")
        self.assertEqual(tool.sales_summary("2026-08")["completed_order_count"], 6)

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

    def test_sku_explanation_includes_why_and_a_concrete_variant_example(self) -> None:
        class GuideRAG:
            def search(self, _question: str) -> dict:
                return {"evidence": [{"document_id": "ESLABONG_GUIDE_001", "title": "Sổ tay vận hành Eslabong", "page": "", "excerpt": "SKU là mã định danh."}]}

        result = AgentRunner(rag_tool=GuideRAG()).run("SKU là gì? Vì sao mỗi biến thể cần SKU riêng?")
        self.assertIn("Vì sao mỗi biến thể cần SKU riêng", result["answer"])
        self.assertIn("AO-THUN-DEN-M", result["answer"])

    def test_sku_follow_up_example_stays_on_the_previous_topic(self) -> None:
        class GuideRAG:
            def search(self, _question: str) -> dict:
                return {"evidence": [{"document_id": "ESLABONG_GUIDE_001", "title": "Sổ tay vận hành Eslabong", "page": "", "excerpt": "SKU là mã định danh."}]}

        result = AgentRunner(rag_tool=GuideRAG()).run(
            "SKU là gì? Vì sao mỗi biến thể cần SKU riêng?\n\nNgười dùng hỏi tiếp: ví dụ"
        )
        self.assertIn("Ví dụ SKU", result["answer"])
        self.assertIn("AO-THUN-DEN-L", result["answer"])

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

    def test_net_revenue_question_answers_before_showing_sources(self) -> None:
        class FeeRAG:
            def search(self, _question: str) -> dict:
                return {
                    "evidence": [
                        {
                            "document_id": "fee-1",
                            "title": "Biểu phí",
                            "page": "1",
                            "excerpt": "Các khoản phí được cấn trừ theo chính sách.",
                        }
                    ]
                }

        result = AgentRunner(rag_tool=FeeRAG()).run("Doanh thu sau phí được tính như thế nào?")
        self.assertIn("Doanh thu sau phí ước tính", result["answer"])
        self.assertIn("GMV − giảm giá người bán", result["answer"])
        self.assertNotIn("Tôi đã tìm được tài liệu", result["answer"])

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

    def test_runner_answers_product_gmv_question_with_a_product_not_generic_sales(self) -> None:
        result = AgentRunner().run("Sản phẩm nào đem về GMV cao nhất trong kỳ?")
        self.assertIn("Cáp sạc USB-C 1m", result["answer"])
        self.assertIn("1,760,000 VND", result["answer"])
        self.assertNotIn("Trong kỳ toàn bộ kỳ có trong dữ liệu", result["answer"])
        self.assertNotIn("Ví dụ bán 2 sản phẩm", result["answer"])

    def test_runner_answers_lowest_product_contribution_with_product_level_numbers(self) -> None:
        result = AgentRunner().run("Sản phẩm nào có lãi góp thấp?")

        self.assertIn("lãi góp thấp nhất", result["answer"])
        self.assertIn("mỗi sản phẩm", result["answer"])
        self.assertNotIn("Sau giá vốn và các phí sàn đã ghi nhận", result["answer"])

    def test_runner_explains_cancelled_orders_without_a_sales_summary(self) -> None:
        result = AgentRunner().run("Nếu đơn bị hủy thì có được tính doanh thu không?")
        self.assertIn("Đơn bị hủy không được cộng", result["answer"])
        self.assertNotIn("Trong kỳ", result["answer"])

    def test_runner_compares_the_latest_two_recorded_months(self) -> None:
        result = AgentRunner().run("So sánh doanh thu tháng này với tháng trước.")
        self.assertIn("So với **2026-07**", result["answer"])
        self.assertIn("tháng **2026-08**", result["answer"])
        self.assertIn("tăng 220.97%", result["answer"])

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

    def test_action_questions_share_one_evidence_first_routing_path(self) -> None:
        price = AgentRunner().run("Tôi có nên giảm giá toàn bộ sản phẩm không?")
        self.assertIn("Chưa có cơ sở để giảm giá toàn bộ", price["answer"])
        self.assertIn("1–2 SKU", price["answer"])

        restock = AgentRunner().run("Sản phẩm bán tốt có chắc nên nhập nhiều hơn không?")
        self.assertIn("Không nên nhập nhiều chỉ vì một sản phẩm bán tốt", restock["answer"])
        self.assertIn("Đơn nhập hàng", restock["answer"])

        ads = AgentRunner().run("Tôi có nên tăng ngân sách quảng cáo không?")
        self.assertIn("ROAS hiện ghi nhận", ads["answer"])
        self.assertIn("chưa đủ để kết luận nên tăng ngân sách", ads["answer"])

    def test_concept_questions_do_not_fall_into_shop_metrics(self) -> None:
        threshold = AgentRunner().run("Ngưỡng nhập thêm là gì?")
        self.assertIn("mốc tồn khả dụng", threshold["answer"])
        self.assertNotIn("cảnh báo tồn kho", threshold["answer"])

        costs = AgentRunner().run("Chi phí quảng cáo có phải toàn bộ chi phí của shop không?")
        self.assertIn("Không. Chi phí quảng cáo chỉ là một khoản", costs["answer"])
        self.assertNotIn("GMV", costs["answer"])

    def test_slow_inventory_answer_exposes_age_data_limit_and_next_upload(self) -> None:
        result = AgentRunner().run("Hàng nào tồn lâu mà ít bán?")
        self.assertIn("Giá đỡ điện thoại", result["answer"])
        self.assertIn("Biến động kho", result["answer"])

    def test_operational_question_bank_uses_topic_routing_and_bounded_advice(self) -> None:
        """Regression coverage for the shared question-bank failure patterns."""
        checks = {
            "Mặt hàng này có được bán trên Shopee không?": "Chưa thể kết luận",
            "Nguồn hàng nào có tỷ lệ lỗi cao hơn?": "tỷ lệ lỗi cao nhất",
            "Làm gì để giảm đánh giá xấu?": "không bảo đảm",
            "Lãi sau chi phí vận hành tháng 8 là bao nhiêu?": "612,200 VND",
            "Khoản vận hành nào đang lớn nhất?": "Nhân sự",
            "Tại sao doanh thu tăng mà tôi vẫn thiếu tiền nhập hàng?": "thời điểm thu tiền",
            "Khoản tiền chi nào lớn nhất tháng này?": "Nhập hàng",
            "Có dấu hiệu thất thoát hàng không?": "Chưa thể kết luận có thất thoát",
            "Tỷ lệ lỗi lô hàng tháng 8 là bao nhiêu?": "1.61%",
            "Tôi có nên phản hồi nhà cung cấp không?": "Nên phản hồi nhà cung cấp",
            "Làm sao tăng khách quay lại?": "không có biện pháp nào bảo đảm",
            "Nếu lượt xem cao nhưng ít thêm giỏ thì nên kiểm tra gì?": "mỗi lần chỉ đổi một yếu tố",
            "Nếu nhiều người thêm giỏ nhưng ít đặt mua thì sao?": "giá cuối",
            "Tôi nên ưu tiên sản phẩm nào trong 30 ngày tới?": "ứng viên ưu tiên",
            "Tôi có nên tạo combo không?": "quy mô nhỏ",
            "Tôi đang có nguy cơ lỗ ở đâu?": "bốn nhóm",
            "Tôi cần làm gì trước trong tuần này?": "tối đa ba việc",
            "AI có cam kết giảm giá sẽ giúp tôi bán tốt hơn không?": "Không. Eslabong không cam kết",
            "AI này đã kết nối trực tiếp với Shopee chưa?": "Chưa. Eslabong hiện chỉ dùng",
            "Nếu tôi không tải bảng quảng cáo thì AI có tự đoán ROAS không?": "không tự đoán ROAS",
        }
        runner = AgentRunner()
        for question, expected_text in checks.items():
            with self.subTest(question=question):
                result = runner.run(question)
                self.assertIn(expected_text, result["answer"])
                self.assertNotIn("Tôi chưa có đủ nội dung đã kiểm chứng", result["answer"])


if __name__ == "__main__":
    unittest.main()
