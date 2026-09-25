from __future__ import annotations

import re
import unicodedata
from dataclasses import asdict, dataclass


VALID_TOOLS = {"rag", "shop_data", "calculator"}


def normalize(text: str) -> str:
    text = unicodedata.normalize("NFD", text or "")
    text = "".join(char for char in text if unicodedata.category(char) != "Mn")
    return re.sub(r"\s+", " ", text.replace("đ", "d").replace("Đ", "D")).lower().strip()


@dataclass(frozen=True)
class AgentPlan:
    intent: str
    tools: tuple[str, ...]
    period: str | None
    needs_private_shop_data: bool
    rationale: tuple[str, ...]

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


class Planner:
    """Rule-based planner that makes tool selection inspectable and testable.

    A deterministic planner is deliberate for the first thesis Agent baseline:
    tool routing can be evaluated independently from a generative model.
    """

    POLICY_TERMS = (
        "theo chinh sach",
        "chinh sach",
        "quy dinh",
        "dieu khoan",
        "shopee",
        "phi co dinh",
        "phi xu ly",
        "tra hang",
        "hoan tien",
        "merchant api",
        "shop api",
    )
    SHOP_TERMS = (
        "shop toi",
        "cua shop toi",
        "doanh thu",
        "doanh so",
        "gmv",
        "don hang",
        "ton kho",
        "san pham cua toi",
        "quang cao",
        "roas",
        "chi phi cua shop",
        "loi nhuan",
    )
    CALCULATION_TERMS = (
        "tinh",
        "bao nhieu",
        "ty le",
        "phan tram",
        "roas",
        "anh huong nhieu nhat",
        "cao nhat",
        "thap nhat",
        "so sanh",
        "so voi",
    )
    OUT_OF_SCOPE_TERMS = (
        "thoi tiet",
        "bong da",
        "doi bong",
        "world cup",
        "phim",
        "am nhac",
        "dich benh",
        "tu van y te",
        "bi sot",
        "uong thuoc",
        "gia vang",
        "chung khoan",
    )

    def plan(self, question: str) -> AgentPlan:
        normalized = normalize(question)
        period = self._period(normalized)
        if any(term in normalized for term in self.OUT_OF_SCOPE_TERMS):
            return AgentPlan(
                intent="out_of_scope",
                tools=(),
                period=period,
                needs_private_shop_data=False,
                rationale=("Câu hỏi nằm ngoài phạm vi chính sách và vận hành Shopee.",),
            )
        needs_shop = any(term in normalized for term in self.SHOP_TERMS)
        needs_policy = any(term in normalized for term in self.POLICY_TERMS)
        needs_calculation = any(term in normalized for term in self.CALCULATION_TERMS)

        tools: list[str] = []
        rationale: list[str] = []
        if needs_shop:
            tools.append("shop_data")
            rationale.append("Câu hỏi cần số liệu vận hành của cửa hàng.")
        if needs_policy:
            tools.append("rag")
            rationale.append("Câu hỏi có nội dung chính sách/tri thức cần truy hồi nguồn.")
        if needs_calculation and needs_shop:
            tools.append("calculator")
            rationale.append("Cần tổng hợp hoặc tính toán từ dữ liệu/tool khác.")

        if not tools:
            tools.append("rag")
            rationale.append("Câu hỏi tri thức mặc định được chuyển tới RAG có nguồn.")

        tools = [tool for tool in tools if tool in VALID_TOOLS]
        if tools == ["shop_data"]:
            intent = "shop_data"
        elif tools == ["rag"]:
            intent = "policy_rag"
        elif set(tools) == {"shop_data", "rag", "calculator"}:
            intent = "multi_tool_policy_and_shop_analysis"
        elif set(tools) == {"shop_data", "rag"}:
            intent = "multi_tool_policy_and_shop_retrieval"
        else:
            intent = "shop_analysis"

        return AgentPlan(
            intent=intent,
            tools=tuple(tools),
            period=period,
            needs_private_shop_data=needs_shop,
            rationale=tuple(rationale),
        )

    @staticmethod
    def _period(question: str) -> str | None:
        match = re.search(r"thang\s*(\d{1,2})(?:\s*(?:nam)?\s*(20\d{2}))?", question)
        if not match:
            return None
        month = int(match.group(1))
        if not 1 <= month <= 12:
            return None
        year = int(match.group(2) or "2026")
        return f"{year:04d}-{month:02d}"
