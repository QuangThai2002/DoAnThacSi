"""Seller-facing Streamlit UI for the thesis RAG + Agent backend.

This is intentionally separate from shopee_chat_web_v19.py so the V19 baseline
and its research UI remain unchanged.
"""

from __future__ import annotations

from pathlib import Path
import sys
from typing import Any

import altair as alt
import pandas as pd
import streamlit as st

SRC_DIR = Path(__file__).resolve().parent
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from agent.agent_runner import AgentRunner
from agent.planner import Planner
from agent.shop_data_tool import ShopDataTool, ShopDataValidationError
from agent.shop_data_library import (
    DEMO_PERIODS,
    REQUIRED_FILES as LIBRARY_REQUIRED_FILES,
    ShopDataLibrary,
    clean_and_validate_rows,
    demo_catalog,
    empty_rows,
)


st.set_page_config(
    page_title="Trợ lý bán hàng AI",
    page_icon=":material/storefront:",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
    <style>
      :root { color-scheme: light !important; }
      html, body, .stApp, [data-testid="stApp"], [data-testid="stAppViewContainer"], [data-testid="stMain"] {
        background: #fffaf8 !important; color: #2b2b2b !important;
      }
      [data-testid="stHeader"] { background: rgba(255, 255, 255, .94) !important; border-bottom: 1px solid #f5e8e3; }
      [data-testid="stSidebar"] { background: #ffffff !important; border-right: 1px solid #f1e7e2; }
      [data-testid="stSidebar"] * { color: #333333 !important; }
      [data-testid="stAppViewContainer"] p,
      [data-testid="stAppViewContainer"] li,
      [data-testid="stAppViewContainer"] span { color: #4b4b4b !important; }
      [data-testid="stAppViewContainer"] h1,
      [data-testid="stAppViewContainer"] h2,
      [data-testid="stAppViewContainer"] h3 { color: #252525 !important; }
      .block-container, .stMainBlockContainer, [data-testid="stMainBlockContainer"] {
        max-width: 1440px; padding-top: 3.25rem !important; padding-bottom: 7rem;
      }
      [data-testid="stSidebarCollapseButton"] { display: none !important; }

      /* Clear, seller-facing navigation */
      [data-testid="stSidebar"] .stButton > button {
        background: #fff1ec !important; border: 1px solid #ffd7ca !important; color: #d83f20 !important;
        border-radius: 10px !important; font-weight: 600 !important;
      }
      [data-testid="stSidebar"] .stButton > button:hover { background: #ffe5dc !important; border-color: #ee4d2d !important; }
      [data-testid="stSidebar"] [data-testid="stRadio"] label { padding: .45rem .55rem; border-radius: 8px; }
      [data-testid="stSidebar"] [data-testid="stRadio"] label:has(input:checked) {
        background: #fff0eb !important; color: #d83f20 !important; font-weight: 650;
      }
      [data-testid="stSidebar"] input[type="radio"] { accent-color: #ee4d2d !important; }
      [data-testid="stMain"] .stButton > button {
        background: #ffffff !important; border: 1px solid #f3cdbf !important; color: #c94124 !important;
        border-radius: 9px !important; font-weight: 650 !important;
      }
      [data-testid="stMain"] .stButton > button:hover { background: #fff0ea !important; border-color: #ee4d2d !important; }

      /* Keep the composer light even if a global Streamlit theme is dark. */
      [data-testid="stChatInput"], [data-testid="stChatInput"] > div, [data-testid="stChatInput"] form {
        background: #ffffff !important; border-color: #f0d5cb !important; box-shadow: 0 5px 18px rgba(115, 51, 27, .08) !important;
      }
      [data-testid="stChatInput"] textarea, [data-testid="stChatInput"] textarea::placeholder { color: #5f5f5f !important; }
      [data-testid="stChatInput"] button { background: #ee4d2d !important; color: #ffffff !important; border-radius: 8px !important; }
      [data-testid="stFileUploader"], [data-testid="stFileUploader"] section,
      [data-testid="stFileUploaderDropzone"] {
        background: #ffffff !important; border-color: #f1cfc3 !important; color: #4b4b4b !important;
      }
      [data-testid="stFileUploader"] button {
        background: #fff3ef !important; border-color: #efb9a9 !important; color: #c94124 !important;
      }
      [data-testid="stFileUploader"] small, [data-testid="stFileUploader"] span {
        color: #6b625f !important;
      }
      [data-testid="stBottom"], [data-testid="stBottom"] > div, [data-testid="stBottomBlockContainer"], .stBottom {
        background: #fffaf8 !important; border-top: 1px solid #f4e3dc !important;
      }
      [data-testid="stChatMessage"] { background: #ffffff !important; border: 1px solid #f4e7e1; border-radius: 14px; padding: .4rem .85rem; }
      [data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatarUser"]) { background: #fff3ee !important; }

      [data-testid="stPills"] { justify-content: center; }
      [data-testid="stPills"] button {
        background: #ffffff !important; border: 1px solid #f3cdbf !important; color: #c94124 !important;
        border-radius: 999px !important; font-weight: 600 !important;
      }
      [data-testid="stPills"] button:hover, [data-testid="stPills"] button[aria-pressed="true"] {
        background: #fff0ea !important; border-color: #ee4d2d !important; color: #b5371e !important;
      }
      [class*="st-key-seller_suggestion"] button {
        background: #ffffff !important; border: 1px solid #f3cdbf !important; color: #c94124 !important;
        border-radius: 999px !important; font-weight: 600 !important;
      }
      [class*="st-key-seller_suggestion"] button:hover {
        background: #fff0ea !important; border-color: #ee4d2d !important; color: #b5371e !important;
      }
      .stButton > button[kind="primary"], [data-testid="stFormSubmitButton"] > button {
        background: #ee4d2d !important; border-color: #ee4d2d !important; color: #ffffff !important;
        border-radius: 9px !important; font-weight: 650 !important;
      }
      .stButton > button[kind="primary"]:hover, [data-testid="stFormSubmitButton"] > button:hover { background: #d83f20 !important; border-color: #d83f20 !important; }

      .seller-eyebrow { color: #ee4d2d !important; font-weight: 750; font-size: .76rem; letter-spacing: .08em; }
      .seller-subtitle { color: #6b625f !important; margin-top: -.4rem; font-size: 1.05rem; }
      .empty-state {
        max-width: 690px; margin: 3.8rem auto 2.2rem; padding: 2.4rem 1.5rem;
        text-align: center; background: #ffffff; border: 1px solid #f5e5df; border-radius: 18px;
        box-shadow: 0 10px 32px rgba(122, 60, 33, .05);
      }
      .empty-state h2 { margin: 0 0 .55rem; font-size: 1.75rem; }
      .empty-state p { margin: 0; color: #756d69 !important; }
    </style>
    """,
    unsafe_allow_html=True,
)


SUGGESTIONS = {
    "learner": {
        "Các loại phí Shopee": "Shopee đang áp dụng những loại phí nào?",
        "Chính sách hoàn tiền": "Người mua có thể yêu cầu hoàn tiền trong trường hợp nào?",
        "Cách bắt đầu bán": "Người mới cần chuẩn bị gì để bắt đầu bán hàng trên Shopee?",
    },
    "owner": {
        "Doanh thu tháng này": "Doanh thu tháng này của shop thế nào?",
        "Hàng sắp hết": "Sản phẩm nào đang sắp hết hàng?",
        "Phí ảnh hưởng doanh thu": "Tháng này shop cần đối chiếu những khoản phí nào?",
    },
}
REQUIRED_FILES = ("orders.csv", "products.csv", "inventory.csv")
CHAT_TYPES = {
    "learner": {
        "name": "Người mới",
        "icon": ":material/school:",
        "description": "Tìm hiểu để mở và vận hành shop trên Shopee.",
        "placeholder": "Hỏi về cách bắt đầu bán hoặc chính sách Shopee...",
    },
    "owner": {
        "name": "Chủ shop",
        "icon": ":material/storefront:",
        "description": "Hỏi về doanh thu, chính sách và hoạt động của shop.",
        "placeholder": "Hỏi về doanh thu, tồn kho, quảng cáo hoặc phí của shop...",
    },
}


def initialise_state() -> None:
    st.session_state.setdefault("seller_messages", [])
    st.session_state.setdefault("seller_uploaded_rows", None)
    st.session_state.setdefault("seller_uploaded_names", ())
    st.session_state.setdefault("seller_upload_message", None)
    st.session_state.setdefault("seller_upload_error", None)
    st.session_state.setdefault("seller_chat_mode", None)
    st.session_state.setdefault("seller_active_chat_id", None)
    st.session_state.setdefault("seller_conversations", [])
    st.session_state.setdefault("seller_show_chat_picker", False)
    st.session_state.setdefault("seller_sidebar_compact", False)
    st.session_state.setdefault("seller_view", "chat")
    st.session_state.setdefault("seller_data_origin", None)
    st.session_state.setdefault("seller_library_scope", "owner")
    st.session_state.setdefault("seller_demo_selected_ids", [])


def active_runner() -> AgentRunner:
    uploaded_rows = st.session_state.get("seller_uploaded_rows")
    if uploaded_rows is None:
        return AgentRunner()
    return AgentRunner(shop_data_tool=ShopDataTool(uploaded_rows=uploaded_rows))


def is_uploaded() -> bool:
    return st.session_state.get("seller_uploaded_rows") is not None


def clear_active_conversation() -> None:
    st.session_state.seller_messages = []
    st.session_state.pop("seller_suggestion", None)


def conversation_title(messages: list[dict[str, Any]], mode: str) -> str:
    first_question = next((item["content"] for item in messages if item["role"] == "user"), None)
    if first_question:
        return human_title(str(first_question))
    return f"Chat {CHAT_TYPES[mode]['name'].lower()}"


def save_active_conversation() -> None:
    chat_id = st.session_state.get("seller_active_chat_id")
    mode = st.session_state.get("seller_chat_mode")
    if not chat_id or mode not in CHAT_TYPES:
        return
    messages = st.session_state.seller_messages
    for conversation in st.session_state.seller_conversations:
        if conversation["id"] == chat_id:
            conversation["messages"] = list(messages)
            conversation["title"] = conversation_title(messages, mode)
            return


def start_conversation(mode: str) -> None:
    chat_id = f"{mode}_{len(st.session_state.seller_conversations) + 1}"
    st.session_state.seller_chat_mode = mode
    st.session_state.seller_active_chat_id = chat_id
    st.session_state.seller_show_chat_picker = False
    st.session_state.seller_view = "chat"
    active_origin = st.session_state.get("seller_data_origin")
    if (mode == "owner" and active_origin == "demo_library") or (
        mode == "learner" and active_origin == "owner_library"
    ):
        st.session_state.seller_uploaded_rows = None
        st.session_state.seller_uploaded_names = ()
        st.session_state.seller_data_origin = None
    clear_active_conversation()
    st.session_state.seller_conversations.append(
        {"id": chat_id, "mode": mode, "title": conversation_title([], mode), "messages": []}
    )


def open_conversation(chat_id: str) -> None:
    conversation = next(item for item in st.session_state.seller_conversations if item["id"] == chat_id)
    st.session_state.seller_active_chat_id = conversation["id"]
    st.session_state.seller_chat_mode = conversation["mode"]
    st.session_state.seller_messages = list(conversation["messages"])
    st.session_state.seller_view = "chat"
    st.session_state.pop("seller_suggestion", None)


def show_chat_picker() -> None:
    st.session_state.seller_show_chat_picker = True


def open_data_library() -> None:
    """Open the right shelf for the active user role."""
    mode = st.session_state.get("seller_chat_mode")
    st.session_state.seller_library_scope = "demo" if mode == "learner" else "owner"
    st.session_state.seller_view = "library"


def open_chat_view() -> None:
    st.session_state.seller_view = "chat"


def toggle_sidebar_compact() -> None:
    st.session_state.seller_sidebar_compact = not st.session_state.seller_sidebar_compact


def render_sidebar_layout_css() -> None:
    if not st.session_state.seller_sidebar_compact:
        return
    st.markdown(
        """
        <style>
          [data-testid="stSidebar"] { min-width: 76px !important; max-width: 76px !important; width: 76px !important; }
          [data-testid="stSidebar"] > div:first-child { width: 76px !important; }
          [data-testid="stSidebar"] [data-testid="stSidebarContent"] { padding: .8rem .45rem !important; }
          [data-testid="stSidebar"] .stButton > button { min-height: 42px; padding: .45rem !important; }
        </style>
        """,
        unsafe_allow_html=True,
    )


def human_title(question: str) -> str:
    text = " ".join(question.split())
    return text[:44] + ("…" if len(text) > 44 else "")


def data_note(source: str | None) -> str | None:
    if source == "uploaded_csv":
        return "Dữ liệu sử dụng: báo cáo bạn tải lên trong phiên này."
    if source == "mock_shop_data":
        return "Dữ liệu sử dụng: dữ liệu mô phỏng phục vụ demo."
    if source == "demo_library":
        return "Dữ liệu sử dụng: bộ dữ liệu demo trong Thư viện dữ liệu."
    if source == "owner_library":
        return "Dữ liệu sử dụng: bảng dữ liệu cửa hàng đã lưu trên máy này."
    return None


def result_from_trace(result: dict[str, Any], suffix: str) -> dict[str, Any] | None:
    for event in result.get("trace", []):
        payload = event.get("result", {})
        if str(payload.get("tool", "")).endswith(suffix):
            return payload
    return None


def render_sources(citations: list[dict[str, str]]) -> None:
    if not citations:
        return
    with st.expander(f"Nguồn tham khảo ({len(citations)})", icon=":material/article:"):
        for citation in citations:
            page = f" — Trang {citation['page']}" if citation.get("page") else ""
            st.markdown(f"**{citation['title']}**{page}")
        st.caption("Bạn nên kiểm tra nguồn chính thức trước khi áp dụng chính sách.")


def render_metrics(result: dict[str, Any]) -> None:
    sales = result_from_trace(result, "sales_summary")
    ads = result_from_trace(result, "advertising_summary")
    inventory = result_from_trace(result, "inventory_alerts")
    if sales:
        metrics = st.columns(3)
        metrics[0].metric("Doanh thu sau phí ước tính", f"{int(sales['net_revenue_after_estimated_fees_vnd']):,} đ")
        metrics[1].metric("Đơn hoàn tất", f"{sales['completed_order_count']}")
        metrics[2].metric("GMV", f"{int(sales['gross_merchandise_value_vnd']):,} đ", help="Tổng giá trị hàng hóa đã bán trước khi trừ các khoản phí.")
    elif ads and ads.get("campaign_count"):
        metrics = st.columns(3)
        metrics[0].metric("Chi phí quảng cáo", f"{int(ads['ad_spend_vnd']):,} đ")
        metrics[1].metric("Doanh thu từ quảng cáo", f"{int(ads['attributed_revenue_vnd']):,} đ")
        metrics[2].metric("ROAS", f"{float(ads['roas']):.2f}", help="Doanh thu thu được trên mỗi 1 đồng chi cho quảng cáo.")
    elif inventory:
        st.metric("Sản phẩm cần chú ý", f"{inventory['alert_count']}")


def render_answer(message: dict[str, Any]) -> None:
    with st.chat_message("assistant", avatar=":material/smart_toy:"):
        st.markdown(str(message["answer"]))
        render_metrics(message)
        note = data_note(message.get("data_source"))
        if note:
            st.caption(":material/table_chart: " + note)
        confidence = message.get("confidence")
        if confidence:
            st.caption(f":material/verified: Độ chắc chắn: {confidence}")
        render_sources(message.get("citations", []))


def missing_data_response() -> dict[str, Any]:
    return {
        "answer": "Mình cần dữ liệu bán hàng của shop để trả lời câu hỏi này chính xác.",
        "citations": [],
        "data_source": None,
        "confidence": "Chưa đủ dữ liệu",
    }


def answer_question(question: str) -> dict[str, Any]:
    plan = Planner().plan(question)
    if plan.needs_private_shop_data and not is_uploaded():
        return missing_data_response()
    result = active_runner().run(question)
    result["confidence"] = (
        "Cao" if result.get("citations") or result.get("data_source") else "Trung bình"
    )
    origin = st.session_state.get("seller_data_origin")
    if origin in {"demo_library", "owner_library"} and result.get("data_source") == "uploaded_csv":
        result["data_source"] = origin
    return result


TABLE_SPECS = {
    "orders.csv": {
        "title": "Đơn hàng",
        "help": "Mỗi dòng là một đơn. Chỉ các đơn có trạng thái completed được tính vào doanh thu.",
        "columns": [
            "order_id", "order_date", "status", "sku", "quantity",
            "gross_merchandise_value_vnd", "seller_discount_vnd", "platform_discount_vnd",
            "estimated_transaction_fee_vnd", "estimated_service_fee_vnd",
        ],
    },
    "products.csv": {
        "title": "Sản phẩm",
        "help": "Danh mục sản phẩm và giá vốn để hệ thống ước tính hiệu quả từng mặt hàng.",
        "columns": ["sku", "product_name", "category", "cost_per_unit_vnd", "list_price_vnd"],
    },
    "inventory.csv": {
        "title": "Tồn kho",
        "help": "Tồn thực tế, lượng đã giữ chỗ và ngưỡng cần nhập thêm.",
        "columns": ["sku", "on_hand", "reserved", "reorder_point", "last_updated"],
    },
    "ads.csv": {
        "title": "Quảng cáo (tùy chọn)",
        "help": "Có thể để trống nếu shop chưa chạy quảng cáo.",
        "columns": ["campaign_id", "month", "campaign_name", "spend_vnd", "attributed_revenue_vnd", "orders"],
    },
}
COLUMN_LABELS = {
    "order_id": "Mã đơn", "order_date": "Ngày đặt", "status": "Trạng thái", "sku": "Mã SKU",
    "quantity": "Số lượng", "gross_merchandise_value_vnd": "GMV (VND)",
    "seller_discount_vnd": "Giảm giá người bán (VND)", "platform_discount_vnd": "Trợ giá sàn (VND)",
    "estimated_transaction_fee_vnd": "Phí giao dịch ước tính (VND)",
    "estimated_service_fee_vnd": "Phí dịch vụ ước tính (VND)",
    "product_name": "Tên sản phẩm", "category": "Ngành hàng", "cost_per_unit_vnd": "Giá vốn/đơn vị (VND)",
    "list_price_vnd": "Giá niêm yết (VND)", "on_hand": "Tồn thực tế", "reserved": "Đã giữ chỗ",
    "reorder_point": "Ngưỡng nhập thêm", "last_updated": "Ngày cập nhật", "campaign_id": "Mã chiến dịch",
    "month": "Tháng", "campaign_name": "Tên chiến dịch", "spend_vnd": "Chi quảng cáo (VND)",
    "attributed_revenue_vnd": "Doanh thu quy gán (VND)", "orders": "Số đơn từ quảng cáo",
}


def library_repository() -> ShopDataLibrary:
    return ShopDataLibrary()


def activate_library_data(scope: str) -> None:
    rows = library_repository().load(scope)
    if rows is None:
        st.session_state.seller_upload_error = "Hãy lưu đủ bảng dữ liệu trước khi dùng trong chat."
        return
    st.session_state.seller_uploaded_rows = rows
    st.session_state.seller_uploaded_names = tuple(rows)
    st.session_state.seller_data_origin = f"{scope}_library"
    st.session_state.seller_upload_message = (
        "Đã dùng bộ dữ liệu demo cho cuộc trò chuyện này."
        if scope == "demo"
        else "Đã dùng dữ liệu cửa hàng đã lưu cho cuộc trò chuyện này."
    )
    st.session_state.seller_view = "chat"


def editor_dataframe(rows: list[dict[str, str]], columns: list[str]) -> pd.DataFrame:
    """Keep empty data editors typed and in the intended column order."""
    if not rows:
        return pd.DataFrame({column: pd.Series(dtype="string") for column in columns})
    return pd.DataFrame(rows).reindex(columns=columns).fillna("")


def number(value: object) -> float:
    try:
        return float(str(value or 0))
    except ValueError:
        return 0.0


def currency(value: float) -> str:
    return f"{value:,.0f} đ"


def filter_dashboard_rows(
    rows: dict[str, list[dict[str, str]]], scope: str
) -> dict[str, list[dict[str, str]]]:
    """Let users read one category/product/month without changing stored data."""
    products = pd.DataFrame(rows["products.csv"])
    orders = pd.DataFrame(rows["orders.csv"])
    categories = sorted(products["category"].dropna().unique().tolist())
    months = sorted(orders["order_date"].str.slice(0, 7).dropna().unique().tolist())
    with st.expander("Lọc báo cáo", icon=":material/filter_list:"):
        category_col, month_col = st.columns(2)
        with category_col:
            selected_categories = st.multiselect(
                "Ngành hàng", categories, default=categories, key=f"dashboard_categories_{scope}"
            )
        allowed_products = products[products["category"].isin(selected_categories)]
        with month_col:
            selected_months = st.multiselect(
                "Tháng", months, default=months, key=f"dashboard_months_{scope}"
            )
        selected_skus = st.multiselect(
            "Sản phẩm", allowed_products["product_name"].tolist(),
            default=allowed_products["product_name"].tolist(), key=f"dashboard_products_{scope}"
        )
    selected_sku_values = set(
        allowed_products[allowed_products["product_name"].isin(selected_skus)]["sku"]
    )
    selected_month_values = set(selected_months)
    return {
        "products.csv": [row for row in rows["products.csv"] if row["sku"] in selected_sku_values],
        "inventory.csv": [row for row in rows["inventory.csv"] if row["sku"] in selected_sku_values],
        "orders.csv": [
            row for row in rows["orders.csv"]
            if row["sku"] in selected_sku_values and row["order_date"][:7] in selected_month_values
        ],
        "ads.csv": [row for row in rows.get("ads.csv", []) if row["month"] in selected_month_values],
    }


def render_management_dashboard(rows: dict[str, list[dict[str, str]]], scope: str) -> None:
    """Show directly usable operational views from the same saved tables."""
    rows = filter_dashboard_rows(rows, scope)
    if not rows["products.csv"] or not rows["orders.csv"]:
        st.info("Hãy chọn ít nhất một sản phẩm và một tháng để xem báo cáo.", icon=":material/info:")
        return
    tool = ShopDataTool(uploaded_rows=rows)
    sales = tool.sales_summary()
    inventory = tool.inventory_alerts()
    ads = tool.advertising_summary()

    with st.container(horizontal=True):
        st.metric("Doanh thu sau phí ước tính", currency(number(sales["net_revenue_after_estimated_fees_vnd"])), border=True)
        st.metric("Đơn hoàn tất", f"{sales['completed_order_count']}", border=True)
        st.metric("Sản phẩm cần nhập thêm", f"{inventory['alert_count']}", border=True)
        st.metric("ROAS quảng cáo", f"{number(ads['roas']):.2f}", border=True)

    orders = pd.DataFrame(rows["orders.csv"])
    completed = orders[orders["status"].str.lower() == "completed"].copy()
    for column in (
        "gross_merchandise_value_vnd", "seller_discount_vnd",
        "estimated_transaction_fee_vnd", "estimated_service_fee_vnd", "quantity",
    ):
        completed[column] = pd.to_numeric(completed[column], errors="coerce").fillna(0)
    products = pd.DataFrame(rows["products.csv"])[["sku", "product_name", "cost_per_unit_vnd"]].copy()
    products["cost_per_unit_vnd"] = pd.to_numeric(products["cost_per_unit_vnd"], errors="coerce").fillna(0)
    product_summary = completed.groupby("sku", as_index=False).agg(
        GMV=("gross_merchandise_value_vnd", "sum"),
        quantity=("quantity", "sum"),
        seller_discount=("seller_discount_vnd", "sum"),
        transaction_fee=("estimated_transaction_fee_vnd", "sum"),
        service_fee=("estimated_service_fee_vnd", "sum"),
    ).merge(products, on="sku", how="left")
    product_summary["Sản phẩm"] = product_summary["product_name"].fillna(product_summary["sku"])
    product_summary["Giá vốn ước tính"] = product_summary["quantity"] * product_summary["cost_per_unit_vnd"]
    product_summary["Lợi nhuận đóng góp ước tính"] = (
        product_summary["GMV"] - product_summary["seller_discount"]
        - product_summary["transaction_fee"] - product_summary["service_fee"]
        - product_summary["Giá vốn ước tính"]
    )

    chart_col, cost_col = st.columns(2)
    with chart_col:
        with st.container(border=True):
            st.markdown("**Doanh thu theo sản phẩm**")
            bar = alt.Chart(product_summary).mark_bar(color="#EE4D2D", cornerRadiusTopLeft=5, cornerRadiusTopRight=5).encode(
                x=alt.X("Sản phẩm:N", sort="-y", title=None),
                y=alt.Y("GMV:Q", title="GMV (VND)"),
                tooltip=[alt.Tooltip("Sản phẩm:N"), alt.Tooltip("GMV:Q", format=",.0f"), alt.Tooltip("quantity:Q", title="Số lượng")],
            )
            st.altair_chart(bar, width="stretch")
    with cost_col:
        with st.container(border=True):
            st.markdown("**Cơ cấu khoản giảm trừ**")
            cost_rows = [
                {"Khoản mục": "Giảm giá người bán", "Giá trị": number(sales["seller_discount_vnd"])},
                {"Khoản mục": "Phí giao dịch", "Giá trị": number(sales["estimated_transaction_fee_vnd"])},
                {"Khoản mục": "Phí dịch vụ", "Giá trị": number(sales["estimated_service_fee_vnd"])},
                {"Khoản mục": "Chi quảng cáo", "Giá trị": number(ads["ad_spend_vnd"])},
            ]
            cost_frame = pd.DataFrame(row for row in cost_rows if row["Giá trị"] > 0)
            if cost_frame.empty:
                st.caption("Chưa có khoản giảm trừ để vẽ biểu đồ.")
            else:
                pie = alt.Chart(cost_frame).mark_arc(innerRadius=45).encode(
                    theta=alt.Theta("Giá trị:Q"),
                    color=alt.Color("Khoản mục:N", scale=alt.Scale(range=["#EE4D2D", "#FF9B77", "#F7C65A", "#8CB7D8"])),
                    tooltip=[alt.Tooltip("Khoản mục:N"), alt.Tooltip("Giá trị:Q", format=",.0f")],
                )
                st.altair_chart(pie, width="stretch")

    completed["Tháng"] = completed["order_date"].str.slice(0, 7)
    monthly = completed.groupby("Tháng", as_index=False)["gross_merchandise_value_vnd"].sum().rename(columns={"gross_merchandise_value_vnd": "GMV"})
    with st.container(border=True):
        st.markdown("**So sánh doanh thu theo kỳ**")
        if len(monthly) > 1:
            st.bar_chart(monthly, x="Tháng", y="GMV", color="#EE4D2D")
        else:
            st.caption("Thêm đơn hàng của ít nhất hai tháng để so sánh biến động doanh thu.")

    details_col, alerts_col = st.columns(2)
    with details_col:
        with st.container(border=True):
            st.markdown("**Hiệu quả ước tính theo sản phẩm**")
            st.dataframe(
                product_summary[["Sản phẩm", "GMV", "Giá vốn ước tính", "Lợi nhuận đóng góp ước tính"]],
                hide_index=True,
                column_config={
                    "GMV": st.column_config.NumberColumn(format="%,.0f đ"),
                    "Giá vốn ước tính": st.column_config.NumberColumn(format="%,.0f đ"),
                    "Lợi nhuận đóng góp ước tính": st.column_config.NumberColumn(format="%,.0f đ"),
                },
            )
    with alerts_col:
        with st.container(border=True):
            st.markdown("**Cảnh báo tồn kho**")
            alerts = pd.DataFrame(inventory["alerts"])
            if alerts.empty:
                st.success("Không có sản phẩm nào chạm ngưỡng cần nhập thêm.", icon=":material/check_circle:")
            else:
                st.dataframe(
                    alerts[["product_name", "available_units", "reorder_point", "shortfall_units"]],
                    hide_index=True,
                    column_config={
                        "product_name": "Sản phẩm",
                        "available_units": "Có thể bán",
                        "reorder_point": "Ngưỡng nhập",
                        "shortfall_units": "Thiếu so với ngưỡng",
                    },
                )


def add_demo_category_to_selection(category_id: str) -> None:
    selected = list(st.session_state.seller_demo_selected_ids)
    if category_id and category_id not in selected:
        selected.append(category_id)
    st.session_state.seller_demo_selected_ids = selected


def render_demo_assortment_builder(
    library: ShopDataLibrary, saved_rows: dict[str, list[dict[str, str]]] | None
) -> None:
    """Let a learner choose shop categories before creating test data."""
    catalog = demo_catalog()
    catalog_by_id = {str(item["id"]): item for item in catalog}
    category_ids = list(catalog_by_id)

    st.markdown("#### Bạn muốn thử mở loại shop nào?")
    st.caption(
        "Mỗi loại shop tự tạo 5 sản phẩm phù hợp trong cùng ngành, rồi tạo đơn hàng, tồn kho và quảng cáo mô phỏng trong 12 tháng. "
        "Bạn không cần tự nhập CSV khi đang thử nghiệm."
    )
    selected_category = st.selectbox(
        "Tìm và chọn loại shop muốn test",
        category_ids,
        index=None,
        placeholder="Bấm để mở 50 loại shop, hoặc gõ tên sản phẩm/ngành hàng...",
        format_func=lambda category_id: f"{catalog_by_id[category_id]['category']} · {catalog_by_id[category_id]['product_count']} sản phẩm demo",
        key="seller_demo_category_picker",
        filter_mode="contains",
    )
    st.caption("Bấm mũi tên để xem toàn bộ 50 loại shop; khi gõ, danh sách sẽ lọc theo tên loại shop.")
    st.button(
        "Thêm loại shop này", icon=":material/add:", key="add_demo_category",
        on_click=add_demo_category_to_selection, args=(selected_category,), disabled=selected_category is None,
    )

    selected_ids = st.multiselect(
        "Loại shop được đưa vào bộ dữ liệu demo", category_ids,
        format_func=lambda category_id: f"{catalog_by_id[category_id]['category']} · {catalog_by_id[category_id]['product_count']} sản phẩm demo",
        key="seller_demo_selected_ids", placeholder="Chưa chọn loại shop nào",
    )
    if selected_ids:
        selected_catalog = pd.DataFrame([
            {
                "category": catalog_by_id[category_id]["category"],
                "product_count": catalog_by_id[category_id]["product_count"],
                "product_examples": " · ".join(str(product) for product in catalog_by_id[category_id]["product_examples"]),
            }
            for category_id in selected_ids
        ])
        total_products = int(selected_catalog["product_count"].sum())
        st.success(
            f"Đã chọn {len(selected_ids)} loại shop → sẽ có {total_products} sản phẩm mô phỏng và {total_products * len(DEMO_PERIODS):,} dòng đơn hàng trong 12 tháng.",
            icon=":material/storefront:",
        )
        st.dataframe(
            selected_catalog[["category", "product_count", "product_examples"]], hide_index=True,
            column_config={
                "category": "Loại shop", "product_count": "Số sản phẩm",
                "product_examples": "5 sản phẩm tương thích sẽ được tạo",
            },
        )
    if st.button(
        "Tạo danh mục và dữ liệu 12 tháng", icon=":material/auto_awesome:",
        key="create_selected_demo", type="primary", disabled=not selected_ids,
    ):
        library.seed_demo(selected_ids)
        total_products = sum(int(catalog_by_id[category_id]["product_count"]) for category_id in selected_ids)
        st.session_state.seller_upload_message = (
            f"Đã tạo {total_products} sản phẩm mô phỏng thuộc {len(selected_ids)} loại shop trong 12 tháng."
        )
        st.rerun()

    if saved_rows is not None:
        product_count = len(saved_rows["products.csv"])
        category_count = len({row["category"] for row in saved_rows["products.csv"]})
        st.caption(f"Bộ demo đang lưu có {product_count} sản phẩm thuộc {category_count} loại shop. Tạo bộ mới sẽ thay bộ demo cũ, không ảnh hưởng dữ liệu Chủ shop.")


def render_data_library() -> None:
    """The persistent local shop-data workspace, reached via the bookshelf."""
    st.markdown('<div class="seller-eyebrow">THƯ VIỆN DỮ LIỆU</div>', unsafe_allow_html=True)
    header, back = st.columns([8, 2], vertical_alignment="center")
    with header:
        st.title("Dữ liệu và báo cáo quản lý")
        st.caption("Tạo bảng trực tiếp, lưu trên máy này và dùng lại cho các cuộc trò chuyện.")
    with back:
        st.button("Quay lại chat", icon=":material/chat:", width="stretch", on_click=open_chat_view)

    scope = st.segmented_control(
        "Không gian dữ liệu",
        options=["demo", "owner"],
        format_func=lambda value: "Bộ demo · Người mới" if value == "demo" else "Dữ liệu shop · Chủ shop",
        key="seller_library_scope",
        required=True,
        width="stretch",
    )
    scope = str(scope or "owner")
    library = library_repository()
    saved_rows = library.load(scope)
    is_demo = scope == "demo"
    scope_title = "Bộ dữ liệu demo cho người mới" if is_demo else "Dữ liệu vận hành của chủ shop"
    scope_note = (
        "Dùng để tập thao tác, kiểm tra biểu đồ và thử các câu hỏi phân tích. Đây không phải dữ liệu shop thật."
        if is_demo
        else "Dùng để quản lý bảng do chủ shop nhập trực tiếp trên ứng dụng. Dữ liệu được lưu cục bộ trên máy này."
    )
    st.subheader(scope_title)
    st.caption(scope_note)

    if is_demo:
        st.info(
            "Danh mục có 50 loại shop đại diện cho các mảng phổ biến trên sàn. Mỗi loại tạo 5 sản phẩm tương thích. Dữ liệu là mô phỏng, "
            "không phải danh mục hoặc số liệu trực tiếp từ Shopee.",
            icon=":material/lightbulb:",
        )
        render_demo_assortment_builder(library, saved_rows)

    if saved_rows is not None:
        action_label = "Dùng bộ demo trong chat" if is_demo else "Dùng dữ liệu shop trong chat"
        st.button(action_label, icon=":material/play_circle:", type="primary", on_click=activate_library_data, args=(scope,))
        render_management_dashboard(saved_rows, scope)
        st.space("small")

    st.markdown("#### Chỉnh sửa bảng dữ liệu")
    st.caption("Nhập trực tiếp hoặc thêm/xóa dòng. Ba bảng Đơn hàng, Sản phẩm và Tồn kho là bắt buộc; Quảng cáo là tùy chọn.")
    editable_rows = saved_rows or empty_rows()
    with st.form(f"library_editor_form_{scope}", border=True):
        edited: dict[str, pd.DataFrame] = {}
        for name, spec in TABLE_SPECS.items():
            with st.expander(spec["title"], expanded=name in LIBRARY_REQUIRED_FILES and saved_rows is None, icon=":material/table_chart:"):
                st.caption(spec["help"])
                st.caption("Ngày nhập theo dạng YYYY-MM-DD; các cột tiền tệ nhập bằng số VND, không dùng dấu phẩy.")
                edited[name] = st.data_editor(
                    editor_dataframe(editable_rows.get(name, []), spec["columns"]),
                    key=f"library_editor_{scope}_{name}",
                    num_rows="dynamic",
                    hide_index=True,
                    width="stretch",
                    column_config={
                        column: st.column_config.TextColumn(COLUMN_LABELS.get(column, column))
                        for column in spec["columns"]
                    },
                )
        submitted = st.form_submit_button("Lưu bảng dữ liệu", type="primary", icon=":material/save:", width="stretch")
    if submitted:
        try:
            rows = {name: frame.to_dict("records") for name, frame in edited.items()}
            validated = clean_and_validate_rows(rows)
            library.save(scope, validated)
        except ShopDataValidationError as exc:
            st.error(str(exc), icon=":material/error:")
            return
        st.session_state.seller_upload_message = "Đã lưu bảng dữ liệu thành công."
        st.rerun()


def render_data_upload(*, inline: bool = False) -> None:
    if not inline:
        st.subheader("Dữ liệu bán hàng")
        st.caption("Dữ liệu này giúp AI phân tích hoạt động kinh doanh của shop.")

    if is_uploaded():
        rows = st.session_state.seller_uploaded_rows
        labels = {
            "orders.csv": "Đơn hàng",
            "products.csv": "Sản phẩm",
            "inventory.csv": "Tồn kho",
            "ads.csv": "Quảng cáo",
        }
        for name in st.session_state.seller_uploaded_names:
            st.success(
                f"{labels.get(name, name)} — {len(rows.get(name, []))} bản ghi — Sẵn sàng",
                icon=":material/check_circle:",
            )
        if st.button("Thay dữ liệu shop", icon=":material/upload_file:"):
            st.session_state.seller_uploaded_rows = None
            st.session_state.seller_uploaded_names = ()
            st.session_state.seller_data_origin = None
            clear_active_conversation()
            save_active_conversation()
            st.rerun()
        return

    st.info(
        "Chưa có dữ liệu shop. Thêm báo cáo để AI phân tích doanh thu, tồn kho và quảng cáo.",
        icon=":material/info:",
    )
    with st.form("seller_upload_form"):
        orders = st.file_uploader("Báo cáo đơn hàng (orders.csv)", type=["csv"])
        products = st.file_uploader("Danh mục sản phẩm (products.csv)", type=["csv"])
        inventory = st.file_uploader("Báo cáo tồn kho (inventory.csv)", type=["csv"])
        ads = st.file_uploader("Báo cáo quảng cáo (ads.csv, không bắt buộc)", type=["csv"])
        submitted = st.form_submit_button("Thêm dữ liệu", icon=":material/upload_file:", width="stretch")
    if not submitted:
        return
    files = {"orders.csv": orders, "products.csv": products, "inventory.csv": inventory, "ads.csv": ads}
    missing = [name for name in REQUIRED_FILES if files[name] is None]
    if missing:
        st.error("Bạn cần thêm đủ báo cáo: " + ", ".join(missing), icon=":material/error:")
        return
    try:
        content = {name: item.getvalue() for name, item in files.items() if item is not None}
        tool = ShopDataTool.from_uploaded_csvs(content)
    except ShopDataValidationError:
        st.error("File này chưa đúng định dạng mà hệ thống hỗ trợ. Hãy kiểm tra lại dữ liệu CSV.", icon=":material/error:")
        return
    st.session_state.seller_uploaded_rows = tool.uploaded_rows
    st.session_state.seller_uploaded_names = tuple(content)
    st.session_state.seller_data_origin = "uploaded_csv"
    if st.session_state.get("seller_chat_mode") is None:
        start_conversation("owner")
    clear_active_conversation()
    save_active_conversation()
    st.session_state.seller_upload_message = "Đã thêm dữ liệu shop thành công."
    st.rerun()


@st.dialog("Chọn loại cuộc trò chuyện")
def choose_chat_type() -> None:
    st.write("Chọn đúng vai trò để AI gợi ý câu hỏi phù hợp.")
    learner_column, owner_column = st.columns(2, gap="medium")
    with learner_column:
        with st.container(border=True):
            st.markdown("#### :material/school: Người mới tìm hiểu")
            st.caption("Dành cho người chuẩn bị tạo shop hoặc mới bắt đầu bán trên Shopee.")
            if st.button("Bắt đầu với vai trò người mới", key="choose_learner", type="primary", width="stretch"):
                start_conversation("learner")
                st.rerun()
    with owner_column:
        with st.container(border=True):
            st.markdown("#### :material/storefront: Chủ shop")
            st.caption("Dành cho chủ shop cần hỏi doanh thu, chính sách và vận hành bán hàng.")
            if st.button("Bắt đầu với vai trò chủ shop", key="choose_owner", width="stretch"):
                start_conversation("owner")
                st.rerun()


def render_assistant() -> None:
    if st.session_state.get("seller_upload_message"):
        st.toast(st.session_state.seller_upload_message, icon=":material/check_circle:")
        st.session_state.seller_upload_message = None

    mode = st.session_state.get("seller_chat_mode")
    if mode not in CHAT_TYPES or not st.session_state.get("seller_active_chat_id"):
        st.markdown('<div class="seller-eyebrow">TRỢ LÝ BÁN HÀNG AI</div>', unsafe_allow_html=True)
        st.title("Bắt đầu cuộc trò chuyện")
        st.markdown('<div class="seller-subtitle">Chọn loại cuộc trò chuyện để AI hỗ trợ đúng nhu cầu của bạn.</div>', unsafe_allow_html=True)
        st.space("small")
        with st.container(border=True):
            st.markdown("#### Bạn muốn hỏi với vai trò nào?")
            st.caption("Bạn có thể tạo nhiều cuộc trò chuyện; mỗi cuộc được đánh dấu riêng là Người mới hoặc Chủ shop.")
            st.button("Cuộc trò chuyện mới", key="new_chat_main", type="primary", icon=":material/add_comment:", on_click=show_chat_picker)
        return

    chat_type = CHAT_TYPES[mode]
    st.markdown('<div class="seller-eyebrow">TRỢ LÝ BÁN HÀNG AI</div>', unsafe_allow_html=True)
    st.subheader(f"{chat_type['icon']} {chat_type['name']}")
    st.caption(chat_type["description"])

    if mode == "owner" and not is_uploaded():
        with st.container(border=True):
            st.markdown("**Chưa có dữ liệu vận hành cho chat này**")
            st.caption("Tạo bảng trực tiếp trong Thư viện dữ liệu để quản lý và phân tích; tải CSV chỉ là lựa chọn phụ.")
            st.button("Mở thư viện dữ liệu", key="open_library_from_chat", icon=":material/auto_stories:", on_click=open_data_library)
        with st.expander("Nhập từ CSV (tùy chọn)", icon=":material/upload_file:"):
            render_data_upload(inline=True)
    elif mode == "learner" and not is_uploaded():
        st.button("Dùng bộ dữ liệu demo để thử phân tích", key="open_demo_library_from_chat", icon=":material/auto_stories:", on_click=open_data_library)

    for message in st.session_state.seller_messages:
        if message["role"] == "user":
            with st.chat_message("user", avatar=":material/person:"):
                st.write(message["content"])
        else:
            render_answer(message)

    prompt: str | None = None
    if not st.session_state.seller_messages:
        choice = st.pills("Câu hỏi gợi ý", list(SUGGESTIONS[mode]), selection_mode="single", label_visibility="collapsed", key="seller_suggestion")
        if choice:
            prompt = SUGGESTIONS[mode][str(choice)]

    typed_prompt = st.chat_input(chat_type["placeholder"], key="seller_chat_input", submit_mode="disable")
    if typed_prompt:
        prompt = typed_prompt
    if not prompt:
        return

    st.session_state.seller_messages.append({"role": "user", "content": prompt})
    with st.chat_message("user", avatar=":material/person:"):
        st.write(prompt)
    with st.chat_message("assistant", avatar=":material/smart_toy:"):
        with st.status("Đang phân tích...", expanded=False, type="compact") as status:
            try:
                result = answer_question(prompt)
                status.update(label="Đã hoàn thành", state="complete", expanded=False)
            except Exception:
                result = {
                    "answer": "Có lỗi khi xử lý yêu cầu. Vui lòng thử lại.",
                    "citations": [],
                    "data_source": None,
                    "confidence": "Chưa đủ dữ liệu",
                }
                status.update(label="Chưa thể hoàn thành", state="error", expanded=False)
        st.markdown(str(result["answer"]))
        render_metrics(result)
        note = data_note(result.get("data_source"))
        if note:
            st.caption(":material/table_chart: " + note)
        st.caption(f":material/verified: Độ chắc chắn: {result['confidence']}")
        render_sources(result.get("citations", []))
    st.session_state.seller_messages.append({"role": "assistant", **result})
    save_active_conversation()


initialise_state()
render_sidebar_layout_css()
with st.sidebar:
    compact = st.session_state.seller_sidebar_compact
    if compact:
        if st.button(" ", key="expand_sidebar", icon=":material/chevron_right:", help="Mở rộng danh sách chat", width="stretch"):
            toggle_sidebar_compact()
            st.rerun()
        st.button(" ", key="compact_new_chat", icon=":material/add_comment:", help="Cuộc trò chuyện mới", width="stretch", on_click=show_chat_picker)
        st.button(" ", key="compact_data_library", icon=":material/auto_stories:", help="Thư viện dữ liệu", width="stretch", on_click=open_data_library)
        for conversation in reversed(st.session_state.seller_conversations[-5:]):
            chat_type = CHAT_TYPES[conversation["mode"]]
            selected = conversation["id"] == st.session_state.get("seller_active_chat_id")
            label = f"{chat_type['name']} · {conversation['title']}"
            st.button(
                " ",
                key=f"compact_open_{conversation['id']}",
                icon=chat_type["icon"],
                help=label,
                width="stretch",
                disabled=selected,
                on_click=open_conversation,
                args=(conversation["id"],),
            )
    else:
        with st.container(horizontal=True, horizontal_alignment="distribute"):
            st.markdown("### :material/storefront: Trợ lý AI")
            if st.button(" ", key="collapse_sidebar", icon=":material/chevron_left:", help="Thu gọn danh sách chat"):
                toggle_sidebar_compact()
                st.rerun()
        st.button("Cuộc trò chuyện mới", icon=":material/add_comment:", width="stretch", on_click=show_chat_picker)
        st.button("Thư viện dữ liệu", key="open_data_library", icon=":material/auto_stories:", width="stretch", on_click=open_data_library)
        st.caption("Cuộc trò chuyện gần đây")
        for conversation in reversed(st.session_state.seller_conversations[-5:]):
            chat_type = CHAT_TYPES[conversation["mode"]]
            selected = conversation["id"] == st.session_state.get("seller_active_chat_id")
            label = f"{chat_type['name']} · {conversation['title']}"
            st.button(
                label,
                key=f"open_{conversation['id']}",
                icon=chat_type["icon"],
                width="stretch",
                disabled=selected,
                on_click=open_conversation,
                args=(conversation["id"],),
            )

if st.session_state.seller_show_chat_picker:
    choose_chat_type()
if st.session_state.seller_upload_error:
    st.toast(st.session_state.seller_upload_error, icon=":material/error:")
    st.session_state.seller_upload_error = None

if st.session_state.seller_view == "library":
    render_data_library()
else:
    render_assistant()
