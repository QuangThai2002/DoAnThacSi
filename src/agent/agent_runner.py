from __future__ import annotations

from dataclasses import asdict
import re
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
        product_scorecard: dict[str, Any] | None = None
        co_purchase: dict[str, Any] | None = None
        price_promotions: dict[str, Any] | None = None
        ads_sku_daily: dict[str, Any] | None = None
        inventory_batches: dict[str, Any] | None = None
        sales_period_comparison: dict[str, Any] | None = None
        ranking: dict[str, Any] | None = None
        rag_result: dict[str, Any] | None = None
        slow_inventory: dict[str, Any] | None = None

        # Interpret the decision need once, then use the same tags for tool
        # selection and answer composition. This avoids one-off fixes for each
        # Vietnamese wording of the same operational question.
        analysis_tags = self._analysis_tags(normalized)
        wants_detail = self._wants_detailed_answer(normalized)
        definition_like = any(
            term in normalized
            for term in ("la gi", "nghia la gi", "giai thich", "co phai", "tinh nhu the nao")
        )
        asks_price_strategy = "price_strategy" in analysis_tags
        asks_restock_strategy = "restock_strategy" in analysis_tags
        asks_inventory = not definition_like and "inventory" in analysis_tags
        asks_product_demand = "product_demand" in analysis_tags
        asks_slow_inventory = not definition_like and "slow_inventory" in analysis_tags
        asks_ad_strategy = "ad_strategy" in analysis_tags

        if "shop_data" in plan.tools:
            try:
                asks_product_gmv = "product_gmv" in analysis_tags
                asks_period_comparison = "sales_comparison" in analysis_tags
                asks_product_contribution = "product_contribution" in analysis_tags
                if asks_product_contribution:
                    product_contribution_ranking = self.shop_data_tool.product_contribution_ranking(plan.period)
                    trace.append({"tool": "shop_data", "status": "ok", "result": product_contribution_ranking})
                if asks_product_gmv:
                    product_gmv_ranking = self.shop_data_tool.product_gmv_ranking(plan.period)
                    trace.append({"tool": "shop_data", "status": "ok", "result": product_gmv_ranking})
                if asks_period_comparison:
                    sales_period_comparison = self.shop_data_tool.sales_period_comparison(plan.period)
                    trace.append({"tool": "shop_data", "status": "ok", "result": sales_period_comparison})
                if asks_inventory:
                    inventory = self.shop_data_tool.inventory_alerts()
                    trace.append({"tool": "shop_data", "status": "ok", "result": inventory})
                if not analysis_tags:
                    sales = self.shop_data_tool.sales_summary(plan.period)
                    trace.append({"tool": "shop_data", "status": "ok", "result": sales})

                if "advertising" in analysis_tags:
                    advertising = self.shop_data_tool.advertising_summary(plan.period)
                    trace.append({"tool": "shop_data", "status": "ok", "result": advertising})
                if "price_promotions" in analysis_tags:
                    price_promotions = self.shop_data_tool.price_promotion_summary(plan.period)
                    trace.append({"tool": "shop_data", "status": "ok", "result": price_promotions})
                if "ads_sku_daily" in analysis_tags:
                    ads_sku_daily = self.shop_data_tool.ads_sku_daily_summary(plan.period)
                    trace.append({"tool": "shop_data", "status": "ok", "result": ads_sku_daily})
                if "inventory_batches" in analysis_tags:
                    inventory_batches = self.shop_data_tool.inventory_batch_age_summary()
                    trace.append({"tool": "shop_data", "status": "ok", "result": inventory_batches})
                if asks_product_demand and product_gmv_ranking is None:
                    product_gmv_ranking = self.shop_data_tool.product_gmv_ranking(plan.period)
                    trace.append({"tool": "shop_data", "status": "ok", "result": product_gmv_ranking})
                if asks_slow_inventory:
                    slow_inventory = self.shop_data_tool.inventory_slow_products(plan.period)
                    trace.append({"tool": "shop_data", "status": "ok", "result": slow_inventory})
                if (asks_price_strategy or asks_ad_strategy or "profitability" in analysis_tags) and profitability is None:
                    profitability = self.shop_data_tool.profitability_summary(plan.period)
                    trace.append({"tool": "shop_data", "status": "ok", "result": profitability})
                if "returns" in analysis_tags:
                    returns = self.shop_data_tool.returns_summary(plan.period)
                    trace.append({"tool": "shop_data", "status": "ok", "result": returns})
                if "reviews" in analysis_tags:
                    reviews = self.shop_data_tool.review_summary(plan.period)
                    trace.append({"tool": "shop_data", "status": "ok", "result": reviews})
                if "procurement" in analysis_tags:
                    procurement = self.shop_data_tool.procurement_summary(plan.period)
                    trace.append({"tool": "shop_data", "status": "ok", "result": procurement})
                if "operating_costs" in analysis_tags:
                    operating_costs = self.shop_data_tool.operating_cost_summary(plan.period)
                    trace.append({"tool": "shop_data", "status": "ok", "result": operating_costs})
                if "inventory_movements" in analysis_tags:
                    inventory_movements = self.shop_data_tool.inventory_movement_summary(plan.period)
                    trace.append({"tool": "shop_data", "status": "ok", "result": inventory_movements})
                if "quality" in analysis_tags:
                    quality = self.shop_data_tool.quality_summary(plan.period)
                    trace.append({"tool": "shop_data", "status": "ok", "result": quality})
                if "cash_flow" in analysis_tags:
                    cash_flow = self.shop_data_tool.cash_flow_summary(plan.period)
                    trace.append({"tool": "shop_data", "status": "ok", "result": cash_flow})
                if "suppliers" in analysis_tags:
                    suppliers = self.shop_data_tool.supplier_performance_summary(plan.period)
                    trace.append({"tool": "shop_data", "status": "ok", "result": suppliers})
                if "customer_retention" in analysis_tags:
                    customer_retention = self.shop_data_tool.customer_retention_summary(plan.period)
                    trace.append({"tool": "shop_data", "status": "ok", "result": customer_retention})
                if "product_funnel" in analysis_tags:
                    product_funnel = self.shop_data_tool.product_funnel_summary(plan.period)
                    trace.append({"tool": "shop_data", "status": "ok", "result": product_funnel})
                if "strategy" in analysis_tags:
                    if product_gmv_ranking is None:
                        product_gmv_ranking = self.shop_data_tool.product_gmv_ranking(plan.period)
                        trace.append({"tool": "shop_data", "status": "ok", "result": product_gmv_ranking})
                    if product_contribution_ranking is None:
                        product_contribution_ranking = self.shop_data_tool.product_contribution_ranking(plan.period)
                        trace.append({"tool": "shop_data", "status": "ok", "result": product_contribution_ranking})
                    if inventory is None:
                        inventory = self.shop_data_tool.inventory_alerts()
                        trace.append({"tool": "shop_data", "status": "ok", "result": inventory})
                    if profitability is None:
                        profitability = self.shop_data_tool.profitability_summary(plan.period)
                        trace.append({"tool": "shop_data", "status": "ok", "result": profitability})
                    product_scorecard = self.shop_data_tool.product_decision_scorecard(plan.period)
                    trace.append({"tool": "shop_data", "status": "ok", "result": product_scorecard})
                    if "combo_strategy" in analysis_tags:
                        co_purchase = self.shop_data_tool.co_purchase_summary(plan.period)
                        trace.append({"tool": "shop_data", "status": "ok", "result": co_purchase})
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
            product_scorecard=product_scorecard,
            co_purchase=co_purchase,
            price_promotions=price_promotions,
            ads_sku_daily=ads_sku_daily,
            inventory_batches=inventory_batches,
            sales_period_comparison=sales_period_comparison,
            ranking=ranking,
            citations=citations,
            asks_price_strategy=asks_price_strategy,
            asks_restock_strategy=asks_restock_strategy,
            asks_ad_strategy=asks_ad_strategy,
            slow_inventory=slow_inventory,
            analysis_tags=analysis_tags,
            wants_detail=wants_detail,
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
            "show_summary_metrics": self._should_show_summary_metrics(analysis_tags),
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
    def _analysis_tags(normalized: str) -> set[str]:
        """Map question meaning to reusable operational analysis topics.

        Tags describe the data and decision being asked about, rather than one
        exact sentence. New phrasings therefore share the same data path and
        safety limits as the tested question bank.
        """
        tags: set[str] = set()
        if "gmv" in normalized and any(term in normalized for term in ("san pham nao", "mat hang nao", "cao nhat")):
            tags.add("product_gmv")
        if "lai gop" in normalized and any(term in normalized for term in ("san pham nao", "mat hang nao", "thap nhat", "thap")):
            tags.add("product_contribution")
        if "so sanh" in normalized and any(term in normalized for term in ("doanh thu", "gmv", "thang truoc")):
            tags.add("sales_comparison")
        if any(term in normalized for term in ("ton kho", "sap het", "ton lau", "it ban", "nhap them", "nhap bao nhieu", "nhap nhieu hon")):
            tags.add("inventory")
        if any(term in normalized for term in ("ton lau", "it ban", "cham ban")):
            tags.add("slow_inventory")
            tags.add("inventory_batches")
        if any(term in normalized for term in ("san pham ban tot", "san pham nao ban tot", "nhap nhieu hon")):
            tags.add("product_demand")
        if any(term in normalized for term in ("quang cao", "roas", "ads")):
            tags.add("advertising")
        if any(term in normalized for term in ("khuyen mai", "ma giam gia", "gia sau khuyen mai", "gia cuoi")):
            tags.add("price_promotions")
        if any(term in normalized for term in ("quang cao theo sku", "quang cao tung san pham", "sku nao nen tang ngan sach")):
            tags.add("ads_sku_daily")
        if any(term in normalized for term in ("tuoi ton", "ton theo lo", "lo hang ton", "lo ton lau")):
            tags.add("inventory_batches")
        if "lo hang" in normalized and any(term in normalized for term in ("ton", "nam lau", "ton lau", "tuoi ton")):
            tags.add("inventory_batch_question")
            tags.add("inventory_batches")
        if any(term in normalized for term in ("giam gia", "dieu chinh gia", "gia ban")) and any(
            term in normalized for term in ("nen", "co nen", "the nao", "toan bo")
        ):
            tags.add("price_strategy")
            tags.add("price_promotions")
        if any(term in normalized for term in ("nhap bao nhieu", "nhap nhieu hon", "nhap them", "nhap hang")):
            tags.add("restock_strategy")
            tags.add("quality")
        if any(term in normalized for term in ("tang ngan sach", "ngan sach quang cao", "chi quang cao")) and any(
            term in normalized for term in ("nen", "co nen", "hieu qua", "tang")
        ):
            tags.add("ad_strategy")
            tags.add("ads_sku_daily")
        if any(term in normalized for term in ("loi nhuan", "lo von", "gia von", "lai sau chi phi van hanh", "nguy co lo")):
            tags.add("profitability")
        if any(term in normalized for term in ("hang hoan", "hoan hang", "ly do hoan")):
            tags.add("returns")
        if any(term in normalized for term in ("danh gia", "review", "phan hoi khach")):
            tags.add("reviews")
        if "danh gia xau" in normalized or "giam danh gia" in normalized or (
            "danh gia" in normalized
            and any(term in normalized for term in ("1-3 sao", "1 3 sao", "xu ly", "van de nao truoc"))
        ):
            tags.add("review_action")
        if any(term in normalized for term in ("nhap hang", "don nhap")):
            tags.add("procurement")
        if any(term in normalized for term in ("chi phi van hanh", "khoan van hanh", "dong goi", "nhan su", "kho bai", "van chuyen phat sinh")):
            tags.add("operating_costs")
        if "khoan van hanh nao" in normalized or "khoan van hanh" in normalized and any(term in normalized for term in ("lon nhat", "cao nhat")):
            tags.add("operating_rank")
        if any(term in normalized for term in ("bien dong kho", "that thoat", "hang hu", "hang loi", "hang loi/huy")):
            tags.add("inventory_movements")
        if any(term in normalized for term in ("kiem tra chat luong", "chat luong lo hang", "ty le loi", "lo hang", "hang loi", "nguon hang nao co ty le loi")):
            tags.add("quality")
        if any(term in normalized for term in ("dong tien", "tien vao", "tien ra", "tien chi", "thieu tien")):
            tags.add("cash_flow")
        if "khoan tien chi" in normalized and any(term in normalized for term in ("lon nhat", "cao nhat")):
            tags.add("cash_rank")
        if "doanh thu tang" in normalized and "thieu tien" in normalized:
            tags.add("cash_explanation")
        if any(term in normalized for term in ("nha cung cap", "nguon hang", "giao hang dung hen")):
            tags.add("suppliers")
        if "phan hoi nha cung cap" in normalized:
            tags.update({"quality", "supplier_action"})
        if "nguon hang nao co ty le loi" in normalized:
            tags.update({"quality", "supplier_defect"})
        if any(term in normalized for term in ("khach quay lai", "khach hang than thiet", "khach trung thanh")):
            tags.add("customer_retention")
        if "lam sao tang khach quay lai" in normalized:
            tags.add("retention_action")
        if any(term in normalized for term in ("luot xem", "them gio", "hieu qua san pham", "phieu san pham", "kho chot don", "dat mua")):
            tags.add("product_funnel")
        if (
            "luot xem" in normalized
            and "them gio" in normalized
            and any(term in normalized for term in ("luot xem cao", "nhieu luot xem", "it them gio", "ty le tu xem sang them gio", "thap nhat"))
        ):
            tags.add("funnel_view_action")
        if "them gio" in normalized and any(term in normalized for term in ("it dat mua", "it dat")):
            tags.add("funnel_cart_action")
        if "that thoat" in normalized:
            tags.add("inventory_shrinkage")
        if "lai sau chi phi van hanh" in normalized:
            tags.update({"profitability", "operating_costs", "profit_after_overhead"})
        if "ty le loi lo hang" in normalized:
            tags.add("quality_rate")
        if any(term in normalized for term in ("30 ngay", "tao combo", "nguy co lo", "tuan nay")):
            tags.add("strategy")
            tags.update({
                "profitability", "operating_costs", "returns", "reviews", "inventory",
                "slow_inventory", "inventory_movements", "quality", "product_funnel",
            })
        if "tao combo" in normalized:
            tags.add("combo_strategy")
        if "nguy co lo" in normalized:
            tags.add("risk_strategy")
        if "tuan nay" in normalized:
            tags.add("weekly_strategy")
        return tags

    @staticmethod
    def _wants_detailed_answer(normalized: str) -> bool:
        """Recognize an explicit request for explanation, not just an answer.

        The default is deliberately concise: state the finding or the missing
        table first.  These phrases opt into the supporting reasoning, examples,
        comparisons, or operational checklist.
        """
        detail_cues = (
            "chi tiet", "cu the", "giai thich", "vi sao", "tai sao",
            "phan tich", "so sanh", "vi du", "lam the nao", "cach tinh",
            "tung buoc", "dieu kien", "neu ro", "ky hon", "the nao",
        )
        return any(cue in normalized for cue in detail_cues)

    @staticmethod
    def _brief_answer(answer: str) -> str:
        """Keep the decisive finding, with enough information to act safely."""
        blocks = [block.strip() for block in answer.split("\n\n") if block.strip()]
        if not blocks:
            return answer

        first = blocks[0]
        # A ranked answer is only useful when its requested rows stay visible.
        if len(blocks) > 1 and re.match(r"(?:1\.|[-*•])\s", blocks[1]):
            return f"{first}\n\n{blocks[1]}"

        # Missing data must always say what the user needs to create or upload.
        sentences = re.split(r"(?<=[.!?])\s+(?=[A-ZÀ-Ỵ])", first)
        first_lower = first.lower()
        if ("chưa thể" in first_lower or "chưa có" in first_lower) and len(sentences) > 1:
            return " ".join(sentences[:2])
        # Never reduce a useful answer to “Có.” or “Không.”, and retain one
        # material caveat such as legal review or an accounting limitation.
        essential_cues = (
            "không phải", "không tự", "không bảo đảm", "không thay thế",
            "chuyên gia pháp lý", "chưa tự suy ra", "không đại diện",
        )
        for sentence in sentences[1:]:
            if any(cue in sentence.lower() for cue in essential_cues):
                return f"{sentences[0]} {sentence}"
        for sentence in sentences[1:]:
            if "bạn hãy tạo hoặc tải" in sentence.lower():
                return f"{sentences[0]} {sentence}"
        if len(sentences[0].strip()) <= 24 and len(sentences) > 1:
            return " ".join(sentences[:2])
        if len(sentences) > 1:
            return sentences[0]
        return first

    @staticmethod
    def _answer_for_detail_level(answer: str, wants_detail: bool) -> str:
        return answer if wants_detail else AgentRunner._brief_answer(answer)

    @staticmethod
    def _should_show_summary_metrics(analysis_tags: set[str]) -> bool:
        """Avoid unrelated dashboard cards below a focused answer.

        A SKU, batch, review, or strategy question already names its key result
        in prose. Aggregate sales/advertising cards below it can look like a
        second, contradictory answer.
        """
        focused_topics = {
            "product_gmv", "product_contribution", "sales_comparison",
            "price_promotions", "ads_sku_daily", "inventory_batches",
            "slow_inventory", "product_funnel", "reviews", "returns",
            "quality", "cash_flow", "suppliers", "customer_retention",
            "strategy", "price_strategy", "restock_strategy", "ad_strategy",
        }
        return not bool(analysis_tags & focused_topics)

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
        product_scorecard: dict[str, Any] | None,
        co_purchase: dict[str, Any] | None,
        price_promotions: dict[str, Any] | None,
        ads_sku_daily: dict[str, Any] | None,
        inventory_batches: dict[str, Any] | None,
        sales_period_comparison: dict[str, Any] | None,
        ranking: dict[str, Any] | None,
        citations: list[dict[str, str]],
        asks_price_strategy: bool = False,
        asks_restock_strategy: bool = False,
        asks_ad_strategy: bool = False,
        slow_inventory: dict[str, Any] | None = None,
        analysis_tags: set[str] | None = None,
        wants_detail: bool = False,
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
            analysis_tags=analysis_tags or set(),
            reviews=reviews,
            quality=quality,
            suppliers=suppliers,
            customer_retention=customer_retention,
            product_funnel=product_funnel,
            operating_costs=operating_costs,
            cash_flow=cash_flow,
            product_contribution_ranking=product_contribution_ranking,
            inventory_movements=inventory_movements,
            returns=returns,
            slow_inventory=slow_inventory,
            product_scorecard=product_scorecard,
            co_purchase=co_purchase,
            price_promotions=price_promotions,
            ads_sku_daily=ads_sku_daily,
            inventory_batches=inventory_batches,
        )
        # Put the direct answer or bounded next step first; supporting metrics follow.
        if action_answer and not knowledge_answer:
            sections.append(action_answer)
        if action_answer and (
            "strategy" in (analysis_tags or set())
            or "slow_inventory" in (analysis_tags or set())
            or asks_price_strategy
            or asks_ad_strategy
        ):
            return AgentRunner._answer_for_detail_level(action_answer, wants_detail)
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
        if ranking and ranking["cost_ranking"]:
            highest = ranking["cost_ranking"][0]
            sections.append(
                "Trong các khoản được xếp hạng, lớn nhất là {name} ({amount:,} VND, {share:.1%}).".format(
                    name=str(highest["name"]).replace("_", " "),
                    amount=int(highest["amount_vnd"]),
                    share=float(highest["share_of_ranked_costs"]),
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
        if advertising and advertising["campaign_count"] and not ads_sku_daily:
            sections.append(
                "Quảng cáo trong kỳ chi {spend:,} VND, doanh thu quy gán {revenue:,} VND từ {orders} đơn quy gán, ROAS {roas:.2f}.".format(
                    spend=int(advertising["ad_spend_vnd"]),
                    revenue=int(advertising["attributed_revenue_vnd"]),
                    orders=int(advertising["attributed_order_count"]),
                    roas=float(advertising["roas"]),
                )
            )
        elif advertising and not ads_sku_daily:
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
        if price_promotions:
            product = price_promotions.get("largest_discount_product")
            if product:
                sections.append(
                    "Giá–khuyến mãi đã ghi của **{name}** có mức giảm bình quân {rate:.2f}%: giá niêm yết bình quân {listed:,} VND, giá cuối bình quân {final:,} VND. {limitation}".format(
                        name=product["product_name"], rate=product["average_discount_percent"] or 0,
                        listed=int(product["average_list_price_vnd"]), final=int(product["average_final_price_vnd"]),
                        limitation=str(price_promotions["limitation"]),
                    )
                )
            else:
                sections.append("Chưa có bản ghi giá và khuyến mãi trong kỳ được hỏi. Hãy tạo hoặc tải bảng **Giá và khuyến mãi theo SKU**.")
        if ads_sku_daily:
            product = ads_sku_daily.get("top_roas_product")
            if product:
                roas_text = "—" if product["roas"] is None else f"{product['roas']:.2f}"
                sections.append(
                    "Theo bảng quảng cáo theo SKU, **{name}** có ROAS đã ghi cao nhất là {roas_text}, chi {spend:,} VND và doanh thu quy gán {revenue:,} VND. {limitation}".format(
                        name=product["product_name"], roas_text=roas_text, spend=int(product["spend_vnd"]),
                        revenue=int(product["attributed_revenue_vnd"]), limitation=str(ads_sku_daily["limitation"]),
                    )
                )
            else:
                sections.append("Chưa có bản ghi quảng cáo theo SKU/ngày trong kỳ được hỏi. Hãy tạo hoặc tải bảng **Quảng cáo theo SKU/ngày**.")
        if inventory_batches:
            batch = inventory_batches.get("oldest_batch")
            if batch:
                sections.append(
                    "Lô tồn lâu nhất đã ghi là **{batch_id}** của **{name}**, nhập ngày {received}, còn {units} sản phẩm và đã nằm {age} ngày. {limitation}".format(
                        batch_id=batch["batch_id"], name=batch["product_name"], received=batch["received_date"],
                        units=batch["available_units"], age=batch["age_days"], limitation=str(inventory_batches["limitation"]),
                    )
                )
            else:
                sections.append("Chưa có dữ liệu tuổi tồn theo lô. Hãy tạo hoặc tải bảng **Tuổi tồn kho theo lô**.")
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
                    "Có {count} yêu cầu hoàn, tương ứng {units} sản phẩm; tổng tiền hoàn đã ghi nhận {refund:,} VND; lý do xuất hiện nhiều nhất là {reason}.".format(
                        count=returns["return_request_count"],
                        units=returns["returned_unit_count"],
                        refund=int(returns["recorded_refund_amount_vnd"]),
                        reason=main_reason,
                    )
                )
            else:
                sections.append("Chưa có bản ghi hoàn hàng trong kỳ được hỏi.")
        if reviews:
            if reviews["review_count"]:
                sections.append(
                    "Có {count} đánh giá, điểm trung bình {rating:.2f}/5 và {low} đánh giá từ 3 sao trở xuống. Vấn đề cần xem trước trong nhóm đánh giá thấp: {issue}.".format(
                        count=reviews["review_count"],
                        rating=float(reviews["average_rating"]),
                        low=reviews["low_rating_count"],
                        issue=reviews.get("priority_low_rating_issue") or "chưa có trường vấn đề để phân loại",
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
            is_view_to_cart_question = "funnel_view_action" in (analysis_tags or set())
            weak = (
                product_funnel["weak_view_to_cart_product"]
                if is_view_to_cart_question
                else product_funnel["weak_product"]
            )
            if weak:
                if is_view_to_cart_question:
                    sections.append(
                        "Trong nhóm có ít nhất {threshold:.0f} lượt xem, {name} cần kiểm tra trước: {views} lượt xem, "
                        "{carts} lượt thêm giỏ và tỷ lệ từ xem sang thêm giỏ {rate:.2f}%. {limitation}".format(
                            threshold=float(product_funnel["high_view_threshold"]), name=weak["product_name"],
                            views=weak["views"], carts=weak["add_to_cart_count"],
                            rate=weak["view_to_cart_rate_percent"] or 0,
                            limitation=str(product_funnel["limitation"]),
                        )
                    )
                else:
                    sections.append(
                        "Có {products} sản phẩm trong phễu. Sản phẩm cần kiểm tra trước là {name}: {views} lượt xem, {carts} lượt thêm giỏ và tỷ lệ từ giỏ sang đơn {rate:.2f}%. {limitation}".format(
                            products=product_funnel["product_count"], name=weak["product_name"], views=weak["views"],
                            carts=weak["add_to_cart_count"], rate=weak["cart_to_order_rate_percent"] or 0,
                            limitation=str(product_funnel["limitation"]),
                        )
                    )
            else:
                sections.append("Chưa có đủ lượt xem để đánh giá phễu sản phẩm trong kỳ được hỏi.")
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
        return AgentRunner._answer_for_detail_level("\n\n".join(sections), wants_detail)

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
        analysis_tags: set[str],
        reviews: dict[str, Any] | None,
        quality: dict[str, Any] | None,
        suppliers: dict[str, Any] | None,
        customer_retention: dict[str, Any] | None,
        product_funnel: dict[str, Any] | None,
        operating_costs: dict[str, Any] | None,
        cash_flow: dict[str, Any] | None,
        product_contribution_ranking: dict[str, Any] | None,
        inventory_movements: dict[str, Any] | None,
        returns: dict[str, Any] | None,
        slow_inventory: dict[str, Any] | None,
        product_scorecard: dict[str, Any] | None,
        co_purchase: dict[str, Any] | None,
        price_promotions: dict[str, Any] | None,
        ads_sku_daily: dict[str, Any] | None,
        inventory_batches: dict[str, Any] | None,
    ) -> str:
        """Give a bounded next step for recommendation questions.

        Metrics remain separate from advice. The advice never promises a result;
        it names the evidence used and the smallest reversible test.
        """
        if asks_price_strategy:
            if profitability is None or price_promotions is None:
                return AgentRunner._data_request_guidance(normalized)
            observed = price_promotions.get("largest_discount_product")
            observation = (
                f" Với **{observed['product_name']}**, mức giảm bình quân đã ghi là {observed['average_discount_percent'] or 0:.2f}% "
                f"(giá cuối bình quân {int(observed['average_final_price_vnd']):,} VND)."
                if observed else ""
            )
            return (
                "Chưa có cơ sở để giảm giá toàn bộ sản phẩm. Hãy chọn 1–2 SKU có lãi góp dương, "
                "thử ưu đãi nhỏ trong thời gian ngắn, rồi so sánh số đơn, doanh thu sau phí và lãi góp "
                "với kỳ trước; nếu biên lãi không chịu được thì dừng thử nghiệm."
                + observation
            )
        if "cash_explanation" in analysis_tags:
            return (
                "Doanh thu tăng vẫn có thể thiếu tiền nhập hàng vì thời điểm thu tiền và thời điểm phải chi không trùng nhau: "
                "tiền có thể đang nằm ở hàng tồn, đơn chưa được thanh toán, phí, hoàn tiền hoặc quảng cáo. "
                "Hãy so sánh lịch tiền thu, tiền chi và các đơn nhập sắp đến theo tuần; chưa thể kết luận nguyên nhân duy nhất chỉ từ doanh thu."
            )
        if asks_restock_strategy:
            alert_text = ""
            if inventory and inventory.get("alert_count"):
                names = ", ".join(item["product_name"] for item in inventory["alerts"][:3])
                alert_text = f" Hiện có cảnh báo cần xem trước: {names}."
            return (
                "Không nên nhập nhiều chỉ vì một sản phẩm bán tốt. "
                "Hãy đối chiếu tốc độ bán, tồn khả dụng, hàng đang về, thời gian nhập, tỷ lệ lỗi và tiền mặt; "
                "sau đó thử một lô nhỏ. Dữ liệu hiện tại chưa đủ để khẳng định một số lượng nhập an toàn. "
                "Muốn tính số lượng cụ thể, hãy tạo hoặc tải thêm bảng **Đơn nhập hàng** có ngày dự kiến về và giá nhập."
                + alert_text
            )
        if asks_ad_strategy:
            if advertising is None or ads_sku_daily is None:
                return AgentRunner._data_request_guidance(normalized)
            roas = float(advertising.get("roas") or 0)
            stock_check = (
                "Hiện có SKU chạm ngưỡng nhập thêm: "
                + ", ".join(item["product_name"] for item in inventory.get("alerts", [])[:3])
                + ". Không nên đẩy quảng cáo cho các SKU này trước khi xác nhận hàng sẵn có. "
                if inventory and inventory.get("alert_count")
                else "Không có SKU nào chạm ngưỡng nhập thêm trong bảng tồn kho hiện tại. "
            )
            return (
                f"ROAS hiện ghi nhận là {roas:.2f}, nhưng ROAS cao chưa đủ để kết luận nên tăng ngân sách "
                "vì còn giá vốn, phí và tồn kho. "
                f"{stock_check}"
                "Trước khi tăng, kiểm tra trang sản phẩm theo 5 điểm: ảnh đầu, giá cuối sau ưu đãi, biến thể còn hàng, đánh giá 1–3 sao và thời gian giao. "
                "Nếu vẫn muốn thử, chỉ tăng từng bước nhỏ trong một nhóm quảng cáo, đặt giới hạn chi và dừng nếu lãi góp sau quảng cáo giảm hoặc tồn khả dụng chạm ngưỡng nhập thêm."
            )
        if "review_action" in analysis_tags:
            if reviews is None or not reviews.get("review_count"):
                return AgentRunner._data_request_guidance(normalized)
            issue = reviews.get("priority_low_rating_issue")
            if issue is None:
                return (
                    "Chưa thể ưu tiên nguyên nhân vì các đánh giá 1–3 sao chưa có trường vấn đề để phân loại. "
                    "Bạn hãy tạo hoặc tải bảng **Đánh giá khách hàng** có các cột: mã đánh giá, ngày đánh giá, SKU, số sao, vấn đề và nhận xét. "
                    "Sau đó AI sẽ xếp hạng nguyên nhân theo số đánh giá thấp thay vì đoán từ điểm trung bình."
                )
            issue_count = int(reviews.get("low_rating_issues", {}).get(issue, 0))
            return (
                f"Ưu tiên xử lý **{issue}** trước vì đây là nhóm xuất hiện nhiều nhất trong các đánh giá 1–3 sao đã phân loại ({issue_count} đánh giá). "
                "Hãy phản hồi các đánh giá liên quan, sửa một nguyên nhân có thể kiểm soát và theo dõi lại hai chỉ số trong kỳ sau: số đánh giá 1–3 sao theo nhóm vấn đề và tỷ lệ đánh giá thấp trên tổng đánh giá. "
                "Nếu còn đánh giá thấp không có vấn đề, hãy bổ sung cột vấn đề thay vì để AI tự đoán nguyên nhân; cách làm này không bảo đảm điểm đánh giá sẽ tăng."
            )
        if "supplier_action" in analysis_tags:
            defective = int(quality.get("defective_unit_count", 0)) if quality else 0
            if defective:
                return (
                    "Nên phản hồi nhà cung cấp bằng dữ liệu đã lưu: ảnh hàng lỗi, mã lô, số lượng kiểm, số lượng lỗi và điều kiện đổi trả đã thỏa thuận. "
                    "Đề nghị hướng xử lý cụ thể trước khi đặt thêm lô lớn; dữ liệu này không tự kết luận trách nhiệm pháp lý của bên nào."
                )
            return AgentRunner._data_request_guidance(normalized)
        if "supplier_defect" in analysis_tags and suppliers:
            rows = suppliers.get("suppliers", [])
            if rows:
                worst = max(rows, key=lambda item: item["defect_rate_percent"])
                return (
                    f"Trong các nguồn đã ghi, **{worst['supplier_name']}** có tỷ lệ lỗi cao nhất: **{worst['defect_rate_percent']:.1f}%**. "
                    "Đây chỉ là so sánh trên lô và đơn đã nhập; hãy kiểm tra thêm số lượng mẫu và điều kiện giao dịch trước khi đổi hoặc dừng nhà cung cấp."
                )
            return AgentRunner._data_request_guidance(normalized)
        if "retention_action" in analysis_tags:
            return (
                "Để tăng khách quay lại, hãy thử một việc nhỏ cho nhóm đã mua: nhắn chăm sóc sau bán, ưu đãi mua lại có thời hạn hoặc combo phù hợp. "
                "Theo dõi riêng tỷ lệ đơn mua lại, đánh giá thấp và chi phí ưu đãi trước khi mở rộng; không có biện pháp nào bảo đảm khách sẽ quay lại."
            )
        if "funnel_view_action" in analysis_tags:
            return (
                "Lượt xem cao nhưng ít thêm giỏ là tín hiệu cần kiểm tra, chưa chứng minh nguyên nhân. Hãy lần lượt thử ảnh đầu, giá hiển thị, mô tả lợi ích, biến thể, đánh giá và phí giao; "
                "mỗi lần chỉ đổi một yếu tố rồi đo tỷ lệ xem sang thêm giỏ."
            )
        if "funnel_cart_action" in analysis_tags:
            return (
                "Nhiều lượt thêm giỏ nhưng ít đặt mua thường cần kiểm tra giá cuối, ưu đãi, tồn khả dụng, thời gian giao, đánh giá và đổi trả. "
                "Hãy thử một thay đổi nhỏ và theo dõi tỷ lệ từ giỏ sang đơn; dữ liệu phễu không cho phép cam kết thay đổi nào sẽ tăng đơn."
            )
        if "inventory_shrinkage" in analysis_tags:
            return (
                "Chưa thể kết luận có thất thoát chỉ từ biến động kho. Hãy kiểm kê thực tế theo SKU và đối chiếu với đơn hoàn tất, hàng lỗi/hủy, phiếu nhập và số hàng giữ chỗ. "
                "Nếu còn chênh lệch sau đối soát, hãy ghi nhận thời điểm và người bàn giao để kiểm tra tiếp."
            )
        if "operating_rank" in analysis_tags and operating_costs:
            category, amount = next(iter(operating_costs.get("by_category", {}).items()), ("chưa phân loại", 0))
            return f"Khoản vận hành đã ghi nhận lớn nhất là **{category}**: **{int(amount):,} VND**. Hãy kiểm tra chứng từ và mức cần thiết của khoản này trước khi cắt giảm."
        if "cash_rank" in analysis_tags and cash_flow:
            category, amount = next(iter(cash_flow.get("outflow_by_category", {}).items()), ("chưa phân loại", 0))
            return f"Khoản tiền chi đã ghi nhận lớn nhất là **{category}**: **{int(amount):,} VND**. Đây là dòng tiền ghi nhận, không tự cho biết khoản đó có hợp lý hay không."
        if "profit_after_overhead" in analysis_tags and profitability and operating_costs:
            value = int(profitability["estimated_contribution_vnd"]) - int(operating_costs["total_operating_cost_vnd"])
            label = "còn lại" if value >= 0 else "lỗ ước tính"
            return f"Sau giá vốn, phí sàn đã ghi nhận và chi phí vận hành đã nhập, kết quả ước tính **{label} {abs(value):,} VND**. Đây chưa phải lợi nhuận ròng quyết toán vì chưa gồm mọi khoản như thuế hoặc chi phí chưa ghi."
        if "quality_rate" in analysis_tags and quality:
            rate = quality.get("defect_rate_percent")
            return "Tỷ lệ lỗi trong các lô đã kiểm là **{}%** ({} lỗi trên {} sản phẩm kiểm). Chỉ số này không đại diện cho những lô chưa kiểm.".format(
                "—" if rate is None else f"{float(rate):.2f}", quality.get("defective_unit_count", 0), quality.get("inspected_unit_count", 0)
            )
        if "inventory_batch_question" in analysis_tags:
            batches = list(inventory_batches.get("batches", [])) if inventory_batches else []
            if not batches:
                return (
                    "Chưa thể nêu **2 lô tồn lâu nhất** vì chat này chưa có bảng **Tuổi tồn kho theo lô**. "
                    "Bạn hãy tạo hoặc tải bảng có: mã lô, SKU, ngày nhập kho, số lượng còn lại và giá vốn đơn vị; "
                    "khi có dữ liệu, AI sẽ xếp đúng hai lô theo số ngày tồn thay vì đoán từ tồn kho chung."
                )
            lines = []
            for index, batch in enumerate(batches[:2], start=1):
                lines.append(
                    f"{index}. **{batch['batch_id']} — {batch['product_name']}**: "
                    f"đã tồn **{batch['age_days']} ngày**, còn **{batch['available_units']}** sản phẩm "
                    f"(nhập ngày {batch['received_date']})."
                )
            return (
                "**Hai lô tồn lâu nhất đã ghi nhận:**\n\n"
                + "\n".join(lines)
                + "\n\n**Cần kiểm tra trước:** đối chiếu tồn thực tế, tình trạng hàng và tốc độ bán của đúng SKU. "
                "Tuổi tồn là tín hiệu ưu tiên kiểm tra, không tự chứng minh cần giảm giá hay xả hàng."
            )
        if "slow_inventory" in analysis_tags and "strategy" not in analysis_tags:
            batch = inventory_batches.get("oldest_batch") if inventory_batches else None
            batch_text = (
                f" Lô nằm lâu nhất đã ghi là {batch['batch_id']} ({batch['product_name']}), còn {batch['available_units']} sản phẩm sau {batch['age_days']} ngày."
                if batch else ""
            )
            slow_rows = slow_inventory.get("candidates", []) if slow_inventory else []
            lead = (
                "Cần kiểm tra trước: "
                + ", ".join(
                    f"**{row['product_name']}** (đã bán {row['sold_units']}, còn {row['available_units']})"
                    for row in slow_rows[:3]
                )
                + ". "
                if slow_rows else "Hàng tồn lâu và bán chậm cần kiểm tra trước. "
            )
            return (
                lead
                + "Chưa nên giảm giá ngay; hãy kiểm tra ảnh, mô tả, giá, đánh giá, nhu cầu và số ngày tồn; "
                "nếu cần xả hàng, chỉ thử ưu đãi nhỏ hoặc combo trên một SKU trước. Muốn tính chính xác số ngày tồn, hãy tạo hoặc tải bảng **Tuổi tồn kho theo lô**."
                + batch_text
            )
        if "inventory" in analysis_tags and "sap het" in normalized:
            return (
                "Cảnh báo sắp hết hàng dựa trên **tồn khả dụng = tồn thực tế − số đã giữ chỗ**, rồi so với ngưỡng nhập thêm của từng SKU. "
                "Đây là tín hiệu để kiểm tra tốc độ bán và đơn đang về, không phải lệnh tự động phải nhập hàng."
            )
        if "strategy" in analysis_tags:
            if "combo_strategy" in analysis_tags:
                pair = co_purchase.get("best_pair") if co_purchase else None
                if pair:
                    stock_is_ready = (
                        pair["available_units"] is not None
                        and pair["paired_available_units"] is not None
                        and pair["available_units"] > 0
                        and pair["paired_available_units"] > 0
                    )
                    stock_text = (
                        f"Cả hai hiện còn {pair['available_units']} và {pair['paired_available_units']} sản phẩm khả dụng."
                        if stock_is_ready else "Cần kiểm tra lại tồn khả dụng của cả hai SKU trước khi thử."
                    )
                    return (
                        f"Cặp có dữ liệu mua cùng nhiều nhất là **{pair['product_name']} + {pair['paired_product_name']}** "
                        f"({pair['joint_order_count']} đơn trong kỳ). {stock_text} "
                        f"Tổng giá niêm yết là {int(pair['combined_list_price_vnd']):,} VND, giá vốn cộng lại là {int(pair['combined_cost_vnd']):,} VND. "
                        f"Giá thử minh họa giảm 5% là {int(pair['trial_price_vnd']):,} VND; chỉ bật thử sau khi đối soát phí sàn, khuyến mãi và lãi góp mỗi combo vẫn dương. "
                        "Dừng thử nếu lãi góp mỗi combo âm, tồn của một SKU chạm ngưỡng nhập thêm hoặc tỷ lệ hoàn tăng. Số đơn mua cùng là tín hiệu để thử, không phải bằng chứng combo sẽ thành công."
                    )
                return (
                    "Chưa nên khẳng định một cặp combo cụ thể chỉ từ dữ liệu hiện có, vì đơn hàng chưa cho biết hai SKU nào thường được mua cùng nhau. "
                    "Bạn hãy tạo hoặc tải bảng **Sản phẩm mua cùng** có SKU thứ nhất, SKU thứ hai, số đơn mua cùng và kỳ dữ liệu. "
                    "Khi có bảng này, chỉ chọn cặp có liên quan, cả hai còn tồn trên ngưỡng nhập thêm và tổng lãi góp vẫn dương. Giá thử nên bắt đầu từ tổng giá niêm yết trừ một ưu đãi nhỏ đã được kiểm tra không làm lãi góp âm; dừng thử nếu lãi góp mỗi combo âm, tồn của một SKU chạm ngưỡng hoặc tỷ lệ hoàn tăng."
                )
            if "risk_strategy" in analysis_tags:
                risks = product_scorecard.get("risk_products", []) if product_scorecard else []
                risk_lines = [
                    f"**{row['product_name']}**: " + ", ".join(row["risk_signals"])
                    for row in risks
                ]
                slow_candidates = slow_inventory.get("candidates", []) if slow_inventory else []
                slow_text = (
                    "Hàng bán chậm so với tồn hiện có: "
                    + ", ".join(
                        f"**{row['product_name']}** (đã bán {row['sold_units']}, còn {row['available_units']})"
                        for row in slow_candidates[:3]
                    )
                    + "."
                    if slow_candidates
                    else "Chưa đủ dữ liệu đơn hoàn tất và tồn kho để nêu SKU bán chậm."
                )
                operating_text = (
                    f"Chi phí vận hành đã ghi nhận là **{int(operating_costs['total_operating_cost_vnd']):,} VND**, "
                    f"khoản lớn nhất là **{next(iter(operating_costs['by_category']), 'chưa phân loại')}**."
                    if operating_costs else "Bạn hãy tạo hoặc tải bảng **Chi phí vận hành** có tháng, nhóm chi phí và số tiền."
                )
                returns_text = (
                    f"Có **{returns['return_request_count']}** yêu cầu hoàn với **{int(returns['recorded_refund_amount_vnd']):,} VND** tiền hoàn đã ghi."
                    if returns else "Bạn hãy tạo hoặc tải bảng **Hoàn hàng** có SKU, lý do, số lượng và tiền hoàn."
                )
                return (
                    "**Các điểm có nguy cơ làm giảm kết quả trước:** "
                    + ("; ".join(risk_lines) if risk_lines else "chưa đủ dữ liệu theo SKU; hãy tạo hoặc tải các bảng Sản phẩm, Đơn hàng, Tồn kho, Hoàn hàng và Kiểm tra chất lượng.")
                    + f". {slow_text} {operating_text} {returns_text} "
                    "Đây là tín hiệu cần đối soát, không phải kết luận lỗ ròng. Tạm dừng mở rộng những SKU có nhiều tín hiệu rủi ro; để tính chính xác số ngày tồn, hãy tạo hoặc tải bảng **Biến động kho** có ngày, SKU, loại biến động và số lượng."
                )
            if "weekly_strategy" in analysis_tags:
                risks = product_scorecard.get("risk_products", []) if product_scorecard else []
                first_risk = risks[0]["product_name"] if risks else "SKU có tín hiệu rủi ro cao nhất"
                cost_name = next(iter(operating_costs.get("by_category", {})), "khoản chi lớn nhất") if operating_costs else "chi phí vận hành"
                review_issue = reviews.get("priority_low_rating_issue") if reviews else None
                return (
                    f"**Ba việc tuần này:** (1) đối soát **{first_risk}** theo tồn khả dụng, hoàn và lỗi; đo số lượng tồn, số hoàn và số lỗi. "
                    f"(2) rà soát **{cost_name}**; đo số tiền chi đã ghi và chứng từ hợp lệ. "
                    + (f"(3) xử lý nhóm đánh giá thấp **{review_issue}**; đo số đánh giá 1–3 sao theo vấn đề." if review_issue else "(3) Bạn hãy tạo hoặc tải bảng Đánh giá khách hàng có số sao và vấn đề; sau đó đo số đánh giá 1–3 sao theo vấn đề.")
                    + " Mỗi việc chỉ thay đổi một yếu tố, chốt số trước/sau trong cùng kỳ và không coi kết quả một tuần là bằng chứng chắc chắn để mở rộng."
                )
            candidate = product_scorecard.get("recommended_candidate") if product_scorecard else None
            if candidate:
                return (
                    f"Trong 30 ngày tới, hãy chọn **{candidate['product_name']}** làm ứng viên **thử nhỏ trước**, không phải SKU để mở rộng ngay: "
                    f"GMV đã ghi là {int(candidate['gmv_vnd']):,} VND, lãi góp ước tính {int(candidate['estimated_contribution_vnd']):,} VND và tồn khả dụng {candidate['available_units']}. "
                    "Ứng viên này có đủ bản ghi đánh giá, kiểm tra chất lượng và phễu theo SKU, đồng thời không có cảnh báo tồn, đánh giá 1–3 sao hoặc lỗi lô trong bộ dữ liệu đã gắn. Trước khi mở rộng, kiểm tra thêm tỷ lệ hoàn; theo dõi GMV, lãi góp, tồn khả dụng, đánh giá thấp, tỷ lệ lỗi và tỷ lệ xem sang thêm giỏ theo SKU. "
                    "Kết quả chỉ là sàng lọc từ dữ liệu hiện có, không phải dự báo chắc chắn."
                )
            evidence_gaps = product_scorecard.get("evidence_gaps", []) if product_scorecard else []
            if evidence_gaps:
                gap_text = "; ".join(
                    f"**{row['product_name']}**: {', '.join(row['evidence_gaps'])}"
                    for row in evidence_gaps[:3]
                )
                risk_rows = product_scorecard.get("risk_products", []) if product_scorecard else []
                risk_text = (
                    " Các SKU đã đủ bản ghi nhưng có tín hiệu cần đối soát: "
                    + "; ".join(
                        f"**{row['product_name']}** ({', '.join(row['risk_signals'])})"
                        for row in risk_rows[:2]
                    )
                    + "."
                    if risk_rows
                    else ""
                )
                return (
                    "Chưa có SKU nào đủ bằng chứng để ưu tiên trong 30 ngày mà không coi dữ liệu thiếu là rủi ro bằng 0. "
                    f"Cần bổ sung bản ghi theo SKU trước: {gap_text}. "
                    "Bạn hãy tạo hoặc tải thêm dòng **Đánh giá khách hàng**, **Kiểm tra chất lượng** hoặc **Hiệu quả sản phẩm** cho các SKU này; sau đó AI mới xếp hạng được theo đủ GMV, lãi góp, tồn, đánh giá, lỗi và phễu."
                    + risk_text
                )
            return (
                "Chưa có SKU nào đủ điều kiện để ưu tiên trong 30 ngày vì các SKU đã đủ dữ liệu đều có tín hiệu rủi ro. Hãy xử lý hoặc đối soát tín hiệu đó trước, rồi thử một thay đổi nhỏ thay vì mở rộng vốn."
            )
        return ""

    @staticmethod
    def _data_request_guidance(normalized: str) -> str:
        """Turn missing evidence into an explicit upload/create instruction."""
        if "tao combo" in normalized or "combo" in normalized:
            return "Để chọn combo bằng dữ liệu, hãy tạo hoặc tải bảng **Sản phẩm mua cùng** có SKU thứ nhất, SKU thứ hai, số đơn mua cùng và kỳ dữ liệu; đồng thời gắn **Sản phẩm và giá vốn**, **Tồn kho** và **Đơn hàng**."
        if any(term in normalized for term in ("30 ngay", "tuan nay", "nguy co lo")):
            return "Để lập ưu tiên vận hành, hãy tạo hoặc tải các bảng **Đơn hàng**, **Sản phẩm và giá vốn**, **Tồn kho**, **Hoàn hàng**, **Chi phí vận hành**, **Đánh giá khách hàng**, **Kiểm tra chất lượng** và **Hiệu quả sản phẩm** theo SKU."
        if any(term in normalized for term in ("quang cao theo sku", "quang cao tung san pham", "sku nao nen tang ngan sach")):
            return "Để so sánh quảng cáo theo sản phẩm, hãy tạo hoặc tải bảng **Quảng cáo theo SKU/ngày** có ngày, mã chiến dịch, SKU, lượt hiển thị, lượt nhấp, chi quảng cáo, thêm giỏ, đơn và doanh thu quy gán."
        if any(term in normalized for term in ("quang cao", "roas", "ngan sach")):
            return "Để trả lời bằng số liệu, hãy tạo hoặc tải bảng **Quảng cáo**; nên có thêm **Quảng cáo theo SKU/ngày**, **Sản phẩm** và **Đơn hàng** để kiểm tra lãi sau quảng cáo."
        if any(term in normalized for term in ("khuyen mai", "ma giam gia", "gia sau khuyen mai")):
            return "Để đối chiếu giá đã áp dụng, hãy tạo hoặc tải bảng **Giá và khuyến mãi theo SKU** có ngày, SKU, giá niêm yết, giá sau khuyến mãi, giảm giá người bán và nguồn mã giảm giá."
        if any(term in normalized for term in ("danh gia", "review")):
            return "Để phân tích đánh giá, hãy tạo hoặc tải bảng **Đánh giá khách hàng**; nên có ngày đánh giá, số sao và vấn đề khách nêu."
        if any(term in normalized for term in ("lo hang", "ty le loi", "chat luong")):
            return "Để kiểm tra chất lượng, hãy tạo hoặc tải bảng **Kiểm tra chất lượng**; nên có ngày kiểm, mã lô, số lượng kiểm, số lỗi và dạng lỗi."
        if any(term in normalized for term in ("dong tien", "tien chi", "thieu tien")):
            return "Để phân tích dòng tiền, hãy tạo hoặc tải bảng **Dòng tiền** và **Đơn nhập hàng** có ngày thu, ngày chi, nhóm chi và số tiền."
        if any(term in normalized for term in ("luot xem", "them gio", "dat mua", "chot don")):
            return "Để phân tích chuyển đổi, hãy tạo hoặc tải bảng **Hiệu quả sản phẩm** có lượt xem, lượt thêm giỏ và số đơn theo từng SKU."
        if any(term in normalized for term in ("tuoi ton", "ton theo lo", "lo hang ton", "lo ton lau")):
            return "Để tính tuổi tồn theo lô, hãy tạo hoặc tải bảng **Tuổi tồn kho theo lô** có mã lô, SKU, ngày nhập kho, số lượng còn lại và giá vốn đơn vị."
        if any(term in normalized for term in ("ton kho", "sap het", "ton lau", "nhap hang", "nhap them")):
            return "Để phân tích, hãy tạo hoặc tải bảng **Tồn kho**, **Sản phẩm** và **Đơn hàng**; nếu cần biết hàng nằm bao lâu, thêm **Tuổi tồn kho theo lô**; nếu hỏi lượng nhập, thêm **Đơn nhập hàng** và thời gian giao dự kiến."
        if any(term in normalized for term in ("giam gia", "gia ban", "lai", "loi nhuan")):
            return "Để đánh giá phương án, hãy tạo hoặc tải bảng **Sản phẩm và giá vốn**, **Đơn hàng** và **Tồn kho**."
        return "Để trả lời câu hỏi này bằng tình hình shop, hãy tạo hoặc tải bộ dữ liệu gồm **Đơn hàng**, **Sản phẩm** và **Tồn kho**."

    @staticmethod
    def _knowledge_answer(question: str) -> str:
        """Give short answers only for source-backed common concepts."""
        normalized_question = normalize(question)
        if "mat hang nay" in normalized_question and "duoc ban" in normalized_question:
            return (
                "Chưa thể kết luận một mặt hàng cụ thể có được bán trên Shopee khi chưa biết tên hàng, thành phần và giấy tờ liên quan. "
                "Hãy đối chiếu danh mục hàng cấm/hạn chế của Shopee và quy định chuyên ngành; với hàng có điều kiện, cần kiểm tra giấy phép hoặc chứng từ trước khi đăng bán."
            )
        if "ai co cam ket" in normalized_question or "cam ket giam gia" in normalized_question:
            return (
                "Không. Eslabong không cam kết giảm giá sẽ làm bán tốt hơn. AI chỉ có thể nêu giả thuyết, điều kiện cần kiểm tra và một thử nghiệm nhỏ khi dữ liệu đủ; "
                "bạn vẫn cần tự quyết định giá, giới hạn chi và điều kiện dừng."
            )
        if "ai nay da ket noi" in normalized_question and "shopee" in normalized_question:
            return (
                "Chưa. Eslabong hiện chỉ dùng bộ dữ liệu demo hoặc các file bạn tự tải lên trong cuộc trò chuyện; AI không tự đọc tài khoản Shopee, không quét dữ liệu shop và không tự gửi thay đổi lên Shopee."
            )
        if "tu doan roas" in normalized_question or "khong tai bang quang cao" in normalized_question:
            return (
                "Không. Khi chưa có bảng **Quảng cáo**, Eslabong không tự đoán ROAS hoặc chi phí quảng cáo. Hãy tạo hoặc tải bảng Quảng cáo có chi tiêu, doanh thu quy gán và số đơn quy gán; "
                "nếu thiếu dữ liệu, AI chỉ nên nêu phần còn thiếu."
            )
        is_definition_question = any(
            cue in normalized_question
            for cue in ("la gi", "nghia la gi", "giai thich", "vi du", "khac gi", "co phai")
        )
        if "sku" in normalized_question and is_definition_question:
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
        if any(
            phrase in f" {normalized_question} "
            for phrase in (" hoan tien ", " tra hang ")
        ):
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
                "Giao dịch điện tử có thể được xem xét về giá trị pháp lý khi thông tin thể hiện được nội dung giao dịch, "
                "có thể truy cập để tham chiếu khi cần và có căn cứ xác định/chứng minh sự chấp thuận của các bên theo tình huống áp dụng. "
                "Bạn nên lưu: đề nghị hoặc hợp đồng, xác nhận đơn hàng, lịch sử trao đổi, thời điểm giao dịch, hóa đơn/chứng từ thanh toán, chứng từ giao nhận và tài liệu chứng minh thẩm quyền người xác nhận nếu có. "
                "Giá trị pháp lý của từng giao dịch vẫn phụ thuộc điều kiện luật định và tình huống cụ thể; Eslabong không tự phán quyết hiệu lực hợp đồng. Với giao dịch giá trị cao hoặc tranh chấp, hãy nhờ chuyên gia pháp lý rà soát."
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
            if term == "nha cung cap" and not any(
                phrase in normalized_question
                for phrase in ("la gi", "can luu y", "chon nha cung cap")
            ):
                continue
            if term in normalized_question:
                return answer
        return ""
