r"""Human-only review interface for the thesis retrieval benchmark.

Run with:
    .\.venv\Scripts\streamlit.exe run src\annotation_workbench.py
"""

from __future__ import annotations

import csv
import json
import re
import sys
from collections import Counter
from pathlib import Path
from typing import Any

import fitz
import streamlit as st


PROJECT_ROOT = Path(__file__).resolve().parents[1]
EVALUATION_DIR = PROJECT_ROOT / "src" / "evaluation"
if str(EVALUATION_DIR) not in sys.path:
    sys.path.insert(0, str(EVALUATION_DIR))

from annotation_store import (  # noqa: E402
    apply_review,
    append_review_event,
    atomic_write_jsonl,
    replace_record,
    reviewed_or_draft,
)
from audit_gold_benchmark import quality_flags, read_jsonl  # noqa: E402


CHUNKS_PATH = PROJECT_ROOT / "data" / "processed" / "chunks.jsonl"
METADATA_PATH = PROJECT_ROOT / "data" / "processed" / "metadata_generated.csv"
REVIEW_DIR = PROJECT_ROOT / "data" / "processed" / "benchmark_review"
BENCHMARKS = {
    "Draft v1 (120 câu sinh tự động)": {
        "draft_path": EVALUATION_DIR / "gold_benchmark_v1.jsonl",
        "reviewed_path": REVIEW_DIR / "gold_benchmark_v1_reviewed.jsonl",
        "journal_path": REVIEW_DIR / "gold_benchmark_v1_review_journal.jsonl",
        "description": (
            "Bản draft cũ có nhiều cờ audit; chỉ dùng để tham khảo hoặc viết lại."
        ),
    },
    "Candidate v2 (34 câu đã khớp source/page)": {
        "draft_path": EVALUATION_DIR / "benchmark_candidate_v2.jsonl",
        "reviewed_path": REVIEW_DIR / "benchmark_candidate_v2_reviewed.jsonl",
        "journal_path": REVIEW_DIR / "benchmark_candidate_v2_review_journal.jsonl",
        "description": (
            "Câu hỏi/evidence đã qua kiểm tra cơ học, nhưng vẫn cần người kiểm "
            "duyệt xem PDF gốc trước khi xác thực."
        ),
    },
}

st.set_page_config(
    page_title="Benchmark annotation workbench",
    page_icon=":material/fact_check:",
    layout="wide",
)


@st.cache_data(ttl="10m")
def load_source_catalog() -> dict[str, dict[str, str]]:
    catalog: dict[str, dict[str, str]] = {}
    with METADATA_PATH.open("r", encoding="utf-8-sig", newline="") as file:
        for row in csv.DictReader(file):
            document_id = str(row.get("document_id", "")).strip()
            file_path = str(row.get("file_path", "")).strip()
            if document_id and file_path:
                catalog[document_id] = {
                    "title": str(row.get("title", document_id)).strip(),
                    "file_path": file_path,
                }
    return catalog


@st.cache_data(ttl="10m")
def load_chunks_by_source() -> dict[tuple[str, str], list[str]]:
    chunks_by_source: dict[tuple[str, str], list[str]] = {}
    for chunk in read_jsonl(CHUNKS_PATH):
        document_id = str(chunk.get("document_id", "")).strip()
        page = str(chunk.get("page", "") or chunk.get("location", "")).strip()
        text = str(chunk.get("text", "")).strip()
        if document_id and text:
            chunks_by_source.setdefault((document_id, page), []).append(text)
    return chunks_by_source


@st.cache_data(ttl="10m")
def render_source_page(relative_path: str, page_label: str) -> tuple[bytes | None, str | None]:
    candidate = (PROJECT_ROOT / relative_path).resolve()
    raw_root = (PROJECT_ROOT / "data" / "raw").resolve()
    if raw_root not in candidate.parents or not candidate.is_file():
        return None, "Không tìm thấy tệp PDF nguồn trong data/raw."
    match = re.search(r"\d+", page_label)
    if not match:
        return None, "Nhãn trang không có số để render."
    page_number = int(match.group())
    document = fitz.open(candidate)
    try:
        if page_number < 1 or page_number > document.page_count:
            return None, f"PDF có {document.page_count} trang, không có trang {page_number}."
        pixmap = document.load_page(page_number - 1).get_pixmap(
            matrix=fitz.Matrix(1.6, 1.6), alpha=False
        )
        return pixmap.tobytes("png"), None
    finally:
        document.close()


def initialize_state(benchmark_key: str, paths: dict[str, Any]) -> tuple[str, str]:
    records_key = f"annotation_records::{benchmark_key}"
    selected_key = f"annotation_selected_id::{benchmark_key}"
    st.session_state.setdefault(
        records_key,
        reviewed_or_draft(paths["draft_path"], paths["reviewed_path"]),
    )
    records = st.session_state[records_key]
    if not records:
        raise ValueError("Benchmark không có bản ghi để kiểm duyệt.")
    st.session_state.setdefault(selected_key, records[0]["id"])
    return records_key, selected_key


def current_record(records: list[dict[str, Any]], selected_id: str) -> dict[str, Any]:
    for item in records:
        if item.get("id") == selected_id:
            return item
    raise ValueError(f"Selected benchmark id no longer exists: {selected_id}")


def review_state(item: dict[str, Any]) -> str:
    if item.get("review_status"):
        return str(item["review_status"])
    if item.get("gold_verified", False):
        return "verified"
    return "not_reviewed"


def evidence_option(source: dict[str, Any]) -> str:
    return f"{source.get('document_id', '?')} — trang {source.get('page', '?')}"


def record_label(item: dict[str, Any]) -> str:
    return f"{item['id']} · {item.get('category', 'uncategorized')} · {review_state(item)}"


catalog = load_source_catalog()
chunks_by_source = load_chunks_by_source()

with st.sidebar:
    benchmark_label = st.selectbox(
        "Bộ benchmark",
        list(BENCHMARKS),
        key="annotation_benchmark_choice",
    )
paths = BENCHMARKS[benchmark_label]
records_key, selected_key = initialize_state(benchmark_label, paths)
records = st.session_state[records_key]
states = Counter(review_state(item) for item in records)

with st.sidebar:
    st.subheader("Tiến độ kiểm duyệt")
    st.metric("Đã xác thực", states["verified"], f"/{len(records)}")
    st.metric("Cần viết lại", states["needs_rewrite"])
    st.metric("Đã loại", states["rejected"])
    st.caption(paths["description"])
    st.caption("Dữ liệu gốc không bị sửa. Bản review và nhật ký được lưu tách riêng trong data/processed/benchmark_review/.")
    split_filter = st.selectbox("Lọc tập", ["Tất cả", "dev", "test", "challenge"], key="annotation_split_filter")
    status_filter = st.selectbox(
        "Lọc trạng thái",
        ["Tất cả", "not_reviewed", "verified", "needs_rewrite", "rejected"],
        key="annotation_status_filter",
    )
    category_options = ["Tất cả"] + sorted({str(item.get("category", "")) for item in records})
    category_filter = st.selectbox("Lọc nhóm", category_options, key="annotation_category_filter")

filtered = [
    item
    for item in records
    if (split_filter == "Tất cả" or item.get("split") == split_filter)
    and (status_filter == "Tất cả" or review_state(item) == status_filter)
    and (category_filter == "Tất cả" or item.get("category") == category_filter)
]
if not filtered:
    st.warning("Không có câu hỏi nào khớp bộ lọc.")
    st.stop()

available_ids = [str(item["id"]) for item in filtered]
if st.session_state[selected_key] not in available_ids:
    st.session_state[selected_key] = available_ids[0]
record_by_id = {str(item["id"]): item for item in records}

st.title("Workbench kiểm duyệt benchmark")
st.caption("Chỉ đánh dấu verified sau khi đã xem PDF và đúng trang nguồn. Hệ thống không tự gắn nhãn gold.")
st.caption(f"Đang review: {benchmark_label}.")

selected_id = st.selectbox(
    "Chọn mẫu để kiểm duyệt",
    available_ids,
    key=selected_key,
    format_func=lambda value: record_label(record_by_id[value]),
)
item = current_record(records, selected_id)
flags = quality_flags(item, chunks_by_source)

progress_position = available_ids.index(selected_id) + 1
st.progress(progress_position / len(available_ids), text=f"Mẫu {progress_position}/{len(available_ids)} theo bộ lọc hiện tại")

left, right = st.columns((1, 1), vertical_alignment="top")
with left:
    with st.container(border=True):
        st.subheader("Nguồn và evidence")
        st.caption(
            f"ID: {item['id']} · Split: {item.get('split')} · Nhóm: {item.get('category')} · Loại: {item.get('query_type')}"
        )
        evidence = item.get("evidence", [])
        if not isinstance(evidence, list) or not evidence:
            st.error("Mẫu này không có evidence hợp lệ.")
            evidence = []
        source_options = [evidence_option(source) for source in evidence if isinstance(source, dict)]
        if source_options:
            selected_source_label = st.selectbox("Evidence để đối chiếu", source_options, key=f"source_{item['id']}")
            source = next(
                source
                for source in evidence
                if isinstance(source, dict) and evidence_option(source) == selected_source_label
            )
            document_id = str(source.get("document_id", ""))
            source_info = catalog.get(document_id)
            st.markdown(f"**Tài liệu:** {source_info['title'] if source_info else document_id}")
            st.caption(f"Mã tài liệu: {document_id} · Trang: {source.get('page', '')}")
            st.text_area(
                "Evidence hiện tại",
                value=str(source.get("support", "")),
                height=220,
                disabled=True,
                key=f"support_{item['id']}",
            )
        else:
            source_info = None
            source = {}

        if flags:
            st.warning("Audit còn cờ cần xử lý trước khi khóa: " + ", ".join(flags))
        else:
            st.success("Không còn cờ audit tự động cho bản ghi hiện tại.")

with right:
    with st.container(border=True):
        st.subheader("Trang PDF gốc")
        if source_info:
            image, error = render_source_page(source_info["file_path"], str(source.get("page", "")))
            if image:
                st.image(image, caption=source_info["file_path"])
            else:
                st.error(error or "Không thể render trang PDF.")
        else:
            st.info("Chọn một evidence có mã tài liệu để xem trang PDF.")

st.subheader("Quyết định của người kiểm duyệt")
with st.form(f"review_form_{item['id']}"):
    reviewer = st.text_input("Tên người kiểm duyệt", value=str(item.get("reviewer", "")))
    status_options = ["verified", "needs_rewrite", "rejected"]
    existing_status = review_state(item)
    status_index = status_options.index(existing_status) if existing_status in status_options else 1
    status = st.segmented_control("Kết quả", status_options, default=status_options[status_index])
    confirmed = st.checkbox(
        "Tôi đã đối chiếu tài liệu PDF gốc và đúng trang được nêu.",
        value=False,
    )
    question = st.text_area("Câu hỏi", value=str(item.get("question", "")), height=110)
    reference_answer = st.text_area(
        "Đáp án tham chiếu",
        value=str(item.get("reference_answer", "")),
        height=150,
    )
    expected_documents = st.text_input(
        "Expected documents (phân cách bằng dấu phẩy)",
        value=", ".join(str(value) for value in item.get("expected_documents", [])),
    )
    expected_pages = st.text_input(
        "Expected pages (phân cách bằng dấu phẩy)",
        value=", ".join(str(value) for value in item.get("expected_pages", [])),
    )
    evidence_text = st.text_area(
        "Evidence JSON (chỉ sửa khi cần)",
        value=json.dumps(item.get("evidence", []), ensure_ascii=False, indent=2),
        height=260,
    )
    note = st.text_area(
        "Ghi chú kiểm duyệt (tối thiểu 10 ký tự)",
        value=str(item.get("review_note", "")),
        height=100,
        placeholder="Nêu rõ đã kiểm tra điều gì, hoặc lý do cần viết lại/loại.",
    )
    submitted = st.form_submit_button("Lưu quyết định", type="primary", icon=":material/save:")

if submitted:
    try:
        parsed_evidence = json.loads(evidence_text)
        if not isinstance(parsed_evidence, list):
            raise ValueError("Evidence JSON phải là một mảng.")
        reviewed = apply_review(
            item,
            reviewer=reviewer,
            status=str(status or "needs_rewrite"),
            confirmed_original_pdf_page=confirmed,
            question=question,
            reference_answer=reference_answer,
            evidence=parsed_evidence,
            expected_documents=expected_documents.split(","),
            expected_pages=expected_pages.split(","),
            note=note,
        )
        post_review_flags = quality_flags(reviewed, chunks_by_source)
        if reviewed["gold_verified"] and post_review_flags:
            raise ValueError(
                "Không thể lưu verified khi audit còn cờ: " + ", ".join(post_review_flags)
            )
        updated_records = replace_record(records, reviewed)
        atomic_write_jsonl(paths["reviewed_path"], updated_records)
        append_review_event(paths["journal_path"], before=item, after=reviewed)
        st.session_state[records_key] = updated_records
        st.success(f"Đã lưu {item['id']} là {reviewed['review_status']}.")
        st.rerun()
    except (ValueError, json.JSONDecodeError) as exc:
        st.error(str(exc))

st.divider()
st.download_button(
    "Tải bản benchmark đang review",
    data="".join(json.dumps(row, ensure_ascii=False) + "\n" for row in records),
    file_name=f"{paths['draft_path'].stem}_reviewed_export.jsonl",
    mime="application/x-ndjson",
    icon=":material/download:",
)
