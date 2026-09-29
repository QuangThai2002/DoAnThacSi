"""Seller-facing Streamlit UI for the thesis RAG + Agent backend.

This is intentionally separate from shopee_chat_web_v19.py so the V19 baseline
and its research UI remain unchanged.
"""

from __future__ import annotations

from datetime import datetime
import json
import random
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
from agent.market_intelligence import (
    MARKET_SNAPSHOT_DATE,
    market_categories,
    simulated_marketplace,
)
from agent.planner import Planner
from agent.shop_data_tool import ShopDataTool, ShopDataValidationError
from agent.strategy_engine import action_plan, inventory_risk_analysis, opportunity_radar, simulate_strategy
from agent.strategy_evidence import STRATEGY_EVIDENCE
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
        min-height: 42px !important; border-radius: 10px !important; font-weight: 650 !important;
        transition: background .16s ease, transform .16s ease, box-shadow .16s ease !important;
      }
      [data-testid="stSidebar"] .stButton > button:hover {
        background: #ffe5dc !important; border-color: #ee4d2d !important;
        box-shadow: 0 4px 12px rgba(202, 72, 38, .10) !important; transform: translateY(-1px);
      }
      [data-testid="stSidebar"] [data-testid="stRadio"] label { padding: .45rem .55rem; border-radius: 8px; }
      [data-testid="stSidebar"] [data-testid="stRadio"] label:has(input:checked) {
        background: #fff0eb !important; color: #d83f20 !important; font-weight: 650;
      }
      [data-testid="stSidebar"] input[type="radio"] { accent-color: #ee4d2d !important; }
      [data-testid="stMain"] .stButton > button {
        min-height: 42px !important; padding: .55rem .9rem !important;
        background: #ffffff !important; border: 1px solid #f0c7b9 !important; color: #b93c22 !important;
        border-radius: 10px !important; font-weight: 650 !important;
        box-shadow: 0 1px 2px rgba(107, 54, 32, .04) !important;
        transition: transform .16s ease, box-shadow .16s ease, background .16s ease, border-color .16s ease !important;
      }
      [data-testid="stMain"] .stButton > button:hover {
        background: #fff4f0 !important; border-color: #ee4d2d !important;
        box-shadow: 0 5px 14px rgba(202, 72, 38, .12) !important; transform: translateY(-1px);
      }
      [data-testid="stMain"] .stButton > button:focus-visible,
      [data-testid="stSidebar"] .stButton > button:focus-visible {
        outline: 3px solid rgba(238, 77, 45, .22) !important; outline-offset: 2px !important;
      }

      /* Keep the composer light even if a global Streamlit theme is dark. */
      [data-testid="stChatInput"], [data-testid="stChatInput"] > div, [data-testid="stChatInput"] form {
        background: #ffffff !important; border-color: #f0d5cb !important; border-radius: 14px !important;
        box-shadow: 0 7px 22px rgba(115, 51, 27, .08) !important;
      }
      [data-testid="stChatInput"] textarea, [data-testid="stChatInput"] textarea::placeholder { color: #5f5f5f !important; }
      [data-testid="stChatInput"] textarea { padding: .35rem .2rem !important; }
      [data-testid="stChatInput"] button { background: #ee4d2d !important; color: #ffffff !important; border-radius: 10px !important; }
      [data-testid="stTextInput"] input, [data-testid="stTextArea"] textarea,
      [data-testid="stSelectbox"] [data-baseweb="select"] > div,
      [data-testid="stMultiSelect"] [data-baseweb="select"] > div {
        background: #ffffff !important; border-color: #edc9bd !important; border-radius: 10px !important;
        min-height: 42px !important; box-shadow: 0 1px 2px rgba(107, 54, 32, .03) !important;
      }
      [data-testid="stTextInput"] input:focus, [data-testid="stTextArea"] textarea:focus,
      [data-testid="stSelectbox"] [data-baseweb="select"] > div:focus-within,
      [data-testid="stMultiSelect"] [data-baseweb="select"] > div:focus-within {
        border-color: #ee4d2d !important; box-shadow: 0 0 0 3px rgba(238, 77, 45, .13) !important;
      }
      [data-testid="stMultiSelect"] [data-baseweb="tag"] {
        background: #fff0eb !important; border: 1px solid #ffd5c6 !important; border-radius: 999px !important;
      }
      [data-testid="stFileUploader"], [data-testid="stFileUploader"] section,
      [data-testid="stFileUploaderDropzone"] {
        background: #ffffff !important; border-color: #f1cfc3 !important; color: #4b4b4b !important;
      }
      [data-testid="stFileUploader"] button {
        min-height: 38px !important; background: #fff3ef !important; border-color: #efb9a9 !important; color: #c94124 !important;
        border-radius: 9px !important; font-weight: 650 !important;
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
      [data-testid="stTabs"] [data-baseweb="tab-list"] { gap: .35rem; }
      [data-testid="stTabs"] button[data-baseweb="tab"] {
        border-radius: 9px 9px 0 0 !important; padding: .6rem .8rem !important; font-weight: 600 !important;
      }
      [data-testid="stTabs"] button[aria-selected="true"] { color: #d83f20 !important; background: #fff2ed !important; }
      [data-testid="stSegmentedControl"] label {
        border-radius: 9px !important; padding: .45rem .75rem !important; font-weight: 600 !important;
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
        min-height: 42px !important; border-radius: 10px !important; font-weight: 700 !important;
        box-shadow: 0 6px 15px rgba(216, 63, 32, .20) !important;
      }
      .stButton > button[kind="primary"]:hover, [data-testid="stFormSubmitButton"] > button:hover {
        background: #d83f20 !important; border-color: #d83f20 !important;
        box-shadow: 0 9px 20px rgba(216, 63, 32, .27) !important; transform: translateY(-1px);
      }

      .seller-eyebrow { color: #ee4d2d !important; font-weight: 750; font-size: .76rem; letter-spacing: .08em; }
      .seller-subtitle { color: #6b625f !important; margin-top: -.4rem; font-size: 1.05rem; }
      .empty-state {
        max-width: 690px; margin: 3.8rem auto 2.2rem; padding: 2.4rem 1.5rem;
        text-align: center; background: #ffffff; border: 1px solid #f5e5df; border-radius: 18px;
        box-shadow: 0 10px 32px rgba(122, 60, 33, .05);
      }
      .empty-state h2 { margin: 0 0 .55rem; font-size: 1.75rem; }
      .empty-state p { margin: 0; color: #756d69 !important; }

      /* The market adviser remains available while the seller reads charts. */
      [class*="st-key-market_advisor_toggle"] {
        position: fixed !important; right: 2rem; bottom: 5.8rem; z-index: 1000;
      }
      [class*="st-key-market_advisor_toggle"] button {
        width: 62px !important; min-width: 62px !important; height: 62px !important; min-height: 62px !important;
        padding: 0 !important; border-radius: 50% !important; background: #ee4d2d !important;
        color: #ffffff !important; border: 2px solid #ffffff !important; box-shadow: 0 8px 24px rgba(187, 61, 31, .32) !important;
        font-size: .86rem !important; font-weight: 750 !important;
      }
      [class*="st-key-market_advisor_toggle"] button:hover { background: #d83f20 !important; transform: translateY(-2px); }
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
    st.session_state.setdefault("seller_market_scenario_seed", random.SystemRandom().randint(1, 999_999_999))
    st.session_state.setdefault("seller_market_advisor_messages", [])
    st.session_state.setdefault("seller_market_advisor_open", False)
    st.session_state.setdefault("seller_strategy_last_simulation", None)
    st.session_state.setdefault("seller_strategy_scenarios", [])
    st.session_state.setdefault("seller_strategy_experiments", [])
    st.session_state.setdefault("seller_strategy_audit_log", [])


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


def open_market_intelligence() -> None:
    """Open the transparent market-demo workspace."""
    st.session_state.seller_view = "market"


def open_strategy_workspace() -> None:
    """Open the business decision-support workspace."""
    st.session_state.seller_view = "strategy"


def refresh_market_scenario() -> None:
    """Create another reproducible-in-session seller and competitor scenario."""
    st.session_state.seller_market_scenario_seed = random.SystemRandom().randint(1, 999_999_999)
    st.session_state.seller_market_advisor_messages = []


def open_market_advisor() -> None:
    st.session_state.seller_market_advisor_open = True


def close_market_advisor() -> None:
    st.session_state.seller_market_advisor_open = False


def strategy_scenario_label(simulation: dict[str, Any]) -> str:
    bundle = "có combo" if simulation["use_bundle"] else "không combo"
    return f"{simulation['category']} · giá {int(simulation['price_change_percent']):+d}% · {bundle} · ads +{int(simulation['ad_budget_change_percent'])}%"


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


def market_advisor_response(
    question: str, category: str, marketplace: dict[str, Any], turn_index: int = 0
) -> str:
    """Give a focused, non-repetitive recommendation for this demo scene."""
    shops = list(marketplace["shops"])
    listings = list(marketplace["listings"])
    own_shop = next(item for item in shops if item["shop_type"] == "Shop của bạn")
    comparable_shops = [item for item in shops if item["shop_type"] != "Shop của bạn"]
    leader = max(comparable_shops, key=lambda item: float(item["gmv_12m_vnd"]))
    typical_price = sum(float(item["average_price_vnd"]) for item in comparable_shops) / len(comparable_shops)
    own_listings = [item for item in listings if item["shop_type"] == "Shop của bạn"]
    strongest_product = max(own_listings, key=lambda item: float(item["product_score"]))
    text = question.lower()
    price_gap = float(own_shop["average_price_vnd"]) - typical_price
    price_direction = (
        "cao hơn" if price_gap > 0 else "thấp hơn" if price_gap < 0 else "gần bằng"
    )
    average_rating = sum(float(item["rating"]) for item in comparable_shops) / len(comparable_shops)
    average_reviews = sum(int(item["review_count"]) for item in comparable_shops) / len(comparable_shops)
    rating_gap = average_rating - float(own_shop["rating"])
    alternative_actions = [
        "**Cách khác 1 — tăng niềm tin trước khi giảm giá:** ưu tiên ảnh thật, mô tả rõ công dụng/kích thước và phản hồi chat nhanh. Mục tiêu là tăng đánh giá tích cực, không phải chạy theo giá rẻ.",
        "**Cách khác 2 — tạo gói dễ mua:** ghép sản phẩm mạnh nhất với một món bổ trợ hoặc tặng ưu đãi nhỏ cho đơn thứ hai. Sau một kỳ, so GMV và lợi nhuận với phương án giảm giá trực tiếp.",
        "**Cách khác 3 — chọn một sản phẩm mũi nhọn:** chỉ quảng bá 1–2 sản phẩm có điểm cao, tối ưu trang sản phẩm của chúng trước rồi mới mở rộng sang các sản phẩm khác.",
    ]
    if any(token in text for token in ("đánh giá", "review", "sao thấp", "uy tín", "phản hồi")):
        review_gap = max(0, average_reviews - int(own_shop["review_count"]))
        return (
            f"Theo dữ liệu thị trường đang xem, điểm đánh giá của shop bạn là **{float(own_shop['rating']):.2f}/5**, "
            f"thấp hơn trung bình nhóm **{rating_gap:.2f} điểm** và ít hơn khoảng **{review_gap:,.0f} review**. "
            "Vì vậy, đây là tín hiệu rằng shop cần tăng độ tin cậy, không phải kết luận về chất lượng thật.\n\n"
            "**Nên làm trước:** chọn 1 sản phẩm bán tốt, bổ sung ảnh/mô tả dễ hiểu, kiểm tra đóng gói và chủ động xin đánh giá sau khi giao thành công. "
            "Sau 2–4 tuần, đo lại tỷ lệ đánh giá tích cực và số đơn quay lại."
        )
    if any(token in text for token in ("cách khác", "phương án khác", "còn", "nữa", "khác không")):
        return alternative_actions[turn_index % len(alternative_actions)]
    if any(token in text for token in ("giá", "định giá", "rẻ", "cao", "khuyến mãi")):
        return (
            f"Giá trung bình của shop bạn đang **{price_direction} {currency(abs(price_gap))}** so với nhóm shop tương tự. "
            f"Shop có GMV cao nhất trong nhóm là **{leader['shop_name']}** với giá trung bình "
            f"{currency(float(leader['average_price_vnd']))}.\n\n"
            "**Hướng thử trước:** không giảm giá toàn bộ. Hãy chọn 1–2 sản phẩm có điểm cao, thử ưu đãi nhỏ hoặc combo trong một kỳ, "
            "sau đó so số đơn, GMV và lợi nhuận với kỳ trước."
        )
    if any(token in text for token in ("sản phẩm", "mặt hàng", "bán gì", "ưu tiên", "tồn kho")):
        return (
            f"Sản phẩm nên ưu tiên kiểm chứng trước là **{strongest_product['product_name']}**: điểm sản phẩm "
            f"{float(strongest_product['product_score']):.1f}/100, lượng bán mô phỏng "
            f"{int(strongest_product['units_sold_12m']):,} trong 12 tháng.\n\n"
            "**Hướng thử trước:** giữ sẵn tồn kho cho sản phẩm này, kiểm tra ảnh/mô tả và thử ghép nó với một sản phẩm bổ trợ. "
            "Đây là gợi ý từ dữ liệu demo, không phải dự báo doanh số thật."
        )
    if any(token in text for token in ("doanh thu", "gmv", "yếu", "mạnh", "cạnh tranh", "shop")):
        gmv_gap = float(leader["gmv_12m_vnd"]) - float(own_shop["gmv_12m_vnd"])
        return (
            f"Mốc để học hỏi là **{leader['shop_name']}**: GMV cao hơn shop bạn {currency(gmv_gap)}, "
            f"điểm shop {float(leader['shop_score']):.1f}/100 và {int(leader['review_count']):,} lượt đánh giá.\n\n"
            "**Hướng đi:** ưu tiên tăng chất lượng trang sản phẩm và trải nghiệm sau mua để có đánh giá tốt, rồi mới mở rộng quảng cáo. "
            "So sánh từng sản phẩm ở tab “Sản phẩm cùng thị trường” để chọn nơi cần cải thiện."
        )
    if any(token in text for token in ("tóm tắt", "tổng quan", "toàn bộ")):
        return (
            f"**Bản đồ hành động cho ngành {category}:** shop bạn có {int(own_shop['listing_count'])} sản phẩm, "
            f"giá trung bình {currency(float(own_shop['average_price_vnd']))}, "
            f"GMV 12 tháng {currency(float(own_shop['gmv_12m_vnd']))} và điểm shop {float(own_shop['shop_score']):.1f}/100.\n\n"
            f"Ưu tiên hiện tại là **{strongest_product['product_name']}**; sau đó cải thiện chất lượng trang sản phẩm và đánh giá trước khi tăng quảng cáo."
        )
    return (
        f"Bạn đang xem **{category}** với 7 shop tương tự. Mình có thể phân tích riêng giá, đánh giá, doanh thu "
        "hoặc sản phẩm nên ưu tiên — hãy hỏi một phần cụ thể để nhận câu trả lời ngắn, không lặp lại toàn bộ báo cáo."
    )


def market_scene_price_summary(marketplace: dict[str, Any]) -> dict[str, Any]:
    """Calculate every displayed price comparison from the same random scene."""
    shops = list(marketplace["shops"])
    own_shop = next(item for item in shops if item["shop_type"] == "Shop của bạn")
    comparable_shops = [item for item in shops if item["shop_type"] != "Shop của bạn"]
    comparison_prices = sorted(float(item["average_price_vnd"]) for item in comparable_shops)
    own_price = float(own_shop["average_price_vnd"])
    lower_price = comparison_prices[0]
    typical_price = float(pd.Series(comparison_prices).median())
    upper_price = comparison_prices[-1]
    if own_price < lower_price:
        position = "Giá shop bạn đang thấp hơn nhóm tham chiếu"
    elif own_price > upper_price:
        position = "Giá shop bạn đang cao hơn nhóm tham chiếu"
    else:
        position = "Giá shop bạn đang nằm trong vùng cạnh tranh"
    return {
        "own_shop": own_shop,
        "references": comparable_shops,
        "lower_price_vnd": lower_price,
        "typical_price_vnd": typical_price,
        "upper_price_vnd": upper_price,
        "own_price_vnd": own_price,
        "position": position,
    }


@st.dialog("Chiến lược gia AI", width="large")
def render_market_advisor_dialog(category: str, marketplace: dict[str, Any]) -> None:
    st.caption("Hỏi về giá, sản phẩm hoặc hướng phát triển. Chiến lược gia AI sẽ dùng dữ liệu thị trường đang xem để đề xuất bước nên làm tiếp theo.")
    messages: list[dict[str, str]] = st.session_state.seller_market_advisor_messages
    if not messages:
        st.info("Gợi ý: hỏi về cách đặt giá, sản phẩm nên ưu tiên hoặc điểm cần cải thiện của shop.", icon=":material/auto_awesome:")
        suggestion_columns = st.columns(3)
        suggestions = [
            "Tôi nên điều chỉnh giá thế nào?",
            "Sản phẩm nào nên ưu tiên?",
            "Shop tôi đang yếu ở đâu?",
        ]
        for column, suggestion in zip(suggestion_columns, suggestions):
            with column:
                if st.button(suggestion, key=f"market_advisor_suggestion_{suggestions.index(suggestion)}", width="stretch"):
                    messages.extend([
                        {"role": "user", "content": suggestion},
                        {"role": "assistant", "content": market_advisor_response(suggestion, category, marketplace, len(messages) // 2)},
                    ])
                    st.rerun()
    for message in messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
    question = st.chat_input("Hỏi về giá, sản phẩm hoặc hướng phát triển shop...", key="market_advisor_input")
    if question:
        messages.extend([
            {"role": "user", "content": question},
            {"role": "assistant", "content": market_advisor_response(question, category, marketplace, len(messages) // 2)},
        ])
        st.rerun()
    if st.button("Đóng trợ lý", key="close_market_advisor", icon=":material/close:"):
        close_market_advisor()
        st.rerun()


def render_strategy_workspace() -> None:
    """Help a seller turn market signals into a small, measurable experiment."""
    st.markdown('<div class="seller-eyebrow">CHIẾN LƯỢC KINH DOANH · DEMO</div>', unsafe_allow_html=True)
    header, back = st.columns([8, 2], vertical_alignment="center")
    with header:
        st.title("Chiến lược kinh doanh")
        st.caption("Tìm cơ hội, mô phỏng phương án và tạo kế hoạch hành động. Kết quả là ước tính để chọn thử nghiệm nhỏ, không phải cam kết doanh thu.")
    with back:
        st.button("Quay lại chat", key="strategy_back_to_chat", icon=":material/chat:", width="stretch", on_click=open_chat_view)

    st.info("Không gian này dùng dữ liệu mô phỏng minh bạch. Khi có dữ liệu shop thật, cùng khung quyết định này có thể dùng để phân tích kết quả thực tế.", icon=":material/lightbulb:")
    with st.expander("Nguồn phương pháp và nguyên tắc an toàn", icon=":material/menu_book:"):
        st.markdown("**AI không cam kết doanh thu hoặc tự thay đổi hoạt động của shop.** Mọi đề xuất dưới 90/100 mức bằng chứng chỉ được trình bày là giả thuyết thử nghiệm nhỏ.")
        for source in STRATEGY_EVIDENCE:
            st.markdown(f"- [{source['title']}]({source['url']}) — {source['author']}, {source['year']}. {source['use']}\n  *Ví dụ áp dụng:* {source['adoption']}")
    radar_tab, simulator_tab, comparison_tab, inventory_tab, plan_tab, diary_tab = st.tabs([
        "Radar cơ hội", "Mô phỏng chiến lược", "So sánh phương án", "Vốn & tồn kho", "Kế hoạch 30 ngày", "Nhật ký thử nghiệm"
    ])

    with radar_tab:
        st.subheader("Radar cơ hội mặt hàng")
        st.caption("Điểm cơ hội cân bằng lượng bán, doanh thu, mức giá, review tích cực và độ bền xu hướng trong bộ dữ liệu demo.")
        radar = opportunity_radar()
        radar_frame = pd.DataFrame(radar).rename(columns={
            "rank": "Xếp hạng", "category": "Ngành hàng", "lead_product": "Sản phẩm gợi ý",
            "units_sold_estimate": "Lượng bán ước tính", "estimated_revenue_vnd": "Doanh thu ước tính",
            "positive_review_score": "Review tích cực", "longevity_score": "Độ bền xu hướng",
            "opportunity_score": "Điểm cơ hội", "recommendation": "Khuyến nghị",
        })
        st.dataframe(
            radar_frame[["Xếp hạng", "Ngành hàng", "Sản phẩm gợi ý", "Lượng bán ước tính", "Doanh thu ước tính", "Review tích cực", "Độ bền xu hướng", "Điểm cơ hội", "Khuyến nghị"]].head(12),
            hide_index=True,
            width="stretch",
            column_config={
                "Doanh thu ước tính": st.column_config.NumberColumn(format="%,d đ"),
                "Điểm cơ hội": st.column_config.ProgressColumn(min_value=0, max_value=100, format="%.1f"),
                "Review tích cực": st.column_config.ProgressColumn(min_value=0, max_value=100, format="%.1f"),
                "Độ bền xu hướng": st.column_config.ProgressColumn(min_value=0, max_value=100, format="%.1f"),
            },
        )
        st.caption("Dùng radar để chọn ngành cần thử trước; không dùng một mình để quyết định nhập hàng lớn.")
        radar_options = {str(item["category_id"]): f"#{int(item['rank'])} · {item['category']} · {item['recommendation']}" for item in radar[:12]}
        chosen_radar_category = st.selectbox("Chọn một cơ hội để mô phỏng", options=list(radar_options), format_func=lambda item: radar_options[str(item)], key="strategy_radar_category")
        if st.button("Dùng ngành này để tạo phương án", key="strategy_use_radar_category", icon=":material/rocket_launch:"):
            st.session_state.strategy_category_id = chosen_radar_category
            st.toast("Đã chọn ngành hàng trong tab Mô phỏng chiến lược.", icon=":material/check_circle:")

    with simulator_tab:
        st.subheader("Mô phỏng một phương án kinh doanh")
        st.caption("Chọn một thay đổi nhỏ. AI ước tính tương quan với kịch bản hiện tại để giúp bạn so sánh phương án, không thay thế số liệu thực tế.")
        catalog = market_categories()
        labels = {str(item["id"]): f"{item['category']} · {item['product_count']} sản phẩm" for item in catalog}
        with st.form("strategy_simulator_form", border=True):
            category_id = st.selectbox("Ngành hàng muốn thử", options=list(labels), format_func=lambda item: labels[str(item)], key="strategy_category_id")
            control_left, control_right = st.columns(2)
            with control_left:
                price_change = st.slider("Thay đổi giá (%)", min_value=-15, max_value=15, value=0, help="Số âm là giảm giá; số dương là tăng giá.")
                use_bundle = st.checkbox("Tạo combo/ưu đãi nhỏ", value=False)
            with control_right:
                ad_change = st.slider("Tăng ngân sách quảng cáo (%)", min_value=0, max_value=50, value=0)
                restock = st.number_input("Số lượng dự kiến nhập thêm", min_value=0, max_value=1000, value=0, step=10)
            acknowledged = st.checkbox("Tôi hiểu đây là giả thuyết mô phỏng; tôi sẽ tự phê duyệt và kiểm tra kết quả trước khi áp dụng.")
            simulate = st.form_submit_button("Phân tích phương án", type="primary", icon=":material/psychology:", width="stretch")
        if simulate:
            if not acknowledged:
                st.warning("Bạn cần xác nhận AI chỉ hỗ trợ ra quyết định, không cam kết kết quả kinh doanh.", icon=":material/gpp_maybe:")
            else:
                simulation_result = simulate_strategy(
                    str(category_id), int(st.session_state.seller_market_scenario_seed), int(price_change), bool(use_bundle), int(ad_change), int(restock)
                )
                st.session_state.seller_strategy_last_simulation = simulation_result
                st.session_state.seller_strategy_audit_log.append({
                    "Thời điểm": datetime.now().isoformat(timespec="seconds"),
                    "Sự kiện": "Người dùng xác nhận chạy mô phỏng",
                    "Ngành hàng": simulation_result["category"],
                    "Sản phẩm mũi nhọn": simulation_result["lead_product"],
                    "Thay đổi giá (%)": simulation_result["price_change_percent"],
                    "Có combo": simulation_result["use_bundle"],
                    "Tăng quảng cáo (%)": simulation_result["ad_budget_change_percent"],
                    "Nhập thêm": simulation_result["restock_units"],
                    "Mức bằng chứng": f"{simulation_result['evidence_score']}/100",
                    "Quy tắc ngôn ngữ": simulation_result["language_policy"],
                })
        simulation = st.session_state.seller_strategy_last_simulation
        if simulation:
            with st.container(border=True):
                st.markdown(f"**Giả thuyết cần kiểm chứng: {simulation['lead_product']}**")
                with st.container(horizontal=True):
                    st.metric("GMV hiện tại trong demo", currency(float(simulation["baseline_gmv_vnd"])), border=True)
                    st.metric("GMV minh họa theo phương án", currency(float(simulation["estimated_gmv_vnd"])), f"{float(simulation['gmv_change_percent']):+.1f}%", border=True)
                    st.metric("Lượng bán minh họa", f"{int(simulation['estimated_units']):,}", border=True)
                    st.metric("Mức bằng chứng", f"{int(simulation['evidence_score'])}/100", border=True)
                st.warning(f"**{simulation['evidence_label']}** — {simulation['language_policy']}", icon=":material/gpp_maybe:")
                st.markdown(f"**Mức rủi ro:** {simulation['risk']}")
                st.markdown(f"**Cách thử an toàn:** {simulation['action']}")
                st.markdown("**Điều kiện dừng:**")
                for condition in simulation["stop_conditions"]:
                    st.markdown(f"- {condition}")
                if st.button("Thêm vào bảng so sánh", key="save_strategy_scenario", icon=":material/add_chart:"):
                    saved_scenarios: list[dict[str, Any]] = st.session_state.seller_strategy_scenarios
                    signature = strategy_scenario_label(simulation)
                    if any(strategy_scenario_label(item) == signature for item in saved_scenarios):
                        st.info("Phương án này đã có trong bảng so sánh.", icon=":material/info:")
                    else:
                        saved_scenarios.append(dict(simulation))
                        st.toast("Đã thêm phương án để so sánh.", icon=":material/check_circle:")
        else:
            st.caption("Chưa có phương án được mô phỏng. Hãy chọn thay đổi và bấm “Phân tích phương án”.")

    with comparison_tab:
        st.subheader("So sánh các phương án đã lưu")
        st.caption("So sánh để chọn một thử nghiệm nhỏ. Các số GMV dưới đây là minh họa của mô phỏng, không phải dự báo chắc chắn.")
        scenarios: list[dict[str, Any]] = st.session_state.seller_strategy_scenarios
        if not scenarios:
            st.info("Hãy tạo một phương án, xác nhận an toàn, rồi bấm “Thêm vào bảng so sánh”.", icon=":material/compare_arrows:")
        else:
            scenario_table = pd.DataFrame([
                {
                    "Phương án": strategy_scenario_label(item),
                    "Sản phẩm mũi nhọn": item["lead_product"],
                    "GMV minh họa": item["estimated_gmv_vnd"],
                    "Thay đổi GMV": item["gmv_change_percent"],
                    "Mức bằng chứng": f"{item['evidence_score']}/100",
                    "Rủi ro": item["risk"],
                }
                for item in scenarios
            ])
            st.dataframe(
                scenario_table,
                hide_index=True,
                width="stretch",
                column_config={
                    "GMV minh họa": st.column_config.NumberColumn(format="%,d đ"),
                    "Thay đổi GMV": st.column_config.NumberColumn(format="%+.1f%%"),
                },
            )
            scenario_index = st.selectbox("Chọn phương án làm kế hoạch 30 ngày", options=list(range(len(scenarios))), format_func=lambda index: strategy_scenario_label(scenarios[index]), key="strategy_plan_scenario")
            if st.button("Dùng phương án này cho kế hoạch", key="strategy_select_plan", icon=":material/calendar_month:"):
                st.session_state.seller_strategy_last_simulation = dict(scenarios[scenario_index])
                st.toast("Kế hoạch 30 ngày đã dùng phương án đã chọn.", icon=":material/check_circle:")

    with inventory_tab:
        st.subheader("Vốn & tồn kho: nên nhập gì, dừng gì?")
        st.caption("Xem từng sản phẩm để tránh giữ vốn ở hàng bán chậm và chỉ nhập nhỏ khi có dấu hiệu sắp hết hàng.")
        catalog = market_categories()
        labels = {str(item["id"]): f"{item['category']} · {item['product_count']} sản phẩm" for item in catalog}
        default_category = str(st.session_state.get("strategy_category_id", next(iter(labels))))
        default_index = list(labels).index(default_category) if default_category in labels else 0
        inventory_category = st.selectbox(
            "Ngành hàng cần kiểm tra tồn kho",
            options=list(labels),
            index=default_index,
            format_func=lambda item: labels[str(item)],
            key="strategy_inventory_category",
        )
        target_stock_months = st.slider(
            "Mức tồn kho an toàn muốn duy trì (tháng)",
            min_value=1.0,
            max_value=3.0,
            value=2.0,
            step=0.5,
            help="Ví dụ chọn 2 tháng: AI chỉ đề xuất nhập đủ khoảng hai tháng bán, không đề xuất ôm hàng dài.",
            key="strategy_target_stock_months",
        )
        inventory_result = inventory_risk_analysis(
            str(inventory_category),
            int(st.session_state.seller_market_scenario_seed),
            float(target_stock_months),
        )
        inventory_rows: list[dict[str, object]] = list(inventory_result["rows"])
        do_not_reorder = [row for row in inventory_rows if "không nhập thêm" in str(row["status"]).lower()]
        restock_rows = [row for row in inventory_rows if int(row["recommended_order_qty"]) > 0]
        capital_at_risk = sum(
            int(row["capital_in_stock_demo_vnd"])
            for row in inventory_rows
            if "lỗ vốn" in str(row["status"]).lower() or "tồn lâu" in str(row["status"]).lower()
        )
        suggested_budget = sum(int(row["recommended_order_budget_demo_vnd"]) for row in restock_rows)
        with st.container(horizontal=True):
            st.metric("Mặt hàng chưa nên nhập", f"{len(do_not_reorder)}", border=True)
            st.metric("Vốn có nguy cơ bị giữ", currency(float(capital_at_risk)), border=True)
            st.metric("Mặt hàng có thể nhập nhỏ", f"{len(restock_rows)}", border=True)
            st.metric("Ngân sách nhập nhỏ minh họa", currency(float(suggested_budget)), border=True)

        st.warning(
            "Giá vốn, ngày không có đơn, mức mua lại và chi phí dự phòng ở đây đều là dữ liệu mô phỏng của kịch bản. "
            "Khi dùng dữ liệu thật, hãy thay bằng hóa đơn nhập, tồn kho và đơn bán thực tế trước khi quyết định bỏ vốn.",
            icon=":material/gpp_maybe:",
        )
        inventory_frame = pd.DataFrame(inventory_rows).rename(columns={
            "product_name": "Sản phẩm",
            "listed_price_vnd": "Giá bán (demo)",
            "unit_cost_demo_vnd": "Giá vốn minh họa",
            "operating_reserve_demo_vnd": "Chi phí dự phòng",
            "break_even_price_demo_vnd": "Giá hòa vốn minh họa",
            "safety_margin_demo_vnd": "Biên an toàn minh họa",
            "monthly_purchases_demo": "Lượt mua/tháng mô phỏng",
            "days_since_last_sale_demo": "Không có đơn (ngày)",
            "on_hand_units_demo": "Số lượng tồn",
            "stock_cover_months_demo": "Đủ bán (tháng)",
            "capital_in_stock_demo_vnd": "Vốn đang nằm trong hàng",
            "repeat_purchase_signal_demo": "Tín hiệu khách quay lại",
            "recommended_order_qty": "Đề xuất nhập (cái)",
            "recommended_order_budget_demo_vnd": "Ngân sách nhập nhỏ",
            "status": "Tình trạng",
            "action": "Việc nên làm",
        })
        visible_columns = [
            "Sản phẩm", "Giá bán (demo)", "Giá vốn minh họa", "Giá hòa vốn minh họa",
            "Biên an toàn minh họa", "Lượt mua/tháng mô phỏng", "Không có đơn (ngày)",
            "Số lượng tồn", "Vốn đang nằm trong hàng", "Tín hiệu khách quay lại",
            "Đề xuất nhập (cái)", "Ngân sách nhập nhỏ", "Tình trạng", "Việc nên làm",
        ]
        st.dataframe(
            inventory_frame[visible_columns],
            hide_index=True,
            width="stretch",
            column_config={
                "Giá bán (demo)": st.column_config.NumberColumn(format="%,d đ"),
                "Giá vốn minh họa": st.column_config.NumberColumn(format="%,d đ"),
                "Giá hòa vốn minh họa": st.column_config.NumberColumn(format="%,d đ"),
                "Biên an toàn minh họa": st.column_config.NumberColumn(format="%+,d đ"),
                "Vốn đang nằm trong hàng": st.column_config.NumberColumn(format="%,d đ"),
                "Ngân sách nhập nhỏ": st.column_config.NumberColumn(format="%,d đ"),
            },
        )
        with st.expander("Cách đọc bảng", icon=":material/help:"):
            st.markdown(
                "- **Nguy cơ lỗ vốn:** giá bán demo không đủ bù giá vốn minh họa và chi phí dự phòng; không nên mua thêm trước khi kiểm tra số thật.\n"
                "- **Tồn lâu:** lâu không có đơn hoặc đang giữ quá nhiều hàng; ưu tiên xử lý hàng hiện có thay vì nhập tiếp.\n"
                "- **Tín hiệu khách quay lại:** chỉ là tín hiệu mô phỏng từ kịch bản bán hàng, không phải tỷ lệ khách quay lại thật.\n"
                "- **Đề xuất nhập:** số lượng nhỏ để duy trì mức tồn kho bạn chọn; đây không phải lệnh mua hàng tự động."
            )

    with plan_tab:
        st.subheader("Kế hoạch hành động 30 ngày")
        simulation = st.session_state.seller_strategy_last_simulation
        if not simulation:
            st.info("Hãy tạo một phương án trong tab “Mô phỏng chiến lược” trước; kế hoạch sẽ tự dùng phương án đó.", icon=":material/arrow_back:")
        else:
            plan = pd.DataFrame(action_plan(simulation))
            st.dataframe(plan, hide_index=True, width="stretch")
            st.caption("Nguyên tắc: chỉ thay đổi một vài yếu tố trong một kỳ để biết kết quả đến từ đâu.")

    with diary_tab:
        st.subheader("Nhật ký thử nghiệm")
        st.caption("Lưu lại giả thuyết, việc đã làm và kết quả. Đây là phần giúp AI trở thành công cụ học từ các lần thử của doanh nghiệp.")
        simulation = st.session_state.seller_strategy_last_simulation
        if simulation:
            with st.form("strategy_diary_form", border=True):
                experiment_name = st.text_input("Tên thử nghiệm", value=f"Thử nghiệm {simulation['lead_product']}")
                result_note = st.text_area("Kết quả hoặc ghi chú", placeholder="Ví dụ: chạy 14 ngày, số đơn tăng nhưng lợi nhuận chưa đạt mục tiêu.")
                saved = st.form_submit_button("Lưu vào nhật ký", icon=":material/bookmark_add:")
            if saved:
                st.session_state.seller_strategy_experiments.append({
                    "Thử nghiệm": experiment_name.strip() or "Thử nghiệm chưa đặt tên",
                    "Ngành hàng": simulation["category"],
                    "Sản phẩm": simulation["lead_product"],
                    "Phương án": f"Giá {int(simulation['price_change_percent']):+d}%; combo: {'Có' if simulation['use_bundle'] else 'Không'}; quảng cáo: +{int(simulation['ad_budget_change_percent'])}%",
                    "Ghi chú": result_note.strip() or "Chưa nhập kết quả",
                })
                st.toast("Đã lưu thử nghiệm vào nhật ký của phiên này.", icon=":material/check_circle:")
        else:
            st.info("Chưa có phương án để lưu. Hãy mô phỏng trước rồi quay lại đây.", icon=":material/info:")
        diary = st.session_state.seller_strategy_experiments
        if diary:
            st.dataframe(pd.DataFrame(diary), hide_index=True, width="stretch")
        else:
            st.caption("Nhật ký đang trống. Khi đã chạy một phương án, bạn có thể lưu lại để so sánh các lần thử.")
        audit_log = st.session_state.seller_strategy_audit_log
        if audit_log:
            with st.expander("Nhật ký kiểm soát và xác nhận", icon=":material/fact_check:"):
                st.caption("Bản ghi chỉ lưu trong phiên hiện tại và không có quyền tự thay đổi hoạt động trên Shopee.")
                st.dataframe(pd.DataFrame(audit_log), hide_index=True, width="stretch")
                st.download_button(
                    "Tải bản ghi kiểm soát",
                    data=json.dumps(audit_log, ensure_ascii=False, indent=2),
                    file_name="nhat-ky-kiem-soat-chien-luoc.json",
                    mime="application/json",
                    icon=":material/download:",
                )


def render_market_intelligence() -> None:
    """Show a useful but explicitly simulated market-analysis workspace."""
    st.markdown('<div class="seller-eyebrow">MARKET INTELLIGENCE · DEMO</div>', unsafe_allow_html=True)
    header, back = st.columns([8, 2], vertical_alignment="center")
    with header:
        st.title("Phân tích thị trường")
        st.caption("So sánh giá, shop tham chiếu và hướng thử nghiệm cho một ngành hàng.")
    with back:
        st.button("Quay lại chat", key="market_back_to_chat", icon=":material/chat:", width="stretch", on_click=open_chat_view)

    st.warning(
        "Đây là Market Demo: giá, shop tham chiếu và tín hiệu xu hướng đều là dữ liệu mô phỏng có thể lặp lại khi demo. "
        "Hệ thống chưa kết nối Shopee, YouTube, Facebook/Instagram hoặc TikTok để lấy dữ liệu trực tiếp.",
        icon=":material/info:",
    )
    catalog = market_categories()
    labels = {
        str(item["id"]): f"{item['category']} · {item['product_count']} sản phẩm demo"
        for item in catalog
    }
    category_id = st.selectbox(
        "Chọn ngành hàng để phân tích",
        options=list(labels),
        format_func=lambda item: labels[str(item)],
        key="seller_market_category_id",
    )
    selected = next(item for item in catalog if item["id"] == category_id)
    st.button(
        "Tạo lại shop và thị trường demo",
        key="refresh_market_scenario",
        icon=":material/autorenew:",
        on_click=refresh_market_scenario,
    )
    marketplace = simulated_marketplace(
        str(category_id), int(st.session_state.seller_market_scenario_seed)
    )
    listings = pd.DataFrame(marketplace["listings"])
    product_names = sorted(listings["product_name"].unique().tolist())
    selected_product = st.selectbox(
        "Chọn sản phẩm để so sánh giá",
        options=product_names,
        key="market_price_product",
        help="Giá và bảng bên dưới chỉ so sánh đúng sản phẩm này giữa các shop.",
    )
    product_rows = listings[listings["product_name"] == selected_product].copy()
    own_product = product_rows[product_rows["shop_type"] == "Shop của bạn"].iloc[0]
    comparable_prices = product_rows[product_rows["shop_type"] != "Shop của bạn"]["listed_price_vnd"]
    product_lower_price = float(comparable_prices.min())
    product_typical_price = float(comparable_prices.median())
    product_upper_price = float(comparable_prices.max())
    product_own_price = float(own_product["listed_price_vnd"])
    if product_own_price < product_lower_price:
        product_position = "Thấp hơn giá các shop cùng sản phẩm"
    elif product_own_price > product_upper_price:
        product_position = "Cao hơn giá các shop cùng sản phẩm"
    else:
        product_position = "Nằm trong vùng giá cạnh tranh"

    with st.container(horizontal=True):
        st.metric("Giá thấp cùng sản phẩm", currency(product_lower_price), help="Mức giá thấp nhất của đúng sản phẩm đang chọn tại 7 shop tham chiếu.", border=True)
        st.metric("Mặt bằng giá", currency(product_typical_price), help="Giá ở giữa của 7 shop cùng bán sản phẩm đang chọn.", border=True)
        st.metric("Giá cao cùng sản phẩm", currency(product_upper_price), help="Mức giá cao nhất của đúng sản phẩm đang chọn tại 7 shop tham chiếu.", border=True)
    with st.container(horizontal=True):
        st.metric("Giá shop của bạn", currency(product_own_price), help="Giá của đúng sản phẩm đang chọn tại Shop của bạn · Demo.", border=True)
        st.metric("Vị trí giá", product_position, help="So sánh trực tiếp cùng một sản phẩm, không phải giá trung bình của cả shop.", border=True)
    st.caption("Đang so sánh từng sản phẩm. Chọn sản phẩm khác để kiểm tra giá khác; bấm “Tạo lại shop và thị trường demo” để tạo bộ shop mới.")
    with st.container(border=True):
        st.markdown("**Cách đọc nhanh**")
        st.write("1. Chọn đúng sản phẩm muốn kiểm tra.  2. So giá shop của bạn với 7 shop cùng bán sản phẩm đó.  3. Xem bảng chi tiết trước khi quyết định đổi giá.")

    price_tab, shop_tab, product_tab = st.tabs(["So sánh giá", "So sánh shop", "Sản phẩm cùng thị trường"])
    with price_tab:
        st.subheader(selected_product)
        st.write("Mỗi cột là giá của đúng sản phẩm này tại một shop. Cột đỏ là Shop của bạn.")
        chart_data = product_rows.copy()
        price_chart = (
            alt.Chart(chart_data)
            .mark_bar(cornerRadiusEnd=4)
            .encode(
                x=alt.X("listed_price_vnd:Q", title="Giá niêm yết (VND)", axis=alt.Axis(format=",d")),
                y=alt.Y("shop_name:N", sort="-x", title=None),
                color=alt.condition(alt.datum.shop_type == "Shop của bạn", alt.value("#ee4d2d"), alt.value("#f7a28f")),
                tooltip=[alt.Tooltip("shop_name:N", title="Shop"), alt.Tooltip("listed_price_vnd:Q", title="Giá", format=",d"), alt.Tooltip("rating:Q", title="Đánh giá", format=".2f")],
            )
            .properties(height=300)
        )
        st.altair_chart(price_chart, width="stretch")
        product_table = product_rows.rename(columns={"shop_name": "Shop", "shop_type": "Loại shop", "listed_price_vnd": "Giá", "rating": "Đánh giá", "review_count": "Số review", "units_sold_12m": "Lượng bán 12T", "gmv_12m_vnd": "GMV 12T"})
        st.dataframe(product_table[["Shop", "Loại shop", "Giá", "Đánh giá", "Số review", "Lượng bán 12T", "GMV 12T"]], hide_index=True, width="stretch", column_config={"Giá": st.column_config.NumberColumn(format="%,d đ"), "GMV 12T": st.column_config.NumberColumn(format="%,d đ")})
        st.caption(
            f"So sánh đúng một sản phẩm ở Shop của bạn và 7 shop tham chiếu mô phỏng; snapshot demo {MARKET_SNAPSHOT_DATE}."
        )

    with shop_tab:
        shops = pd.DataFrame(marketplace["shops"])
        st.caption(f"So sánh shop của bạn với {marketplace['reference_count']} shop tương tự trong cùng ngành hàng. Mỗi lần tạo lại sẽ có một kịch bản demo mới.")
        shop_chart = alt.Chart(shops).mark_arc(innerRadius=58, padAngle=0.02).encode(
            theta=alt.Theta("gmv_12m_vnd:Q", title="GMV 12 tháng"),
            color=alt.Color("shop_name:N", title="Shop", scale=alt.Scale(scheme="set2")),
            tooltip=[
                alt.Tooltip("shop_name:N", title="Tên shop"),
                alt.Tooltip("shop_type:N", title="Quy mô shop"),
                alt.Tooltip("average_price_vnd:Q", title="Giá bán trung bình", format=",d"),
                alt.Tooltip("gmv_12m_vnd:Q", title="Tổng doanh thu 12 tháng", format=",d"),
                alt.Tooltip("shop_score:Q", title="Điểm đánh giá shop", format=".1f"),
            ],
        ).properties(height=340)
        st.markdown("**Tỷ trọng doanh thu 12 tháng của các shop**")
        st.caption("Miếng lớn hơn nghĩa là shop đó có GMV cao hơn trong bộ dữ liệu đang xem.")
        st.altair_chart(shop_chart, width="stretch")
        table = shops.rename(columns={"shop_name": "Shop", "shop_type": "Quy mô", "listing_count": "Số sản phẩm", "units_sold_12m": "Lượng bán 12T", "gmv_12m_vnd": "GMV 12T", "average_price_vnd": "Giá TB", "rating": "Đánh giá", "review_count": "Review", "shop_score": "Điểm shop"})
        st.dataframe(table[["Shop", "Quy mô", "Số sản phẩm", "Lượng bán 12T", "GMV 12T", "Giá TB", "Đánh giá", "Review", "Điểm shop"]], hide_index=True, width="stretch", column_config={"GMV 12T": st.column_config.NumberColumn(format="%,d đ"), "Giá TB": st.column_config.NumberColumn(format="%,d đ"), "Điểm shop": st.column_config.ProgressColumn(min_value=0, max_value=100, format="%.1f")})

    with product_tab:
        st.caption(f"Bảng trộn sản phẩm của Shop của bạn · Demo và {marketplace['reference_count']} shop tương tự. Lọc theo shop để xem các mặt hàng cạnh tranh.")
        selected_shops = st.multiselect("Hiển thị shop", listings["shop_name"].unique().tolist(), default=listings["shop_name"].unique().tolist(), key="market_listing_shops")
        shown = listings[listings["shop_name"].isin(selected_shops)].copy()
        product_chart_data = shown.groupby("product_name", as_index=False).agg(
            GMV_12T=("gmv_12m_vnd", "sum"),
            Luong_ban_12T=("units_sold_12m", "sum"),
        ).nlargest(12, "GMV_12T")
        product_chart = alt.Chart(product_chart_data).mark_bar(color="#ee4d2d", cornerRadiusEnd=4).encode(
            x=alt.X("GMV_12T:Q", title="GMV 12 tháng", axis=alt.Axis(format=".2s")),
            y=alt.Y("product_name:N", title=None, sort="-x"),
            tooltip=[
                alt.Tooltip("product_name:N", title="Tên sản phẩm"),
                alt.Tooltip("GMV_12T:Q", title="Tổng doanh thu 12 tháng", format=",d"),
                alt.Tooltip("Luong_ban_12T:Q", title="Lượng bán 12 tháng", format=",d"),
            ],
        ).properties(height=340)
        st.markdown("**12 sản phẩm có GMV cao nhất**")
        st.caption("Dùng biểu đồ cột để nhìn rõ sản phẩm nào tạo doanh thu cao; bảng bên dưới dùng để xem từng shop và từng giá.")
        st.altair_chart(product_chart, width="stretch")
        display = shown.rename(columns={"shop_name": "Shop", "shop_type": "Quy mô", "product_name": "Sản phẩm", "listed_price_vnd": "Giá", "units_sold_12m": "Lượng bán 12T", "gmv_12m_vnd": "GMV 12T", "rating": "Đánh giá", "review_count": "Review", "product_score": "Điểm sản phẩm", "data_scope": "Nguồn dữ liệu"})
        st.dataframe(display[["Shop", "Quy mô", "Sản phẩm", "Giá", "Lượng bán 12T", "GMV 12T", "Đánh giá", "Review", "Điểm sản phẩm", "Nguồn dữ liệu"]], hide_index=True, width="stretch", column_config={"Giá": st.column_config.NumberColumn(format="%,d đ"), "GMV 12T": st.column_config.NumberColumn(format="%,d đ"), "Điểm sản phẩm": st.column_config.ProgressColumn(min_value=0, max_value=100, format="%.1f")})
        st.info("Điểm sản phẩm cân bằng lượng bán, GMV và review. Nó không phải dự báo chắc chắn; dùng để chọn mặt hàng cần thử trước.", icon=":material/insights:")

    st.button(
        "AI",
        key="market_advisor_toggle",
        help="Mở Chiến lược gia AI",
        on_click=open_market_advisor,
    )
    if st.session_state.seller_market_advisor_open:
        render_market_advisor_dialog(str(selected["category"]), marketplace)

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
        "Mỗi loại shop tự tạo từ 5 đến 12 sản phẩm phù hợp trong cùng ngành, rồi tạo đơn hàng, tồn kho và quảng cáo mô phỏng trong 12 tháng. "
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
        total_products = sum(int(catalog_by_id[category_id]["product_count"]) for category_id in selected_ids)
        st.success(
            f"Đã chọn {len(selected_ids)} loại shop → sẽ có {total_products} sản phẩm mô phỏng và {total_products * len(DEMO_PERIODS):,} dòng đơn hàng trong 12 tháng.",
            icon=":material/storefront:",
        )
        with st.container(border=True):
            st.markdown("##### Danh mục sản phẩm sắp được tạo")
            st.caption(
                "Đây chưa phải bảng doanh thu. Mỗi khối là một loại shop bạn chọn; con số là số sản phẩm AI sẽ tạo. "
                "Bấm vào từng khối để xem chính xác các sản phẩm trong shop demo."
            )
            for category_id in selected_ids:
                item = catalog_by_id[category_id]
                product_names = list(item["product_examples"])
                with st.expander(
                    f"{item['category']} · {item['product_count']} sản phẩm",
                    expanded=len(selected_ids) == 1,
                    icon=":material/inventory_2:",
                ):
                    st.dataframe(
                        pd.DataFrame({"Sản phẩm AI sẽ tạo cho loại shop này": product_names}),
                        hide_index=True,
                        column_config={
                            "Sản phẩm AI sẽ tạo cho loại shop này": st.column_config.TextColumn("Sản phẩm AI sẽ tạo cho loại shop này", pinned=True),
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


def render_business_terms_guide() -> None:
    """Explain the three operational terms that appear in the shop dashboard."""
    with st.expander("Giải thích nhanh: SKU, GMV và ROAS", icon=":material/help:"):
        st.markdown(
            """
**SKU — mã riêng của từng sản phẩm**

SKU giúp phân biệt và nối đúng *một sản phẩm* với đơn hàng và tồn kho của nó. Ví dụ, `FRUIT-TAO-001` có thể là mã của giỏ táo; nhờ mã này, AI biết được giỏ táo đã bán bao nhiêu và còn bao nhiêu trong kho.

**GMV — tổng tiền hàng đã bán**

GMV là tổng giá trị đơn hoàn tất trước khi trừ khuyến mãi của shop và các khoản phí ước tính. Ví dụ: khách mua 2 sản phẩm, mỗi sản phẩm 250.000 đ → **GMV = 500.000 đ**. GMV chưa phải lợi nhuận, vì còn giá vốn, khuyến mãi và phí.

**ROAS — hiệu quả của tiền quảng cáo**

ROAS = doanh thu quy gán từ quảng cáo ÷ tiền chạy quảng cáo. Ví dụ: chi 100.000 đ quảng cáo và tạo ra 400.000 đ doanh thu → **ROAS = 4,0**. Nghĩa là mỗi 1 đ quảng cáo mang về 4 đ doanh thu; chỉ số này cũng chưa trừ giá vốn hay phí.

:small[Mẹo nhớ: SKU = mã sản phẩm · GMV = tổng tiền hàng bán · ROAS = số tiền thu về trên mỗi đồng quảng cáo.]
"""
        )


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
    render_business_terms_guide()

    if is_demo:
        st.info(
            "Danh mục có 50 loại shop đại diện cho các mảng phổ biến trên sàn. Mỗi loại tạo từ 5 đến 12 sản phẩm tương thích. Dữ liệu là mô phỏng, "
            "không phải danh mục hoặc số liệu trực tiếp từ Shopee.",
            icon=":material/lightbulb:",
        )
        render_demo_assortment_builder(library, saved_rows)

    if saved_rows is not None:
        if is_demo:
            st.button(
                "Mở phân tích thị trường demo",
                icon=":material/insights:",
                type="primary",
                on_click=open_market_intelligence,
            )
            st.caption("Từ đây bạn sẽ xem shop demo, các shop tương tự và hỏi Trợ lý AI về hướng phát triển.")
        else:
            st.button(
                "Dùng dữ liệu shop trong chat",
                icon=":material/play_circle:",
                type="primary",
                on_click=activate_library_data,
                args=(scope,),
            )
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
        st.button(" ", key="compact_market_intelligence", icon=":material/insights:", help="Phân tích thị trường", width="stretch", on_click=open_market_intelligence)
        st.button(" ", key="compact_strategy_workspace", icon=":material/rocket_launch:", help="Chiến lược kinh doanh", width="stretch", on_click=open_strategy_workspace)
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
        st.button("Phân tích thị trường", key="open_market_intelligence", icon=":material/insights:", width="stretch", on_click=open_market_intelligence)
        st.button("Chiến lược kinh doanh", key="open_strategy_workspace", icon=":material/rocket_launch:", width="stretch", on_click=open_strategy_workspace)
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
elif st.session_state.seller_view == "market":
    render_market_intelligence()
elif st.session_state.seller_view == "strategy":
    render_strategy_workspace()
else:
    render_assistant()
