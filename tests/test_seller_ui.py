from __future__ import annotations

import unittest
from pathlib import Path

from streamlit.testing.v1 import AppTest


SRC_DIR = Path(__file__).resolve().parents[1] / "src"


class SellerFacingUiTests(unittest.TestCase):
    def test_assistant_starts_with_a_clear_empty_state(self) -> None:
        app = AppTest.from_file(SRC_DIR / "shopee_seller_ai.py", default_timeout=15).run()

        self.assertEqual([title.value for title in app.title], ["Bắt đầu cuộc trò chuyện"])
        self.assertIn("Cuộc trò chuyện mới", [button.label for button in app.button])
        app.button(key="new_chat_main").click().run()
        self.assertIn("Bắt đầu với vai trò người mới", [button.label for button in app.button])
        app.button(key="choose_learner").click().run()
        self.assertEqual(len(app.chat_input), 1)
        self.assertIn("Người mới · Chat người mới", [button.label for button in app.button])
        self.assertFalse(app.button(key="open_learner_1").disabled)
        app.button(key="open_learner_1").click().run()
        self.assertEqual(len(app.chat_input), 1)
        self.assertEqual(app.session_state["seller_chat_scroll_sequence"], 1)
        self.assertEqual(len(app.error), 0)

    def test_new_seller_chat_includes_a_fifteen_question_bank(self) -> None:
        app = AppTest.from_file(SRC_DIR / "shopee_seller_ai.py", default_timeout=15).run()
        app.button(key="new_chat_main").click().run()
        app.button(key="choose_learner").click().run()

        self.assertIn("Bộ câu hỏi người mới", [button.label for button in app.button])
        self.assertFalse(app.session_state["seller_learner_question_bank_open"])
        app.button(key="toggle_learner_question_bank").click().run()

        picker = app.selectbox(key="learner_question_picker")
        self.assertEqual(len(picker.options), 15)
        self.assertFalse(any(button.key and button.key.startswith("learner_question_") for button in app.button))
        picker.select("Người mới cần chuẩn bị gì trước khi mở shop trên Shopee?").run()
        self.assertEqual(
            app.session_state["seller_messages"][0]["content"],
            "Người mới cần chuẩn bị gì trước khi mở shop trên Shopee?",
        )
        self.assertEqual(len(app.error), 0)

    def test_new_seller_guidance_about_order_processing_is_not_blocked_for_missing_shop_data(self) -> None:
        app = AppTest.from_file(SRC_DIR / "shopee_seller_ai.py", default_timeout=20).run()
        app.button(key="new_chat_main").click().run()
        app.button(key="choose_learner").click().run()

        app.button(key="toggle_learner_question_bank").click().run()
        app.selectbox(key="learner_question_picker").select(
            "Khi có đơn hàng mới, tôi cần xử lý theo các bước nào?"
        ).run()

        answer = app.session_state["seller_messages"][1]["answer"]
        self.assertIn("Khi có đơn mới", answer)
        self.assertNotIn("cần dữ liệu bán hàng", answer)
        self.assertEqual(
            app.session_state["seller_messages"][1]["data_requirement"],
            "no_shop_data_required",
        )

    def test_missing_shop_data_names_the_required_table_and_question_type(self) -> None:
        app = AppTest.from_file(SRC_DIR / "shopee_seller_ai.py", default_timeout=20).run()
        app.button(key="new_chat_main").click().run()
        app.button(key="choose_owner").click().run()

        app.chat_input(key="seller_chat_input").set_value("Shop có bao nhiêu đơn giao trễ?").run()

        result = app.session_state["seller_messages"][1]
        self.assertEqual(result["data_requirement"], "shop_data_required")
        self.assertIn("Bạn hãy tạo hoặc tải dữ liệu cần thiết", result["answer"])
        self.assertIn("bảng **Vận chuyển**", result["answer"])
        self.assertTrue(any("cần dữ liệu shop" in item.value for item in app.caption))
        self.assertEqual(len(app.error), 0)

    def test_owner_chat_exposes_human_readable_uploads(self) -> None:
        app = AppTest.from_file(SRC_DIR / "shopee_seller_ai.py", default_timeout=15).run()
        app.button(key="new_chat_main").click().run()
        app.button(key="choose_owner").click().run()

        upload_labels = [uploader.label for uploader in app.file_uploader]
        self.assertEqual(
            upload_labels,
            [
                "Chọn file Excel (.xlsx)",
                "Đơn hàng (bắt buộc)",
                "Sản phẩm và giá vốn (bắt buộc)",
                "Tồn kho (bắt buộc)",
            ],
        )
        self.assertIn("Tải bộ kiểm thử đầy đủ (.xlsx)", [item.label for item in app.download_button])
        self.assertEqual(len(app.error), 0)

    def test_settings_switch_interface_language_and_dark_mode_without_losing_state(self) -> None:
        app = AppTest.from_file(SRC_DIR / "shopee_seller_ai.py", default_timeout=15).run()

        app.selectbox(key="seller_language").select("en").run()
        self.assertEqual(app.session_state["seller_language"], "en")
        self.assertIn("New chat", [button.label for button in app.button])

        app.toggle(key="seller_dark_mode").set_value(True).run()
        self.assertTrue(app.session_state["seller_dark_mode"])
        rendered_styles = "\n".join(item.value for item in app.markdown)
        self.assertIn("#111827", rendered_styles)
        self.assertIn("#2563eb", rendered_styles)
        self.assertIn("st-key-seller_suggestion", rendered_styles)
        self.assertIn("st-key-open_", rendered_styles)
        self.assertIn('st-key-open_"] button[kind="primary"]', rendered_styles)
        self.assertIn("stSegmentedControl", rendered_styles)
        self.assertIn("label:has(input:checked)", rendered_styles)
        self.assertIn("stSelectbox", rendered_styles)
        self.assertIn('button[data-variant="segmented_control"]', rendered_styles)
        self.assertIn('[data-testid="stSelectbox"] [role="group"]', rendered_styles)
        self.assertIn("stDownloadButton", rendered_styles)
        self.assertIn("--gdg-bg-cell: #1f2937", rendered_styles)
        self.assertIn("user-select: none", rendered_styles)
        self.assertIn("height: 56px", rendered_styles)
        self.assertNotIn("background: #000000", rendered_styles)
        self.assertEqual(len(app.error), 0)

    def test_english_market_shell_has_no_vietnamese_navigation_or_guidance(self) -> None:
        app = AppTest.from_file(SRC_DIR / "shopee_seller_ai.py", default_timeout=15).run()
        app.selectbox(key="seller_language").select("en").run()
        app.button(key="open_market_intelligence").click().run()

        self.assertEqual([title.value for title in app.title], ["Market analysis"])
        self.assertEqual(
            [item.label for item in app.selectbox[:2]],
            ["Choose a category to analyze", "Choose a product to compare prices"],
        )
        self.assertIn("Regenerate demo shop and market", [button.label for button in app.button])
        self.assertTrue(any("Quick guide" in item.value for item in app.markdown))
        self.assertFalse(any("Cách dùng nhanh" in item.value for item in app.markdown))
        self.assertFalse(any("Chưa chọn cuộc trò chuyện" in item.value for item in app.caption))
        self.assertEqual(len(app.error), 0)

    def test_attached_data_can_be_downloaded_as_an_editable_excel_workbook(self) -> None:
        app = AppTest.from_file(SRC_DIR / "shopee_seller_ai.py", default_timeout=15).run()
        app.button(key="new_chat_main").click().run()
        app.button(key="choose_owner").click().run()
        app.session_state["seller_uploaded_rows"] = {
            "orders.csv": [{"order_id": "DH-01", "order_date": "2026-09-01", "status": "completed", "sku": "SP-01", "quantity": "1", "gross_merchandise_value_vnd": "100000", "seller_discount_vnd": "0", "platform_discount_vnd": "0", "estimated_transaction_fee_vnd": "5000", "estimated_service_fee_vnd": "2500"}],
            "products.csv": [{"sku": "SP-01", "product_name": "Sản phẩm thử", "category": "Thử nghiệm", "cost_per_unit_vnd": "50000", "list_price_vnd": "100000"}],
            "inventory.csv": [{"sku": "SP-01", "on_hand": "5", "reserved": "0", "reorder_point": "2", "last_updated": "2026-09-01"}],
        }
        app.session_state["seller_uploaded_names"] = ("orders.csv", "products.csv", "inventory.csv")
        app.run()

        self.assertIn("Tải bộ dữ liệu đang dùng (.xlsx)", [item.label for item in app.download_button])
        self.assertEqual(len(app.error), 0)

    def test_sidebar_compacts_to_icon_controls(self) -> None:
        app = AppTest.from_file(SRC_DIR / "shopee_seller_ai.py", default_timeout=15).run()
        app.button(key="collapse_sidebar").click().run()

        self.assertTrue(app.session_state["seller_sidebar_compact"])
        self.assertEqual(app.button(key="expand_sidebar").icon, ":material/chevron_right:")
        self.assertEqual(app.button(key="compact_new_chat").icon, ":material/add_comment:")

    def test_bookshelf_opens_the_local_data_workspace(self) -> None:
        app = AppTest.from_file(SRC_DIR / "shopee_seller_ai.py", default_timeout=15).run()
        app.button(key="open_data_library").click().run()

        self.assertEqual([title.value for title in app.title], ["Dữ liệu và báo cáo quản lý"])
        self.assertIn("Lưu bảng dữ liệu", [button.label for button in app.button])
        self.assertIn("Bộ demo · Người mới", app.segmented_control(key="seller_library_scope").options)
        self.assertIn("Dữ liệu shop · Chủ shop", app.segmented_control(key="seller_library_scope").options)
        self.assertEqual(len(app.error), 0)

    def test_market_workspace_labels_its_reference_data_as_a_demo(self) -> None:
        app = AppTest.from_file(SRC_DIR / "shopee_seller_ai.py", default_timeout=15).run()
        app.button(key="open_market_intelligence").click().run()

        self.assertEqual([title.value for title in app.title], ["Phân tích thị trường"])
        self.assertEqual(len(app.selectbox(key="seller_market_category_id").options), 50)
        self.assertGreaterEqual(len(app.selectbox(key="market_price_product").options), 5)
        self.assertLessEqual(len(app.selectbox(key="market_price_product").options), 12)
        self.assertEqual(
            app.segmented_control(key="market_section").options,
            ["So sánh giá", "So sánh shop", "Sản phẩm cùng thị trường"],
        )
        self.assertEqual(app.button(key="market_open_advisor").label, "Chiến lược gia AI")
        self.assertTrue(any("dữ liệu thị trường mô phỏng" in warning.value for warning in app.warning))
        self.assertEqual(len(app.error), 0)

    def test_strategy_workspace_exposes_decision_tools(self) -> None:
        app = AppTest.from_file(SRC_DIR / "shopee_seller_ai.py", default_timeout=15).run()
        app.button(key="open_strategy_workspace").click().run()

        self.assertEqual([title.value for title in app.title], ["Chiến lược kinh doanh"])
        self.assertEqual(
            app.segmented_control(key="strategy_section").options,
            ["Radar cơ hội", "Mô phỏng chiến lược", "Vốn & tồn kho", "Kế hoạch 30 ngày"],
        )
        self.assertEqual(len(app.error), 0)

    def test_market_adviser_opens_a_chat_for_the_current_demo_scene(self) -> None:
        app = AppTest.from_file(SRC_DIR / "shopee_seller_ai.py", default_timeout=15).run()
        app.button(key="open_market_intelligence").click().run()
        app.button(key="market_open_advisor").click().run()

        self.assertTrue(app.session_state["seller_market_advisor_open"])
        self.assertEqual(len(app.chat_input), 1)
        self.assertEqual(app.chat_input[0].placeholder, "Hỏi về giá, sản phẩm hoặc hướng phát triển shop...")
        app.chat_input[0].set_value("Tôi nên điều chỉnh giá thế nào?").run()
        self.assertEqual(len(app.chat_message), 2)
        self.assertTrue(any("Giá trung bình" in markdown.value for markdown in app.markdown))
        self.assertEqual(len(app.error), 0)

    def test_market_adviser_history_is_saved_in_the_active_conversation_context(self) -> None:
        app = AppTest.from_file(SRC_DIR / "shopee_seller_ai.py", default_timeout=15).run()
        app.button(key="new_chat_main").click().run()
        app.button(key="choose_learner").click().run()
        app.button(key="open_market_intelligence").click().run()
        app.button(key="market_open_advisor").click().run()
        app.chat_input[0].set_value("Sản phẩm nào nên ưu tiên?").run()

        conversation = app.session_state["seller_conversations"][0]
        self.assertEqual(conversation["id"], "learner_1")
        self.assertEqual(len(conversation["context"]["seller_market_advisor_messages"]), 2)
        self.assertEqual(conversation["context"]["seller_market_scenario_seed"], app.session_state["seller_market_scenario_seed"])

    def test_adviser_can_handoff_a_note_to_the_linked_main_chat(self) -> None:
        app = AppTest.from_file(SRC_DIR / "shopee_seller_ai.py", default_timeout=15).run()
        app.button(key="new_chat_main").click().run()
        app.button(key="choose_owner").click().run()
        app.button(key="open_market_intelligence").click().run()
        app.button(key="market_open_advisor").click().run()
        app.chat_input[0].set_value("Tôi nên điều chỉnh giá thế nào?").run()
        app.button(key="advisor_handoff_to_chat").click().run()

        self.assertEqual(app.session_state["seller_view"], "chat")
        self.assertFalse(app.session_state["seller_market_advisor_open"])
        self.assertEqual(len(app.session_state["seller_advisor_handoffs"]), 1)
        self.assertEqual(
            len(app.session_state["seller_conversations"][0]["context"]["seller_advisor_handoffs"]),
            1,
        )
        self.assertTrue(any("Ghi chú từ Chiến lược gia AI" in item.value for item in app.markdown))

    def test_adviser_navigation_performs_a_full_view_change(self) -> None:
        app = AppTest.from_file(SRC_DIR / "shopee_seller_ai.py", default_timeout=15).run()
        app.button(key="new_chat_main").click().run()
        app.button(key="choose_learner").click().run()
        app.button(key="open_market_intelligence").click().run()
        app.button(key="market_open_advisor").click().run()
        app.button(key="advisor_to_strategy").click().run()

        self.assertEqual(app.session_state["seller_view"], "strategy")
        self.assertFalse(app.session_state["seller_market_advisor_open"])
        self.assertEqual(
            app.session_state["strategy_category_id"],
            app.session_state["seller_market_category_id"],
        )
        self.assertEqual(len(app.error), 0)

    def test_market_adviser_answers_follow_up_without_repeating_a_summary(self) -> None:
        app = AppTest.from_file(SRC_DIR / "shopee_seller_ai.py", default_timeout=15).run()
        app.button(key="open_market_intelligence").click().run()
        app.button(key="market_open_advisor").click().run()
        app.chat_input[0].set_value("Tại sao shop tôi có đánh giá thấp?").run()
        app.chat_input[0].set_value("Còn cách khác nữa không?").run()

        answers = [message.markdown[0].value for message in app.chat_message if message.name == "assistant"]
        self.assertTrue(any("độ tin cậy" in answer for answer in answers))
        self.assertTrue(any("Cách khác" in answer for answer in answers))
        self.assertFalse(any("Tóm tắt kịch bản" in answer for answer in answers))

    def test_learner_opens_the_demo_shelf(self) -> None:
        app = AppTest.from_file(SRC_DIR / "shopee_seller_ai.py", default_timeout=15).run()
        app.button(key="new_chat_main").click().run()
        app.button(key="choose_learner").click().run()
        app.button(key="open_demo_library_from_chat").click().run()

        self.assertEqual(app.segmented_control(key="seller_library_scope").value, "demo")
        self.assertIn("Bộ dữ liệu demo cho người mới", [header.value for header in app.subheader])

    def test_learner_can_choose_a_demo_shop_category_from_the_dropdown(self) -> None:
        app = AppTest.from_file(SRC_DIR / "shopee_seller_ai.py", default_timeout=15).run()
        app.button(key="new_chat_main").click().run()
        app.button(key="choose_learner").click().run()
        app.button(key="open_demo_library_from_chat").click().run()

        picker = app.selectbox(key="seller_demo_category_picker")
        self.assertEqual(len(picker.options), 50)
        self.assertIsNone(picker.value)
        picker.select("fresh-fruit").run()
        app.button(key="add_demo_category").click().run()
        self.assertEqual(app.multiselect(key="seller_demo_selected_ids").value, ["fresh-fruit"])
        self.assertFalse(app.button(key="create_selected_demo").disabled)

    def test_learner_category_picker_requires_a_category_before_adding(self) -> None:
        app = AppTest.from_file(SRC_DIR / "shopee_seller_ai.py", default_timeout=15).run()
        app.button(key="new_chat_main").click().run()
        app.button(key="choose_learner").click().run()
        app.button(key="open_demo_library_from_chat").click().run()

        picker = app.selectbox(key="seller_demo_category_picker")
        self.assertEqual(len(picker.options), 50)
        self.assertTrue(app.button(key="add_demo_category").disabled)
        picker.select("fresh-fruit").run()
        self.assertFalse(app.button(key="add_demo_category").disabled)


if __name__ == "__main__":
    unittest.main()
