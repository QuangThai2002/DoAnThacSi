from __future__ import annotations

import sys
import unittest
from pathlib import Path


SRC_DIR = Path(__file__).resolve().parents[1] / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from hybrid_search_shopee_v2 import SearchResult, query_aware_bonus  # noqa: E402


def result(document_id: str, title: str, page: str, text: str) -> SearchResult:
    return SearchResult(
        chunk_id=f"{document_id}_{page}",
        text=text,
        metadata={
            "document_id": document_id,
            "title": title,
            "page": page,
            "source_group": "shopee_policy",
        },
    )


class QueryAwareHeuristicTests(unittest.TestCase):
    def test_transaction_fee_query_prioritizes_its_specialized_guide(self) -> None:
        query = "Tôi muốn biết các kênh dùng để xem khoản Shopee khấu trừ ở một giao dịch."
        fee_guide = result(
            "SHP_FEE_004",
            "Phi xu ly giao dich 2026",
            "1",
            "Phí Xử Lý Giao Dịch = (...) *6%",
        )
        unrelated_policy = result(
            "SHP_POL_006",
            "Dieu khoan dich vu",
            "1",
            "Quy định chung của nền tảng.",
        )

        self.assertGreater(
            query_aware_bonus(query, fee_guide),
            query_aware_bonus(query, unrelated_policy),
        )

    def test_listing_rule_query_prioritizes_listing_policy(self) -> None:
        query = "Người nào phải tuân theo các nguyên tắc đăng sản phẩm của Shopee?"
        listing_policy = result(
            "SHP_POL_007",
            "Quy dinh dang ban san pham",
            "1",
            "Quy định này áp dụng đối với tất cả Người Bán.",
        )
        unrelated_policy = result(
            "SHP_POL_005",
            "Quy che hoat dong",
            "1",
            "Quy định chung.",
        )

        self.assertGreater(
            query_aware_bonus(query, listing_policy),
            query_aware_bonus(query, unrelated_policy),
        )

    def test_buyer_refund_window_prioritizes_the_direct_page(self) -> None:
        query = "Người mua có thể bắt đầu yêu cầu hoàn tiền trong thời hạn nào?"
        direct_page = result(
            "SHP_RET_003",
            "Quy trinh tra hang hoan tien nguoi ban",
            "1",
            "Người mua có thể nhấn yêu cầu Trả hàng/Hoàn tiền trong vòng 15 ngày kể từ khi đơn giao thành công.",
        )
        later_page = result(
            "SHP_RET_003",
            "Quy trinh tra hang hoan tien nguoi ban",
            "4",
            "Thời gian hiển thị nút khiếu nại trong vòng 2 ngày.",
        )

        self.assertGreater(
            query_aware_bonus(query, direct_page),
            query_aware_bonus(query, later_page),
        )


if __name__ == "__main__":
    unittest.main()
