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


def product_opportunities() -> list[dict[str, object]]:
    """Rank category opportunities by a balanced, explicitly simulated model.

    The score intentionally rewards the *combination* of demand and revenue.
    A cheap product with volume alone, or an expensive product with too few
    orders, cannot dominate the list merely because of one dimension.
    """
    raw: list[dict[str, float | str]] = []
    for item in market_categories():
        category_id = str(item["id"])
        references = reference_listings(category_id)
        rng = random.Random(f"market-opportunity:{category_id}")
        units = rng.randint(280, 6200)
        average_price = float(median([float(row["listed_price_vnd"]) for row in references]))
        revenue = int(units * average_price)
        average_rating = sum(float(row["rating"]) for row in references) / len(references)
        raw.append(
            {
                "category_id": category_id,
                "category": str(item["category"]),
                "lead_product": str(item["product_examples"][0]),
                "units_sold_estimate": float(units),
                "estimated_revenue_vnd": float(revenue),
                "price_fit_score": float(rng.randint(62, 96)),
                "positive_review_score": round(min(98.0, average_rating / 5 * 100), 1),
                "longevity_score": float(rng.randint(58, 95)),
            }
        )

    max_units = max(float(row["units_sold_estimate"]) for row in raw)
    max_revenue = max(float(row["estimated_revenue_vnd"]) for row in raw)
    results: list[dict[str, object]] = []
    for row in raw:
        volume = float(row["units_sold_estimate"]) / max_units * 100
        revenue = float(row["estimated_revenue_vnd"]) / max_revenue * 100
        balance = min(volume, revenue)
        score = (
            balance * 0.30
            + ((volume + revenue) / 2) * 0.15
            + float(row["price_fit_score"]) * 0.20
            + float(row["positive_review_score"]) * 0.20
            + float(row["longevity_score"]) * 0.15
        )
        results.append(
            {
                **row,
                "volume_score": round(volume, 1),
                "revenue_score": round(revenue, 1),
                "balance_score": round(balance, 1),
                "opportunity_score": round(score, 1),
            }
        )
    results.sort(key=lambda item: float(item["opportunity_score"]), reverse=True)
    for rank, item in enumerate(results, start=1):
        item["rank"] = rank
    return results


SIMILAR_SHOPS_PER_CATEGORY = 7


def simulated_marketplace(category_id: str, scenario_seed: int = 0) -> dict[str, list[dict[str, object]]]:
    """Create a consistent mixed catalogue for one realistic demo market.

    It contains one clearly labelled randomly generated seller demo and exactly
    seven comparable shops. Across 50 categories this models 350 competitor-shop
    profiles; only the selected category is generated for the screen at a time.
    Products are intentionally interleaved so the UI compares one market rather
    than isolated examples.
    """
    _id, _lead, category, _cost, anchor_price, _aliases = _category_seed(category_id)
    catalogue = next(item for item in market_categories() if item["id"] == category_id)
    products = [str(name) for name in catalogue["product_examples"]]
    market_rng = random.Random(f"market-scenario:{category_id}:{scenario_seed}")
    reference_count = SIMILAR_SHOPS_PER_CATEGORY
    size_pool = ["Shop nhỏ", "Shop nhỏ", "Shop vừa", "Shop vừa", "Shop vừa", "Shop lớn", "Shop lớn", "Shop dẫn đầu"]
    market_rng.shuffle(size_pool)
    profiles: list[tuple[str, str, float]] = [
        ("Shop của bạn · Demo", "Shop của bạn", round(market_rng.uniform(0.78, 1.22), 2))
    ]
    for index, shop_type in enumerate(size_pool[:reference_count], start=1):
        label = shop_type.replace("Shop ", "")
        profiles.append((f"Shop tương tự {index} · {label}", shop_type, round(market_rng.uniform(0.68, 1.38), 2)))
    listings: list[dict[str, object]] = []
    shops: list[dict[str, object]] = []
    for shop_index, (shop_name, shop_type, price_factor) in enumerate(profiles):
        rng = random.Random(f"marketplace:{category_id}:{scenario_seed}:{shop_index}")
        listing_count = 5 + ((shop_index * 3 + len(category_id)) % 8)
        shop_units = 0
        shop_gmv = 0
        rating = round(min(4.95, 4.12 + shop_index * 0.065 + rng.uniform(-0.09, 0.14)), 2)
        reviews = int((shop_index + 1) ** 2 * rng.randint(45, 115))
        for product_index in range(listing_count):
            product_name = products[product_index % len(products)]
            price = int(round(anchor_price * price_factor * (0.82 + (product_index % 5) * 0.09) / 1000) * 1000)
            units = int((shop_index + 2) * rng.randint(18, 72))
            gmv = price * units
            shop_units += units
            shop_gmv += gmv
            listings.append(
                {
                    "shop_name": shop_name,
                    "shop_type": shop_type,
                    "product_name": product_name,
                    "listed_price_vnd": price,
                    "units_sold_12m": units,
                    "gmv_12m_vnd": gmv,
                    "rating": rating,
                    "review_count": max(8, reviews // listing_count),
                    "data_scope": "Dữ liệu shop của bạn (demo)" if shop_index == 0 else "Shop tương tự (demo)",
                }
            )
        shops.append(
            {
                "shop_name": shop_name,
                "shop_type": shop_type,
                "listing_count": listing_count,
                "units_sold_12m": shop_units,
                "gmv_12m_vnd": shop_gmv,
                "average_price_vnd": round(shop_gmv / shop_units),
                "rating": rating,
                "review_count": reviews,
                "positive_review_score": round(rating / 5 * 100, 1),
                "longevity_score": min(96, 48 + shop_index * 5 + rng.randint(0, 10)),
                "data_scope": "Dữ liệu shop của bạn (demo)" if shop_index == 0 else "Shop tương tự (demo)",
            }
        )

    max_units = max(int(shop["units_sold_12m"]) for shop in shops)
    max_gmv = max(int(shop["gmv_12m_vnd"]) for shop in shops)
    for shop in shops:
        volume = int(shop["units_sold_12m"]) / max_units * 100
        revenue = int(shop["gmv_12m_vnd"]) / max_gmv * 100
        score = min(volume, revenue) * 0.45 + (volume + revenue) / 2 * 0.20 + float(shop["positive_review_score"]) * 0.20 + float(shop["longevity_score"]) * 0.15
        shop["shop_score"] = round(score, 1)
    max_listing_units = max(int(row["units_sold_12m"]) for row in listings)
    max_listing_gmv = max(int(row["gmv_12m_vnd"]) for row in listings)
    for row in listings:
        volume = int(row["units_sold_12m"]) / max_listing_units * 100
        revenue = int(row["gmv_12m_vnd"]) / max_listing_gmv * 100
        review = float(row["rating"]) / 5 * 100
        row["product_score"] = round(min(volume, revenue) * 0.50 + (volume + revenue) / 2 * 0.20 + review * 0.30, 1)
    listings.sort(key=lambda row: (str(row["product_name"]), -float(row["product_score"])))
    shops.sort(key=lambda row: float(row["shop_score"]), reverse=True)
    return {"shops": shops, "listings": listings, "category": category, "reference_count": reference_count}


def source_status() -> list[Mapping[str, str]]:
    """Expose connector readiness without implying any live integration."""
    return list(SOURCE_STATUS)
