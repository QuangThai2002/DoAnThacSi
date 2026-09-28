from __future__ import annotations

import unittest
from pathlib import Path

from streamlit.testing.v1 import AppTest


SRC_DIR = Path(__file__).resolve().parents[1] / "src"


class SellerFacingUiTests(unittest.TestCase):
    def test_assistant_starts_with_a_clear_empty_state(self) -> None:
        app = AppTest.from_file(SRC_DIR / "shopee_seller_ai.py", default_timeout=15).run()

        self.assertEqual([title.value for title in app.title], ["Bạn cần hỗ trợ điều gì?"])
        self.assertIn("Bắt đầu hỏi", [button.label for button in app.button])
        self.assertIn("Phân tích shop", [button.label for button in app.button])
        next(button for button in app.button if button.label == "Bắt đầu hỏi").click().run()
        self.assertEqual(len(app.chat_input), 1)
        self.assertEqual(len(app.error), 0)

    def test_data_page_exposes_only_human_readable_uploads(self) -> None:
        app = AppTest.from_file(SRC_DIR / "shopee_seller_ai.py", default_timeout=15).run()
        app.radio[0].set_value("Dữ liệu shop").run()

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


if __name__ == "__main__":
    unittest.main()
