from __future__ import annotations

from typing import Any

import streamlit as st

from agent.agent_runner import AgentRunner


st.set_page_config(
    page_title="Shopee Agent Demo",
    page_icon=":material/smart_toy:",
    layout="wide",
)

SUGGESTIONS = {
    "Doanh thu và phí": "Tháng 8 năm 2026 shop tôi có doanh thu bao nhiêu và theo chính sách Shopee các khoản phí nào cần đối chiếu?",
    "Cảnh báo tồn kho": "Sản phẩm của tôi còn tồn kho nào dưới ngưỡng?",
    "Câu hỏi chính sách": "Phí cố định của Shopee được tính như thế nào?",
    "Ngoài phạm vi": "Thời tiết Hà Nội ngày mai thế nào?",
}


@st.cache_resource
def agent_runner() -> AgentRunner:
    return AgentRunner()


def initialize_state() -> None:
    st.session_state.setdefault("agent_messages", [])


def render_assistant_message(message: dict[str, Any]) -> None:
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
    with st.expander("Xem plan và tool trace"):
        st.json(
            {
                "plan": message.get("plan", {}),
                "trace": message.get("trace", []),
                "limitations": message.get("limitations", []),
            }
        )


initialize_state()

with st.sidebar:
    st.subheader("Phạm vi demo")
    st.info(
        "Dữ liệu vận hành đến từ CSV mô phỏng trong luận văn. Ứng dụng không kết nối Seller Centre hoặc tài khoản Shopee thật."
    )
    st.caption("RAG được gọi khi planner nhận diện câu hỏi chính sách/tri thức.")
    if st.button("Xóa hội thoại", icon=":material/delete_sweep:"):
        st.session_state.agent_messages = []
        st.rerun()

st.title("Shopee Agent Demo")
st.caption("Planner → Shop Data Tool / RAG Tool / Calculator Tool → answer + trace")

for message in st.session_state.agent_messages:
    with st.chat_message(message["role"]):
        if message["role"] == "user":
            st.write(message["content"])
        else:
            render_assistant_message(message)

prompt: str | None = None
if not st.session_state.agent_messages:
    selected = st.pills(
        "Thử một câu hỏi",
        list(SUGGESTIONS),
        selection_mode="single",
        label_visibility="collapsed",
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

if prompt:
    st.session_state.agent_messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.write(prompt)

    with st.chat_message("assistant"):
        with st.status("Agent đang lập kế hoạch và gọi tool...", expanded=True) as status:
            result = agent_runner().run(prompt)
            status.update(label="Agent đã hoàn thành", state="complete", expanded=False)
        render_assistant_message(result)

    st.session_state.agent_messages.append({"role": "assistant", **result})
