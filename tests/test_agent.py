from __future__ import annotations

import sys
import unittest
from datetime import date
from io import BytesIO
from pathlib import Path
from unittest.mock import patch


SRC_DIR = Path(__file__).resolve().parents[1] / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from agent.agent_runner import AgentRunner
from agent.calculator_tool import CalculatorTool
from agent.planner import Planner, normalize
from agent.rag_tool import RAGTool
from agent.shop_data_library import build_demo_rows
from agent.shop_data_tool import (
    OPTIONAL_UPLOAD_FILES,
    REQUIRED_UPLOAD_COLUMNS,
    WORKBOOK_SHEET_FILE_NAMES,
    ShopDataTool,
    ShopDataValidationError,
)


class PlannerTests(unittest.TestCase):
    def test_normalize_keeps_question_words_and_repairs_narrow_operational_typos(self) -> None:
        self.assertEqual(normalize("Lô hàng nào tồn lâu nhất?"), "lo hang nao ton lau nhat")
        self.assertIn("quang cao", normalize("SKU nào có ROAS quagn cáo tốt nhất?"))
        self.assertIn("xem nhieu", normalize("Sản phẩm xem nhieuu nhưng thêm giỏ thấp?"))
        self.assertIn("chi phi van hanh", normalize("Khoản chhi vận hnah lớn nhất?"))

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

    def test_basic_greeting_uses_a_no_tool_casual_plan(self) -> None:
        plan = Planner().plan("Xin chào")
        self.assertEqual(plan.intent, "casual")
        self.assertEqual(plan.tools, ())
        self.assertFalse(plan.needs_private_shop_data)

    def test_cost_question_routes_to_shop_data_and_calculator(self) -> None:
        plan = Planner().plan("Khoản chi phí nào ảnh hưởng nhiều nhất trong tháng 8 năm 2026?")
        self.assertEqual(plan.period, "2026-08")
        self.assertEqual(plan.tools, ("shop_data", "calculator"))

    def test_metric_definition_does_not_request_private_shop_data(self) -> None:
        plan = Planner().plan("GMV là gì? GMV có phải lợi nhuận không?")
        self.assertEqual(plan.tools, ("rag",))
        self.assertFalse(plan.needs_private_shop_data)
        self.assertEqual(plan.data_requirement, "no_shop_data_required")

    def test_shop_metric_is_classified_as_requiring_shop_data(self) -> None:
        plan = Planner().plan("Shop có bao nhiêu đơn giao trễ?")
        self.assertTrue(plan.needs_private_shop_data)
        self.assertEqual(plan.data_requirement, "shop_data_required")

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

    def test_demo_co_purchase_table_produces_a_stock_checked_bundle_candidate(self) -> None:
        demo_tool = ShopDataTool(uploaded_rows=build_demo_rows(seed=7))

        bundle = demo_tool.co_purchase_summary("2026-08")["best_pair"]

        self.assertIsNotNone(bundle)
        self.assertNotEqual(bundle["sku"], bundle["paired_sku"])
        self.assertGreater(bundle["joint_order_count"], 0)
        self.assertIsNotNone(bundle["available_units"])
        self.assertIsNotNone(bundle["paired_available_units"])
        self.assertLess(bundle["trial_price_vnd"], bundle["combined_list_price_vnd"])
        self.assertGreater(bundle["trial_price_vnd"], bundle["combined_cost_vnd"])

    def test_new_price_ads_and_inventory_age_tables_support_sku_level_analysis(self) -> None:
        tool = ShopDataTool(uploaded_rows=build_demo_rows(seed=20261001))

        prices = tool.price_promotion_summary("2026-08")
        ads = tool.ads_sku_daily_summary("2026-08")
        batches = tool.inventory_batch_age_summary()

        self.assertGreater(prices["product_count"], 0)
        self.assertIsNotNone(prices["largest_discount_product"])
        self.assertGreater(ads["product_count"], 0)
        self.assertIsNotNone(ads["top_roas_product"])
        self.assertGreater(batches["batch_count"], 0)
        self.assertIsNotNone(batches["oldest_batch"])

    def test_new_search_shipping_settlement_and_competitor_tables_are_usable(self) -> None:
        tool = ShopDataTool(uploaded_rows=build_demo_rows(seed=20261001))

        self.assertIsNotNone(tool.search_performance_summary("2026-08")["top_term"])
        self.assertGreater(tool.shipping_performance_summary("2026-08")["order_count"], 0)
        self.assertGreater(tool.settlement_summary("2026-08")["settlement_count"], 0)
        self.assertIsNotNone(tool.competitor_catalog_summary("2026-08")["leading_reference"])

    def test_complete_demo_workbook_reimports_every_test_table(self) -> None:
        """The published test workbook must retain data, not just sheet tabs."""
        import pandas as pd

        rows = build_demo_rows(["phone-accessories", "appliance"], seed=20260930)
        self.assertEqual(set(rows), set(REQUIRED_UPLOAD_COLUMNS))
        self.assertTrue(all(rows[name] for name in REQUIRED_UPLOAD_COLUMNS))
        sheet_names = {file_name: sheet_name for sheet_name, file_name in WORKBOOK_SHEET_FILE_NAMES.items()}
        output = BytesIO()
        with pd.ExcelWriter(output, engine="openpyxl") as writer:
            for name, table_rows in rows.items():
                pd.DataFrame(table_rows).to_excel(writer, sheet_name=sheet_names[name], index=False)

        imported = ShopDataTool.from_uploaded_workbook(output.getvalue())

        self.assertEqual(set(imported.uploaded_rows or {}), set(REQUIRED_UPLOAD_COLUMNS))
        self.assertIsNotNone(imported.search_performance_summary("2026-08")["top_term"])
        self.assertGreater(imported.shipping_performance_summary("2026-08")["order_count"], 0)
        self.assertGreater(imported.settlement_summary("2026-08")["settlement_count"], 0)
        self.assertIsNotNone(imported.competitor_catalog_summary("2026-08")["leading_reference"])
        self.assertIn(
            "lượng bán ước tính cao nhất",
            AgentRunner(shop_data_tool=imported).run("Đối thủ nào bán ước tính cao nhất?")["answer"],
        )

    def test_header_only_optional_workbook_sheets_are_ignored(self) -> None:
        """A current-data export can include blank optional templates safely."""
        import pandas as pd

        rows = build_demo_rows(["phone-accessories"], seed=20260930)
        sheet_names = {file_name: sheet_name for sheet_name, file_name in WORKBOOK_SHEET_FILE_NAMES.items()}
        output = BytesIO()
        with pd.ExcelWriter(output, engine="openpyxl") as writer:
            for name in REQUIRED_UPLOAD_COLUMNS:
                table_rows = rows[name] if name not in OPTIONAL_UPLOAD_FILES else []
                frame = pd.DataFrame(table_rows, columns=list(REQUIRED_UPLOAD_COLUMNS[name]))
                frame.to_excel(writer, sheet_name=sheet_names[name], index=False)

        imported = ShopDataTool.from_uploaded_workbook(output.getvalue())

        self.assertEqual(set(imported.uploaded_rows or {}), {"orders.csv", "products.csv", "inventory.csv"})

    def test_new_tables_accept_vietnamese_no_accent_headers(self) -> None:
        files = {
            name: (SRC_DIR.parent / "data" / "shop_mock" / name).read_bytes()
            for name in ("orders.csv", "products.csv", "inventory.csv")
        }
        files.update({
            "price_promotions.csv": (
                "ngay,ma_san_pham,gia_niem_yet_vnd,gia_sau_khuyen_mai,giam_gia_nguoi_ban_vnd,nguon_ma_giam_gia,ten_chuong_trinh\n"
                "2026-08-10,SKU-001,100000,90000,10000,Ma nguoi ban,Uu dai thu\n"
            ).encode(),
            "ads_sku_daily.csv": (
                "ngay,ma_chien_dich,ma_san_pham,luot_hien_thi,luot_nhap,chi_quang_cao_vnd,luot_them_gio,so_don_quy_gan,doanh_thu_quy_gan_vnd\n"
                "2026-08-10,ADS-1,SKU-001,100,10,10000,3,1,50000\n"
            ).encode(),
            "inventory_batches.csv": (
                "ma_lo,ma_san_pham,ngay_nhap_kho,so_luong_con_lai,gia_von_don_vi_vnd\n"
                "LO-1,SKU-001,2026-06-01,12,50000\n"
            ).encode(),
        })

        tool = ShopDataTool.from_uploaded_files(files)

        self.assertEqual(tool.price_promotion_summary("2026-08")["product_count"], 1)
        self.assertEqual(tool.ads_sku_daily_summary("2026-08")["top_roas_product"]["roas"], 5.0)
        self.assertEqual(tool.inventory_batch_age_summary(date.fromisoformat("2026-10-01"))["oldest_batch"]["age_days"], 122)

    def test_scorecard_keeps_missing_sku_evidence_visible(self) -> None:
        rows = build_demo_rows(seed=7)
        rows["quality_checks.csv"] = []
        scorecard = ShopDataTool(uploaded_rows=rows).product_decision_scorecard("2026-08")

        self.assertTrue(scorecard["evidence_gaps"])
        self.assertTrue(all("chưa có kiểm tra chất lượng theo SKU" in row["evidence_gaps"] for row in scorecard["products"]))
        self.assertIsNone(scorecard["recommended_candidate"])


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

    def test_runner_handles_greeting_and_capability_question_without_retrieval(self) -> None:
        greeting = AgentRunner().run("Chào bạn")
        capability = AgentRunner().run("Bạn có thể làm gì?")

        self.assertEqual(greeting["plan"]["intent"], "casual")
        self.assertEqual(greeting["trace"], [])
        self.assertIn("mình là Eslabong", greeting["answer"])
        self.assertIn("doanh thu", capability["answer"])
        self.assertIn("Bạn muốn xem phần nào?", capability["answer"])

    def test_default_demo_includes_the_core_sku_and_inventory_answers(self) -> None:
        """The out-of-box demo must cover the questions used in a defense."""
        runner = AgentRunner()
        checks = {
            "SKU nào có ROAS quảng cáo tốt nhất?": "ROAS đã ghi cao nhất",
            "SKU nào đang được giảm giá nhiều nhất?": "SKU giảm giá nhiều nhất",
            "2 lô tồn lâu nhất": "Hai lô tồn lâu nhất đã ghi nhận",
        }
        for question, expected in checks.items():
            with self.subTest(question=question):
                self.assertIn(expected, runner.run(question)["answer"])

    def test_morning_twenty_question_bank_returns_direct_operational_answers(self) -> None:
        """Keep the user's manual test bank from regressing to a generic fallback."""
        checks = {
            "Từ khóa nào có lượt nhấp cao nhất?": "Từ khóa có nhiều lượt nhấp nhất",
            "Từ khóa nào có vị trí tìm kiếm trung bình tốt nhất?": "vị trí tìm kiếm trung bình tốt nhất",
            "Shop có bao nhiêu đơn giao trễ?": "đơn giao trễ",
            "Lý do hủy đơn phổ biến nhất là gì?": "Lý do hủy đơn phổ biến nhất",
            "Thời gian xử lý đơn trung bình là bao lâu?": "Thời gian xử lý đơn trung bình",
            "Đối soát thanh toán tháng 8 thế nào?": "Đối soát đã ghi",
            "Tiền Shopee phải trả, phí thực tế và tiền đã nhận có khớp không?": "Khoản đối soát",
            "Shop tham khảo nào có lượng bán ước tính cao nhất?": "lượng bán ước tính cao nhất",
            "Giá của đối thủ đang cao hay thấp hơn giá sản phẩm tương ứng của shop?": "Giá trung vị của đối thủ",
            "SKU nào đang được giảm giá nhiều nhất?": "SKU giảm giá nhiều nhất",
            "SKU ROAS cao nhất": "ROAS đã ghi cao nhất",
            "2 lô tồn lâu nhất": "Hai lô tồn lâu nhất đã ghi nhận",
            "Sản phẩm nào sắp hết hàng?": "Sản phẩm sắp hết hàng cần kiểm tra trước",
            "Sản phẩm nào có lãi góp thấp nhất?": "lãi góp thấp nhất",
            "Tháng 8 shop có doanh thu sau phí ước tính là bao nhiêu?": "Doanh thu sau phí ước tính",
            "Đánh giá thấp đang tập trung ở vấn đề nào?": "Ưu tiên xử lý",
            "Khoản chi vận hành lớn nhất là gì?": "Khoản vận hành đã ghi nhận lớn nhất",
            "Nhà cung cấp nào có tỷ lệ giao đúng hẹn thấp nhất?": "tỷ lệ giao đúng hẹn thấp nhất",
            "Sản phẩm nào xem nhiều nhưng tỷ lệ thêm giỏ thấp?": "lượt xem nhưng tỷ lệ thêm giỏ thấp nhất",
            "Tôi nên ưu tiên xử lý việc gì trước trong tuần này?": "Ba việc tuần này",
        }
        runner = AgentRunner()
        for question, expected in checks.items():
            with self.subTest(question=question):
                answer = runner.run(question)["answer"]
                self.assertIn(expected, answer)
                self.assertNotIn("Tôi chưa có đủ nội dung", answer)

    def test_curated_new_seller_questions_do_not_fall_back_or_use_demo_metrics(self) -> None:
        questions = (
            "Người mới cần chuẩn bị gì trước khi mở shop trên Shopee?",
            "Ai có thể đăng ký mở shop trên Shopee?",
            "Cách đăng ký mở shop trên Shopee như thế nào?",
            "Tôi cần chuẩn bị gì để đăng sản phẩm đầu tiên?",
            "SKU là gì và vì sao mỗi biến thể nên có SKU riêng?",
            "Giá bán nên tính những khoản chi phí nào?",
            "Làm sao viết mô tả sản phẩm rõ ràng và đúng quy định?",
            "Shopee đang áp dụng những loại phí nào?",
            "Phí cố định là gì?",
            "Khi nào người mua có thể yêu cầu trả hàng hoặc hoàn tiền?",
            "Đơn bị hủy có được tính doanh thu không?",
            "Khi có đơn hàng mới, tôi cần xử lý theo các bước nào?",
            "Làm sao đóng gói hàng để giảm nguy cơ trả hàng?",
            "Làm thế nào để tránh đánh giá thấp từ người mua?",
            "Khi nào người mới nên bắt đầu chạy quảng cáo?",
        )
        runner = AgentRunner()
        for question in questions:
            with self.subTest(question=question):
                answer = runner.run(question)["answer"]
                self.assertTrue(answer)
                self.assertNotIn("Tôi chưa có đủ nội dung", answer)
                self.assertNotIn("Chưa truy hồi được", answer)

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
        self.assertIn("chỉ tính các đơn có trạng thái **hoàn tất**", result["answer"])
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

        restock = AgentRunner().run("Sản phẩm bán tốt có chắc nên nhập nhiều hơn không?")
        self.assertIn("Không nên nhập nhiều chỉ vì một sản phẩm bán tốt", restock["answer"])

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
        self.assertTrue(result["answer"].startswith("Cần kiểm tra trước:"))

    def test_sku_analysis_question_does_not_fall_back_to_sku_definition(self) -> None:
        runner = AgentRunner(shop_data_tool=ShopDataTool(uploaded_rows=build_demo_rows(seed=20261001)))
        result = runner.run("Giá khuyến mãi SKU nào đang giảm nhiều nhất?")
        answer = result["answer"]

        self.assertIn("Giá–khuyến mãi đã ghi", answer)
        self.assertNotIn("SKU là mã riêng", answer)
        self.assertFalse(result["show_summary_metrics"])

    def test_inventory_batch_question_leads_with_two_oldest_batches(self) -> None:
        runner = AgentRunner(shop_data_tool=ShopDataTool(uploaded_rows=build_demo_rows(seed=20261001)))
        answer = runner.run("Lô hàng nào tồn lâu nhất?")["answer"]

        self.assertIn("Hai lô tồn lâu nhất", answer)
        self.assertIn("1. **", answer)
        self.assertIn("2. **", answer)
        self.assertNotIn("Hàng tồn lâu và bán chậm chưa nên", answer)

    def test_default_answer_is_brief_but_detail_cues_keep_the_explanation(self) -> None:
        runner = AgentRunner(shop_data_tool=ShopDataTool(uploaded_rows=build_demo_rows(seed=20261001)))

        brief = runner.run("Lô hàng nào tồn lâu nhất?")["answer"]
        detailed = runner.run("Lô hàng nào tồn lâu nhất? Hãy phân tích chi tiết.")["answer"]

        self.assertIn("Hai lô tồn lâu nhất", brief)
        self.assertIn("1. **", brief)
        self.assertIn("2. **", brief)
        self.assertNotIn("Cần kiểm tra trước", brief)
        self.assertIn("Cần kiểm tra trước", detailed)

    def test_missing_data_keeps_a_concrete_create_or_upload_instruction_when_brief(self) -> None:
        runner = AgentRunner(shop_data_tool=ShopDataTool(uploaded_rows={
            name: build_demo_rows(seed=20261001)[name]
            for name in ("orders.csv", "products.csv", "inventory.csv")
        }))

        answer = runner.run("Lô hàng nào tồn lâu nhất?")["answer"]

        self.assertIn("Chưa thể nêu", answer)
        self.assertIn("Bạn hãy tạo hoặc tải", answer)
        self.assertIn("Tuổi tồn kho theo lô", answer)

    def test_new_operational_data_routes_directly_to_its_own_table(self) -> None:
        runner = AgentRunner(shop_data_tool=ShopDataTool(uploaded_rows=build_demo_rows(seed=20261001)))
        checks = {
            "Từ khóa nào có lượt nhấp cao nhất?": "Từ khóa có nhiều lượt nhấp nhất",
            "Từ khóa nào có vị trí tìm kiếm trung bình tốt nhất?": "càng nhỏ càng tốt",
            "Shop có bao nhiêu đơn giao trễ?": "đơn giao trễ",
            "ý do hủy đơn phổ biến nhất là gì?": "Lý do hủy đơn phổ biến nhất",
            "Thời gian xử lý đơn trung bình là bao lâu?": "Thời gian xử lý đơn trung bình là",
            "Đối soát thanh toán tháng 8 thế nào?": "Shopee phải trả",
            "Tiền Shopee phải trả, phí thực tế và tiền đã nhận có khớp không?": "Khoản đối soát **khớp**",
            "Đối thủ nào bán ước tính cao nhất?": "chỉ là dữ liệu tham khảo",
            "Giá của đối thủ đang cao hay thấp hơn giá sản phẩm tương ứng của shop?": "Giá trung vị của đối thủ",
            "SKU nào đang được giảm giá nhiều nhất?": "SKU giảm giá nhiều nhất",
            "SKU nào có ROAS quagn cáo tốt nhất?": "ROAS đã ghi cao nhất",
            "Lô hàng nào tồn lâu nhất?": "2. **",
            "2 lô tồn lâu nhất": "2. **",
            "Sản phẩm nào sắp hết hàng?": "Sản phẩm sắp hết hàng cần kiểm tra trước",
            "Tháng 8 shop có doanh thu sau phí ước tính là bao nhiêu?": "Doanh thu sau phí ước tính",
            "Đánh giá thấp đang tập trung ở vấn đề nào?": "Ưu tiên xử lý",
            "Khoản chhi vận hnah lớn nhất là gì?": "Khoản vận hành đã ghi nhận lớn nhất",
            "Nhà cung cấp nào có tỷ lệ giao đúng hẹn thấp nhất?": "tỷ lệ giao đúng hẹn thấp nhất",
            "Sản phẩm nào xem nhieuu nhưng tỷ lệ thêm giỏ thấp?": "Sản phẩm có nhiều lượt xem nhưng tỷ lệ thêm giỏ thấp nhất",
        }
        for question, expected in checks.items():
            with self.subTest(question=question):
                self.assertIn(expected, runner.run(question)["answer"])

    def test_single_ambiguous_word_requests_the_missing_metric_instead_of_rag_fallback(self) -> None:
        answer = AgentRunner().run("nhieuu")["answer"]

        self.assertIn("chưa xác định được chỉ số", answer)
        self.assertIn("nêu đầy đủ", answer)
        self.assertNotIn("Chưa truy hồi được", answer)

    def test_operational_question_bank_uses_topic_routing_and_bounded_advice(self) -> None:
        """Regression coverage for the shared question-bank failure patterns."""
        checks = {
            "Mặt hàng này có được bán trên Shopee không?": "Chưa thể kết luận",
            "Nguồn hàng nào có tỷ lệ lỗi cao hơn?": "tỷ lệ lỗi cao nhất",
            "Làm gì để giảm đánh giá xấu?": "Ưu tiên xử lý",
            "Lãi sau chi phí vận hành tháng 8 là bao nhiêu?": "612,200 VND",
            "Khoản vận hành nào đang lớn nhất?": "Nhân sự",
            "Tại sao doanh thu tăng mà tôi vẫn thiếu tiền nhập hàng?": "thời điểm thu tiền",
            "Khoản tiền chi nào lớn nhất tháng này?": "Nhập hàng",
            "Có dấu hiệu thất thoát hàng không?": "Chưa thể kết luận có thất thoát",
            "Tỷ lệ lỗi lô hàng tháng 8 là bao nhiêu?": "1.61%",
            "Tôi có nên phản hồi nhà cung cấp không?": "Nên phản hồi nhà cung cấp",
            "Làm sao tăng khách quay lại?": "Để tăng khách quay lại",
            "Nếu lượt xem cao nhưng ít thêm giỏ thì nên kiểm tra gì?": "Lượt xem cao nhưng ít thêm giỏ",
            "Nếu nhiều người thêm giỏ nhưng ít đặt mua thì sao?": "giá cuối",
            "Tôi nên ưu tiên sản phẩm nào trong 30 ngày tới?": "không coi dữ liệu thiếu là rủi ro bằng 0",
            "Tôi có nên tạo combo không?": "Sản phẩm mua cùng",
            "Tôi đang có nguy cơ lỗ ở đâu?": "Các điểm có nguy cơ",
            "Tôi cần làm gì trước trong tuần này?": "Ba việc tuần này",
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

    def test_extended_strategy_questions_use_the_metric_and_next_data_action_requested(self) -> None:
        runner = AgentRunner()
        checks = {
            "Tôi có nên tăng ngân sách quảng cáo không? Trước khi tăng cần kiểm tra trang sản phẩm và tồn kho thế nào?": [
                "5 điểm", "tồn khả dụng chạm ngưỡng nhập thêm",
            ],
            "Dựa trên các đánh giá 1–3 sao, shop nên xử lý vấn đề nào trước và đo lại thế nào?": [
                "đánh giá 1–3 sao", "tỷ lệ đánh giá thấp",
            ],
            "Sản phẩm nào có nhiều lượt xem nhưng tỷ lệ từ xem sang thêm giỏ thấp nhất? Tôi nên thử cải thiện gì trước?": [
                "Lượt xem cao nhưng ít thêm giỏ",
            ],
            "Tôi nên ưu tiên sản phẩm nào trong 30 ngày tới nếu xét GMV, lãi góp, tồn kho, đánh giá, tỷ lệ lỗi và phễu?": [
                "không coi dữ liệu thiếu là rủi ro bằng 0", "bổ sung bản ghi theo SKU",
            ],
            "Tôi có nên tạo combo nào? Hãy nêu điều kiện chọn hai sản phẩm, giá thử và chỉ số dừng thử nghiệm.": [
                "Sản phẩm mua cùng", "dừng thử",
            ],
            "Tôi đang có nguy cơ lỗ ở đâu nếu xét lãi góp, chi phí vận hành, hàng hoàn, hàng lỗi và tồn chậm?": [
                "Các điểm có nguy cơ", "không phải kết luận lỗ ròng",
            ],
            "Dựa trên dữ liệu hiện có, ba việc nào tôi cần làm trước trong tuần này? Mỗi việc đo bằng chỉ số nào?": [
                "Ba việc tuần này", "chứng từ hợp lệ",
            ],
            "Giao dịch điện tử có thể có giá trị pháp lý khi đáp ứng điều kiện nào? Tôi cần lưu chứng từ gì?": [
                "có thể truy cập", "chứng từ giao nhận",
            ],
        }
        for question, expected_phrases in checks.items():
            with self.subTest(question=question):
                answer = runner.run(question)["answer"]
                for expected_phrase in expected_phrases:
                    self.assertIn(expected_phrase, answer)
                self.assertNotIn("Tôi chưa có đủ nội dung đã kiểm chứng", answer)

    def test_strategy_answers_do_not_treat_missing_evidence_as_zero_risk(self) -> None:
        rows = build_demo_rows(seed=7)
        rows["quality_checks.csv"] = []
        runner = AgentRunner(shop_data_tool=ShopDataTool(uploaded_rows=rows))
        priority = runner.run("Tôi nên ưu tiên sản phẩm nào trong 30 ngày tới?")["answer"]

        self.assertIn("không coi dữ liệu thiếu là rủi ro bằng 0", priority)
        risk = AgentRunner().run("Tôi đang có nguy cơ lỗ ở đâu?")["answer"]
        self.assertIn("Các điểm có nguy cơ", risk)

    def test_combo_with_pair_data_includes_a_labeled_trial_price_and_stop_rules(self) -> None:
        runner = AgentRunner(shop_data_tool=ShopDataTool(uploaded_rows=build_demo_rows(seed=7)))
        answer = runner.run("Tôi có nên tạo combo nào? Hãy nêu giá thử và điều kiện dừng.")["answer"]

        self.assertIn("Giá thử minh họa giảm 5%", answer)
        self.assertIn("Dừng thử nếu", answer)


if __name__ == "__main__":
    unittest.main()
