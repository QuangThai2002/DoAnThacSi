from __future__ import annotations

import json
import re
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path
from typing import Iterable


PROJECT_ROOT = Path(__file__).resolve().parents[2]
CHUNKS_PATH = PROJECT_ROOT / "data" / "processed" / "chunks.jsonl"
OUTPUT_PATH = Path(__file__).with_name("gold_benchmark_v1.jsonl")
SUMMARY_PATH = Path(__file__).with_name("gold_benchmark_v1_summary.json")

SPLITS = ["dev"] * 72 + ["test"] * 24 + ["challenge"] * 24
QUERY_TYPE_POOL = (
    ["exact"] * 25
    + ["paraphrase"] * 25
    + ["typo_noisy"] * 15
    + ["multi_document"] * 20
    + ["technical_api"] * 15
    + ["numerical_fee"] * 10
    + ["ambiguous_evidence_weak"] * 10
)
CATEGORY_POOL = (
    ["shopee_api"] * 20
    + ["fee_seller_cost"] * 20
    + ["policy_listing"] * 15
    + ["logistics_return_refund"] * 15
    + ["privacy_dispute"] * 10
    + ["vietnamese_law"] * 15
    + ["market_sea_reports"] * 15
    + ["cross_domain_synthesis"] * 10
)

DOMAIN_DOCS = {
    "shopee_api": ["SHP_API"],
    "fee_seller_cost": ["SHP_FEE", "SHP_ADS", "SHP_FIN"],
    "policy_listing": ["SHP_POL_002", "SHP_POL_003", "SHP_POL_005", "SHP_POL_006", "SHP_POL_007", "SHP_MKT", "SHP_DATA", "SHP_IP"],
    "logistics_return_refund": ["SHP_RET", "SHP_LOG"],
    "privacy_dispute": ["SHP_POL_001", "SHP_POL_004", "SHP_POL_003"],
    "vietnamese_law": ["LAW_", "LEGAL_ECOMMERCE"],
    "market_sea_reports": ["MARKET_VN", "SEA_REP", "ELECTRONICS_VN", "VECOM_PLAN"],
    "cross_domain_synthesis": ["SHP_API", "SHP_FEE", "SHP_POL", "SHP_RET", "MARKET_VN", "SEA_REP", "LAW_"],
}


def spread(values: list[str], step: int) -> list[str]:
    if len(set(values)) == 1:
        return values[:]

    if math_gcd(len(values), step) != 1:
        raise ValueError("Step must be coprime with values length.")

    return [values[(index * step) % len(values)] for index in range(len(values))]


def math_gcd(left: int, right: int) -> int:
    while right:
        left, right = right, left % right
    return abs(left)


def clean_text(text: str) -> str:
    text = re.sub(r"\s+", " ", text or "").strip()
    text = re.sub(r"\.{4,}", "...", text)
    return text


def normalize(text: str) -> str:
    text = text.replace("Đ", "D").replace("đ", "d")
    text = unicodedata.normalize("NFD", text)
    text = "".join(ch for ch in text if unicodedata.category(ch) != "Mn")
    return text.lower()


def load_chunks() -> list[dict]:
    chunks: list[dict] = []
    with CHUNKS_PATH.open("r", encoding="utf-8") as file:
        for line in file:
            line = line.strip()
            if not line:
                continue
            chunk = json.loads(line)
            text = clean_text(str(chunk.get("text", "")))
            if len(text) < 180:
                continue
            if text.count("...") > 8:
                continue
            chunk["text"] = text
            chunks.append(chunk)
    return chunks


def matches_prefix(document_id: str, prefixes: Iterable[str]) -> bool:
    return any(document_id.startswith(prefix) for prefix in prefixes)


def chunks_for_category(chunks: list[dict], category: str) -> list[dict]:
    prefixes = DOMAIN_DOCS[category]
    candidates = [
        chunk
        for chunk in chunks
        if matches_prefix(str(chunk.get("document_id", "")), prefixes)
    ]
    return sorted(
        candidates,
        key=lambda chunk: (
            str(chunk.get("document_id", "")),
            int(str(chunk.get("chunk_index", "0")) or 0),
        ),
    )


def support_snippet(text: str, limit: int = 360) -> str:
    text = clean_text(text)
    if len(text) <= limit:
        return text
    cut = text[:limit]
    breakpoint = max(cut.rfind(". "), cut.rfind("; "), cut.rfind(": "), cut.rfind(" "))
    if breakpoint > limit * 0.55:
        cut = cut[:breakpoint]
    return cut.rstrip(" .,;:") + "..."


def evidence_hint(support: str) -> str:
    normalized = clean_text(support)
    normalized = re.sub(r"[^0-9A-Za-zÀ-ỹ_/%.-]+", " ", normalized)
    words = [
        word
        for word in normalized.split()
        if len(word) >= 4 and not word.isdigit()
    ]
    if not words:
        return "đoạn này"
    return " ".join(words[:8])


def noisy(text: str) -> str:
    text = normalize(text)
    replacements = {
        "chinh sach": "chin sach",
        "thuong mai dien tu": "tmdt",
        "hoan tien": "hoan tien",
        "nguoi ban": "ng ban",
        "giao dich": "giao dich",
        "du lieu": "du lieu",
        "quang cao": "qc",
        "signature": "signatre",
        "base_string": "base strng",
    }
    for source, target in replacements.items():
        text = text.replace(source, target)
    return text


def question_for(
    category: str,
    query_type: str,
    title: str,
    page: str,
    support: str,
) -> str:
    title_lc = title[:1].lower() + title[1:]
    hint = evidence_hint(support)

    if query_type == "technical_api":
        return f"Theo tài liệu {title}, phần liên quan '{hint}' ở trang {page} mô tả điểm kỹ thuật API nào?"
    if query_type == "numerical_fee":
        return f"Trong {title}, đoạn '{hint}' ở trang {page} có số liệu hoặc mức phí nào cần chú ý?"
    if query_type == "multi_document":
        return f"Tổng hợp các điểm liên quan giữa {title_lc} và các tài liệu cùng nhóm."
    if query_type == "typo_noisy":
        return noisy(f"{title_lc} trang {page} noi gi ve {hint}")
    if query_type == "paraphrase":
        return f"Nội dung chính cần rút ra từ phần '{hint}' trong {title_lc} ở trang {page} là gì?"
    if query_type == "ambiguous_evidence_weak":
        return f"Có thể kết luận gì từ phần '{hint}' ở trang {page} của {title_lc}, và cần thận trọng ở điểm nào?"

    if category == "shopee_api":
        return f"{title} trình bày nội dung API nào liên quan '{hint}' ở trang {page}?"
    if category == "fee_seller_cost":
        return f"{title} nêu loại phí hoặc chi phí nào liên quan '{hint}' ở trang {page}?"
    if category == "logistics_return_refund":
        return f"{title} mô tả quy trình vận chuyển, trả hàng hoặc hoàn tiền nào liên quan '{hint}' ở trang {page}?"
    if category == "privacy_dispute":
        return f"{title} nêu quy định bảo mật hoặc xử lý tranh chấp nào liên quan '{hint}' ở trang {page}?"
    if category == "vietnamese_law":
        return f"Văn bản pháp luật {title_lc} nêu nội dung gì về '{hint}' ở trang {page}?"
    if category == "market_sea_reports":
        return f"Báo cáo {title_lc} cung cấp thông tin gì về '{hint}' ở trang {page}?"
    return f"Theo {title}, trang {page} nêu nội dung gì về '{hint}'?"


def make_single_item(
    index: int,
    category: str,
    query_type: str,
    split: str,
    chunk: dict,
) -> dict:
    document_id = str(chunk.get("document_id", ""))
    page = str(chunk.get("page", "") or chunk.get("location", ""))
    title = str(chunk.get("title", document_id))
    support = support_snippet(str(chunk.get("text", "")))

    return {
        "id": f"{category}_{index:03d}",
        "question": question_for(category, query_type, title, page, support),
        "category": category,
        "query_type": query_type,
        "split": split,
        "answerable": True,
        "requires_private_shop_data": False,
        "expected_documents": [document_id],
        "expected_pages": [page] if page else [],
        "reference_answer": support,
        "evidence": [
            {
                "document_id": document_id,
                "page": page,
                "support": support,
            }
        ],
        "gold_verified": False,
        "verification_note": "Auto-derived from processed chunk; needs manual source-PDF verification before locked TEST use.",
    }


def make_multi_item(
    index: int,
    category: str,
    query_type: str,
    split: str,
    chunks: list[dict],
) -> dict:
    selected: list[dict] = []
    seen: set[str] = set()
    for chunk in chunks:
        document_id = str(chunk.get("document_id", ""))
        if document_id in seen:
            continue
        selected.append(chunk)
        seen.add(document_id)
        if len(selected) >= 3:
            break

    if len(selected) < 2:
        return make_single_item(index, category, "paraphrase", split, chunks[0])

    documents = [str(chunk.get("document_id", "")) for chunk in selected]
    pages = [str(chunk.get("page", "") or chunk.get("location", "")) for chunk in selected]
    titles = [str(chunk.get("title", document_id)) for chunk, document_id in zip(selected, documents)]
    evidence = [
        {
            "document_id": document_id,
            "page": page,
            "support": support_snippet(str(chunk.get("text", "")), limit=260),
        }
        for chunk, document_id, page in zip(selected, documents, pages)
    ]
    reference_answer = " ".join(item["support"] for item in evidence)

    return {
        "id": f"{category}_{index:03d}",
        "question": f"Tổng hợp điểm chung và khác nhau giữa {', '.join(titles[:3])}.",
        "category": category,
        "query_type": query_type,
        "split": split,
        "answerable": True,
        "requires_private_shop_data": False,
        "expected_documents": documents,
        "expected_pages": [page for page in pages if page],
        "reference_answer": support_snippet(reference_answer, limit=700),
        "evidence": evidence,
        "gold_verified": False,
        "verification_note": "Auto-derived from multiple processed chunks; needs manual source-PDF verification before locked TEST use.",
    }


def build_benchmark() -> list[dict]:
    chunks = load_chunks()
    by_category = {
        category: chunks_for_category(chunks, category)
        for category in DOMAIN_DOCS
    }
    offsets = defaultdict(int)
    items: list[dict] = []
    query_types = spread(QUERY_TYPE_POOL, step=37)
    categories = spread(CATEGORY_POOL, step=41)

    for index, (split, query_type, category) in enumerate(
        zip(SPLITS, query_types, categories),
        start=1,
    ):
        candidates = by_category[category]
        if not candidates:
            raise ValueError(f"No candidates for category: {category}")

        offset = offsets[category]
        rotated = candidates[offset:] + candidates[:offset]
        offsets[category] += 3 if query_type == "multi_document" else 1

        if query_type == "multi_document" or category == "cross_domain_synthesis":
            item = make_multi_item(index, category, query_type, split, rotated)
        else:
            item = make_single_item(index, category, query_type, split, rotated[0])

        items.append(item)

    return items


def write_outputs(items: list[dict]) -> None:
    with OUTPUT_PATH.open("w", encoding="utf-8", newline="\n") as file:
        for item in items:
            file.write(json.dumps(item, ensure_ascii=False) + "\n")

    summary = {
        "total": len(items),
        "split": Counter(item["split"] for item in items),
        "query_type": Counter(item["query_type"] for item in items),
        "category": Counter(item["category"] for item in items),
        "gold_verified": Counter(str(item["gold_verified"]) for item in items),
    }
    SUMMARY_PATH.write_text(
        json.dumps(summary, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def main() -> None:
    items = build_benchmark()
    write_outputs(items)
    print(f"Wrote {len(items)} items to {OUTPUT_PATH}")
    print(f"Wrote summary to {SUMMARY_PATH}")


if __name__ == "__main__":
    main()
