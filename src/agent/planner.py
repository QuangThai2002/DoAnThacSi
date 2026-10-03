from __future__ import annotations

import re
import unicodedata
from dataclasses import asdict, dataclass


VALID_TOOLS = {"rag", "shop_data", "calculator"}

# Map common seller phrasing to the operational vocabulary used by the planner.
# The list is deliberately narrow: it corrects predictable variations without
# silently changing product names, SKUs, or financial values supplied by users.
QUERY_INTENT_ALIASES: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("chi phi van hanh khoan van hanh", ("khoan chi van hanh", "chi van hanh", "khoan van hanh")),
    ("luot xem cao", ("xem nhieu", "nhieu nguoi xem", "xem cao")),
    ("it them gio", ("ty le them gio thap", "them gio thap", "it vao gio")),
    ("quang cao theo sku", ("roas quang cao sku", "roas theo sku", "quang cao sku")),
    ("danh gia thap", ("danh gia xau", "danh gia kem", "danh gia 1 3 sao")),
    ("ty le giao dung hen", ("giao dung hen", "giao on time", "ty le dung hen")),
)
TYPO_VOCABULARY = frozenset({
    "quang", "cao", "ton", "kho", "van", "hanh", "danh", "gia", "doi", "soat",
    "giao", "tre", "huy", "don", "luot", "xem", "them", "gio", "nha", "cung",
    "cap", "doanh", "thu", "phi", "loi", "nhuan", "khuyen", "mai", "sku", "roas",
    "chi", "nhieu",
})
# Short, ordinary Vietnamese question words must never be repaired into a
# business keyword merely because their unaccented spelling is one edit away.
# Intent recovery is deliberately conservative: preserve these words, then
# correct only a likely typo of the small operational vocabulary above.
PROTECTED_QUERY_TOKENS = frozenset({
    "ai", "bao", "cua", "da", "de", "gi", "hay", "la", "lo", "nao", "nhat",
    "neu", "sau", "san", "pham", "shop", "thang", "uoc", "tinh", "ve", "voi",
})


def _one_edit_away(left: str, right: str) -> bool:
    """Return whether two operational words differ by one simple typo."""
    if left == right or abs(len(left) - len(right)) > 1:
        return left == right
    if len(left) == len(right):
        differences = [index for index, (a, b) in enumerate(zip(left, right)) if a != b]
        if not differences:
            return True
        # A transposition (for example ``quagn`` instead of ``quang``) is a
        # common keyboard slip and is as safe to repair as one substitution.
        if len(differences) == 2 and differences[1] == differences[0] + 1:
            first, second = differences
            return left[first] == right[second] and left[second] == right[first]
        return False
    if len(left) > len(right):
        left, right = right, left
    left_index = right_index = edits = 0
    while left_index < len(left) and right_index < len(right):
        if left[left_index] == right[right_index]:
            left_index += 1
        else:
            edits += 1
        right_index += 1
        if edits > 1:
            return False
    return True


def normalize(text: str) -> str:
    text = unicodedata.normalize("NFD", text or "")
    text = "".join(char for char in text if unicodedata.category(char) != "Mn")
    normalized = re.sub(r"[^a-z0-9]+", " ", text.replace("đ", "d").replace("Đ", "D").lower())
    normalized = re.sub(r"\s+", " ", normalized).strip()

    # Correct only a compact, operational vocabulary. This makes intent
    # routing tolerant of a missing/extra character or adjacent-key swap, but
    # deliberately leaves product names, values, and unknown identifiers
    # untouched. Replacing the token also preserves phrase order: "xem nhieuu"
    # becomes "xem nhieu".
    corrected_tokens: list[str] = []
    for token in normalized.split():
        if token in TYPO_VOCABULARY or token in PROTECTED_QUERY_TOKENS or len(token) < 3:
            corrected_tokens.append(token)
            continue
        matches = sorted(candidate for candidate in TYPO_VOCABULARY if _one_edit_away(token, candidate))
        corrected_tokens.append(matches[0] if len(matches) == 1 else token)
    enriched = " ".join(corrected_tokens)
    # Keep the untouched normalized text available to every existing routing
    # rule. The repaired form is an additional interpretation, never a
    # replacement that could hide a valid phrase such as "từ khóa".
    semantic_text = normalized if enriched == normalized else f"{normalized} {enriched}"
    canonical_terms = [
        canonical
        for canonical, variants in QUERY_INTENT_ALIASES
        if any(variant in semantic_text for variant in variants)
    ]
    return re.sub(r"\s+", " ", " ".join([semantic_text, *canonical_terms])).strip()


@dataclass(frozen=True)
class AgentPlan:
    intent: str
    tools: tuple[str, ...]
    period: str | None
    needs_private_shop_data: bool
    rationale: tuple[str, ...]

    @property
    def data_requirement(self) -> str:
        """Expose the two seller-facing question classes.

        The planner may still distinguish policy, calculation, and small-talk
        internally, but a seller only needs one reliable decision: whether the
        answer depends on that seller's own operational data.
        """
        return "shop_data_required" if self.needs_private_shop_data else "no_shop_data_required"

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
        "hop dong",
        "giao dich dien tu",
        "phap luat",
        "luat",
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
        "lai gop",
        "lo von",
        "gia von",
        "hang hoan",
        "hoan hang",
        "danh gia",
        "phan hoi",
        "review",
        "nhap hang",
        "nha cung cap",
        "don nhap",
        "chi phi van hanh",
        "dong goi",
        "nhan su",
        "kho bai",
        "bien dong kho",
        "hang loi",
        "hang hu",
        "kiem tra chat luong",
        "chat luong lo hang",
        "that thoat",
        "dong tien",
        "tien vao",
        "tien ra",
        "nha cung cap tot",
        "giao hang dung hen",
        "khach quay lai",
        "khach hang than thiet",
        "khach trung thanh",
        "luot xem",
        "them gio hang",
        "hieu qua san pham",
        "phieu san pham",
        # Decision questions still require shop evidence even when they do not
        # contain the words “shop tôi” or “tồn kho”.
        "giam gia",
        "nhap bao nhieu",
        "nhap nhieu hon",
        "sap het",
        "ton lau",
        "it ban",
        "san pham ban tot",
        "ty le loi lo hang",
        "ty le loi",
        "nguon hang",
        "danh gia xau",
        "khoan van hanh",
        "tien chi",
        "thieu tien",
        "luot xem cao",
        "it them gio",
        "it dat mua",
        "kho chot don",
        "30 ngay",
        "tao combo",
        "nguy co lo",
        "tuan nay",
        "khuyen mai",
        "ma giam gia",
        "gia sau khuyen mai",
        "quang cao theo sku",
        "tuoi ton",
        "lo hang ton",
        "tu khoa",
        "tim kiem",
        "vi tri tim kiem",
        "giao tre",
        "van chuyen",
        "thoi gian xu ly",
        "ly do huy don",
        # Accept ordinary shorthand and the common missing-initial-letter typo
        # in "lý do hủy đơn".  These are still unambiguously shop metrics.
        "huy don",
        "do huy",
        "doi soat",
        "tien shopee phai tra",
        "phi thuc te",
        "ngay nhan tien",
        "doi thu",
        "shop tham khao",
    )
    # A metric word can be either a request for a definition or a request for
    # the seller's own numbers. Only the latter must have shop data attached.
    BUSINESS_TERM_DEFINITION_TERMS = (
        "gmv", "roas", "sku", "doanh thu", "loi nhuan", "gia von",
        "hoa von", "dong tien", "ton kho", "don bi huy", "don huy", "don da huy",
        "nguong nhap them", "chi phi quang cao",
    )
    DEFINITION_QUESTION_TERMS = (
        "la gi", "nghia la gi", "co phai", "khac gi", "tinh nhu the nao",
        "tinh sao", "giai thich", "co duoc tinh", "co tinh", "tinh doanh thu khong",
    )
    PRIVATE_DATA_CUES = (
        "shop toi", "cua shop", "cua toi", "cua hang toi", "bao nhieu",
        "san pham nao", "thang nay", "thang ", "ky nay", "hien tai",
    )
    COST_ANALYSIS_TERMS = (
        "khoan chi phi",
        "chi phi nao",
        "chi phi lon nhat",
        "khoan phi lon nhat",
        "anh huong nhieu nhat",
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
    # Small-talk is intentionally narrow.  This keeps Eslabong approachable
    # without turning it into a general-purpose assistant or bypassing the
    # evidence rules for shop questions.
    CASUAL_ONLY_PHRASES = (
        "chao", "xin chao", "hello", "hi", "alo", "cam on", "thanks", "thank you",
        "ban khoe khong", "ban la ai", "eslabong la gi", "ban co the lam gi",
        "ban lam duoc gi", "eslabong co the lam gi", "ban co the giup gi",
        "giup toi voi", "toi can giup do",
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
        has_shop_or_policy_signal = any(
            term in normalized
            for term in (*self.SHOP_TERMS, *self.POLICY_TERMS, *self.CALCULATION_TERMS)
        )
        is_casual_request = any(
            normalized == phrase or normalized.startswith(f"{phrase} ")
            for phrase in self.CASUAL_ONLY_PHRASES
        )
        if is_casual_request and not has_shop_or_policy_signal:
            return AgentPlan(
                intent="casual",
                tools=(),
                period=None,
                needs_private_shop_data=False,
                rationale=("Lời chào hoặc câu hỏi giao tiếp cơ bản không cần truy hồi dữ liệu.",),
            )
        is_definition_question = (
            any(term in normalized for term in self.BUSINESS_TERM_DEFINITION_TERMS)
            and any(term in normalized for term in self.DEFINITION_QUESTION_TERMS)
            and not any(term in normalized for term in self.PRIVATE_DATA_CUES)
        )
        # Questions that contrast one cost with all shop costs are conceptual,
        # even when the wording contains “của shop”; they do not need CSV data.
        if "chi phi quang cao" in normalized and "co phai" in normalized:
            is_definition_question = True
        is_system_limit_question = any(
            term in normalized
            for term in (
                "ai co cam ket",
                "ai nay da ket noi",
                "tu doan roas",
                "khong tai bang quang cao",
            )
        )
        needs_policy = any(term in normalized for term in self.POLICY_TERMS)
        is_general_policy_question = (
            any(term in normalized for term in ("hop dong", "giao dich dien tu", "phap luat", "luat"))
            and not any(term in normalized for term in self.PRIVATE_DATA_CUES)
        )
        is_general_policy_question = is_general_policy_question or (
            "mat hang nay" in normalized and "duoc ban" in normalized
        )
        # A general policy/process question such as return-refund guidance is
        # not a request for this seller's return records.  Without a clear
        # private-data cue, keep it on the cited policy path.
        is_general_policy_question = is_general_policy_question or (
            needs_policy
            and not any(term in normalized for term in self.PRIVATE_DATA_CUES)
            and not any(term in normalized for term in (
                "doi soat", "tien shopee phai tra", "phi thuc te", "ngay nhan tien",
            ))
            and not any(term in normalized for term in (
                "shop toi", "cua shop", "cua toi", "cua hang toi", "thang ",
                "ky nay", "hien tai", "bao nhieu", "san pham nao",
            ))
        )
        needs_cost_analysis = any(
            term in normalized for term in self.COST_ANALYSIS_TERMS
        )
        needs_shop = (
            any(term in normalized for term in self.SHOP_TERMS)
            or needs_cost_analysis
        ) and not (is_definition_question or is_general_policy_question or is_system_limit_question)
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
