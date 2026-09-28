"""Reusable Streamlit view for the traceable Agent demonstration.

The view keeps its history separate from the RAG chat. Operational values are
explicitly labelled as mock or session-uploaded CSV data, never Seller Centre
data.
"""

from __future__ import annotations

from typing import Any

import streamlit as st

from .agent_runner import AgentRunner
from .shop_data_tool import ShopDataTool, ShopDataValidationError


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
    st.session_state.setdefault("agent_uploaded_rows", None)
    st.session_state.setdefault("agent_uploaded_filenames", ())
    st.session_state.setdefault("agent_upload_success_message", None)
    st.session_state.setdefault("agent_upload_error", None)


def clear_agent_conversation() -> None:
    """Clear the chat and the prior suggestion selection together.

    A selected suggestion remains in Streamlit session state after a rerun. If
    it is not reset, clearing the Agent chat immediately submits the old
    suggestion again, which makes the visible clear button ineffective.
    """
    st.session_state.agent_messages = []
    st.session_state.pop("agent_suggestion", None)


def active_agent_runner() -> AgentRunner:
    """Create a per-session runner when operational CSVs were uploaded."""
    uploaded_rows = st.session_state.get("agent_uploaded_rows")
    if uploaded_rows is not None:
        return AgentRunner(shop_data_tool=ShopDataTool(uploaded_rows=uploaded_rows))
    return agent_runner()


def clear_uploaded_shop_data() -> None:
    """Return the Agent to its disclosed mock dataset."""
    st.session_state.agent_uploaded_rows = None
    st.session_state.agent_uploaded_filenames = ()
    st.session_state.agent_upload_success_message = None
    st.session_state.agent_upload_error = None
    for widget_key in (
        "agent_orders_upload",
        "agent_products_upload",
        "agent_inventory_upload",
        "agent_ads_upload",
    ):
        st.session_state.pop(widget_key, None)
    clear_agent_conversation()


def render_operational_data_controls() -> bool:
    """Render session-scoped CSV upload controls and return the active source."""
    using_uploaded_data = st.session_state.get("agent_uploaded_rows") is not None

    with st.expander(
        "Dữ liệu vận hành",
        expanded=bool(st.session_state.get("agent_upload_error")),
    ):
        if using_uploaded_data:
            if st.button(
                "Dùng lại dữ liệu mô phỏng",
                icon=":material/restart_alt:",
                key="reset_agent_uploaded_data",
            ):
                clear_uploaded_shop_data()
                st.rerun()
        else:
            st.caption(
                "Chưa có dữ liệu tải lên. Agent đang dùng CSV mô phỏng của luận văn."
            )

        st.caption(
            "Tải CSV UTF-8 theo schema mẫu. Ba file đầu là bắt buộc; ads là tùy chọn. "
            "Dữ liệu chỉ tồn tại trong phiên trình duyệt hiện tại."
        )
        st.code(
            "orders.csv: order_id, order_date, status, sku, quantity, "
            "gross_merchandise_value_vnd, seller_discount_vnd, "
            "platform_discount_vnd, estimated_transaction_fee_vnd, "
            "estimated_service_fee_vnd\n"
            "products.csv: sku, product_name, category, cost_per_unit_vnd, list_price_vnd\n"
            "inventory.csv: sku, on_hand, reserved, reorder_point, last_updated\n"
            "ads.csv (tùy chọn): campaign_id, month, campaign_name, spend_vnd, "
            "attributed_revenue_vnd, orders",
            language="text",
        )
        upload_error = st.session_state.get("agent_upload_error")
        if upload_error:
            st.error(upload_error, icon=":material/error:")

        with st.form("agent_operational_csv_upload", border=False):
            orders_file = st.file_uploader(
                "orders.csv",
                type=["csv"],
                key="agent_orders_upload",
            )
            products_file = st.file_uploader(
                "products.csv",
                type=["csv"],
                key="agent_products_upload",
            )
            inventory_file = st.file_uploader(
                "inventory.csv",
                type=["csv"],
                key="agent_inventory_upload",
            )
            ads_file = st.file_uploader(
                "ads.csv (tùy chọn)",
                type=["csv"],
                key="agent_ads_upload",
            )
            submitted = st.form_submit_button(
                "Dùng dữ liệu CSV này",
                icon=":material/upload_file:",
                width="stretch",
            )

        if submitted:
            uploaded_files = {
                "orders.csv": orders_file,
                "products.csv": products_file,
                "inventory.csv": inventory_file,
                "ads.csv": ads_file,
            }
            missing_files = [
                name
                for name in ("orders.csv", "products.csv", "inventory.csv")
                if uploaded_files[name] is None
            ]
            if missing_files:
                st.session_state.agent_upload_error = (
                    "Cần tải đủ: " + ", ".join(missing_files)
                )
                st.rerun()
            else:
                try:
                    content = {
                        name: file.getvalue()
                        for name, file in uploaded_files.items()
                        if file is not None
                    }
                    tool = ShopDataTool.from_uploaded_csvs(content)
                except ShopDataValidationError as exc:
                    st.session_state.agent_upload_error = str(exc)
                    st.rerun()
                else:
                    st.session_state.agent_uploaded_rows = tool.uploaded_rows
                    st.session_state.agent_uploaded_filenames = tuple(content)
                    st.session_state.agent_upload_success_message = (
                        "Đã nạp dữ liệu CSV thành công."
                    )
                    st.session_state.agent_upload_error = None
                    clear_agent_conversation()
                    st.rerun()

    return using_uploaded_data


def _render_assistant_message(message: dict[str, Any]) -> None:
    st.markdown(str(message["answer"]))
    data_source = message.get("data_source")
    if data_source == "uploaded_csv":
        st.caption(":material/table_chart: Dữ liệu: CSV tải lên trong phiên này.")
    elif data_source == "mock_shop_data":
        st.caption(":material/database: Dữ liệu: mô phỏng cho mục đích demo.")
    citations = message.get("citations", [])
    if citations:
        st.caption(
            ":material/article: Nguồn: "
            + "; ".join(
                f"{citation['title']}{', trang ' + citation['page'] if citation['page'] else ''}"
                for citation in citations
            )
        )
    with st.expander("Kiểm chứng và chi tiết"):
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
            clear_agent_conversation()
            st.rerun()

    render_operational_data_controls()
    success_message = st.session_state.get("agent_upload_success_message")
    if success_message:
        st.success(success_message, icon=":material/check_circle:")
        st.session_state.agent_upload_success_message = None

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
        "Hỏi về chính sách Shopee hoặc dữ liệu vận hành của shop",
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
                result = active_agent_runner().run(prompt)
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
