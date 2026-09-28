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
