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
        self.assertEqual(len(app.error), 0)

    def test_owner_chat_exposes_human_readable_uploads(self) -> None:
        app = AppTest.from_file(SRC_DIR / "shopee_seller_ai.py", default_timeout=15).run()
        app.button(key="new_chat_main").click().run()
        app.button(key="choose_owner").click().run()

        self.assertEqual(
            [uploader.label for uploader in app.file_uploader],
            [
                "Báo cáo đơn hàng (orders.csv)",
                "Danh mục sản phẩm (products.csv)",
                "Báo cáo tồn kho (inventory.csv)",
                "Báo cáo quảng cáo (ads.csv, không bắt buộc)",
            ],
        )
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
        self.assertEqual(app.button(key="market_advisor_toggle").label, "AI")
        self.assertTrue(any("Market Demo" in warning.value for warning in app.warning))
        self.assertEqual(len(app.error), 0)

    def test_strategy_workspace_exposes_decision_tools(self) -> None:
        app = AppTest.from_file(SRC_DIR / "shopee_seller_ai.py", default_timeout=15).run()
        app.button(key="open_strategy_workspace").click().run()

        self.assertEqual([title.value for title in app.title], ["Chiến lược kinh doanh"])
        self.assertEqual([tab.label for tab in app.tabs], ["Radar cơ hội", "Mô phỏng chiến lược", "So sánh phương án", "Kế hoạch 30 ngày", "Nhật ký thử nghiệm"])
        self.assertEqual(len(app.error), 0)

    def test_market_adviser_opens_a_chat_for_the_current_demo_scene(self) -> None:
        app = AppTest.from_file(SRC_DIR / "shopee_seller_ai.py", default_timeout=15).run()
        app.button(key="open_market_intelligence").click().run()
        app.button(key="market_advisor_toggle").click().run()

        self.assertTrue(app.session_state["seller_market_advisor_open"])
        self.assertEqual(len(app.chat_input), 1)
        self.assertEqual(app.chat_input[0].placeholder, "Hỏi về giá, sản phẩm hoặc hướng phát triển shop...")
        app.chat_input[0].set_value("Tôi nên điều chỉnh giá thế nào?").run()
        self.assertEqual(len(app.chat_message), 2)
        self.assertTrue(any("Giá trung bình" in markdown.value for markdown in app.markdown))
        self.assertEqual(len(app.error), 0)

    def test_market_adviser_answers_follow_up_without_repeating_a_summary(self) -> None:
        app = AppTest.from_file(SRC_DIR / "shopee_seller_ai.py", default_timeout=15).run()
        app.button(key="open_market_intelligence").click().run()
        app.button(key="market_advisor_toggle").click().run()
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
