"""Decision-support calculations for the seller strategy workspace.

All outputs are scenario estimates over the transparent market-demo dataset.
They are designed to help users choose a small experiment, not to promise a
real business outcome.
"""

from __future__ import annotations

import random
from math import ceil
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


def inventory_risk_analysis(
    category_id: str,
    scenario_seed: int,
    target_stock_months: float = 2.0,
) -> dict[str, object]:
    """Create transparent demo signals for capital, stock age, and replenishment.

    The current project does not have a live Shopee connector or purchase
    invoices.  Cost, stock age, and repeat-purchase signals are therefore
    deliberately *scenario data*, not claimed as real shop facts.  The output
    is still useful for demonstrating the decision flow a real connector would
    support: stop buying slow stock, check possible losses, and buy small when
    a healthy product is near stock-out.
    """
    market = simulated_marketplace(category_id, scenario_seed)
    category = next(item for item in market_categories() if str(item["id"]) == category_id)
    own_listings = [item for item in market["listings"] if item["shop_type"] == "Shop của bạn"]
    rows: list[dict[str, object]] = []

    for position, listing in enumerate(own_listings):
        price = int(round(float(listing["listed_price_vnd"])))
        sold_per_month = max(1.0, float(listing["units_sold_12m"]) / 12)
        product_score = float(listing["product_score"])
        rng = random.Random(f"inventory-risk:{category_id}:{scenario_seed}:{position}")

        # This deliberately allows a small number of loss-risk examples.  It
        # models purchase cost plus a generic operating-cost reserve, never a
        # precise Shopee fee calculation.
        cost_ratio = 0.58 + ((int(scenario_seed) + position * 17) % 39) / 100
        unit_cost = int(round(price * cost_ratio, -3))
        operating_reserve = int(round(price * 0.12, -3))
        safety_margin = price - unit_cost - operating_reserve
        break_even_price = unit_cost + operating_reserve

        stock_factor = 0.35 + ((int(scenario_seed) * 3 + position * 41) % 450) / 100
        on_hand = max(1, int(round(sold_per_month * stock_factor)))
        stock_cover_months = round(on_hand / sold_per_month, 1)
        activity_signal = (int(scenario_seed) + position * 29) % 100
        if product_score < 58:
            days_since_last_sale = 45 + activity_signal % 70
        else:
            days_since_last_sale = 4 + activity_signal % 42
        capital_in_stock = on_hand * unit_cost
        repeat_signal = (
            "Thấp" if product_score < 58 or days_since_last_sale >= 60
            else "Khá" if product_score >= 76 and days_since_last_sale <= 20
            else "Trung bình"
        )

        recommended_order_qty = 0
        recommended_budget = 0
        if safety_margin <= 0:
            status = "Nguy cơ lỗ vốn — không nhập thêm"
            action = "Dừng nhập; kiểm tra lại giá vốn, giá bán và ưu đãi trước khi tiếp tục."
        elif days_since_last_sale >= 60:
            status = "Tồn lâu — không nhập thêm"
            action = "Ưu tiên xử lý lượng đang có bằng ưu đãi nhỏ hoặc combo; chưa mua lại."
        elif stock_cover_months >= target_stock_months + 1.5:
            status = "Vốn đang bị giữ trong tồn kho"
            action = "Chưa nhập thêm; theo dõi bán ra trước khi mở đơn mới."
        elif stock_cover_months < 0.8 and product_score >= 62:
            recommended_order_qty = max(1, ceil(sold_per_month * target_stock_months - on_hand))
            recommended_budget = recommended_order_qty * unit_cost
            status = "Có thể nhập nhỏ để tránh hết hàng"
            action = "Chỉ nhập mức nhỏ đề xuất, rồi kiểm tra lại tốc độ bán sau 2–4 tuần."
        else:
            status = "Theo dõi thêm trước khi nhập"
            action = "Chưa cần mua thêm; kiểm tra lại khi tốc độ bán hoặc tồn kho thay đổi."

        rows.append({
            "product_name": str(listing["product_name"]),
            "listed_price_vnd": price,
            "unit_cost_demo_vnd": unit_cost,
            "operating_reserve_demo_vnd": operating_reserve,
            "break_even_price_demo_vnd": break_even_price,
            "safety_margin_demo_vnd": safety_margin,
            "monthly_purchases_demo": round(sold_per_month, 1),
            "days_since_last_sale_demo": days_since_last_sale,
            "on_hand_units_demo": on_hand,
            "stock_cover_months_demo": stock_cover_months,
            "capital_in_stock_demo_vnd": capital_in_stock,
            "repeat_purchase_signal_demo": repeat_signal,
            "recommended_order_qty": recommended_order_qty,
            "recommended_order_budget_demo_vnd": recommended_budget,
            "status": status,
            "action": action,
        })

    # Keep every scenario actionable: when random demo factors produce no
    # stock-out, choose the healthiest low-cover item for a deliberately small
    # replenishment example.  It remains a scenario suggestion, never a buy
    # instruction.
    if not any(int(row["recommended_order_qty"]) > 0 for row in rows):
        eligible = [
            row for row in rows
            if int(row["safety_margin_demo_vnd"]) > 0
            and int(row["days_since_last_sale_demo"]) < 60
        ]
        if eligible:
            candidate = min(eligible, key=lambda row: float(row["stock_cover_months_demo"]))
            suggested_units = max(
                1,
                ceil(float(candidate["monthly_purchases_demo"]) * target_stock_months * 0.5),
            )
            candidate["recommended_order_qty"] = suggested_units
            candidate["recommended_order_budget_demo_vnd"] = suggested_units * int(candidate["unit_cost_demo_vnd"])
            candidate["status"] = "Có thể thử nhập nhỏ để kiểm chứng"
            candidate["action"] = "Có thể nhập lô nhỏ để kiểm chứng nhu cầu; không tăng vốn nếu tốc độ bán không cải thiện."

    return {
        "category": str(category["category"]),
        "category_id": category_id,
        "target_stock_months": target_stock_months,
        "rows": rows,
        "evidence_score": DEMO_EVIDENCE_SCORE,
        "evidence_label": DEMO_EVIDENCE_LABEL,
        "language_policy": safe_language_policy(DEMO_EVIDENCE_SCORE),
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
