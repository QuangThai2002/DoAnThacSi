from __future__ import annotations

import streamlit as st

from agent.streamlit_view import initialize_agent_state, render_agent_view


st.set_page_config(
    page_title="Shopee Agent Demo",
    page_icon=":material/smart_toy:",
    layout="wide",
)

initialize_agent_state()

with st.sidebar:
    st.subheader("Phạm vi demo")
    st.info(
        "Agent dùng CSV mô phỏng hoặc CSV bạn tải lên trong phiên hiện tại. "
        "Ứng dụng không kết nối Seller Centre hoặc tài khoản Shopee thật."
    )
    st.caption("RAG được gọi khi planner nhận diện câu hỏi chính sách/tri thức.")

render_agent_view()
