"""Reusable Streamlit view for the traceable Agent demonstration.

The view keeps its history separate from the RAG chat. Operational values are
always labelled as mock data, so it cannot imply a Seller Centre connection.
"""

from __future__ import annotations

from typing import Any

import streamlit as st

from .agent_runner import AgentRunner


SUGGESTIONS = {
    "Doanh thu và phí": (
        "Tháng 8 năm 2026 shop tôi có doanh thu bao nhiêu và theo chính sách "
        "Shopee các khoản phí nào cần đối chiếu?"
    ),
    "Cảnh báo tồn kho": "Sản phẩm của tôi còn tồn kho nào dưới ngưỡng?",
    "Câu hỏi chính sách": "Phí cố định của Shopee được tính như thế nào?",
    "Ngoài phạm vi": "Thời tiết Hà Nội ngày mai thế nào?",
}


@st.cache_resource
def agent_runner() -> AgentRunner:
    """Reuse the deterministic tool runner for one Streamlit server process."""
    return AgentRunner()


def initialize_agent_state() -> None:
    """Initialize only state owned by the Agent view."""
    st.session_state.setdefault("agent_messages", [])


def _render_assistant_message(message: dict[str, Any]) -> None:
    st.markdown(str(message["answer"]))
    citations = message.get("citations", [])
    if citations:
        st.caption(
            "Nguồn truy hồi: "
            + "; ".join(
                f"{citation['title']}{', trang ' + citation['page'] if citation['page'] else ''}"
                for citation in citations
            )
        )
    with st.expander("Plan và tool trace"):
        st.json(
            {
                "plan": message.get("plan", {}),
                "trace": message.get("trace", []),
                "limitations": message.get("limitations", []),
            }
        )


def render_agent_view() -> None:
    """Render the multi-tool Agent conversation in the current page body."""
    initialize_agent_state()

    header, clear_control = st.columns([5, 1])
    with header:
        st.title("Shopee Agent demo")
        st.caption("Planner → Shop data / RAG / calculator → câu trả lời + trace")
    with clear_control:
        if st.button("Xóa", icon=":material/delete_sweep:", key="clear_agent_chat"):
            st.session_state.agent_messages = []
            st.rerun()

    st.info(
        "Dữ liệu vận hành lấy từ CSV mô phỏng trong luận văn; Agent không kết nối "
        "Seller Centre hoặc tài khoản Shopee thật.",
        icon=":material/info:",
    )

    for message in st.session_state.agent_messages:
        with st.chat_message(message["role"]):
            if message["role"] == "user":
                st.write(message["content"])
            else:
                _render_assistant_message(message)

    prompt: str | None = None
    if not st.session_state.agent_messages:
        selected = st.pills(
            "Thử một câu hỏi",
            list(SUGGESTIONS),
            selection_mode="single",
            label_visibility="collapsed",
            key="agent_suggestion",
        )
        if selected:
            prompt = SUGGESTIONS[str(selected)]

    typed_prompt = st.chat_input(
        "Hỏi về chính sách Shopee hoặc dữ liệu shop mô phỏng",
        submit_mode="disable",
        key="agent_chat_input",
    )
    if typed_prompt:
        prompt = typed_prompt

    if not prompt:
        return

    st.session_state.agent_messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.write(prompt)

    with st.chat_message("assistant"):
        try:
            with st.status(
                "Agent đang lập kế hoạch và gọi tool...",
                expanded=True,
                type="compact",
            ) as status:
                result = agent_runner().run(prompt)
                status.update(
                    label="Agent đã hoàn thành",
                    state="complete",
                    expanded=False,
                )
            _render_assistant_message(result)
        except Exception as exc:  # Keep the demo available when a tool fails.
            result = {
                "answer": "Agent gặp lỗi khi chạy tool nên chưa thể đưa ra kết quả.",
                "citations": [],
                "plan": {},
                "trace": [{"tool": "agent", "status": "error", "error": str(exc)}],
                "limitations": ["Không suy diễn kết quả khi tool gặp lỗi."],
            }
            st.error(result["answer"])

    st.session_state.agent_messages.append({"role": "assistant", **result})
