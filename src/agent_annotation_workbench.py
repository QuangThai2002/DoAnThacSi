r"""Human review workbench for the candidate Agent evaluation benchmark.

Run:
    .\.venv\Scripts\streamlit.exe run src\agent_annotation_workbench.py

The Agent may be run as a *review aid*, but it never fills or verifies a label.
Only a reviewer can save a decision, and reviewed data is written separately
from the generated candidate and accompanied by an append-only journal.
"""

from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any

import streamlit as st


PROJECT_ROOT = Path(__file__).resolve().parents[1]
EVALUATION_DIR = PROJECT_ROOT / "src" / "evaluation"
if str(EVALUATION_DIR) not in sys.path:
    sys.path.insert(0, str(EVALUATION_DIR))

from agent.agent_runner import AgentRunner  # noqa: E402
from agent_annotation_store import (  # noqa: E402
    append_review_event,
    apply_agent_review,
    atomic_write_jsonl,
    parse_delimited_values,
    replace_record,
    reviewed_or_draft,
)
from agent_eval import load_jsonl  # noqa: E402


DRAFT_PATH = EVALUATION_DIR / "agent_benchmark_candidate_v1.jsonl"
REVIEW_DIR = PROJECT_ROOT / "data" / "processed" / "agent_benchmark_review"
REVIEWED_PATH = REVIEW_DIR / "agent_benchmark_candidate_v1_reviewed.jsonl"
JOURNAL_PATH = REVIEW_DIR / "agent_benchmark_candidate_v1_review_journal.jsonl"
SUPPORTED_TOOLS = ["shop_data", "rag", "calculator"]


st.set_page_config(
    page_title="Agent benchmark review",
    page_icon=":material/fact_check:",
    layout="wide",
)


@st.cache_data(ttl="10m")
def load_document_ids() -> list[str]:
    path = PROJECT_ROOT / "data" / "processed" / "chunks.jsonl"
    if not path.is_file():
        return []
    return sorted(
        {
            str(item.get("document_id", "")).strip()
            for item in load_jsonl(path)
            if str(item.get("document_id", "")).strip()
        }
    )


@st.cache_resource
def get_runner() -> AgentRunner:
    """Construct once per server; RAG material loads only when a RAG tool runs."""
    return AgentRunner()


def review_state(item: dict[str, Any]) -> str:
    if item.get("review_status"):
        return str(item["review_status"])
    return "verified" if item.get("gold_verified", False) else "not_reviewed"


def requirements_text(item: dict[str, Any]) -> str:
    tools = set(item.get("expected_tools", []))
    requirements: list[str] = ["reviewer, intent, thứ tự tool, ghi chú"]
    if "rag" in tools:
        requirements.append("mã tài liệu citation và xác nhận đã đối chiếu nguồn")
    if tools & {"shop_data", "calculator"}:
        requirements.append("answer marker có thể kiểm tra")
    return "; ".join(requirements)


def initialize_records() -> list[dict[str, Any]]:
    st.session_state.setdefault("agent_annotation_records", reviewed_or_draft(DRAFT_PATH, REVIEWED_PATH))
    records = st.session_state["agent_annotation_records"]
    if not records:
        raise ValueError("Agent benchmark candidate does not contain any records.")
    return records


def run_as_review_aid(item: dict[str, Any]) -> None:
    """Run only after a reviewer explicitly asks; do not persist or label output."""
    with st.spinner("Đang chạy Agent để đối chiếu. Kết quả này không tự gắn nhãn gold..."):
        st.session_state[f"agent_review_run::{item['id']}"] = get_runner().run(str(item["question"]))


if not DRAFT_PATH.is_file():
    st.error("Chưa có Agent candidate. Hãy chạy generate_agent_benchmark_candidate_v1.py trước.")
    st.stop()

records = initialize_records()
states = Counter(review_state(item) for item in records)
document_ids = load_document_ids()
intents = sorted({str(item["expected_intent"]) for item in records})

with st.sidebar:
    st.header("Tiến độ kiểm duyệt")
    st.metric("Đã xác thực", states["verified"], f"/{len(records)}")
    st.metric("Cần viết lại", states["needs_rewrite"])
    st.metric("Đã loại", states["rejected"])
    st.caption("Bản candidate gốc không bị sửa. Bản review và nhật ký được lưu riêng trong data/processed/agent_benchmark_review/.")
    split_filter = st.selectbox("Lọc tập", ["Tất cả", "dev", "test", "challenge"], key="agent_review_split_filter")
    status_filter = st.selectbox(
        "Lọc trạng thái",
        ["Tất cả", "not_reviewed", "verified", "needs_rewrite", "rejected"],
        key="agent_review_status_filter",
    )
    intent_filter = st.selectbox("Lọc intent", ["Tất cả", *intents], key="agent_review_intent_filter")

filtered = [
    item
    for item in records
    if (split_filter == "Tất cả" or str(item.get("split")) == split_filter)
    and (status_filter == "Tất cả" or review_state(item) == status_filter)
    and (intent_filter == "Tất cả" or str(item.get("expected_intent")) == intent_filter)
]
if not filtered:
    st.warning("Không có mẫu phù hợp với bộ lọc hiện tại.")
    st.stop()

st.title("Workbench kiểm duyệt Agent benchmark")
st.caption(
    "Candidate có split cố định nhưng tất cả nhãn vẫn chưa được xác thực. Chỉ đánh dấu verified sau khi đối chiếu độc lập route, nguồn chính sách và dữ liệu mock."
)

record_by_id = {str(item["id"]): item for item in records}
available_ids = [str(item["id"]) for item in filtered]
selected_key = "agent_annotation_selected_id"
if st.session_state.get(selected_key) not in available_ids:
    st.session_state[selected_key] = available_ids[0]
selected_id = st.selectbox(
    "Chọn mẫu để kiểm duyệt",
    available_ids,
    key=selected_key,
    format_func=lambda value: (
        f"{value} · {record_by_id[value].get('split')} · "
        f"{record_by_id[value].get('expected_intent')} · {review_state(record_by_id[value])}"
    ),
)
item = record_by_id[selected_id]
position = available_ids.index(selected_id) + 1
st.progress(position / len(available_ids), text=f"Mẫu {position}/{len(available_ids)} theo bộ lọc hiện tại")

left, right = st.columns((1, 1), vertical_alignment="top")
with left:
    with st.container(border=True):
        st.subheader("Nhãn candidate cần kiểm tra")
        st.caption(f"ID: {item['id']} · Nhóm: {item.get('category')} · Loại: {item.get('query_type')}")
        st.markdown(f"**Câu hỏi:** {item['question']}")
        st.write("Intent candidate:", item.get("expected_intent"))
        st.write("Tool theo thứ tự:", " → ".join(item.get("expected_tools", [])) or "Không gọi tool")
        st.write("Kỳ dữ liệu:", item.get("expected_period") or "Không yêu cầu")
        st.info("Verified yêu cầu: " + requirements_text(item))

with right:
    with st.container(border=True):
        st.subheader("Chạy Agent để hỗ trợ đối chiếu")
        st.caption("Output chỉ để người review tham khảo; không được sao chép thành gold tự động.")
        if st.button("Chạy Agent cho mẫu này", key=f"run_agent_review::{item['id']}", icon=":material/play_arrow:"):
            try:
                run_as_review_aid(item)
            except Exception as exc:  # pragma: no cover - depends on local model/index
                st.error(f"Agent không chạy được: {exc}")
        result = st.session_state.get(f"agent_review_run::{item['id']}")
        if result:
            st.write("Answer preview")
            st.text_area(
                "Kết quả Agent (chỉ đọc)",
                value=str(result.get("answer", "")),
                height=160,
                disabled=True,
                key=f"agent_result_answer::{item['id']}",
            )
            with st.expander("Plan, citations và trace"):
                st.json(
                    {
                        "plan": result.get("plan"),
                        "citations": result.get("citations"),
                        "trace": result.get("trace"),
                        "limitations": result.get("limitations"),
                    }
                )

st.subheader("Quyết định của người kiểm duyệt")
with st.form(f"agent_review_form::{item['id']}"):
    reviewer = st.text_input("Tên người kiểm duyệt", value=str(item.get("reviewer", "")))
    status_options = ["verified", "needs_rewrite", "rejected"]
    current_status = review_state(item)
    status = st.segmented_control(
        "Kết quả",
        status_options,
        default=current_status if current_status in status_options else "needs_rewrite",
    )
    question = st.text_area("Câu hỏi", value=str(item.get("question", "")), height=100)
    intent_index = intents.index(str(item.get("expected_intent")))
    expected_intent = st.selectbox("Expected intent", intents, index=intent_index)
    expected_tools = st.multiselect(
        "Expected tools (thứ tự có ý nghĩa)",
        SUPPORTED_TOOLS,
        default=[tool for tool in item.get("expected_tools", []) if tool in SUPPORTED_TOOLS],
    )
    expected_period = st.text_input("Expected period (YYYY-MM, để trống nếu không yêu cầu)", value=str(item.get("expected_period") or ""))
    expected_citation_document_ids = st.multiselect(
        "Citation document IDs kỳ vọng (bắt buộc nếu có RAG)",
        document_ids,
        default=[value for value in item.get("expected_citation_document_ids", []) if value in document_ids],
    )
    confirmed_reference_source = st.checkbox(
        "Tôi đã đối chiếu độc lập tài liệu/chính sách nguồn cho citation kỳ vọng.",
        value=bool(item.get("confirmed_reference_source", False)),
    )
    answer_markers = st.text_area(
        "Answer markers (mỗi dòng hoặc dấu phẩy; bắt buộc cho shop/calculator)",
        value="\n".join(str(value) for value in item.get("expected_answer_markers", [])),
        height=90,
        placeholder="Ví dụ: 3.980.000\n3.537.200",
    )
    note = st.text_area(
        "Ghi chú kiểm duyệt (tối thiểu 10 ký tự)",
        value=str(item.get("review_note", "")),
        height=100,
        placeholder="Nêu cách bạn kiểm tra route, nguồn hoặc marker; ghi lý do nếu cần viết lại/loại.",
    )
    submitted = st.form_submit_button("Lưu quyết định", type="primary", icon=":material/save:")

if submitted:
    try:
        reviewed = apply_agent_review(
            item,
            reviewer=reviewer,
            status=str(status or "needs_rewrite"),
            question=question,
            expected_intent=expected_intent,
            expected_tools=list(expected_tools),
            expected_period=expected_period,
            expected_citation_document_ids=list(expected_citation_document_ids),
            expected_answer_markers=parse_delimited_values(answer_markers),
            confirmed_reference_source=confirmed_reference_source,
            note=note,
        )
        updated_records = replace_record(records, reviewed)
        atomic_write_jsonl(REVIEWED_PATH, updated_records)
        append_review_event(JOURNAL_PATH, before=item, after=reviewed)
        st.session_state["agent_annotation_records"] = updated_records
        st.success(f"Đã lưu {item['id']} là {reviewed['review_status']}.")
        st.rerun()
    except ValueError as exc:
        st.error(str(exc))

st.divider()
st.download_button(
    "Tải bản Agent benchmark đang review",
    data="".join(json.dumps(row, ensure_ascii=False) + "\n" for row in records),
    file_name="agent_benchmark_candidate_v1_reviewed_export.jsonl",
    mime="application/x-ndjson",
    icon=":material/download:",
)
