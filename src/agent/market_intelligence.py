"""Transparent market-intelligence demo data and deterministic analysis.

This module is intentionally a *market snapshot simulator*.  It never claims
to know a real competitor's sales, inventory, or private advertising outcome.
The UI can later replace these functions with permitted API connectors while
keeping the same output contract.
"""

from __future__ import annotations

import random
from statistics import median
from typing import Iterable, Mapping

from .shop_data_library import DEMO_CATEGORY_SEEDS, demo_catalog


MARKET_SNAPSHOT_DATE = "2026-09-28"
MARKET_REFERENCE_COUNT = 8
SOURCE_STATUS = (
    {
        "source": "Snapshot thị trường demo",
        "status": "Đang dùng",
        "detail": "Dữ liệu mô phỏng, có thể lặp lại khi trình bày bảo vệ.",
    },
    {
        "source": "YouTube Data API",
        "status": "Chưa kết nối",
        "detail": "Cần API key và chính sách làm mới dữ liệu.",
    },
    {
        "source": "Facebook / Instagram",
        "status": "Chưa kết nối",
        "detail": "Cần ứng dụng Meta, quyền phù hợp và quy trình xét duyệt.",
    },
    {
        "source": "TikTok",
        "status": "Chưa kết nối",
        "detail": "Cần quyền truy cập hợp lệ theo loại API và khu vực dữ liệu.",
    },
)

_SHOP_DESCRIPTORS = (
    "Giá cạnh tranh",
    "Nhiều phân loại",
    "Combo phụ kiện",
    "Đánh giá tích cực",
    "Mô tả sản phẩm rõ",
    "Giao hàng nhanh",
    "Quà tặng kèm",
    "Bảo hành minh bạch",
)
_PRICE_FACTORS = (0.67, 0.76, 0.84, 0.93, 1.03, 1.13, 1.26, 1.42)


def _category_seed(category_id: str) -> tuple[str, str, str, int, int, str]:
    for seed in DEMO_CATEGORY_SEEDS:
        if seed[0] == category_id:
            return seed
    raise KeyError(f"Không có loại shop market demo: {category_id}")


def market_categories() -> list[dict[str, object]]:
    """Return the same 50 categories used by the learner demo catalogue."""
    return demo_catalog()


def reference_listings(category_id: str) -> list[dict[str, object]]:
    """Generate reproducible, explicitly simulated public-market signals."""
    _id, lead_product, category, _cost, anchor_price, _aliases = _category_seed(category_id)
    catalogue = next(item for item in market_categories() if item["id"] == category_id)
    product_examples = tuple(str(name) for name in catalogue["product_examples"])
    rng = random.Random(f"market-demo:{category_id}")
    rows: list[dict[str, object]] = []
    for index, factor in enumerate(_PRICE_FACTORS, start=1):
        price = int(round(anchor_price * factor * rng.uniform(0.97, 1.03) / 1000) * 1000)
        rating = round(4.25 + rng.uniform(0.08, 0.69), 2)
        reviews = rng.randint(80, 2800)
        descriptor = _SHOP_DESCRIPTORS[(index + len(category_id)) % len(_SHOP_DESCRIPTORS)]
        rows.append(
            {
                "shop_name": f"Shop tham chiếu {index}",
                "product_name": product_examples[(index - 1) % len(product_examples)],
                "category": category,
                "listed_price_vnd": price,
                "rating": min(rating, 4.94),
                "review_count": reviews,
                "observed_signal": descriptor,
                "source_mode": "Mô phỏng",
            }
        )
    return rows


def _currency_band(value: float) -> int:
    return int(round(value / 1000) * 1000)


def price_comparison(
    category_id: str, own_prices: Iterable[float] | None = None
) -> dict[str, object]:
    """Compare a shop's catalogue price with the market-demo reference band."""
    references = reference_listings(category_id)
    prices = sorted(float(row["listed_price_vnd"]) for row in references)
    lower = _currency_band(prices[1])
    typical = _currency_band(float(median(prices)))
    upper = _currency_band(prices[-2])
    usable_own_prices = [float(price) for price in (own_prices or ()) if float(price) > 0]
    own_price = _currency_band(float(median(usable_own_prices))) if usable_own_prices else None

    if own_price is None:
        position = "Chưa có giá shop để đối chiếu"
        interpretation = (
            "Hãy dùng dữ liệu Chủ shop hoặc thêm giá niêm yết sản phẩm để AI đặt giá của bạn vào dải tham chiếu."
        )
    elif own_price < lower:
        position = "Thấp hơn dải tham chiếu"
        interpretation = (
            "Giá thấp có thể hỗ trợ thử nghiệm nhu cầu, nhưng cần kiểm tra lại biên lợi nhuận và lý do khách hàng tin tưởng sản phẩm."
        )
    elif own_price > upper:
        position = "Cao hơn dải tham chiếu"
        interpretation = (
            "Giá cao chỉ hợp lý khi có bằng chứng về khác biệt như bundle, bảo hành, chất lượng nội dung hoặc trải nghiệm giao hàng."
        )
    else:
        position = "Nằm trong dải giá tham chiếu"
        interpretation = (
            "Giá đang gần mặt bằng; ưu tiên so sánh bundle, đánh giá và cách trình bày sản phẩm thay vì giảm giá ngay."
        )

    return {
        "category_id": category_id,
        "snapshot_date": MARKET_SNAPSHOT_DATE,
        "reference_count": len(references),
        "lower_price_vnd": lower,
        "typical_price_vnd": typical,
        "upper_price_vnd": upper,
        "own_price_vnd": own_price,
        "position": position,
        "interpretation": interpretation,
        "references": references,
    }


def trend_brief(category_id: str) -> list[dict[str, str]]:
    """Return transparent trend-demo prompts, not claimed live social signals."""
    catalogue = next(item for item in market_categories() if item["id"] == category_id)
    category = str(catalogue["category"])
    examples = tuple(str(name) for name in catalogue["product_examples"])
    return [
        {
            "headline": f"Combo cho {category.lower()}",
            "signal": "Tín hiệu mô phỏng: tăng",
            "detail": f"Thử ghép {examples[0]} với một sản phẩm bổ trợ để kiểm tra khả năng tăng giá trị mỗi đơn.",
            "action": "Tạo một bundle nhỏ, theo dõi GMV và lợi nhuận trong 2–4 tuần.",
        },
        {
            "headline": "Nội dung giải đáp trước khi mua",
            "signal": "Tín hiệu mô phỏng: cần kiểm chứng",
            "detail": f"Làm video/ngắn hoặc ảnh giải đáp chất liệu, kích thước, cách dùng cho {examples[1]}.",
            "action": "Đo số lượt xem trang và tỷ lệ thêm vào giỏ trước/sau khi cập nhật nội dung.",
        },
        {
            "headline": "Sản phẩm mũi nhọn",
            "signal": "Tín hiệu mô phỏng: thử nghiệm",
            "detail": f"Chọn {examples[2]} làm sản phẩm mồi, sau đó gợi ý sản phẩm liên quan trong cùng danh mục.",
            "action": "Chỉ nhập thêm khi số đơn và lợi nhuận của thử nghiệm đạt ngưỡng bạn đặt ra.",
        },
    ]


def source_status() -> list[Mapping[str, str]]:
    """Expose connector readiness without implying any live integration."""
    return list(SOURCE_STATUS)
