from __future__ import annotations

from dataclasses import asdict
from time import perf_counter
from typing import Any

from .calculator_tool import CalculatorTool
from .planner import AgentPlan, Planner, normalize
from .rag_tool import RAGTool
from .shop_data_tool import ShopDataTool


class AgentRunner:
    """Run a transparent, read-only multi-tool agent over mock shop data.

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
        ranking: dict[str, Any] | None = None
        rag_result: dict[str, Any] | None = None

        if "shop_data" in plan.tools:
            try:
                if "ton kho" in normalized:
                    inventory = self.shop_data_tool.inventory_alerts()
                    trace.append({"tool": "shop_data", "status": "ok", "result": inventory})
                else:
                    sales = self.shop_data_tool.sales_summary(plan.period)
                    trace.append({"tool": "shop_data", "status": "ok", "result": sales})

                if any(term in normalized for term in ("quang cao", "roas", "ads")):
                    advertising = self.shop_data_tool.advertising_summary(plan.period)
                    trace.append({"tool": "shop_data", "status": "ok", "result": advertising})
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
            plan=plan,
            sales=sales,
            inventory=inventory,
            advertising=advertising,
            ranking=ranking,
            citations=citations,
        )
        return {
            "question": question,
            "plan": asdict(plan),
            "answer": answer,
            "citations": citations,
            "trace": trace,
            "agent_latency_seconds": round(perf_counter() - started, 6),
            "limitations": [
                "Shop operational values come only from data/shop_mock and are not connected to a real Shopee shop.",
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
        plan: AgentPlan,
        sales: dict[str, Any] | None,
        inventory: dict[str, Any] | None,
        advertising: dict[str, Any] | None,
        ranking: dict[str, Any] | None,
        citations: list[dict[str, str]],
    ) -> str:
        if plan.intent == "out_of_scope":
            return (
                "Câu hỏi này nằm ngoài phạm vi Agent hiện tại. Agent chỉ hỗ trợ "
                "chính sách Shopee có nguồn và dữ liệu vận hành mô phỏng của shop."
            )
        sections = [
            "Kết quả dưới đây dùng dữ liệu vận hành mô phỏng của luận văn; không phải dữ liệu tài khoản Shopee thật."
        ]
        if sales:
            sections.append(
                "Trong kỳ {period}, có {orders} đơn hoàn tất, GMV {gmv:,} VND và doanh thu sau các khoản phí ước tính là {net:,} VND.".format(
                    period=sales["period"],
                    orders=sales["completed_order_count"],
                    gmv=int(sales["gross_merchandise_value_vnd"]),
                    net=int(sales["net_revenue_after_estimated_fees_vnd"]),
                )
            )
        if advertising:
            sections.append(
                "Quảng cáo trong kỳ chi {spend:,} VND, doanh thu quy gán {revenue:,} VND, ROAS {roas:.2f}.".format(
                    spend=int(advertising["ad_spend_vnd"]),
                    revenue=int(advertising["attributed_revenue_vnd"]),
                    roas=float(advertising["roas"]),
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
        if inventory:
            if inventory["alert_count"]:
                products = ", ".join(
                    f"{item['product_name']} (còn {item['available_units']})"
                    for item in inventory["alerts"]
                )
                sections.append(f"Có {inventory['alert_count']} cảnh báo tồn kho: {products}.")
            else:
                sections.append("Không có cảnh báo tồn kho theo ngưỡng đã cấu hình.")
        if citations:
            labels = "; ".join(
                f"{citation['title']}{', trang ' + citation['page'] if citation['page'] else ''}"
                for citation in citations[:2]
            )
            sections.append(
                "Để đối chiếu chính sách, Agent đã truy hồi các nguồn: " + labels + "."
            )
            evidence_text = " ".join(citation["excerpt"].lower() for citation in citations)
            policy_terms: list[str] = []
            if "phí cố định" in evidence_text:
                policy_terms.append("Phí Cố Định")
            if "phí xử lý giao dịch" in evidence_text:
                policy_terms.append("Phí Xử lý Giao Dịch")
            if policy_terms:
                sections.append(
                    "Các nhóm phí xuất hiện trực tiếp trong evidence truy hồi: "
                    + ", ".join(policy_terms)
                    + ". Cần đối chiếu tỷ lệ/điều kiện theo đúng ngành hàng và tài liệu nguồn trước khi áp dụng."
                )
        elif "rag" in plan.tools:
            sections.append("Agent chưa truy hồi được nguồn chính sách; không đưa ra kết luận chính sách.")
        return "\n\n".join(sections)
