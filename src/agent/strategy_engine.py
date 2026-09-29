"""Decision-support calculations for the seller strategy workspace.

All outputs are scenario estimates over the transparent market-demo dataset.
They are designed to help users choose a small experiment, not to promise a
real business outcome.
"""

from __future__ import annotations

from typing import Any

from .market_intelligence import market_categories, product_opportunities, simulated_marketplace
from .strategy_evidence import DEMO_EVIDENCE_LABEL, DEMO_EVIDENCE_SCORE, safe_language_policy


def opportunity_radar() -> list[dict[str, object]]:
    """Return plain-language opportunity signals for all demo categories."""
    results: list[dict[str, object]] = []
    for item in product_opportunities():
        score = float(item["opportunity_score"])
        if score >= 80:
            recommendation = "Có thể thử quy mô nhỏ"
        elif score >= 68:
            recommendation = "Theo dõi và kiểm chứng trước"
        else:
            recommendation = "Chưa nên ưu tiên vốn"
        results.append({**item, "recommendation": recommendation})
    return results


def simulate_strategy(
    category_id: str,
    scenario_seed: int,
    price_change_percent: int,
    use_bundle: bool,
    ad_budget_change_percent: int,
    restock_units: int,
) -> dict[str, object]:
    """Estimate the relative effect of one controlled shop experiment."""
    market = simulated_marketplace(category_id, scenario_seed)
    shops = list(market["shops"])
    own_shop = next(item for item in shops if item["shop_type"] == "Shop của bạn")
    listings = [item for item in market["listings"] if item["shop_type"] == "Shop của bạn"]
    strongest = max(listings, key=lambda item: float(item["product_score"]))
    category = next(item for item in market_categories() if str(item["id"]) == category_id)

    baseline_gmv = float(own_shop["gmv_12m_vnd"])
    baseline_units = int(own_shop["units_sold_12m"])
    price_factor = 1 + price_change_percent / 100
    # A bounded demand reaction keeps the demonstration interpretable rather
    # than presenting a falsely precise forecasting model.
    demand_factor = max(0.72, min(1.28, 1 - price_change_percent * 0.012))
    bundle_factor = 1.08 if use_bundle else 1.0
    ad_factor = 1 + min(0.12, max(0, ad_budget_change_percent) * 0.0024)
    inventory_factor = 1 + min(0.10, restock_units / max(1, baseline_units) * 0.8)
    estimated_units = int(round(baseline_units * demand_factor * bundle_factor * ad_factor * inventory_factor))
    estimated_gmv = int(round(baseline_gmv * price_factor * demand_factor * bundle_factor * ad_factor * inventory_factor))
    gmv_change_percent = (estimated_gmv / baseline_gmv - 1) * 100 if baseline_gmv else 0.0

    if price_change_percent <= -10 and not use_bundle:
        risk = "Cao: giảm giá mạnh có thể làm doanh thu tăng nhưng làm biên lợi nhuận xấu đi."
    elif ad_budget_change_percent >= 40 and not use_bundle:
        risk = "Trung bình: chỉ tăng quảng cáo khi trang sản phẩm và tồn kho đã sẵn sàng."
    elif restock_units == 0:
        risk = "Trung bình: chưa có hàng bổ sung; cần kiểm tra tồn kho trước khi đẩy nhu cầu."
    else:
        risk = "Có kiểm soát: phù hợp để thử trong quy mô nhỏ rồi đo kết quả."

    action = (
        f"Thử với **{strongest['product_name']}** trong 14 ngày, đặt ngưỡng dừng trước khi chạy: "
        "GMV, lợi nhuận sau phí và số review tích cực phải tốt hơn kỳ đối chứng."
    )
    return {
        "category": str(category["category"]),
        "category_id": category_id,
        "lead_product": str(strongest["product_name"]),
        "baseline_gmv_vnd": int(round(baseline_gmv)),
        "baseline_units": baseline_units,
        "estimated_gmv_vnd": estimated_gmv,
        "estimated_units": estimated_units,
        "gmv_change_percent": round(gmv_change_percent, 1),
        "price_change_percent": price_change_percent,
        "use_bundle": use_bundle,
        "ad_budget_change_percent": ad_budget_change_percent,
        "restock_units": restock_units,
        "risk": risk,
        "action": action,
        "evidence_score": DEMO_EVIDENCE_SCORE,
        "evidence_label": DEMO_EVIDENCE_LABEL,
        "language_policy": safe_language_policy(DEMO_EVIDENCE_SCORE),
        "requires_human_approval": True,
        "stop_conditions": [
            "Dừng nếu lợi nhuận sau phí không đạt ngưỡng người dùng đặt ra.",
            "Dừng nếu tồn kho xuống dưới mức an toàn hoặc phản hồi tiêu cực tăng.",
            "Không mở rộng ngân sách hay nhập hàng chỉ từ một kỳ quan sát.",
        ],
    }


def action_plan(simulation: dict[str, object]) -> list[dict[str, str]]:
    """Turn a simulation into a small, measurable four-week plan."""
    bundle_step = "Tạo combo nhỏ cho sản phẩm mũi nhọn" if simulation["use_bundle"] else "Hoàn thiện ảnh, mô tả và ưu đãi của sản phẩm mũi nhọn"
    ad_step = (
        f"Tăng ngân sách quảng cáo tối đa {simulation['ad_budget_change_percent']}% theo kịch bản"
        if int(simulation["ad_budget_change_percent"]) > 0
        else "Chạy thử không tăng ngân sách quảng cáo"
    )
    return [
        {"Tuần": "Tuần 1", "Việc cần làm": f"Chuẩn bị {simulation['lead_product']}: {bundle_step.lower()}.", "Chỉ số kiểm tra": "Lượt xem, thêm giỏ, tồn kho"},
        {"Tuần": "Tuần 2", "Việc cần làm": f"Chạy thử giá {simulation['price_change_percent']:+d}% và {ad_step.lower()}.", "Chỉ số kiểm tra": "Đơn hoàn tất, GMV, chi phí"},
        {"Tuần": "Tuần 3", "Việc cần làm": "So sánh với tuần trước; giữ hoặc dừng phương án nếu không đạt ngưỡng.", "Chỉ số kiểm tra": "Lợi nhuận sau phí, review tích cực"},
        {"Tuần": "Tuần 4", "Việc cần làm": "Ghi kết quả, quyết định mở rộng hay thử phương án khác.", "Chỉ số kiểm tra": "GMV, lợi nhuận, tỷ lệ mua lại"},
    ]
