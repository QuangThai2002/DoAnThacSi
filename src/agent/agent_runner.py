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
                if any(term in normalized for term in ("loi nhuan", "lo von", "gia von", "lai gop")):
                    profitability = self.shop_data_tool.profitability_summary(plan.period)
                    trace.append({"tool": "shop_data", "status": "ok", "result": profitability})
                if any(term in normalized for term in ("hang hoan", "hoan hang", "ly do hoan")):
                    returns = self.shop_data_tool.returns_summary(plan.period)
                    trace.append({"tool": "shop_data", "status": "ok", "result": returns})
                if any(term in normalized for term in ("danh gia", "phan hoi", "review")):
                    reviews = self.shop_data_tool.review_summary(plan.period)
                    trace.append({"tool": "shop_data", "status": "ok", "result": reviews})
                if any(term in normalized for term in ("nhap hang", "nha cung cap", "don nhap")):
                    procurement = self.shop_data_tool.procurement_summary(plan.period)
                    trace.append({"tool": "shop_data", "status": "ok", "result": procurement})
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
            ranking=ranking,
            citations=citations,
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
        ranking: dict[str, Any] | None,
        citations: list[dict[str, str]],
    ) -> str:
        if plan.intent == "out_of_scope":
            return (
                "Câu hỏi này nằm ngoài phạm vi Agent hiện tại. Agent chỉ hỗ trợ "
                "chính sách Shopee có nguồn và dữ liệu vận hành mô phỏng của shop."
            )
        sections: list[str] = []
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
            knowledge_answer = AgentRunner._knowledge_answer(question)
            if knowledge_answer:
                sections.append(knowledge_answer)
            elif not sections:
                sections.append(
                    "Tôi đã tìm được tài liệu chính sách liên quan. Xem nguồn bên dưới "
                    "để đối chiếu chi tiết."
                )
        elif "rag" in plan.tools:
            sections.append("Agent chưa truy hồi được nguồn chính sách; không đưa ra kết luận chính sách.")
        return "\n\n".join(sections)

    @staticmethod
    def _knowledge_answer(question: str) -> str:
        """Give short answers only for source-backed common concepts."""
        normalized_question = normalize(question)
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
            "sku": "SKU là mã riêng cho từng sản phẩm hoặc biến thể; dùng để tránh nhầm hàng khi theo dõi đơn và tồn kho.",
            "roas": "ROAS = doanh thu được quy gán cho quảng cáo chia cho chi quảng cáo. Chỉ số này không tự chứng minh chiến dịch có lãi vì còn giá vốn và phí.",
            "gia von": "Giá vốn là chi phí trực tiếp để có sản phẩm sẵn sàng bán. Cần có giá vốn thì mới ước lượng được biên lợi nhuận gộp.",
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
        }
        for term, answer in definitions.items():
            if term in normalized_question:
                return answer
        return ""
