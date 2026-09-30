from __future__ import annotations

from dataclasses import asdict
from time import perf_counter
from typing import Any

from .calculator_tool import CalculatorTool
from .planner import AgentPlan, Planner, normalize
from .rag_tool import RAGTool
from .shop_data_tool import ShopDataTool


class AgentRunner:
    """Run a transparent, read-only multi-tool agent over available shop data.

    This baseline deliberately returns evidence and deterministic calculations
    instead of asking an LLM to invent tool calls. The serialized trace supports
    later agent evaluation and a defense demonstration.
    """

    def __init__(
        self,
        planner: Planner | None = None,
        shop_data_tool: ShopDataTool | None = None,
        calculator_tool: CalculatorTool | None = None,
        rag_tool: RAGTool | None = None,
    ) -> None:
        self.planner = planner or Planner()
        self.shop_data_tool = shop_data_tool or ShopDataTool()
        self.calculator_tool = calculator_tool or CalculatorTool()
        self.rag_tool = rag_tool or RAGTool()

    def run(self, question: str) -> dict[str, Any]:
        started = perf_counter()
        plan = self.planner.plan(question)
        normalized = normalize(question)
        trace: list[dict[str, Any]] = []
        sales: dict[str, Any] | None = None
        inventory: dict[str, Any] | None = None
        advertising: dict[str, Any] | None = None
        profitability: dict[str, Any] | None = None
        returns: dict[str, Any] | None = None
        reviews: dict[str, Any] | None = None
        procurement: dict[str, Any] | None = None
        operating_costs: dict[str, Any] | None = None
        inventory_movements: dict[str, Any] | None = None
        quality: dict[str, Any] | None = None
        cash_flow: dict[str, Any] | None = None
        suppliers: dict[str, Any] | None = None
        customer_retention: dict[str, Any] | None = None
        product_funnel: dict[str, Any] | None = None
        product_gmv_ranking: dict[str, Any] | None = None
        product_contribution_ranking: dict[str, Any] | None = None
        sales_period_comparison: dict[str, Any] | None = None
        ranking: dict[str, Any] | None = None
        rag_result: dict[str, Any] | None = None
        slow_inventory: dict[str, Any] | None = None

        # Route action questions by their decision need, rather than by one
        # exact keyword. This keeps new phrasings on the same evidence path.
        definition_like = any(
            term in normalized
            for term in ("la gi", "nghia la gi", "giai thich", "co phai", "tinh nhu the nao")
        )
        asks_price_strategy = (
            any(term in normalized for term in ("giam gia", "dieu chinh gia", "gia ban"))
            and any(term in normalized for term in ("nen", "co nen", "the nao", "toan bo"))
        )
        asks_restock_strategy = any(
            term in normalized
            for term in ("nhap bao nhieu", "nhap nhieu hon", "nhap them", "nhap hang")
        )
        asks_inventory = not definition_like and any(
            term in normalized
            for term in ("ton kho", "sap het", "ton lau", "it ban", "nhap them", "nhap bao nhieu", "nhap nhieu hon")
        )
        asks_product_demand = any(
            term in normalized
            for term in ("san pham nao ban tot", "san pham ban tot", "nhap nhieu hon")
        )
        asks_slow_inventory = not definition_like and any(term in normalized for term in ("ton lau", "it ban", "cham ban"))
        asks_ad_strategy = (
            any(term in normalized for term in ("tang ngan sach", "ngan sach quang cao", "chi quang cao"))
            and any(term in normalized for term in ("nen", "co nen", "hieu qua", "tang"))
        )

        if "shop_data" in plan.tools:
            try:
                focused_operational_terms = (
                    "ton kho", "hang hoan", "hoan hang", "ly do hoan",
                    "danh gia", "phan hoi", "review", "nhap hang", "nha cung cap", "don nhap",
                    "chi phi van hanh", "dong goi", "nhan su", "kho bai", "van chuyen phat sinh",
                    "bien dong kho", "that thoat", "hang hu", "hang loi", "hang loi/huy",
                    "kiem tra chat luong", "chat luong lo hang", "ty le loi", "lo hang",
                    "dong tien", "tien vao", "tien ra", "nha cung cap tot", "giao hang dung hen",
                    "khach quay lai", "khach hang than thiet", "khach trung thanh",
                    "luot xem", "them gio hang", "hieu qua san pham", "phieu san pham",
                    "san pham nao", "mat hang nao", "gmv cao nhat", "thang truoc",
                )
                asks_product_gmv = (
                    "gmv" in normalized
                    and any(term in normalized for term in ("san pham nao", "mat hang nao", "cao nhat"))
                )
                asks_period_comparison = (
                    "so sanh" in normalized
                    and any(term in normalized for term in ("doanh thu", "gmv", "thang truoc"))
                )
                asks_product_contribution = (
                    "lai gop" in normalized
                    and any(term in normalized for term in ("san pham nao", "mat hang nao", "thap nhat", "thap"))
                )
                if asks_product_contribution:
                    product_contribution_ranking = self.shop_data_tool.product_contribution_ranking(plan.period)
                    trace.append({"tool": "shop_data", "status": "ok", "result": product_contribution_ranking})
                elif asks_product_gmv:
                    product_gmv_ranking = self.shop_data_tool.product_gmv_ranking(plan.period)
                    trace.append({"tool": "shop_data", "status": "ok", "result": product_gmv_ranking})
                elif asks_period_comparison:
                    sales_period_comparison = self.shop_data_tool.sales_period_comparison(plan.period)
                    trace.append({"tool": "shop_data", "status": "ok", "result": sales_period_comparison})
                elif asks_inventory:
                    inventory = self.shop_data_tool.inventory_alerts()
                    trace.append({"tool": "shop_data", "status": "ok", "result": inventory})
                elif not any(term in normalized for term in focused_operational_terms):
                    sales = self.shop_data_tool.sales_summary(plan.period)
                    trace.append({"tool": "shop_data", "status": "ok", "result": sales})

                if any(term in normalized for term in ("quang cao", "roas", "ads")):
                    advertising = self.shop_data_tool.advertising_summary(plan.period)
                    trace.append({"tool": "shop_data", "status": "ok", "result": advertising})
                if asks_product_demand and product_gmv_ranking is None:
                    product_gmv_ranking = self.shop_data_tool.product_gmv_ranking(plan.period)
                    trace.append({"tool": "shop_data", "status": "ok", "result": product_gmv_ranking})
                if asks_slow_inventory:
                    slow_inventory = self.shop_data_tool.inventory_slow_products(plan.period)
                    trace.append({"tool": "shop_data", "status": "ok", "result": slow_inventory})
                if (asks_price_strategy or asks_ad_strategy) and profitability is None:
                    profitability = self.shop_data_tool.profitability_summary(plan.period)
                    trace.append({"tool": "shop_data", "status": "ok", "result": profitability})
                if (
                    any(term in normalized for term in ("loi nhuan", "lo von", "gia von", "lai gop"))
                    and not asks_product_contribution
                ):
                    profitability = self.shop_data_tool.profitability_summary(plan.period)
                    trace.append({"tool": "shop_data", "status": "ok", "result": profitability})
                if any(term in normalized for term in ("hang hoan", "hoan hang", "ly do hoan")):
                    returns = self.shop_data_tool.returns_summary(plan.period)
                    trace.append({"tool": "shop_data", "status": "ok", "result": returns})
                if any(term in normalized for term in ("danh gia", "phan hoi", "review")):
                    reviews = self.shop_data_tool.review_summary(plan.period)
                    trace.append({"tool": "shop_data", "status": "ok", "result": reviews})
                supplier_comparison_terms = ("nha cung cap tot", "nha cung cap nao", "giao hang dung hen")
                if any(term in normalized for term in ("nhap hang", "nha cung cap", "don nhap")) and "hop dong" not in normalized and not any(
                    term in normalized for term in supplier_comparison_terms
                ):
                    procurement = self.shop_data_tool.procurement_summary(plan.period)
                    trace.append({"tool": "shop_data", "status": "ok", "result": procurement})
                if any(term in normalized for term in ("chi phi van hanh", "dong goi", "nhan su", "kho bai", "van chuyen phat sinh")):
                    operating_costs = self.shop_data_tool.operating_cost_summary(plan.period)
                    trace.append({"tool": "shop_data", "status": "ok", "result": operating_costs})
                if any(term in normalized for term in ("bien dong kho", "that thoat", "hang hu", "hang loi", "hang loi/huy")):
                    inventory_movements = self.shop_data_tool.inventory_movement_summary(plan.period)
                    trace.append({"tool": "shop_data", "status": "ok", "result": inventory_movements})
                if any(term in normalized for term in ("kiem tra chat luong", "chat luong lo hang", "ty le loi", "lo hang", "hang loi")):
                    quality = self.shop_data_tool.quality_summary(plan.period)
                    trace.append({"tool": "shop_data", "status": "ok", "result": quality})
                if any(term in normalized for term in ("dong tien", "tien vao", "tien ra")):
                    cash_flow = self.shop_data_tool.cash_flow_summary(plan.period)
                    trace.append({"tool": "shop_data", "status": "ok", "result": cash_flow})
                if any(term in normalized for term in ("nha cung cap tot", "giao hang dung hen", "nha cung cap nao")):
                    suppliers = self.shop_data_tool.supplier_performance_summary(plan.period)
                    trace.append({"tool": "shop_data", "status": "ok", "result": suppliers})
                if any(term in normalized for term in ("khach quay lai", "khach hang than thiet", "khach trung thanh")):
                    customer_retention = self.shop_data_tool.customer_retention_summary(plan.period)
                    trace.append({"tool": "shop_data", "status": "ok", "result": customer_retention})
                if any(term in normalized for term in ("luot xem", "them gio hang", "hieu qua san pham", "phieu san pham")):
                    product_funnel = self.shop_data_tool.product_funnel_summary(plan.period)
                    trace.append({"tool": "shop_data", "status": "ok", "result": product_funnel})
            except Exception as exc:  # Keep an inspectable failure in the agent trace.
                trace.append({"tool": "shop_data", "status": "error", "error": str(exc)})

        if "rag" in plan.tools:
            try:
                rag_result = self.rag_tool.search(question)
                trace.append({"tool": "rag", "status": "ok", "result": rag_result})
            except Exception as exc:
                trace.append({"tool": "rag", "status": "error", "error": str(exc)})

        if "calculator" in plan.tools:
            if sales:
                cost_inputs = {
                    "seller_discount": sales["seller_discount_vnd"],
                    "estimated_transaction_fee": sales["estimated_transaction_fee_vnd"],
                    "estimated_service_fee": sales["estimated_service_fee_vnd"],
                }
                if advertising:
                    cost_inputs["advertising_spend"] = advertising["ad_spend_vnd"]
                ranking = self.calculator_tool.rank_costs(cost_inputs)
                trace.append({"tool": "calculator", "status": "ok", "result": ranking})
            else:
                trace.append(
                    {
                        "tool": "calculator",
                        "status": "skipped",
                        "reason": "No numerical shop-data result is available for calculation.",
                    }
                )

        citations = self._citations(rag_result)
        answer = self._compose_answer(
            question=question,
            plan=plan,
            sales=sales,
            inventory=inventory,
            advertising=advertising,
            profitability=profitability,
            returns=returns,
            reviews=reviews,
            procurement=procurement,
            operating_costs=operating_costs,
            inventory_movements=inventory_movements,
            quality=quality,
            cash_flow=cash_flow,
            suppliers=suppliers,
            customer_retention=customer_retention,
            product_funnel=product_funnel,
            product_gmv_ranking=product_gmv_ranking,
            product_contribution_ranking=product_contribution_ranking,
            sales_period_comparison=sales_period_comparison,
            ranking=ranking,
            citations=citations,
            asks_price_strategy=asks_price_strategy,
            asks_restock_strategy=asks_restock_strategy,
            asks_ad_strategy=asks_ad_strategy,
            slow_inventory=slow_inventory,
        )
        data_scope = self.shop_data_tool.data_scope
        data_limitation = (
            "Shop operational values come from CSV files uploaded in the current "
            "session and are not connected to a real Shopee shop."
            if data_scope == "uploaded_csv"
            else (
                "Shop operational values come only from data/shop_mock and are not "
                "connected to a real Shopee shop."
            )
        )
        return {
            "question": question,
            "plan": asdict(plan),
            "answer": answer,
            "citations": citations,
            "data_source": (
                data_scope if "shop_data" in plan.tools else None
            ),
            "trace": trace,
            "agent_latency_seconds": round(perf_counter() - started, 6),
            "limitations": [
                data_limitation,
                "RAG evidence is retrieved text; a policy conclusion still requires evidence review and, when appropriate, LLM synthesis constrained by those sources.",
            ],
        }

    @staticmethod
    def _citations(rag_result: dict[str, Any] | None) -> list[dict[str, str]]:
        if not rag_result:
            return []
        citations: list[dict[str, str]] = []
        seen: set[tuple[str, str]] = set()
        for evidence in rag_result.get("evidence", []):
            title = str(evidence.get("title", "Tài liệu chưa xác định"))
            page = str(evidence.get("page", ""))
            key = (title, page)
            if key in seen:
                continue
            seen.add(key)
            citations.append(
                {
                    "document_id": str(evidence.get("document_id", "")),
                    "title": title,
                    "page": page,
                    "excerpt": str(evidence.get("excerpt", "")),
                }
            )
        return citations[:3]

    @staticmethod
    def _compose_answer(
        question: str,
        plan: AgentPlan,
        sales: dict[str, Any] | None,
        inventory: dict[str, Any] | None,
        advertising: dict[str, Any] | None,
        profitability: dict[str, Any] | None,
        returns: dict[str, Any] | None,
        reviews: dict[str, Any] | None,
        procurement: dict[str, Any] | None,
        operating_costs: dict[str, Any] | None,
        inventory_movements: dict[str, Any] | None,
        quality: dict[str, Any] | None,
        cash_flow: dict[str, Any] | None,
        suppliers: dict[str, Any] | None,
        customer_retention: dict[str, Any] | None,
        product_funnel: dict[str, Any] | None,
        product_gmv_ranking: dict[str, Any] | None,
        product_contribution_ranking: dict[str, Any] | None,
        sales_period_comparison: dict[str, Any] | None,
        ranking: dict[str, Any] | None,
        citations: list[dict[str, str]],
        asks_price_strategy: bool = False,
        asks_restock_strategy: bool = False,
        asks_ad_strategy: bool = False,
        slow_inventory: dict[str, Any] | None = None,
    ) -> str:
        if plan.intent == "out_of_scope":
            return (
                "Câu hỏi này nằm ngoài phạm vi Agent hiện tại. Agent chỉ hỗ trợ "
                "chính sách Shopee có nguồn và dữ liệu vận hành mô phỏng của shop."
            )
        sections: list[str] = []
        knowledge_answer = AgentRunner._knowledge_answer(question)
        action_answer = AgentRunner._action_answer(
            question=question,
            normalized=normalize(question),
            inventory=inventory,
            product_gmv_ranking=product_gmv_ranking,
            profitability=profitability,
            advertising=advertising,
            asks_price_strategy=asks_price_strategy,
            asks_restock_strategy=asks_restock_strategy,
            asks_ad_strategy=asks_ad_strategy,
        )
        # Put the direct answer or bounded next step first; supporting metrics follow.
        if action_answer and not knowledge_answer:
            sections.append(action_answer)
        if product_gmv_ranking:
            top_product = product_gmv_ranking["top_product"]
            if top_product is None:
                sections.append("Chưa có đơn hoàn tất trong kỳ được hỏi nên chưa thể xếp hạng GMV theo sản phẩm.")
            else:
                sections.append(
                    "Sản phẩm có GMV cao nhất là **{name}**: **{gmv:,} VND** từ {orders} đơn hoàn tất, "
                    "tổng {units} sản phẩm. {limitation}".format(
                        name=top_product["product_name"],
                        gmv=int(top_product["gmv_vnd"]),
                        orders=top_product["completed_order_count"],
                        units=top_product["completed_unit_count"],
                        limitation=str(product_gmv_ranking["limitation"]),
                    )
                )
        if product_contribution_ranking:
            lowest_product = product_contribution_ranking["lowest_product"]
            if lowest_product is None:
                sections.append("Chưa có đơn hoàn tất trong kỳ được hỏi nên chưa thể tính lãi góp theo từng sản phẩm.")
            else:
                per_unit = int(lowest_product["estimated_contribution_per_unit_vnd"])
                total = int(lowest_product["estimated_contribution_vnd"])
                margin = lowest_product["contribution_margin_percent"]
                label = "lỗ góp" if total < 0 else "lãi góp"
                margin_text = "chưa tính được tỷ lệ" if margin is None else f"biên lãi góp {margin:.2f}%"
                sections.append(
                    "Sản phẩm có **{label} thấp nhất** là **{name}**: {total:,} VND trong {orders} đơn hoàn tất "
                    "({units} sản phẩm), tương đương {per_unit:,} VND mỗi sản phẩm; {margin_text}. {limitation}".format(
                        label=label, name=lowest_product["product_name"], total=abs(total),
                        orders=lowest_product["completed_order_count"], units=lowest_product["completed_unit_count"],
                        per_unit=abs(per_unit), margin_text=margin_text,
                        limitation=str(product_contribution_ranking["limitation"]),
                    )
                )
        if sales_period_comparison:
            current = sales_period_comparison["current"]
            previous = sales_period_comparison["previous"]
            if current is None or previous is None:
                sections.append("Cần ít nhất hai tháng có đơn hoàn tất để so sánh doanh thu.")
            else:
                change = sales_period_comparison["gmv_change_percent"]
                direction = "tăng" if change is not None and change >= 0 else "giảm"
                change_text = "không tính được tỷ lệ" if change is None else f"{direction} {abs(change):.2f}%"
                sections.append(
                    "So với **{previous_period}**, tháng **{current_period}** có GMV **{current_gmv:,} VND** "
                    "so với **{previous_gmv:,} VND** ({change_text}). Doanh thu sau phí ước tính là "
                    "**{current_net:,} VND** so với **{previous_net:,} VND**. {limitation}".format(
                        previous_period=previous["period"], current_period=current["period"],
                        current_gmv=int(current["gmv_vnd"]), previous_gmv=int(previous["gmv_vnd"]),
                        change_text=change_text,
                        current_net=int(current["net_revenue_after_estimated_fees_vnd"]),
                        previous_net=int(previous["net_revenue_after_estimated_fees_vnd"]),
                        limitation=str(sales_period_comparison["limitation"]),
                    )
                )
        if sales:
            sections.append(
                "Trong kỳ {period}, có {orders} đơn hoàn tất, GMV {gmv:,} VND và doanh thu sau các khoản phí ước tính là {net:,} VND.".format(
                    period=(
                        "toàn bộ kỳ có trong dữ liệu"
                        if sales["period"] == "all_available_periods"
                        else sales["period"]
                    ),
                    orders=sales["completed_order_count"],
                    gmv=int(sales["gross_merchandise_value_vnd"]),
                    net=int(sales["net_revenue_after_estimated_fees_vnd"]),
                )
            )
        if advertising and advertising["campaign_count"]:
            sections.append(
                "Quảng cáo trong kỳ chi {spend:,} VND, doanh thu quy gán {revenue:,} VND, ROAS {roas:.2f}.".format(
                    spend=int(advertising["ad_spend_vnd"]),
                    revenue=int(advertising["attributed_revenue_vnd"]),
                    roas=float(advertising["roas"]),
                )
            )
        elif advertising:
            sections.append(
                "Không tìm thấy bản ghi quảng cáo cho kỳ {period} trong ads.csv, "
                "nên Agent không suy diễn chi phí hoặc ROAS.".format(
                    period=(
                        "được hỏi"
                        if advertising["period"] == "all_available_periods"
                        else advertising["period"]
                    )
                )
            )
        if profitability:
            contribution = int(profitability["estimated_contribution_vnd"])
            label = "lãi góp ước tính" if contribution >= 0 else "lỗ góp ước tính"
            sections.append(
                "Sau giá vốn và các phí sàn đã ghi nhận, {label} là {amount:,} VND. {limitation}".format(
                    label=label,
                    amount=abs(contribution),
                    limitation=str(profitability["limitation"]),
                )
            )
        if operating_costs:
            total = int(operating_costs["total_operating_cost_vnd"])
            largest = next(iter(operating_costs["by_category"]), "chưa phân loại")
            sections.append(
                "Chi phí vận hành đã ghi nhận là {total:,} VND; khoản lớn nhất là {largest}. {limitation}".format(
                    total=total, largest=largest, limitation=str(operating_costs["limitation"])
                )
            )
            if profitability:
                after_overhead = int(profitability["estimated_contribution_vnd"]) - total
                label = "kết quả sau chi phí vận hành đã nhập" if after_overhead >= 0 else "lỗ ước tính sau chi phí vận hành đã nhập"
                sections.append(f"{label.capitalize()} là {abs(after_overhead):,} VND; đây chưa phải lợi nhuận ròng đã quyết toán.")
        if returns:
            if returns["return_request_count"]:
                main_reason = next(iter(returns["reasons"]), "chưa phân loại")
                sections.append(
                    "Có {count} yêu cầu hoàn, tổng tiền hoàn đã ghi nhận {refund:,} VND; lý do xuất hiện nhiều nhất là {reason}.".format(
                        count=returns["return_request_count"],
                        refund=int(returns["recorded_refund_amount_vnd"]),
                        reason=main_reason,
                    )
                )
            else:
                sections.append("Chưa có bản ghi hoàn hàng trong kỳ được hỏi.")
        if reviews:
            if reviews["review_count"]:
                sections.append(
                    "Có {count} đánh giá, điểm trung bình {rating:.2f}/5 và {low} đánh giá từ 3 sao trở xuống. Vấn đề cần xem trước: {issue}.".format(
                        count=reviews["review_count"],
                        rating=float(reviews["average_rating"]),
                        low=reviews["low_rating_count"],
                        issue=next(iter(reviews["issues"]), "chưa phân loại"),
                    )
                )
            else:
                sections.append("Chưa có đánh giá khách hàng trong kỳ được hỏi.")
        if procurement:
            sections.append(
                "Có {count} đơn nhập; {open_count} đơn còn mở với {units} sản phẩm dự kiến về, trị giá nhập ước tính {value:,} VND.".format(
                    count=procurement["purchase_order_count"],
                    open_count=procurement["open_purchase_order_count"],
                    units=procurement["open_unit_count"],
                    value=int(procurement["open_purchase_value_vnd"]),
                )
            )
        if inventory_movements:
            sections.append(
                "Biến động kho đã ghi nhận: nhập {inbound} sản phẩm, bán ra {outbound} sản phẩm và tách {damaged} sản phẩm lỗi/hủy. {limitation}".format(
                    inbound=inventory_movements["inbound_unit_count"],
                    outbound=inventory_movements["outbound_unit_count"],
                    damaged=inventory_movements["damaged_unit_count"],
                    limitation=str(inventory_movements["limitation"]),
                )
            )
        if quality:
            if quality["check_count"]:
                defect_rate = quality["defect_rate_percent"]
                issue = next(iter(quality["defects"]), "chưa phân loại")
                sections.append(
                    "Đã kiểm tra {inspected} sản phẩm ở {checks} lô; phát hiện {defective} sản phẩm lỗi ({rate}%). Dạng lỗi cần xem trước: {issue}. {limitation}".format(
                        inspected=quality["inspected_unit_count"], checks=quality["check_count"],
                        defective=quality["defective_unit_count"], rate="—" if defect_rate is None else f"{defect_rate:.2f}",
                        issue=issue, limitation=str(quality["limitation"]),
                    )
                )
            else:
                sections.append("Chưa có bảng kiểm tra chất lượng trong kỳ được hỏi.")
        if cash_flow:
            movement = int(cash_flow["net_cash_movement_vnd"])
            label = "dòng tiền tăng ròng" if movement >= 0 else "dòng tiền giảm ròng"
            sections.append(
                "Trong kỳ, tiền thu đã ghi nhận là {inflow:,} VND, tiền chi là {outflow:,} VND; {label} {amount:,} VND. {limitation}".format(
                    inflow=int(cash_flow["inflow_vnd"]), outflow=int(cash_flow["outflow_vnd"]),
                    label=label, amount=abs(movement), limitation=str(cash_flow["limitation"]),
                )
            )
        if suppliers:
            best = suppliers["best_supplier"]
            slowest = suppliers["slowest_supplier"]
            if best and slowest:
                sections.append(
                    "Trong {count} nguồn đã ghi, {best} có tỷ lệ giao đúng hẹn {best_rate:.1f}% và lỗi {best_defect:.1f}%; nguồn có thời gian giao lâu nhất là {slowest} ({days:.1f} ngày). {limitation}".format(
                        count=suppliers["supplier_count"], best=best["supplier_name"],
                        best_rate=best["on_time_delivery_rate_percent"], best_defect=best["defect_rate_percent"],
                        slowest=slowest["supplier_name"], days=slowest["average_lead_time_days"],
                        limitation=str(suppliers["limitation"]),
                    )
                )
            else:
                sections.append("Chưa có dữ liệu hiệu quả nhà cung cấp trong kỳ được hỏi.")
        if customer_retention:
            rate = customer_retention["repeat_order_rate_percent"]
            sections.append(
                "Có {customers} khách trong bảng tổng hợp, gồm {returning} khách quay lại; đơn mua lại chiếm {rate}%. {limitation}".format(
                    customers=customer_retention["customer_count"], returning=customer_retention["returning_customer_count"],
                    rate="—" if rate is None else f"{rate:.2f}", limitation=str(customer_retention["limitation"]),
                )
            )
        if product_funnel:
            weak = product_funnel["weak_product"]
            if weak:
                sections.append(
                    "Có {products} sản phẩm trong phễu. Sản phẩm cần kiểm tra trước là {name}: {views} lượt xem, {carts} lượt thêm giỏ và tỷ lệ từ giỏ sang đơn {rate:.2f}%. {limitation}".format(
                        products=product_funnel["product_count"], name=weak["product_name"], views=weak["views"],
                        carts=weak["add_to_cart_count"], rate=weak["cart_to_order_rate_percent"] or 0,
                        limitation=str(product_funnel["limitation"]),
                    )
                )
            else:
                sections.append("Chưa có đủ lượt xem để đánh giá phễu sản phẩm trong kỳ được hỏi.")
        if ranking and ranking["cost_ranking"]:
            highest = ranking["cost_ranking"][0]
            sections.append(
                "Trong các khoản được xếp hạng, lớn nhất là {name} ({amount:,} VND, {share:.1%}).".format(
                    name=str(highest["name"]).replace("_", " "),
                    amount=int(highest["amount_vnd"]),
                    share=float(highest["share_of_ranked_costs"]),
                )
            )
        if inventory:
            if inventory["alert_count"]:
                products = ", ".join(
                    f"{item['product_name']} (còn {item['available_units']})"
                    for item in inventory["alerts"]
                )
                sections.append(f"Có {inventory['alert_count']} cảnh báo tồn kho: {products}.")
            else:
                sections.append("Không có cảnh báo tồn kho theo ngưỡng đã cấu hình.")
        if slow_inventory:
            candidates = slow_inventory.get("candidates", [])
            if candidates:
                labels = ", ".join(
                    f"{item['product_name']} (đã bán {item['sold_units']}, còn {item['available_units']})"
                    for item in candidates[:5]
                )
                sections.append(
                    f"Nhóm cần kiểm tra vì bán chậm so với tồn hiện có: {labels}. "
                    f"{slow_inventory['limitation']} Hãy tạo hoặc tải thêm bảng **Biến động kho** nếu muốn tính chính xác số ngày tồn."
                )
            else:
                sections.append("Chưa có đủ dữ liệu đơn hoàn tất và tồn kho để nhận diện hàng bán chậm.")
        if knowledge_answer and not sections:
            sections.append(knowledge_answer)
        elif citations and not sections:
            sections.append(
                "Tôi chưa có đủ nội dung đã kiểm chứng để trả lời trực tiếp. "
                "Bạn có thể mở phần nguồn nếu cần đối chiếu."
            )
        elif plan.needs_private_shop_data and not sections:
            sections.append(AgentRunner._data_request_guidance(normalize(question)))
        elif "rag" in plan.tools and not sections:
            sections.append("Chưa truy hồi được nội dung đủ tin cậy để trả lời trực tiếp.")
        return "\n\n".join(sections)

    @staticmethod
    def _action_answer(
        question: str,
        normalized: str,
        inventory: dict[str, Any] | None,
        product_gmv_ranking: dict[str, Any] | None,
        profitability: dict[str, Any] | None,
        advertising: dict[str, Any] | None,
        asks_price_strategy: bool,
        asks_restock_strategy: bool,
        asks_ad_strategy: bool,
    ) -> str:
        """Give a bounded next step for recommendation questions.

        Metrics remain separate from advice. The advice never promises a result;
        it names the evidence used and the smallest reversible test.
        """
        if asks_price_strategy:
            if profitability is None:
                return AgentRunner._data_request_guidance(normalized)
            return (
                "Chưa có cơ sở để giảm giá toàn bộ sản phẩm. Hãy chọn 1–2 SKU có lãi góp dương, "
                "thử ưu đãi nhỏ trong thời gian ngắn, rồi so sánh số đơn, doanh thu sau phí và lãi góp "
                "với kỳ trước; nếu biên lãi không chịu được thì dừng thử nghiệm."
            )
        if asks_restock_strategy:
            alert_text = ""
            if inventory and inventory.get("alert_count"):
                names = ", ".join(item["product_name"] for item in inventory["alerts"][:3])
                alert_text = f"Hiện có cảnh báo cần xem trước: {names}. "
            return (
                f"{alert_text}Không nên nhập nhiều chỉ vì một sản phẩm bán tốt. "
                "Hãy đối chiếu tốc độ bán, tồn khả dụng, hàng đang về, thời gian nhập và tiền mặt; "
                "sau đó thử một lô nhỏ. Dữ liệu hiện tại chưa đủ để khẳng định một số lượng nhập an toàn. "
                "Muốn tính số lượng cụ thể, hãy tạo hoặc tải thêm bảng **Đơn nhập hàng** có ngày dự kiến về và giá nhập."
            )
        if asks_ad_strategy:
            if advertising is None:
                return AgentRunner._data_request_guidance(normalized)
            roas = float(advertising.get("roas") or 0)
            return (
                f"ROAS hiện ghi nhận là {roas:.2f}, nhưng ROAS cao chưa đủ để kết luận nên tăng ngân sách "
                "vì còn giá vốn, phí và tồn kho. Nếu vẫn muốn thử, chỉ tăng từng bước nhỏ trong một nhóm quảng cáo, "
                "đặt giới hạn chi và so sánh lãi góp sau quảng cáo trước khi mở rộng."
            )
        return ""

    @staticmethod
    def _data_request_guidance(normalized: str) -> str:
        """Turn missing evidence into an explicit upload/create instruction."""
        if any(term in normalized for term in ("quang cao", "roas", "ngan sach")):
            return "Để trả lời bằng số liệu, hãy tạo hoặc tải bảng **Quảng cáo**; nên có thêm **Sản phẩm** và **Đơn hàng** để kiểm tra lãi sau quảng cáo."
        if any(term in normalized for term in ("ton kho", "sap het", "ton lau", "nhap hang", "nhap them")):
            return "Để phân tích, hãy tạo hoặc tải bảng **Tồn kho**, **Sản phẩm** và **Đơn hàng**; nếu hỏi lượng nhập, thêm **Đơn nhập hàng** và thời gian giao dự kiến."
        if any(term in normalized for term in ("giam gia", "gia ban", "lai", "loi nhuan")):
            return "Để đánh giá phương án, hãy tạo hoặc tải bảng **Sản phẩm và giá vốn**, **Đơn hàng** và **Tồn kho**."
        return "Để trả lời câu hỏi này bằng tình hình shop, hãy tạo hoặc tải bộ dữ liệu gồm **Đơn hàng**, **Sản phẩm** và **Tồn kho**."

    @staticmethod
    def _knowledge_answer(question: str) -> str:
        """Give short answers only for source-backed common concepts."""
        normalized_question = normalize(question)
        if "sku" in normalized_question:
            if "vi du" in normalized_question:
                return (
                    "**Ví dụ SKU:** một áo thun cùng mẫu nhưng khác màu và size cần mã khác nhau: "
                    "`AO-THUN-DEN-M`, `AO-THUN-DEN-L`, `AO-THUN-TRANG-M`. Khi bán một áo đen size M, "
                    "hệ thống chỉ trừ tồn của đúng biến thể đó; áo đen size L vẫn còn nguyên."
                )
            return (
                "**SKU là mã riêng để nhận diện từng sản phẩm hoặc từng biến thể trong shop.** "
                "SKU không nhất thiết là mã vạch của nhà sản xuất; đây là mã shop dùng để quản lý cho nhất quán.\n\n"
                "**Vì sao mỗi biến thể cần SKU riêng?** Màu, size hoặc phiên bản có tồn kho, giá vốn, đơn hoàn và hiệu quả bán khác nhau. "
                "Dùng chung một SKU sẽ khiến shop trừ nhầm tồn hoặc không biết biến thể nào đang bán tốt.\n\n"
                "**Ví dụ:** áo thun đen size M có mã `AO-THUN-DEN-M`; áo thun đen size L có mã `AO-THUN-DEN-L`. "
                "Khách mua size M thì chỉ tồn kho size M giảm, còn size L không thay đổi."
            )
        if "nguong nhap them" in normalized_question:
            return (
                "**Ngưỡng nhập thêm** là mốc tồn khả dụng mà shop đặt ra để bắt đầu kiểm tra việc nhập hàng. "
                "Đây là cảnh báo nội bộ, không phải lệnh bắt buộc phải nhập. Có thể đặt mốc dựa trên tốc độ bán, "
                "thời gian chờ hàng về và lượng tồn an toàn."
            )
        if any(term in normalized_question for term in ("doanh thu sau phi", "doanh thu thuc nhan", "tien nhan duoc")):
            return (
                "**Doanh thu sau phí ước tính** = **GMV − giảm giá người bán − phí giao dịch − phí dịch vụ**. "
                "Ví dụ: GMV 1.000.000 đ, giảm giá 50.000 đ, phí giao dịch 30.000 đ và phí dịch vụ 20.000 đ "
                "→ còn **900.000 đ**. Con số này chưa trừ giá vốn, quảng cáo, đóng gói, nhân sự, thuế hay các chi phí chưa ghi nhận; vì vậy chưa phải lợi nhuận ròng."
            )
        if any(term in normalized_question for term in ("don bi huy", "don huy", "don da huy")):
            return (
                "Không. Trong Eslabong, doanh thu và GMV chỉ tính các đơn có trạng thái **hoàn tất**. "
                "Đơn bị hủy không được cộng vào doanh thu; cần đối chiếu trạng thái đơn và khoản hoàn tiền riêng nếu có."
            )
        if "phi co dinh" in normalized_question:
            return (
                "Phí cố định được tính bằng (giá sản phẩm trước Shopee trợ giá − "
                "khuyến mãi người bán áp dụng) × tỷ lệ phí cố định theo ngành hàng. "
                "Khoản này đã gồm thuế GTGT và được cấn trừ trên từng đơn trước khi "
                "Shopee chuyển tiền thanh toán cho người bán."
            )
        if "phi xu ly giao dich" in normalized_question:
            return (
                "Phí xử lý giao dịch được tính trên giá sản phẩm trước Shopee trợ giá "
                "+ phí vận chuyển người mua trả − khuyến mãi người bán − khuyến mãi "
                "ngân hàng (nếu có), rồi nhân với mức phí xử lý giao dịch."
            )
        if "hoan tien" in normalized_question or "tra hang" in normalized_question:
            return (
                "Người mua có thể yêu cầu trả hàng/hoàn tiền theo Chính sách Trả hàng "
                "và Hoàn tiền của Shopee. Nguồn truy hồi nêu việc hoàn tiền khi người "
                "bán xác nhận đã nhận hàng hoàn trả hoặc khi người mua chấp nhận đề xuất "
                "hoàn tiền không cần trả hàng."
            )
        if "hop dong" in normalized_question:
            return (
                "Một hợp đồng mua hàng nên làm rõ chủ thể, hàng hóa, chất lượng, số lượng, "
                "giá, giao hàng, thanh toán, đổi trả, chứng từ và cách xử lý tranh chấp. "
                "Đây là hướng dẫn nghiệp vụ; hợp đồng có rủi ro cao cần được chuyên gia pháp lý rà soát."
            )
        if "giao dich dien tu" in normalized_question:
            return (
                "Lịch sử giao dịch điện tử cần được lưu theo cách có thể kiểm tra. Giá trị pháp lý "
                "của từng giao dịch phụ thuộc điều kiện luật định và tình huống cụ thể, nên Eslabong "
                "không tự phán quyết hiệu lực hợp đồng."
            )
        definitions = {
            "gmv": "GMV là tổng giá trị hàng hóa đã bán trong các đơn được tính, trước khi trừ giảm giá của shop, phí sàn, giá vốn và các chi phí khác. Ví dụ bán 2 sản phẩm giá 250.000 đ thì GMV là 500.000 đ. Vì còn các khoản phải trừ, GMV không phải lợi nhuận.",
            "roas": "ROAS = doanh thu được quy gán cho quảng cáo chia cho chi quảng cáo. Ví dụ chi 1.000.000 đ và tạo 4.000.000 đ doanh thu quy gán thì ROAS = 4,0. ROAS cao chưa chắc có lãi vì còn giá vốn và phí.",
            "gia von": "Giá vốn là chi phí trực tiếp để có sản phẩm sẵn sàng bán. Với dữ liệu shop, nhập tại **Thư viện dữ liệu → Sản phẩm và giá vốn**. Cần có giá vốn thì mới ước lượng được biên lợi nhuận gộp.",
            "hoa von": "Điểm hòa vốn là mức bán đủ bù chi phí. Đây là ước tính kế hoạch, không phải cam kết kết quả thực tế.",
            "ton kho an toan": "Tồn kho an toàn là lượng dự phòng để giảm nguy cơ hết hàng khi nhu cầu hoặc thời gian nhập thay đổi.",
            "dat hang lai": "Điểm đặt hàng lại có thể ước tính từ tốc độ bán, thời gian chờ nhập và tồn kho an toàn.",
            "hang cham ban": "Hàng chậm bán cần được kiểm tra về ảnh, mô tả, giá, đánh giá và nhu cầu trước khi giảm giá mạnh.",
            "mo shop": "Khi mới mở shop, nên bắt đầu bằng ngành hàng, nguồn hàng, giá vốn và một số SKU có thể quản lý được. Mục tiêu đầu tiên là tạo dữ liệu thật để học, không phải hứa doanh số.",
            "dong tien": "Dòng tiền khác doanh thu: cần xem thời điểm nhập hàng, chi quảng cáo, phí, hoàn tiền và thời điểm nhận thanh toán.",
            "doi soat": "Đối soát là so sánh đơn hoàn tất, hoàn tiền, phí, khuyến mãi, quảng cáo và khoản tiền nhận được trong cùng kỳ. Thiếu báo cáo nào thì chưa thể gọi kết quả là lợi nhuận cuối cùng.",
            "nha cung cap": "Trước khi đặt số lượng lớn, nên xác nhận mẫu, tiêu chuẩn hàng, giá, thời gian giao, đổi hàng lỗi và chứng từ bằng kênh có thể truy vết.",
            "hang cam": "Với hàng cấm hoặc hạn chế, cần đối chiếu danh mục Shopee và quy định hiện hành trước khi đăng. Eslabong không tự cấp phép hoặc kết luận một mặt hàng được bán.",
            "hang han che": "Với hàng cấm hoặc hạn chế, cần đối chiếu danh mục Shopee và quy định hiện hành trước khi đăng. Eslabong không tự cấp phép hoặc kết luận một mặt hàng được bán.",
            "du lieu khach hang": "Chỉ nên thu thập dữ liệu cần thiết để xử lý đơn và hỗ trợ khách, nêu rõ mục đích sử dụng và hạn chế chia sẻ. Không tải dữ liệu khách hàng lên bản demo công khai.",
            "bao mat tai khoan": "Không chia sẻ mật khẩu, mã xác thực hoặc khóa API trong chat hay file demo. Kết nối thật cần cơ chế cấp quyền hợp lệ và lưu bí mật an toàn.",
            "chi phi quang cao": "Không. Chi phí quảng cáo chỉ là một khoản. Shop còn có thể có giá vốn, phí sàn, đóng gói, nhân sự, kho bãi, vận chuyển và thuế. Muốn tính kết quả sau chi phí, cần xem từng khoản đã được ghi trong dữ liệu.",
        }
        for term, answer in definitions.items():
            if term in normalized_question:
                return answer
        return ""
