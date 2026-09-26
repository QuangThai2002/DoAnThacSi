from __future__ import annotations

from pathlib import Path
from datetime import datetime
import json
import csv
import os
import re
import sys
import time
import unicodedata
from typing import Any
from urllib import request, error

from hybrid_search_shopee_v2 import (
    SearchResult,
    business_private_data_question,
    hybrid_search,
    load_resources as load_hybrid_resources,
    normalize_for_match,
    normalize_unicode,
)


# ============================================================
# CẤU HÌNH
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parents[1]

OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen3:1.7b")
OLLAMA_URL = os.getenv(
    "OLLAMA_URL",
    "http://localhost:11434/api/chat",
)

# Chỉ lấy Top 1 sau Hybrid Search, sau đó mở rộng sang các chunk lân cận.
NEIGHBOR_RADIUS = 2
MAX_CONTEXT_CHUNKS = 4
MAX_CONTEXT_CHARS = 5200

# Model local.
OLLAMA_CONTEXT = 3072
OLLAMA_MAX_TOKENS = 520
OLLAMA_KEEP_ALIVE = -1

LAST_ANSWER_CONTEXT: list[dict] = []
CONVERSATION_HISTORY: list[dict[str, str]] = []
MAX_HISTORY_TURNS = 3
LAST_USER_QUERY: str = ""
LAST_ASSISTANT_ANSWER: str = ""
DEBUG_MODE: bool = False
LOG_PATH = PROJECT_ROOT / "data" / "processed" / "chatbot_v4_log.csv"


def clean_terminal_markdown(text: str) -> str:
    if not text:
        return ""
    text = text.replace("**", "").replace("__", "").replace("`", "")
    text = re.sub(r"(?m)^#{1,6}\s*", "", text)
    text = re.sub(r"(?m)^\s*[-*]\s+", "• ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()



def add_history(role: str, content: str) -> None:
    global CONVERSATION_HISTORY

    content = normalize_unicode(content).strip()
    if not content:
        return

    CONVERSATION_HISTORY.append(
        {
            "role": role,
            "content": content[:1800],
        }
    )

    max_messages = MAX_HISTORY_TURNS * 2
    if len(CONVERSATION_HISTORY) > max_messages:
        CONVERSATION_HISTORY = CONVERSATION_HISTORY[-max_messages:]


def resolve_follow_up_question(query: str) -> str:
    """
    Bổ sung ngữ cảnh cho câu hỏi nối tiếp ngắn như:
    "Nó dùng để làm gì?", "Lấy ở đâu?", "Còn Merchant API thì sao?"
    """
    normalized = normalize_for_match(query)
    words = normalized.split()

    markers = [
        "no ",
        "no dung",
        "no dung de",
        "cai nay",
        "cai do",
        "lay o dau",
        "dung de lam gi",
        "thi sao",
        "khac gi",
        "con ",
        "vay ",
        "the ",
    ]

    is_follow_up = (
        len(words) <= 10
        and any(
            normalized == marker.strip()
            or normalized.startswith(marker)
            or marker.strip() in normalized
            for marker in markers
        )
    )

    if not is_follow_up or not CONVERSATION_HISTORY:
        return query

    previous_questions = [
        item["content"]
        for item in CONVERSATION_HISTORY
        if item.get("role") == "user"
    ]

    if not previous_questions:
        return query

    return (
        f"Câu hỏi trước: {previous_questions[-1]}\n"
        f"Câu hỏi tiếp theo: {query}"
    )






def reconstruct_transaction_fee_formula(raw_text: str) -> str | None:
    """
    Ghép lại công thức Phí Xử Lý Giao Dịch khi nội dung bị xuống dòng
    trong PDF hoặc trang web đã trích xuất.

    Hàm chỉ sử dụng nội dung có trong context, không tự bổ sung dữ liệu.
    """
    text = normalize_unicode(raw_text)

    start_match = re.search(
        r"Phí\s*Xử\s*Lý\s*Giao\s*Dịch\s*=",
        text,
        flags=re.IGNORECASE,
    )
    if not start_match:
        return None

    # Lấy một đoạn vừa đủ sau vị trí bắt đầu công thức.
    segment = text[start_match.start(): start_match.start() + 1200]
    lines = [
        line.strip()
        for line in segment.splitlines()
        if line.strip()
    ]

    collected: list[str] = []

    for line in lines:
        normalized_line = normalize_for_match(line)

        # Dừng khi sang phần nội dung khác.
        if collected and any(
            stop_phrase in normalized_line
            for stop_phrase in [
                "cach kiem tra phi xu ly giao dich",
                "shopee uni",
                "hoc vien shopee",
                "nguon tham khao",
            ]
        ):
            break

        collected.append(line)

        # Dừng khi đã gặp mức phí cuối công thức.
        if re.search(
            r"\)\s*(?:x|×|\*)?\s*6\s*%",
            line,
            flags=re.IGNORECASE,
        ):
            break

    formula = " ".join(collected)
    formula = re.sub(r"\s+", " ", formula).strip()

    if "=" not in formula:
        return None

    # Tránh lấy sang nội dung sau công thức nếu nguồn không xuống dòng đẹp.
    formula = re.split(
        r"(?i)\bCách kiểm tra Phí Xử Lý Giao Dịch\b",
        formula,
        maxsplit=1,
    )[0].strip()

    return formula or None

def compact_source_name(title: str) -> str:
    """
    Chuẩn hóa tên tài liệu để hiển thị nguồn gọn và ổn định.
    """
    title = normalize_unicode(title)
    title = re.sub(r"\s+", " ", title).strip()
    return title or "Tài liệu chưa xác định"


SYSTEM_PROMPT = """
Bạn là trợ lý AI hỗ trợ doanh nghiệp bán hàng trên Shopee.

QUY TẮC BẮT BUỘC:
1. Luôn trả lời hoàn toàn bằng tiếng Việt.
2. Chỉ sử dụng thông tin trong NGỮ CẢNH.
3. Không tự thêm kiến thức ngoài nguồn.
4. Nếu ngữ cảnh không đủ hoặc không trực tiếp trả lời câu hỏi, phải nói:
   "Tôi chưa có đủ dữ liệu để trả lời chắc chắn."
5. Không dịch endpoint, tên trường, biến hoặc tham số API.
6. Không thay đổi công thức, thứ tự tham số, số liệu, tỷ lệ, đơn vị hoặc ngày tháng.
7. Giữ nguyên các thuật ngữ kỹ thuật như partner_id, api_path, timestamp,
   access_token, shop_id, merchant_id, base_string, signature, HMAC-SHA256,
   GMV, GAAP revenue và adjusted EBITDA.
8. Không hiển thị đường dẫn file, chunk_id, điểm retrieval hoặc thông tin kỹ thuật nội bộ.
9. Trả lời tự nhiên, trực tiếp và dễ hiểu như ChatGPT.
10. Không sao chép nguyên khối tài liệu dài nếu có thể tổng hợp chính xác.
11. Phân biệt rõ các mốc thời gian khác nhau. Không lấy thời hạn khiếu nại
    để trả lời thành thời hạn phản hồi nếu nguồn không nói như vậy.
12. Phân biệt chính sách của Shopee với nghĩa vụ pháp luật chung của doanh nghiệp.
13. Cuối câu trả lời ghi tối đa 2 nguồn theo dạng:
    "Nguồn tham khảo: <tên tài liệu>, trang <số trang>."
14. Trả lời đủ ý nhưng gọn, ưu tiên 3–6 ý chính.
15. Không kết thúc câu trả lời giữa câu.
16. Nếu câu hỏi mang tính pháp luật chung nhưng nguồn chỉ là chính sách Shopee,
    phải nói rõ đây là thông tin theo chính sách Shopee và chưa đủ để kết luận
    nghĩa vụ pháp lý chung của mọi doanh nghiệp.
17. Mở đầu tự nhiên theo phạm vi nguồn, ví dụ:
    "Theo chính sách Shopee..." hoặc "Theo tài liệu được cung cấp...".
18. Không gọi nguồn là "NGUỒN 1", "NGUỒN 2" trong câu trả lời.
19. Không lặp lại cùng một ý bằng nhiều cách.
20. Với câu hỏi quy trình, trình bày theo thứ tự các bước.
21. Với câu hỏi trách nhiệm/nghĩa vụ, nhóm câu trả lời thành các ý rõ ràng.
22. Không được thêm API, tính năng, quy định hoặc khái niệm không xuất hiện trong ngữ cảnh.
23. Nếu nguồn chỉ so sánh Shop API và Merchant API, không được tự thêm Public API.
24. Không tự viết phần nguồn; chương trình sẽ tự gắn nguồn chính thức.
""".strip()



def detect_follow_up_intent(query: str) -> str | None:
    """
    Nhận diện mục đích của câu hỏi nối tiếp ngắn.
    """
    normalized = normalize_for_match(query)

    if any(
        phrase in normalized
        for phrase in [
            "dung de lam gi",
            "co tac dung gi",
            "muc dich la gi",
            "de lam gi",
        ]
    ):
        return "purpose"

    if any(
        phrase in normalized
        for phrase in [
            "lay o dau",
            "tim o dau",
            "o dau",
        ]
    ):
        return "location"

    if any(
        phrase in normalized
        for phrase in [
            "khac gi",
            "khac nhau the nao",
            "so sanh",
        ]
    ):
        return "comparison"

    return None


def latest_user_question() -> str | None:
    for item in reversed(CONVERSATION_HISTORY):
        if item.get("role") == "user":
            return item.get("content")
    return None


def build_follow_up_query(original_query: str) -> str:
    """
    Viết lại câu hỏi nối tiếp thành truy vấn đầy đủ hơn để retrieval hiểu đúng.
    """
    intent = detect_follow_up_intent(original_query)
    previous = latest_user_question()

    if not intent or not previous:
        return original_query

    if intent == "purpose":
        return (
            f"Dựa trên câu hỏi trước: {previous}. "
            f"Hãy giải thích mục đích và vai trò của nội dung đó. "
            f"Câu hỏi hiện tại: {original_query}"
        )

    if intent == "location":
        return (
            f"Dựa trên câu hỏi trước: {previous}. "
            f"Hãy xác định nội dung đó được lấy hoặc cấu hình ở đâu. "
            f"Câu hỏi hiện tại: {original_query}"
        )

    if intent == "comparison":
        return (
            f"Dựa trên câu hỏi trước: {previous}. "
            f"Hãy so sánh nội dung đó với phần liên quan gần nhất. "
            f"Câu hỏi hiện tại: {original_query}"
        )

    return original_query



def is_out_of_scope_question(query: str) -> bool:
    """
    Chặn nhanh các câu hỏi rõ ràng nằm ngoài phạm vi Shopee/RAG hiện tại.
    """
    normalized = normalize_for_match(query)

    allowed_terms = [
        "shopee",
        "shop",
        "nguoi ban",
        "nguoi mua",
        "phi",
        "tra hang",
        "hoan tien",
        "api",
        "base_string",
        "partner key",
        "gmv",
        "thuong mai dien tu",
        "bao ve du lieu",
        "nguoi tieu dung",
        "don hang",
        "doanh thu",
        "ton kho",
        "quang cao",
        "san pham",
        "van chuyen",
    ]

    if any(term in normalized for term in allowed_terms):
        return False

    out_of_scope_terms = [
        "bitcoin",
        "btc",
        "ethereum",
        "thoi tiet",
        "bong da",
        "world cup",
        "gia vang",
        "chung khoan",
        "ty gia",
        "lich thi dau",
        "du bao thoi tiet",
    ]

    return any(term in normalized for term in out_of_scope_terms)


def is_shop_data_file_followup(query: str) -> bool:
    normalized = normalize_for_match(query)

    return any(
        phrase in normalized
        for phrase in [
            "toi can cung cap file gi",
            "can cung cap file gi",
            "gui file gi",
            "can du lieu gi",
            "can cung cap du lieu gi",
            "toi can gui gi",
        ]
    )


def shop_data_file_guidance() -> str:
    return (
        "Để chatbot phân tích dữ liệu vận hành của shop, bạn nên cung cấp file Excel hoặc CSV "
        "xuất từ Kênh Người Bán. Tối thiểu nên có:\n"
        "1. Đơn hàng: mã đơn, ngày đặt, trạng thái, sản phẩm, SKU, số lượng.\n"
        "2. Doanh thu: giá bán, doanh thu gộp, giảm giá, doanh thu thực nhận.\n"
        "3. Phí: phí cố định, phí xử lý giao dịch, phí vận chuyển, phí dịch vụ.\n"
        "4. Trả hàng/hoàn tiền: mã đơn, lý do, số tiền hoàn, trạng thái xử lý.\n"
        "5. Tồn kho: SKU, số lượng tồn, mức cảnh báo.\n"
        "6. Quảng cáo: chi phí, lượt nhấp, đơn hàng, doanh thu và ROAS nếu có.\n\n"
        "Không gửi mật khẩu, access_token, Partner Key, thông tin thẻ hoặc dữ liệu cá nhân nhạy cảm."
    )


def has_direct_partner_key_location(contexts: list[dict]) -> bool:
    """
    Chỉ cho phép trả lời nơi lấy Partner Key khi nguồn trực tiếp nói rõ
    Open Platform Console / Partner Platform / App details.
    """
    merged = normalize_for_match(
        "\n".join(
            str(item.get("text", ""))
            for item in contexts
        )
    )

    direct_markers = [
        "open platform console",
        "partner platform",
        "app details",
        "application details",
        "partner key",
        "developer console",
    ]

    return "partner key" in merged and any(
        marker in merged
        for marker in direct_markers
        if marker != "partner key"
    )


def partner_key_location_question(query: str) -> bool:
    normalized = normalize_for_match(query)

    return (
        "partner key" in normalized
        and any(
            phrase in normalized
            for phrase in [
                "lay o dau",
                "o dau",
                "tim o dau",
                "xem o dau",
            ]
        )
    )


def duration_question_requires_exact_relation(query: str) -> bool:
    normalized = normalize_for_match(query)

    return (
        "phan hoi" in normalized
        and "tra hang" in normalized
        and (
            "bao lau" in normalized
            or "thoi han" in normalized
        )
    )


def has_exact_response_deadline(contexts: list[dict]) -> bool:
    """
    Chỉ công nhận khi context có quan hệ trực tiếp:
    người bán + phản hồi + X ngày/giờ.
    """
    raw = "\n".join(
        str(item.get("text", ""))
        for item in contexts
    )

    patterns = [
        r"người\s*bán.{0,140}phản\s*hồi.{0,80}\d+\s*(ngày|giờ)",
        r"phản\s*hồi.{0,80}\d+\s*(ngày|giờ).{0,140}người\s*bán",
        r"trong\s*vòng\s*\d+\s*(ngày|giờ).{0,120}phản\s*hồi",
    ]

    return any(
        re.search(pattern, raw, flags=re.IGNORECASE | re.DOTALL)
        for pattern in patterns
    )


def mostly_english(text: str) -> bool:
    """
    Phát hiện đầu ra nghiêng mạnh sang tiếng Anh.
    """
    if not text:
        return False

    english_words = re.findall(
        r"\b(the|is|are|was|were|this|that|with|from|for|and|or|not|source|according|current|provided|within|used|merchant|seller)\b",
        text.lower(),
    )
    vietnamese_words = re.findall(
        r"\b(là|của|và|được|trong|theo|người|doanh|nghiệp|phải|không|nguồn|tài|liệu|thời|hạn)\b",
        text.lower(),
    )

    return len(english_words) >= 5 and len(english_words) > len(vietnamese_words) * 1.5


def remove_prompt_leakage(text: str) -> str:
    """
    Loại các câu hướng dẫn nội bộ bị model lặp lại.
    """
    blocked_prefixes = [
        "mở đầu tự nhiên",
        "nguồn chính là",
        "yêu cầu trả lời",
        "trả lời trực tiếp bằng tiếng việt",
        "chỉ dùng thông tin trong ngữ cảnh",
        "không dùng nhãn nguồn",
    ]

    kept_lines = []

    for line in text.splitlines():
        normalized = normalize_for_match(line)

        if any(
            normalized.startswith(prefix)
            for prefix in blocked_prefixes
        ):
            continue

        kept_lines.append(line)

    cleaned = "\n".join(kept_lines)
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)

    return cleaned.strip()


def force_vietnamese_rewrite(
    original_answer: str,
    question: str,
    contexts: list[dict],
) -> str:
    """
    Gọi lại model một lần ngắn để chuyển đầu ra sang tiếng Việt,
    không bổ sung thông tin mới.
    """
    prompt = f"""
Hãy viết lại câu trả lời sau hoàn toàn bằng tiếng Việt.

QUY TẮC:
- Không thêm thông tin mới.
- Giữ nguyên endpoint, biến, tham số API và công thức.
- Không dùng tiếng Anh, trừ thuật ngữ kỹ thuật bắt buộc.
- Không nhắc đến NGUỒN 1 hoặc NGUỒN 2.
- Trả lời gọn, rõ và không kết thúc giữa câu.

CÂU HỎI:
{question}

CÂU TRẢ LỜI CẦN VIẾT LẠI:
{original_answer}

NGUỒN:
{build_context(contexts)}
""".strip()

    payload = {
        "model": OLLAMA_MODEL,
        "messages": [
            {
                "role": "system",
                "content": "Bạn chỉ làm nhiệm vụ viết lại bằng tiếng Việt, không được thêm kiến thức.",
            },
            {
                "role": "user",
                "content": prompt,
            },
        ],
        "stream": False,
        "keep_alive": OLLAMA_KEEP_ALIVE,
        "options": {
            "temperature": 0,
            "top_p": 0.8,
            "num_ctx": OLLAMA_CONTEXT,
            "num_predict": 320,
        },
    }

    try:
        http_request = request.Request(
            OLLAMA_URL,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )

        with request.urlopen(
            http_request,
            timeout=600,
        ) as response:
            data = json.loads(
                response.read().decode("utf-8")
            )

        rewritten = normalize_unicode(
            data.get("message", {}).get("content", "")
        )

        return clean_terminal_markdown(
            remove_prompt_leakage(rewritten)
        ) or original_answer

    except Exception:
        return original_answer



def sanitize_model_answer(text: str) -> str:
    """
    Làm sạch câu trả lời cuối cùng:
    - loại nguồn do model tự bịa;
    - loại prompt bị lộ;
    - giữ tiếng Việt và nội dung chính.
    """
    text = clean_terminal_markdown(
        remove_prompt_leakage(
            normalize_unicode(text)
        )
    )

    cleaned_lines = []

    for line in text.splitlines():
        normalized = normalize_for_match(line)

        if normalized.startswith("source"):
            continue

        if normalized.startswith("nguon tham khao"):
            continue

        if normalized.startswith("nguon chinh la"):
            continue

        cleaned_lines.append(line)

    cleaned = "\n".join(cleaned_lines)
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
    cleaned = re.sub(r"[ \t]{2,}", " ", cleaned)

    return cleaned.strip()


def confidence_label(score: float) -> tuple[str, int]:
    """
    Chuyển hybrid score thành mức đủ bằng chứng để phục vụ demo.
    Đây là heuristic nội bộ theo thang 0--100, không phải xác suất đúng.
    """
    bounded = max(0.0, min(1.0, score))
    percent = int(round(bounded * 100))

    if bounded >= 0.78:
        return "Cao", percent

    if bounded >= 0.58:
        return "Trung bình", percent

    return "Thấp", percent


def append_chat_log(
    query: str,
    answer: str,
    mode: str,
    retrieval_seconds: float,
    llm_seconds: float,
    top_result: SearchResult | None,
) -> None:
    """
    Ghi log phục vụ đánh giá luận văn.
    """
    LOG_PATH.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    exists = LOG_PATH.exists()
    metadata = (
        top_result.metadata
        if top_result
        else {}
    )

    with LOG_PATH.open(
        "a",
        encoding="utf-8-sig",
        newline="",
    ) as file:
        writer = csv.DictWriter(
            file,
            fieldnames=[
                "timestamp",
                "query",
                "answer",
                "mode",
                "document_id",
                "title",
                "page",
                "source_group",
                "hybrid_score",
                "retrieval_seconds",
                "llm_seconds",
            ],
        )

        if not exists:
            writer.writeheader()

        writer.writerow(
            {
                "timestamp": datetime.now().isoformat(
                    timespec="seconds"
                ),
                "query": query,
                "answer": answer,
                "mode": mode,
                "document_id": metadata.get(
                    "document_id",
                    "",
                ),
                "title": metadata.get(
                    "title",
                    "",
                ),
                "page": metadata.get(
                    "page",
                    "",
                ),
                "source_group": metadata.get(
                    "source_group",
                    "",
                ),
                "hybrid_score": (
                    round(top_result.hybrid_score, 6)
                    if top_result
                    else ""
                ),
                "retrieval_seconds": round(
                    retrieval_seconds,
                    4,
                ),
                "llm_seconds": round(
                    llm_seconds,
                    4,
                ),
            }
        )


def strip_duplicate_question(text: str) -> str:
    text = re.sub(
        r"(?i)(shop api khác gì\??)\s*\1",
        r"\1",
        text,
    )
    return re.sub(r"\s+", " ", text).strip()


def api_comparison_question(query: str) -> bool:
    normalized = normalize_for_match(query)

    return (
        "shop api" in normalized
        and (
            "merchant api" in normalized
            or "khac gi" in normalized
            or "khac nhau" in normalized
        )
    )


def deterministic_api_comparison(
    query: str,
    contexts: list[dict],
) -> str | None:
    """
    Trả lời cố định từ nội dung nguồn để tránh Qwen tự thêm Public API.
    """
    if not api_comparison_question(query):
        return None

    merged = normalize_for_match(
        "\n".join(
            str(item.get("text", ""))
            for item in contexts
        )
    )

    required = [
        "shop api",
        "merchant api",
        "shop_id",
        "merchant_id",
    ]

    if not all(term in merged for term in required):
        return None

    source = source_reference(
        contexts,
        preferred_page=str(
            contexts[0].get("metadata", {}).get("page", "")
        ).strip(),
    )

    return (
        "Khi tạo base_string, Shop API và Merchant API giống nhau ở các tham số "
        "partner_id, api_path, timestamp và access_token.\n\n"
        "Điểm khác nhau là:\n"
        "1. Shop API dùng shop_id.\n"
        "2. Merchant API dùng merchant_id.\n\n"
        "Các tham số phải được ghép đúng thứ tự trước khi tính signature. "
        "Tài liệu hiện tại không cung cấp đủ thông tin để kết luận thêm các khác biệt "
        "ngoài nội dung trên.\n\n"
        f"{source}"
    )


def subject_followup_answer(
    original_query: str,
    contexts: list[dict],
) -> str | None:
    """
    Xử lý các follow-up phổ biến bằng dữ liệu có cấu trúc,
    tránh gọi LLM khi không cần.
    """
    intent = detect_follow_up_intent(
        original_query
    )

    if intent != "purpose":
        return None

    previous = normalize_for_match(
        latest_user_question() or ""
    )
    source = source_reference(
        contexts,
        preferred_page=str(
            contexts[0].get("metadata", {}).get("page", "")
        ).strip(),
    )

    if "merchant api" in previous and "base_string" in previous:
        return (
            "base_string của Merchant API là chuỗi đầu vào dùng để tạo signature "
            "xác thực yêu cầu API. Hệ thống ghép partner_id, api_path, timestamp, "
            "access_token và merchant_id theo đúng thứ tự, rồi dùng Partner Key "
            "để tính signature bằng HMAC-SHA256.\n\n"
            "Mục đích là giúp Shopee kiểm tra yêu cầu đến từ đối tác hợp lệ "
            "và phát hiện nội dung yêu cầu bị thay đổi.\n\n"
            f"{source}"
        )

    if "shop api" in previous and "base_string" in previous:
        return (
            "base_string của Shop API là chuỗi đầu vào dùng để tạo signature "
            "xác thực yêu cầu API. Chuỗi gồm partner_id, api_path, timestamp, "
            "access_token và shop_id theo đúng thứ tự, sau đó được ký bằng "
            "Partner Key với HMAC-SHA256.\n\n"
            f"{source}"
        )

    return None


def format_debug_results(
    hybrid_results: list[SearchResult],
) -> str:
    lines = ["\n--- DEBUG RETRIEVAL ---"]

    for index, result in enumerate(
        hybrid_results[:5],
        start=1,
    ):
        metadata = result.metadata
        lines.append(
            f"{index}. {metadata.get('title', 'Không rõ')} | "
            f"trang {metadata.get('page', '')} | "
            f"Hybrid={result.hybrid_score:.4f} | "
            f"Vector={result.vector_score:.4f} | "
            f"BM25={result.bm25_score:.4f}"
        )

    return "\n".join(lines)


# ============================================================
# GIAO TIẾP CƠ BẢN
# ============================================================

def smalltalk_response(query: str) -> str | None:
    normalized = normalize_for_match(query)

    greetings = {
        "hi",
        "hello",
        "xin chao",
        "chao",
        "chao ban",
        "alo",
        "hey",
    }

    if normalized in greetings:
        return (
            "Xin chào! Tôi là trợ lý hỗ trợ doanh nghiệp bán hàng trên Shopee. "
            "Bạn có thể hỏi tôi về chính sách, phí bán hàng, trả hàng/hoàn tiền, "
            "pháp luật, thị trường và Shopee Open Platform/API."
        )

    if normalized.startswith("cam on"):
        return "Không có gì, rất vui được hỗ trợ bạn."

    if normalized in {
        "ok",
        "oke",
        "okay",
        "duoc",
        "duoc roi",
        "roi",
        "tiep",
        "tiep di",
        "hieu roi",
    }:
        return (
            "Được rồi. Bạn có thể tiếp tục hỏi về chính sách Shopee, phí, "
            "trả hàng/hoàn tiền, API, pháp luật thương mại điện tử hoặc dữ liệu shop."
        )

    if (
        normalized in {
            "ban co the giup gi",
            "ban co the giup gi cho toi",
            "ban giup duoc gi",
            "ban lam duoc gi",
            "toi co the hoi gi",
        }
        or (
            "ban" in normalized
            and "giup" in normalized
            and "gi" in normalized
        )
    ):
        return (
            "Tôi có thể tra cứu và giải thích chính sách Shopee, các loại phí, "
            "đăng bán sản phẩm, vận chuyển, trả hàng/hoàn tiền, pháp luật thương mại điện tử, "
            "báo cáo thị trường và Shopee Open Platform/API. "
            "Tôi trả lời bằng tiếng Việt và giữ nguyên endpoint, biến, tham số cùng công thức kỹ thuật."
        )

    if normalized in {"ban la ai", "ban la tro ly gi"}:
        return (
            "Tôi là chatbot RAG hỗ trợ doanh nghiệp bán hàng trên Shopee, "
            "sử dụng Hybrid Search, mở rộng ngữ cảnh và mô hình Qwen chạy cục bộ."
        )

    return None


def meta_response(query: str) -> str | None:
    normalized = normalize_for_match(query)

    if not any(
        phrase in normalized
        for phrase in [
            "nguon vua roi",
            "tai lieu vua roi",
            "lay dung nhom tai lieu",
            "ket qua vua roi lay tu dau",
        ]
    ):
        return None

    if not LAST_ANSWER_CONTEXT:
        return "Chưa có kết quả tra cứu trước đó để kiểm tra."

    first = LAST_ANSWER_CONTEXT[0]
    metadata = first.get("metadata", {})
    title = metadata.get("title", "Không rõ")
    page = metadata.get("page", "")
    group = metadata.get("source_group", "")

    result = f"Kết quả trước lấy từ nhóm `{group}`, tài liệu “{title}”"
    if page:
        result += f", trang {page}"
    return result + "."


# ============================================================
# CONTEXT EXPANSION
# ============================================================

def document_key(metadata: dict) -> str:
    return str(
        metadata.get("document_id")
        or metadata.get("source_file")
        or metadata.get("file_path")
        or metadata.get("title")
        or ""
    ).strip()


def chunk_text(chunk: dict) -> str:
    return normalize_unicode(str(chunk.get("text", ""))).strip()


def expand_context(
    top_result: SearchResult,
    chunks: list[dict],
    chunk_id_to_index: dict[str, int],
) -> list[dict]:
    """
    Lấy Top 1 rồi bổ sung các chunk liền trước/sau trong cùng tài liệu.
    Ưu tiên chunk cùng trang, sau đó mới lấy trang lân cận.
    """
    top_index = chunk_id_to_index.get(top_result.chunk_id)

    primary = {
        "chunk_id": top_result.chunk_id,
        "text": top_result.text,
        "metadata": top_result.metadata,
        "distance_from_top": 0,
    }

    if top_index is None:
        return [primary]

    top_document_key = document_key(top_result.metadata)
    top_page = str(top_result.metadata.get("page", "")).strip()

    candidates = [primary]

    for offset in range(1, NEIGHBOR_RADIUS + 1):
        for candidate_index in (
            top_index - offset,
            top_index + offset,
        ):
            if candidate_index < 0 or candidate_index >= len(chunks):
                continue

            candidate = chunks[candidate_index]
            candidate_metadata = candidate

            if document_key(candidate_metadata) != top_document_key:
                continue

            text = chunk_text(candidate)
            if not text:
                continue

            candidates.append(
                {
                    "chunk_id": str(candidate.get("chunk_id", "")),
                    "text": text,
                    "metadata": candidate_metadata,
                    "distance_from_top": offset,
                }
            )

    # Cùng trang được ưu tiên cao nhất, sau đó theo khoảng cách chunk.
    candidates.sort(
        key=lambda item: (
            0
            if str(item["metadata"].get("page", "")).strip() == top_page
            else 1,
            item["distance_from_top"],
        )
    )

    selected = []
    seen_texts = set()
    total_chars = 0

    for candidate in candidates:
        text = normalize_unicode(candidate["text"]).strip()
        fingerprint = normalize_for_match(text[:250])

        if not text or fingerprint in seen_texts:
            continue

        if (
            total_chars + len(text) > MAX_CONTEXT_CHARS
            and selected
        ):
            continue

        selected.append(candidate)
        seen_texts.add(fingerprint)
        total_chars += len(text)

        if len(selected) >= MAX_CONTEXT_CHUNKS:
            break

    return selected or [primary]


# ============================================================
# ANSWERABILITY CHECK
# ============================================================

def detect_question_type(query: str) -> str:
    normalized = normalize_for_match(query)

    if "bao lau" in normalized or "thoi han" in normalized:
        return "duration"

    if (
        "bao nhieu" in normalized
        or "muc phi" in normalized
        or "ty le" in normalized
        or "gmv" in normalized
    ):
        return "number"

    if (
        "tinh nhu the nao" in normalized
        or "cong thuc" in normalized
        or "base_string" in normalized
        or "chu ky" in normalized
    ):
        return "formula"

    if (
        "nhung san pham nao" in normalized
        or "danh sach" in normalized
        or "bi cam" in normalized
    ):
        return "list"

    if (
        "trach nhiem" in normalized
        or "nghia vu" in normalized
        or "bao ve" in normalized
    ):
        return "obligation"

    return "general"


def answerability_check(query: str, contexts: list[dict]) -> tuple[bool, str]:
    if not contexts:
        return False, "Không có ngữ cảnh."
    question_type=detect_question_type(query)
    raw_context="\n".join(str(item.get("text", "")) for item in contexts)
    normalized_context=normalize_for_match(raw_context)
    if question_type=="duration":
        has_duration=(bool(re.search(r"\b\d+\s*(ngày|giờ|tháng|năm)\b", raw_context, flags=re.IGNORECASE)) or any(p in normalized_context for p in ["trong vong","thoi han","moc thoi gian"]))
        if not has_duration:
            return False, "Tài liệu được tìm thấy chưa nêu mốc thời gian rõ ràng."
    elif question_type=="number":
        if not re.search(r"\d+(?:[.,]\d+)?\s*(%|VND|USD|tỷ|triệu|ngày)?", raw_context, flags=re.IGNORECASE):
            return False, "Tài liệu được tìm thấy chưa có số liệu trực tiếp."
    elif question_type=="formula":
        has_formula=("=" in raw_context or any(t in normalized_context for t in ["base_string","partner_id","api_path","cach tinh","cong thuc","phi xu ly giao dich","muc phi"]))
        if not has_formula:
            return False, "Tài liệu được tìm thấy chưa chứa công thức hoặc tham số cần thiết."
    elif question_type=="list":
        if not any(p in normalized_context for p in ["danh sach","bi cam","khong duoc phep","4.1","4.2","4.3"]):
            return False, "Tài liệu được tìm thấy chưa chứa danh sách trực tiếp."
    return True, ""


# ============================================================
# FAST ANSWERS
# ============================================================

def source_reference(
    contexts: list[dict],
    preferred_page: str | None = None,
) -> str:
    """
    Hiển thị nguồn đẹp, không dùng nhãn NGUỒN 1/2.
    Nếu có preferred_page thì chỉ ưu tiên trang trực tiếp chứa đáp án.
    """
    if not contexts:
        return ""

    candidates = []
    seen = set()

    for item in contexts:
        metadata = item.get("metadata", {})
        title = compact_source_name(
            str(metadata.get("title", ""))
        )
        page = str(metadata.get("page", "")).strip()

        key = (title, page)
        if key in seen:
            continue

        seen.add(key)
        candidates.append((title, page))

    if preferred_page:
        preferred = [
            item for item in candidates
            if item[1] == preferred_page
        ]
        if preferred:
            candidates = preferred

    if not candidates:
        return ""

    labels = []
    for title, page in candidates[:2]:
        label = title
        if page:
            label += f", trang {page}"
        labels.append(label)

    return "Nguồn tham khảo: " + "; ".join(labels) + "."


def fast_factual_answer(
    query: str,
    contexts: list[dict],
    original_query: str | None = None,
) -> str | None:
    if not contexts:
        return None

    if original_query and detect_follow_up_intent(original_query):
        return None

    normalized_query = normalize_for_match(query)
    merged_text = "\n".join(
        str(item.get("text", ""))
        for item in contexts
    )
    normalized_text = normalize_for_match(merged_text)
    primary_page = str(
        contexts[0].get("metadata", {}).get("page", "")
    ).strip()
    source = source_reference(
        contexts,
        preferred_page=primary_page,
    )

    if (
        "phi co dinh" in normalized_query
        and "cap" in normalized_query
        and "sac" in normalized_query
    ):
        if (
            "cap sac bo chuyen doi" in normalized_text
            and "12" in normalized_text
        ):
            return (
                "Phí Cố Định đối với nhóm cáp, sạc và bộ chuyển đổi là 12%.\n\n"
                f"{source}"
            )

    if "phi xu ly giao dich" in normalized_query:
        reconstructed = reconstruct_transaction_fee_formula(
            merged_text
        )

        if reconstructed:
            return (
                "Phí Xử Lý Giao Dịch được tính theo công thức:\n\n"
                f"{reconstructed}\n\n"
                f"{source}"
            )

        if "6%" in merged_text or "6 %" in merged_text:
            return (
                "Theo tài liệu hiện có, Phí Xử Lý Giao Dịch được tính từ "
                "giá sản phẩm trước Shopee trợ giá, phí vận chuyển Người mua trả "
                "và các khoản khuyến mãi liên quan; mức phí áp dụng là 6%.\n\n"
                f"{source}"
            )

    if "shop api" in normalized_query and "base_string" in normalized_query:
        return (
            "Shop API tạo `base_string` theo thứ tự:\n\n"
            "`partner_id + api_path + timestamp + access_token + shop_id`\n\n"
            f"{source}"
        )

    if "merchant api" in normalized_query and "base_string" in normalized_query:
        return (
            "Merchant API tạo `base_string` theo thứ tự:\n\n"
            "`partner_id + api_path + timestamp + access_token + merchant_id`\n\n"
            f"{source}"
        )

    if "chu ky" in normalized_query and "api" in normalized_query:
        return (
            "Để tạo `signature` khi gọi Shopee API, trước tiên cần tạo `base_string` "
            "theo đúng thứ tự tham số.\n\n"
            "Với Shop API:\n"
            "`partner_id + api_path + timestamp + access_token + shop_id`\n\n"
            "Với Merchant API:\n"
            "`partner_id + api_path + timestamp + access_token + merchant_id`\n\n"
            "Sau đó dùng Partner Key để tính `signature` theo HMAC-SHA256. "
            "Không thay đổi thứ tự tham số hoặc tự thêm ký tự phân cách.\n\n"
            f"{source}"
        )

    if original_query and detect_follow_up_intent(original_query) == "purpose":
        previous = latest_user_question()
        previous_normalized = normalize_for_match(previous or "")

        if "merchant api" in previous_normalized and "base_string" in previous_normalized:
            return (
                "base_string của Merchant API là chuỗi đầu vào dùng để tạo signature "
                "xác thực cho yêu cầu API. Hệ thống ghép partner_id, api_path, timestamp, "
                "access_token và merchant_id theo đúng thứ tự, sau đó dùng Partner Key "
                "để tính signature bằng HMAC-SHA256. Signature giúp Shopee kiểm tra rằng "
                "yêu cầu đến từ đối tác hợp lệ và nội dung yêu cầu không bị thay đổi.\n\n"
                f"{source}"
            )

        if "shop api" in previous_normalized and "base_string" in previous_normalized:
            return (
                "base_string của Shop API là chuỗi đầu vào dùng để tạo signature "
                "xác thực cho yêu cầu API. Chuỗi này gồm partner_id, api_path, timestamp, "
                "access_token và shop_id theo đúng thứ tự, sau đó được ký bằng Partner Key "
                "với HMAC-SHA256.\n\n"
                f"{source}"
            )

    if (
        "gmv" in normalized_query
        and "quy 4" in normalized_query
        and "2025" in normalized_query
    ):
        match = re.search(
            r"GMV was US\$(\d+(?:\.\d+)?) billion"
            r"[^.\n]{0,160}?"
            r"increasing by (\d+(?:\.\d+)?)% year-on-year",
            merged_text,
            flags=re.IGNORECASE,
        )

        if match:
            return (
                f"Trong quý 4 năm 2025, Shopee đạt GMV {match.group(1)} tỷ USD, "
                f"tăng {match.group(2)}% so với cùng kỳ năm trước.\n\n"
                f"{source}"
            )

    return None


# ============================================================
# OLLAMA
# ============================================================

def preload_ollama() -> None:
    payload = {
        "model": OLLAMA_MODEL,
        "messages": [],
        "stream": False,
        "keep_alive": OLLAMA_KEEP_ALIVE,
    }

    http_request = request.Request(
        OLLAMA_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    started = time.perf_counter()

    try:
        with request.urlopen(
            http_request,
            timeout=300,
        ) as response:
            response.read()

        print(
            f"Đã nạp model {OLLAMA_MODEL} trong "
            f"{time.perf_counter() - started:.1f} giây."
        )
    except Exception as exception:
        print(
            "Chưa preload được Ollama. "
            f"Chatbot vẫn sẽ thử kết nối khi có câu hỏi: {exception}"
        )


def build_context(contexts: list[dict]) -> str:
    blocks = []

    for index, item in enumerate(contexts, start=1):
        metadata = item.get("metadata", {})
        title = str(metadata.get("title", "")).strip()
        page = str(metadata.get("page", "")).strip()
        source_group = str(
            metadata.get("source_group", "")
        ).strip()
        text = normalize_unicode(
            str(item.get("text", ""))
        ).strip()

        header = f"[NGUỒN {index}]"
        if title:
            header += f"\nTài liệu: {title}"
        if page:
            header += f"\nTrang: {page}"
        if source_group:
            header += f"\nNhóm: {source_group}"

        blocks.append(
            f"{header}\nNội dung:\n{text}"
        )

    return "\n\n".join(blocks)


def build_answer_instruction(
    question: str,
    contexts: list[dict],
) -> str:
    question_type = detect_question_type(question)
    groups = {
        str(item.get("metadata", {}).get("source_group", ""))
        for item in contexts
    }

    titles = [
        compact_source_name(
            str(item.get("metadata", {}).get("title", ""))
        )
        for item in contexts
    ]
    main_title = titles[0] if titles else "tài liệu được cung cấp"

    instructions = [
        "Trả lời hoàn toàn bằng tiếng Việt.",
        "Chỉ dùng thông tin trong ngữ cảnh.",
        "Mở đầu tự nhiên và nêu phạm vi nguồn.",
        "Không kết thúc giữa câu.",
        "Không dùng nhãn NGUỒN 1 hoặc NGUỒN 2.",
        "Không lặp lại các câu hướng dẫn nội bộ.",
        f"Nguồn chính là: {main_title}.",
    ]

    if question_type == "duration":
        instructions.extend(
            [
                "Phân biệt rõ thời hạn phản hồi, thời hạn gửi trả và thời hạn khiếu nại.",
                "Nếu tài liệu không nêu trực tiếp thời hạn phản hồi ban đầu, phải nói rõ điều đó.",
            ]
        )
    elif question_type == "number":
        instructions.append(
            "Nêu số liệu trước, sau đó giải thích ngắn gọn."
        )
    elif question_type == "formula":
        instructions.append(
            "Giữ nguyên công thức và thứ tự tham số."
        )
    elif question_type == "list":
        instructions.append(
            "Trình bày danh sách theo các ý ngắn gọn, không chép cả đoạn dài."
        )
    elif question_type == "obligation":
        instructions.extend(
            [
                "Tổng hợp thành 3–6 nhóm trách nhiệm hoặc nghĩa vụ rõ ràng.",
                "Mỗi ý chỉ nên có một nội dung chính.",
            ]
        )

    follow_up_intent = detect_follow_up_intent(question)

    if follow_up_intent == "purpose":
        instructions.extend(
            [
                "Giải thích mục đích, vai trò và khi nào nội dung đó được sử dụng.",
                "Không chỉ lặp lại công thức hoặc danh sách tham số.",
            ]
        )
    elif follow_up_intent == "location":
        instructions.extend(
            [
                "Chỉ nêu nơi lấy hoặc nơi cấu hình nếu ngữ cảnh có thông tin trực tiếp.",
                "Nếu nguồn không nói rõ vị trí, phải nói chưa đủ dữ liệu.",
            ]
        )
    elif follow_up_intent == "comparison":
        instructions.append(
            "Nêu điểm giống và khác nhau theo từng ý rõ ràng."
        )

    normalized_question = normalize_for_match(question)
    asks_general_legal = (
        any(
            term in normalized_question
            for term in [
                "doanh nghiep",
                "phap luat",
                "trach nhiem",
                "nghia vu",
                "bao ve du lieu ca nhan",
            ]
        )
        and "legal_ecommerce" not in groups
        and "shopee_policy" in groups
    )

    if asks_general_legal:
        instructions.append(
            "Nguồn hiện có chỉ là chính sách Shopee. Phải nói rõ phạm vi này "
            "và không suy rộng thành nghĩa vụ pháp lý chung của mọi doanh nghiệp."
        )

    return "\n".join(
        f"- {item}"
        for item in instructions
    )


def call_ollama(
    question: str,
    contexts: list[dict],
) -> tuple[str, float]:
    prompt = f"""
CÂU HỎI:
{question}

LỊCH SỬ HỘI THOẠI GẦN NHẤT:
{json.dumps(CONVERSATION_HISTORY, ensure_ascii=False)}

NGỮ CẢNH:
{build_context(contexts)}

YÊU CẦU TRẢ LỜI:
{build_answer_instruction(question, contexts)}
""".strip()

    payload = {
        "model": OLLAMA_MODEL,
        "messages": [
            {
                "role": "system",
                "content": SYSTEM_PROMPT,
            },
            {
                "role": "user",
                "content": prompt,
            },
        ],
        "stream": False,
        "keep_alive": OLLAMA_KEEP_ALIVE,
        "options": {
            "temperature": 0.1,
            "top_p": 0.9,
            "num_ctx": OLLAMA_CONTEXT,
            "num_predict": OLLAMA_MAX_TOKENS,
        },
    }

    started = time.perf_counter()

    try:
        http_request = request.Request(
            OLLAMA_URL,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )

        with request.urlopen(
            http_request,
            timeout=600,
        ) as response:
            response_data = json.loads(
                response.read().decode("utf-8")
            )

        answer = clean_terminal_markdown(
            normalize_unicode(
                response_data.get("message", {}).get("content", "")
            )
        )

        answer = re.sub(
            r"(?i)\[?NGUỒN\s*\d+\]?",
            "",
            answer,
        )
        answer = re.sub(
            r"(?im)^\s*Source\s*:",
            "Nguồn tham khảo:",
            answer,
        )
        answer = re.sub(
            r"\s+,",
            ",",
            answer,
        )

        answer = remove_prompt_leakage(answer)

        if mostly_english(answer):
            answer = force_vietnamese_rewrite(
                original_answer=answer,
                question=question,
                contexts=contexts,
            )

        if answer and answer[-1] not in ".!?。":
            answer = answer.rstrip() + "."

        return (
            answer
            or "Tôi chưa có đủ dữ liệu để trả lời chắc chắn.",
            time.perf_counter() - started,
        )

    except error.HTTPError as exception:
        body = exception.read().decode(
            "utf-8",
            errors="ignore",
        )
        return (
            f"Ollama trả lỗi HTTP {exception.code}: {body[:250]}",
            time.perf_counter() - started,
        )

    except error.URLError:
        return (
            "Không kết nối được Ollama. Hãy mở Ollama và kiểm tra model local.",
            time.perf_counter() - started,
        )

    except Exception as exception:
        return (
            f"Có lỗi khi gọi mô hình local: {exception}",
            time.perf_counter() - started,
        )



def reset_conversation() -> str:
    global CONVERSATION_HISTORY
    global LAST_ANSWER_CONTEXT
    global DEBUG_MODE
    global LAST_USER_QUERY
    global LAST_ASSISTANT_ANSWER

    CONVERSATION_HISTORY = []
    LAST_ANSWER_CONTEXT = []
    LAST_USER_QUERY = ""
    LAST_ASSISTANT_ANSWER = ""

    return "Đã xóa lịch sử hội thoại hiện tại."


def exact_repeat_answer(query: str) -> str | None:
    normalized = normalize_for_match(query)

    if (
        LAST_USER_QUERY
        and LAST_ASSISTANT_ANSWER
        and normalized == normalize_for_match(LAST_USER_QUERY)
    ):
        return LAST_ASSISTANT_ANSWER

    return None


def save_last_exchange(
    user_query: str,
    assistant_answer: str,
) -> None:
    global LAST_USER_QUERY
    global LAST_ASSISTANT_ANSWER

    LAST_USER_QUERY = user_query
    LAST_ASSISTANT_ANSWER = assistant_answer


def direct_partner_key_answer(
    contexts: list[dict],
) -> str | None:
    """
    Chỉ trả lời nơi lấy Partner Key khi câu nguồn có thông tin trực tiếp.
    Không dùng suy luận tự do của mô hình.
    """
    for item in contexts:
        raw_text = normalize_unicode(
            str(item.get("text", ""))
        )
        normalized = normalize_for_match(raw_text)
        metadata = item.get("metadata", {})

        if "partner key" not in normalized:
            continue

        location_patterns = [
            r"partner key.{0,180}(detail page|app details|application details|developer console|open platform console)",
            r"(detail page|app details|application details|developer console|open platform console).{0,180}partner key",
        ]

        matched = any(
            re.search(
                pattern,
                raw_text,
                flags=re.IGNORECASE | re.DOTALL,
            )
            for pattern in location_patterns
        )

        if not matched:
            continue

        title = compact_source_name(
            str(metadata.get("title", ""))
        )
        page = str(metadata.get("page", "")).strip()
        source = title + (f", trang {page}" if page else "")

        if "detail page" in normalized or "app details" in normalized or "application details" in normalized:
            return (
                "Theo tài liệu hiện có, Partner Key được lấy tại trang chi tiết "
                "của ứng dụng trên Shopee Open Platform.\n\n"
                f"Nguồn tham khảo: {source}."
            )

        if "developer console" in normalized or "open platform console" in normalized:
            return (
                "Theo tài liệu hiện có, Partner Key được lấy trong khu vực quản lý "
                "ứng dụng trên Shopee Open Platform Console.\n\n"
                f"Nguồn tham khảo: {source}."
            )

    return None


# ============================================================
# XỬ LÝ CÂU HỎI
# ============================================================

def answer_query(
    query: str,
    embedding_model: Any,
    collection: Any,
    chunks: list[dict],
    bm25_index: Any,
    chunk_id_to_index: dict[str, int],
) -> None:
    global LAST_ANSWER_CONTEXT
    global DEBUG_MODE

    query = strip_duplicate_question(
        normalize_unicode(" ".join(query.split()))
    )

    if not query:
        print("Vui lòng nhập câu hỏi.")
        return

    normalized_command = normalize_for_match(query)

    if normalized_command in {
        "/help",
        "help",
        "tro giup",
    }:
        print(
            "\nCác lệnh hỗ trợ:\n"
            "/reset  - Xóa lịch sử hội thoại\n"
            "/debug  - Bật/tắt Top 5 retrieval\n"
            "/status - Xem trạng thái chatbot\n"
            "exit    - Thoát chương trình"
        )
        return

    if normalized_command in {
        "/status",
        "status",
    }:
        print(
            f"\nModel: {OLLAMA_MODEL}\n"
            f"Context tối đa: {OLLAMA_CONTEXT}\n"
            f"Debug: {'BẬT' if DEBUG_MODE else 'TẮT'}\n"
            f"Log: {LOG_PATH}"
        )
        return

    if normalized_command in {
        "/debug",
        "debug",
    }:
        DEBUG_MODE = not DEBUG_MODE
        print(
            "\nDebug retrieval: "
            + ("BẬT" if DEBUG_MODE else "TẮT")
        )
        return

    if normalized_command in {
        "/reset",
        "reset",
        "xoa lich su",
        "lam moi hoi thoai",
    }:
        message = reset_conversation()
        print("\n" + message)
        return

    cached = exact_repeat_answer(query)
    if cached:
        print("\n" + cached)
        print("\n[Trả lời từ bộ nhớ hội thoại]")
        return

    original_query = query
    query = build_follow_up_query(original_query)
    if query == original_query:
        query = resolve_follow_up_question(original_query)
    add_history("user", original_query)

    direct = smalltalk_response(original_query)
    if direct:
        print("\n" + direct)
        add_history("assistant", direct)
        save_last_exchange(original_query, direct)
        return

    if is_shop_data_file_followup(original_query):
        guidance = shop_data_file_guidance()
        print("\n" + guidance)
        add_history("assistant", guidance)
        save_last_exchange(original_query, guidance)
        return

    if is_out_of_scope_question(original_query):
        rejection = (
            "Câu hỏi này nằm ngoài phạm vi dữ liệu của trợ lý Shopee hiện tại. "
            "Tôi có thể hỗ trợ về chính sách Shopee, phí, trả hàng/hoàn tiền, "
            "API, pháp luật thương mại điện tử, báo cáo thị trường và dữ liệu vận hành của shop."
        )
        print("\n" + rejection)
        add_history("assistant", rejection)
        save_last_exchange(original_query, rejection)
        return

    meta = meta_response(query)
    if meta:
        print("\n" + meta)
        add_history("assistant", meta)
        return

    if business_private_data_question(query):
        rejection = (
            "Tôi chưa có dữ liệu vận hành thực tế của shop để trả lời câu hỏi này. "
            "Bạn cần bổ sung dữ liệu đơn hàng, doanh thu, chi phí, tồn kho hoặc quảng cáo của shop."
        )
        print("\n" + rejection)
        add_history("assistant", rejection)
        return

    retrieval_started = time.perf_counter()

    (
        _vector_results,
        _bm25_results,
        hybrid_results,
        retrieval_elapsed,
    ) = hybrid_search(
        query=query,
        embedding_model=embedding_model,
        collection=collection,
        chunks=chunks,
        bm25_index=bm25_index,
    )

    if not hybrid_results:
        answer = "Tôi chưa tìm thấy tài liệu phù hợp để trả lời chắc chắn."
        print("\n" + answer)
        append_chat_log(
            query=original_query,
            answer=answer,
            mode="no_retrieval_result",
            retrieval_seconds=retrieval_elapsed,
            llm_seconds=0.0,
            top_result=None,
        )
        return

    if DEBUG_MODE:
        print(
            format_debug_results(
                hybrid_results
            )
        )

    top_result = hybrid_results[0]

    contexts = expand_context(
        top_result=top_result,
        chunks=chunks,
        chunk_id_to_index=chunk_id_to_index,
    )

    LAST_ANSWER_CONTEXT = contexts

    if partner_key_location_question(original_query):
        direct_partner_answer = direct_partner_key_answer(contexts)

        if direct_partner_answer:
            print("\n" + direct_partner_answer)
            add_history("assistant", direct_partner_answer)
            save_last_exchange(
                original_query,
                direct_partner_answer,
            )
            return

        answer = (
            "Tài liệu hiện tại chưa chỉ rõ vị trí lấy Partner Key. "
            "Bạn cần bổ sung hướng dẫn chính thức của Shopee Open Platform "
            "hoặc tài liệu mô tả trang quản lý ứng dụng/đối tác. "
            "Tôi không nên suy đoán vị trí khi nguồn chưa xác nhận."
        )
        print("\n" + answer)
        add_history("assistant", answer)
        save_last_exchange(original_query, answer)
        return

    if duration_question_requires_exact_relation(original_query):
        if not has_exact_response_deadline(contexts):
            answer = (
                "Tài liệu hiện tại chưa nêu rõ thời hạn người bán phải phản hồi "
                "yêu cầu trả hàng ban đầu. Nguồn có các mốc khác như thời hạn người mua "
                "gửi trả hàng và thời hạn người bán khiếu nại, nhưng không nên dùng các mốc đó "
                "để thay thế cho thời hạn phản hồi."
            )
            print("\n" + answer)
            add_history("assistant", answer)
            save_last_exchange(original_query, answer)
            return

    deterministic = (
        subject_followup_answer(
            original_query=original_query,
            contexts=contexts,
        )
        or deterministic_api_comparison(
            query=query,
            contexts=contexts,
        )
    )

    if deterministic:
        clean_answer = clean_terminal_markdown(
            deterministic
        )
        print("\n" + clean_answer)
        add_history(
            "assistant",
            clean_answer,
        )
        save_last_exchange(
            original_query,
            clean_answer,
        )
        append_chat_log(
            query=original_query,
            answer=clean_answer,
            mode="deterministic",
            retrieval_seconds=retrieval_elapsed,
            llm_seconds=0.0,
            top_result=top_result,
        )
        return

    answerable, reason = answerability_check(
        query=query,
        contexts=contexts,
    )

    if not answerable:
        print(
            "\nTôi chưa có đủ dữ liệu để trả lời chắc chắn. "
            f"{reason}"
        )
        print(
            f"\n[Retrieval: {retrieval_elapsed:.3f}s | "
            f"Context: {len(contexts)} chunk]"
        )
        return

    fast_answer = fast_factual_answer(
        query=query,
        contexts=contexts,
        original_query=original_query,
    )

    if fast_answer:
        clean_answer = clean_terminal_markdown(fast_answer)
        print("\n" + clean_answer)
        add_history("assistant", clean_answer)
        save_last_exchange(original_query, clean_answer)
        append_chat_log(
            query=original_query,
            answer=clean_answer,
            mode="fast",
            retrieval_seconds=retrieval_elapsed,
            llm_seconds=0.0,
            top_result=top_result,
        )

        confidence_name, confidence_percent = confidence_label(
            top_result.hybrid_score
        )

        print(
            f"\n[Chế độ nhanh | Retrieval: {retrieval_elapsed:.3f}s | "
            f"Context: {len(contexts)} chunk | "
            f"Mức đủ bằng chứng nội bộ: {confidence_name} "
            f"(điểm {confidence_percent}/100, không phải xác suất đúng)]"
        )
        return

    print("\nĐang tổng hợp câu trả lời...", flush=True)

    answer, llm_elapsed = call_ollama(
        question=query,
        contexts=contexts,
    )

    answer = sanitize_model_answer(
        answer
    )

    official_source = source_reference(
        contexts,
        preferred_page=str(
            contexts[0].get("metadata", {}).get("page", "")
        ).strip(),
    )

    if official_source:
        answer = (
            answer.rstrip()
            + "\n\n"
            + official_source
        )

    print("\n" + answer)
    add_history(
        "assistant",
        answer,
    )
    save_last_exchange(
        original_query,
        answer,
    )
    append_chat_log(
        query=original_query,
        answer=answer,
        mode="llm",
        retrieval_seconds=retrieval_elapsed,
        llm_seconds=llm_elapsed,
        top_result=top_result,
    )

    confidence_name, confidence_percent = confidence_label(
        top_result.hybrid_score
    )

    print(
        f"\n[Retrieval: {retrieval_elapsed:.3f}s | "
        f"Context: {len(contexts)} chunk | "
        f"LLM: {llm_elapsed:.1f}s | "
        f"Tổng: {time.perf_counter() - retrieval_started:.1f}s | "
        f"Mức đủ bằng chứng nội bộ: {confidence_name} "
        f"(điểm {confidence_percent}/100, không phải xác suất đúng)]"
    )


def main() -> None:
    (
        embedding_model,
        collection,
        chunks,
        bm25_index,
        chunk_id_to_index,
    ) = load_hybrid_resources()

    preload_ollama()

    print("\nTRỢ LÝ SHOPEE RAG HOÀN THIỆN V4.0.1")
    print(
        "Hybrid Search + Context Expansion + Answerability Check + Qwen local."
    )
    print("Không dùng OpenAI API. Gõ /help để xem lệnh, exit để thoát.")

    if len(sys.argv) > 1:
        answer_query(
            query=" ".join(sys.argv[1:]),
            embedding_model=embedding_model,
            collection=collection,
            chunks=chunks,
            bm25_index=bm25_index,
            chunk_id_to_index=chunk_id_to_index,
        )
        return

    while True:
        try:
            query = input("\nBạn: ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\nĐã thoát.")
            break

        if normalize_for_match(query) in {
            "exit",
            "quit",
            "thoat",
        }:
            print("Đã thoát.")
            break

        answer_query(
            query=query,
            embedding_model=embedding_model,
            collection=collection,
            chunks=chunks,
            bm25_index=bm25_index,
            chunk_id_to_index=chunk_id_to_index,
        )


if __name__ == "__main__":
    main()
