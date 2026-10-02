"""Seller-facing Streamlit UI for the thesis RAG + Agent backend.

This is intentionally separate from shopee_chat_web_v19.py so the V19 baseline
and its research UI remain unchanged.
"""

from __future__ import annotations

from copy import deepcopy
from datetime import datetime
from io import BytesIO
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
from agent.planner import Planner, normalize
from agent.shop_data_tool import (
    OPTIONAL_UPLOAD_FILES,
    REQUIRED_UPLOAD_COLUMNS,
    VIETNAMESE_COLUMN_ALIASES,
    ShopDataTool,
    ShopDataValidationError,
)
from agent.strategy_engine import action_plan, inventory_risk_analysis, opportunity_radar, simulate_strategy
from agent.strategy_evidence import STRATEGY_EVIDENCE
from agent.shop_data_library import (
    DEMO_PERIODS,
    REQUIRED_FILES as LIBRARY_REQUIRED_FILES,
    ShopDataLibrary,
    build_demo_rows,
    clean_and_validate_rows,
    demo_catalog,
    empty_rows,
)


st.set_page_config(
    page_title="Eslabong",
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
      /* Navigation chrome should feel like controls, not like editable text.
         Keep reports, chat responses, and data tables selectable for copying. */
      [data-testid="stSidebar"] h3,
      [data-testid="stSidebar"] details > summary,
      [data-testid="stSidebar"] details > summary *,
      [data-testid="stMain"] h1 {
        user-select: none !important;
        -webkit-user-select: none !important;
      }
      /* Recent-chat controls deliberately have one compact, stable footprint. */
      [class*="st-key-open_"] > div > button {
        height: 56px !important; min-height: 56px !important; max-height: 56px !important;
        padding: .55rem .65rem !important; overflow: hidden !important; flex-wrap: nowrap !important;
      }
      [class*="st-key-open_"] > div > button > div,
      [class*="st-key-open_"] > div > button [data-testid="stMarkdownContainer"] {
        min-width: 0 !important; overflow: hidden !important;
      }
      [class*="st-key-open_"] > div > button p,
      [class*="st-key-open_"] > div > button [data-testid="stMarkdownContainer"] p {
        display: block !important; width: 100% !important; overflow: hidden !important; text-overflow: ellipsis !important;
        white-space: nowrap !important;
      }
      [class*="st-key-open_"] > div > button * {
        user-select: none !important; -webkit-user-select: none !important;
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
      /* Highlight the currently open chat like a focused Codex conversation. */
      [class*="st-key-open_"] button[kind="primary"],
      [class*="st-key-compact_open_"] button[kind="primary"] {
        background: #fff0ea !important; border: 1.5px solid #ee4d2d !important;
        color: #a8321d !important; font-weight: 750 !important;
        box-shadow: 0 4px 14px rgba(238, 77, 45, .16) !important;
      }
      [class*="st-key-open_"] button[kind="primary"]:hover,
      [class*="st-key-compact_open_"] button[kind="primary"]:hover {
        background: #ffe4dc !important; border-color: #d83f20 !important; color: #8f2817 !important;
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

    </style>
    """,
    unsafe_allow_html=True,
)

# Stable destination for the floating navigation control. It is deliberately
# placed before every page view so the same button works in chat and on mobile.
st.markdown('<span id="seller-page-top" aria-hidden="true"></span>', unsafe_allow_html=True)


_SCROLL_NAVIGATION = st.components.v2.component(
    "seller_scroll_navigation",
    html="""
    <button id="scroll-to-top" type="button" aria-label="Scroll to top">
      <span aria-hidden="true">↑</span>
    </button>
    """,
    css="""
    #scroll-to-top {
      align-items: center;
      background: #ee4d2d;
      border: 2px solid #ffffff;
      border-radius: 999px;
      /* Keep it in the upper-right corner, below the Streamlit header. */
      top: 4.25rem;
      box-shadow: 0 8px 24px rgba(187, 61, 31, .28);
      color: #ffffff;
      cursor: pointer;
      display: inline-flex;
      font-size: 1.45rem;
      font-weight: 700;
      height: 52px;
      justify-content: center;
      line-height: 1;
      padding: 0;
      position: fixed;
      right: 1.25rem;
      opacity: 0;
      pointer-events: none;
      transform: translateY(-8px);
      transition: background .16s ease, opacity .16s ease, transform .16s ease;
      width: 52px;
      z-index: 1001;
    }
    #scroll-to-top:hover { background: #d83f20; transform: translateY(-2px); }
    #scroll-to-top.is-visible { opacity: 1; pointer-events: auto; transform: translateY(0); }
    #scroll-to-top:focus-visible { outline: 3px solid rgba(238, 77, 45, .32); outline-offset: 3px; }
    @media (max-width: 640px) {
      #scroll-to-top { top: 3.6rem; right: .75rem; width: 44px; height: 44px; font-size: 1.25rem; }
    }
    """,
    js="""
    export default function(component) {
      const { data, parentElement } = component;
      const button = parentElement.querySelector("#scroll-to-top");
      if (!button) return;

      // CCv2 runs in the app document, so use its real scroll containers.
      // This also works on mobile where the scrolling element can differ.
      const hostWindow = window;
      const hostDocument = document;
      const main = hostDocument.querySelector('[data-testid="stMain"]');
      const scrollContainers = [
        main,
        hostDocument.scrollingElement,
        hostDocument.documentElement,
        hostDocument.body,
      ].filter((item, index, items) => item && items.indexOf(item) === index);

      const scrollToTop = () => {
        const start = hostDocument.querySelector("#seller-page-top");
        if (start) start.scrollIntoView({ block: "start", behavior: "smooth" });
        hostWindow.scrollTo({ top: 0, behavior: "smooth" });
        scrollContainers.forEach((container) => {
          if (typeof container.scrollTo === "function") {
            container.scrollTo({ top: 0, behavior: "smooth" });
          }
        });
      };
      const updateButtonState = () => {
        const top = Math.max(
          hostWindow.scrollY || 0,
          ...scrollContainers.map((container) => container.scrollTop || 0),
        );
        button.classList.toggle("is-visible", top >= (data?.show_after || 180));
      };
      button.setAttribute("aria-label", data?.top_label || "Scroll to top");
      button.onclick = scrollToTop;
      updateButtonState();
      hostWindow.addEventListener("scroll", updateButtonState, { passive: true });
      hostDocument.addEventListener("scroll", updateButtonState, { capture: true, passive: true });
      scrollContainers.forEach((container) => container.addEventListener("scroll", updateButtonState, { passive: true }));

      const token = data?.scroll_token;
      if (data?.scroll_to_latest && token && parentElement.dataset.scrollToken !== token) {
        parentElement.dataset.scrollToken = token;
        requestAnimationFrame(() => {
          requestAnimationFrame(() => {
            const target = hostDocument.querySelector('[data-testid="stChatInput"]') || main;
            if (target) target.scrollIntoView({ block: "end", behavior: "auto" });
          });
        });
      }
      return () => {
        hostWindow.removeEventListener("scroll", updateButtonState);
        hostDocument.removeEventListener("scroll", updateButtonState, { capture: true });
        scrollContainers.forEach((container) => container.removeEventListener("scroll", updateButtonState));
      };
    }
    """,
    isolate_styles=False,
)


SUGGESTIONS = {
    "owner": {
        "Doanh thu tháng này": "Doanh thu tháng này của shop thế nào?",
        "Hàng sắp hết": "Sản phẩm nào đang sắp hết hàng?",
        "Phí ảnh hưởng doanh thu": "Tháng này shop cần đối chiếu những khoản phí nào?",
    },
}

# A compact, guided starting point for first-time sellers. These are common
# questions that can be answered without requiring the seller to upload shop
# data, unlike the owner operating-data prompts.
LEARNER_QUESTION_BANK: tuple[dict[str, str], ...] = (
    {"group_vi": "Bắt đầu bán", "question_vi": "Người mới cần chuẩn bị gì trước khi mở shop trên Shopee?", "group_en": "Getting started", "question_en": "What should a new seller prepare before opening a Shopee shop?"},
    {"group_vi": "Bắt đầu bán", "question_vi": "Ai có thể đăng ký mở shop trên Shopee?", "group_en": "Getting started", "question_en": "Who can register to open a Shopee shop?"},
    {"group_vi": "Bắt đầu bán", "question_vi": "Cách đăng ký mở shop trên Shopee như thế nào?", "group_en": "Getting started", "question_en": "How do I register to open a Shopee shop?"},
    {"group_vi": "Bắt đầu bán", "question_vi": "Tôi cần chuẩn bị gì để đăng sản phẩm đầu tiên?", "group_en": "Getting started", "question_en": "What do I need to prepare to list my first product?"},
    {"group_vi": "Sản phẩm và giá", "question_vi": "SKU là gì và vì sao mỗi biến thể nên có SKU riêng?", "group_en": "Products and pricing", "question_en": "What is an SKU and why should each variant have its own SKU?"},
    {"group_vi": "Sản phẩm và giá", "question_vi": "Giá bán nên tính những khoản chi phí nào?", "group_en": "Products and pricing", "question_en": "Which costs should I include when setting a selling price?"},
    {"group_vi": "Sản phẩm và giá", "question_vi": "Làm sao viết mô tả sản phẩm rõ ràng và đúng quy định?", "group_en": "Products and pricing", "question_en": "How can I write a clear, compliant product description?"},
    {"group_vi": "Phí và chính sách", "question_vi": "Shopee đang áp dụng những loại phí nào?", "group_en": "Fees and policies", "question_en": "What types of fees does Shopee charge?"},
    {"group_vi": "Phí và chính sách", "question_vi": "Phí cố định là gì?", "group_en": "Fees and policies", "question_en": "What is a fixed fee?"},
    {"group_vi": "Phí và chính sách", "question_vi": "Khi nào người mua có thể yêu cầu trả hàng hoặc hoàn tiền?", "group_en": "Fees and policies", "question_en": "When can a buyer request a return or refund?"},
    {"group_vi": "Đơn hàng", "question_vi": "Đơn bị hủy có được tính doanh thu không?", "group_en": "Orders", "question_en": "Does a cancelled order count as revenue?"},
    {"group_vi": "Đơn hàng", "question_vi": "Khi có đơn hàng mới, tôi cần xử lý theo các bước nào?", "group_en": "Orders", "question_en": "What steps should I take when I receive a new order?"},
    {"group_vi": "Đơn hàng", "question_vi": "Làm sao đóng gói hàng để giảm nguy cơ trả hàng?", "group_en": "Orders", "question_en": "How should I pack an order to reduce return risk?"},
    {"group_vi": "Chăm sóc shop", "question_vi": "Làm thế nào để tránh đánh giá thấp từ người mua?", "group_en": "Shop care", "question_en": "How can I reduce low ratings from buyers?"},
    {"group_vi": "Chăm sóc shop", "question_vi": "Khi nào người mới nên bắt đầu chạy quảng cáo?", "group_en": "Shop care", "question_en": "When should a new seller start running ads?"},
)
REQUIRED_FILES = ("orders.csv", "products.csv", "inventory.csv")
# Bump this key whenever the sample schema changes.  The exported workbook is
# cached by Streamlit, so relying only on build_demo_rows() can otherwise keep
# serving an older file after new sheets are added.
DEMO_WORKBOOK_VERSION = "2026.10.02-full-data-v3"
CHAT_TYPES = {
    "learner": {
        "name": "Người mới",
        "name_en": "New seller",
        "icon": ":material/school:",
        "description": "Tìm hiểu để mở và vận hành shop trên Shopee.",
        "description_en": "Learn how to open and run a shop on Shopee.",
        "placeholder": "Hỏi về cách bắt đầu bán hoặc chính sách Shopee...",
        "placeholder_en": "Ask how to start selling or about Shopee policies...",
    },
    "owner": {
        "name": "Chủ shop",
        "name_en": "Shop owner",
        "icon": ":material/storefront:",
        "description": "Hỏi về doanh thu, chính sách và hoạt động của shop.",
        "description_en": "Ask about revenue, policies, and shop operations.",
        "placeholder": "Hỏi về doanh thu, tồn kho, quảng cáo hoặc phí của shop...",
        "placeholder_en": "Ask about revenue, inventory, ads, or shop fees...",
    },
}


def ui_text(vietnamese: str, english: str) -> str:
    """Keep every setting-controlled UI label in one Vietnamese/English pair."""
    return english if st.session_state.get("seller_language", "vi") == "en" else vietnamese


def market_shop_type_label(shop_type: str) -> str:
    """Translate demo-only shop-size labels before putting them on screen."""
    labels = {
        "Shop của bạn": ui_text("Shop của bạn (demo)", "Your shop (demo)"),
        "Shop nhỏ": ui_text("Shop nhỏ", "Small shop"),
        "Shop vừa": ui_text("Shop vừa", "Medium shop"),
        "Shop lớn": ui_text("Shop lớn", "Large shop"),
        "Shop dẫn đầu": ui_text("Shop dẫn đầu (mô phỏng)", "Leading shop (simulated)"),
    }
    return labels.get(shop_type, shop_type)


def market_shop_name_label(shop_name: str) -> str:
    """Keep generated reference names understandable in both interface languages."""
    if st.session_state.get("seller_language", "vi") != "en":
        return shop_name.replace(" · dẫn đầu", " · dẫn đầu (mô phỏng)")
    if shop_name == "Shop của bạn · Demo":
        return "Your shop · Demo"
    if shop_name.startswith("Shop tương tự "):
        prefix, _separator, size = shop_name.partition(" · ")
        number = prefix.rsplit(" ", 1)[-1]
        return f"Reference shop {number} · {market_shop_type_label(f'Shop {size}')}"
    return shop_name


def dark_mode_chart(chart: alt.Chart) -> alt.Chart:
    """Give Altair charts an explicit slate canvas; Streamlit theme CSS cannot style SVG output."""
    if not st.session_state.get("seller_dark_mode"):
        return chart
    return (
        chart.configure(background="#1f2937")
        .configure_view(fill="#1f2937", stroke="#475569", strokeWidth=1)
        .configure_axis(
            domainColor="#64748b",
            gridColor="#334155",
            labelColor="#cbd5e1",
            tickColor="#64748b",
            titleColor="#e5edf7",
        )
        .configure_legend(labelColor="#e5edf7", titleColor="#f8fafc", symbolStrokeColor="#94a3b8")
        .configure_title(color="#f8fafc")
    )


def themed_dataframe(data: pd.DataFrame, **kwargs: Any) -> None:
    """Render every app table in the same calm palette as dark-mode charts."""
    display_data: Any = data
    if st.session_state.get("seller_dark_mode"):
        display_data = (
            data.style
            .set_properties(**{"background-color": "#1f2937", "color": "#e5edf7", "border-color": "#475569"})
            .set_table_styles([
                {"selector": "th", "props": [("background-color", "#273449"), ("color", "#f8fafc")]},
            ])
        )
    st.dataframe(display_data, **kwargs)


def active_chat_type(mode: str) -> dict[str, str]:
    chat_type = dict(CHAT_TYPES[mode])
    if st.session_state.get("seller_language", "vi") == "en":
        chat_type["name"] = chat_type["name_en"]
        chat_type["description"] = chat_type["description_en"]
        chat_type["placeholder"] = chat_type["placeholder_en"]
    return chat_type

# These values belong to one conversation, rather than to the whole browser
# session.  Switching chats snapshots the current workspace and restores the
# selected chat's own data, market scenario, strategy work, and adviser log.
CONVERSATION_CONTEXT_KEYS = (
    "seller_uploaded_rows",
    "seller_uploaded_names",
    "seller_data_origin",
    "seller_library_scope",
    "seller_demo_selected_ids",
    "seller_market_scenario_seed",
    "seller_market_category_id",
    "market_section",
    "market_price_product",
    "market_listing_shops",
    "seller_market_advisor_messages",
    "seller_advisor_handoffs",
    "seller_advisor_surface",
    "seller_strategy_last_simulation",
    "strategy_section",
    "strategy_category_id",
    "strategy_inventory_category",
    "strategy_target_stock_months",
)
CONVERSATION_WIDGET_KEYS = {
    "seller_market_category_id",
    "market_section",
    "market_price_product",
    "market_listing_shops",
    "strategy_category_id",
    "strategy_inventory_category",
    "strategy_section",
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
    st.session_state.setdefault("market_section", "So sánh giá")
    st.session_state.setdefault("seller_market_advisor_messages", [])
    st.session_state.setdefault("seller_advisor_handoffs", [])
    st.session_state.setdefault("seller_pending_main_prompt", None)
    st.session_state.setdefault("seller_market_advisor_open", False)
    st.session_state.setdefault("seller_advisor_surface", "market")
    st.session_state.setdefault("seller_strategy_last_simulation", None)
    st.session_state.setdefault("strategy_section", "Radar cơ hội")
    st.session_state.setdefault("seller_language", "vi")
    st.session_state.setdefault("seller_dark_mode", False)
    st.session_state.setdefault("seller_scroll_to_latest", False)
    st.session_state.setdefault("seller_chat_scroll_sequence", 0)


def render_color_mode_css() -> None:
    """Use a calm slate theme that keeps dark mode readable for long sessions."""
    if not st.session_state.get("seller_dark_mode"):
        return
    st.markdown(
        """
        <style>
          :root { color-scheme: dark !important; }
          html, body, .stApp, [data-testid="stApp"], [data-testid="stAppViewContainer"], [data-testid="stMain"],
          [data-testid="stBottom"], [data-testid="stBottom"] > div, [data-testid="stBottomBlockContainer"], .stBottom {
            background: #111827 !important; color: #f3f4f6 !important;
          }
          [data-testid="stHeader"] { background: rgba(17, 24, 39, .95) !important; border-color: #334155 !important; }
          [data-testid="stSidebar"] { background: #172033 !important; border-color: #334155 !important; }
          [data-testid="stSidebar"] *, [data-testid="stAppViewContainer"] p, [data-testid="stAppViewContainer"] li,
          [data-testid="stAppViewContainer"] span, [data-testid="stAppViewContainer"] h1,
          [data-testid="stAppViewContainer"] h2, [data-testid="stAppViewContainer"] h3 { color: #f3f4f6 !important; }
          [data-testid="stAppViewContainer"] [data-testid="stCaptionContainer"] *,
          [data-testid="stAppViewContainer"] small { color: #b9c5d4 !important; }
          [data-testid="stMain"] .stButton > button, [data-testid="stSidebar"] .stButton > button,
          [data-testid="stChatInput"], [data-testid="stChatInput"] > div, [data-testid="stChatInput"] form,
          [data-testid="stTextInput"] input, [data-testid="stTextArea"] textarea,
          [data-testid="stSelectbox"] [data-baseweb="select"] > div,
          [data-testid="stMultiSelect"] [data-baseweb="select"] > div,
          [data-testid="stFileUploader"], [data-testid="stFileUploader"] section,
          [data-testid="stFileUploaderDropzone"], [data-testid="stChatMessage"] {
            background: #1f2937 !important; border-color: #475569 !important; color: #f3f4f6 !important;
          }
          [data-testid="stMain"] .stButton > button, [data-testid="stSidebar"] .stButton > button,
          [data-testid="stChatInput"] textarea, [data-testid="stChatInput"] textarea::placeholder,
          [data-testid="stTextInput"] input, [data-testid="stTextArea"] textarea { color: #f3f4f6 !important; }
          [data-testid="stChatInput"] textarea::placeholder { color: #94a3b8 !important; }
          .stButton > button[kind="primary"], [data-testid="stFormSubmitButton"] > button,
          [data-testid="stChatInput"] button {
            background: #2563eb !important; border-color: #3b82f6 !important; color: #ffffff !important;
            box-shadow: 0 6px 18px rgba(37, 99, 235, .28) !important;
          }
          [data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatarUser"]),
          [data-testid="stSidebar"] .stButton > button:hover, [data-testid="stMain"] .stButton > button:hover,
          [data-testid="stPills"] button:hover, [data-testid="stPills"] button[aria-pressed="true"] {
            background: #273449 !important; border-color: #60a5fa !important; color: #f8fafc !important;
          }
          [data-testid="stPills"] button, [data-testid="stTabs"] button, [data-testid="stTabs"] button[aria-selected="true"],
          [data-testid="stSidebar"] [data-testid="stRadio"] label:has(input:checked) {
            background: #1f2937 !important; border-color: #475569 !important; color: #e5edf7 !important;
          }
          [data-testid="stPills"] button[aria-pressed="true"], [data-testid="stTabs"] button[aria-selected="true"] {
            background: #1d4ed8 !important; border-color: #60a5fa !important; color: #ffffff !important;
          }
          /* Streamlit renders segmented controls as labels in some releases and
             as buttons in others, so both structures need the same palette. */
          [data-testid="stSegmentedControl"],
          [data-testid="stSegmentedControl"] [role="radiogroup"] {
            background: #1b2638 !important; border-color: #475569 !important;
          }
          [data-testid="stSegmentedControl"] label,
          [data-testid="stSegmentedControl"] button {
            background: #1f2937 !important; border-color: #475569 !important; color: #e5edf7 !important;
            box-shadow: none !important;
          }
          [data-testid="stSegmentedControl"] label:has(input:checked),
          [data-testid="stSegmentedControl"] button[aria-checked="true"],
          [data-testid="stSegmentedControl"] button[aria-pressed="true"] {
            background: #1d4ed8 !important; border-color: #60a5fa !important; color: #ffffff !important;
          }
          /* Current Streamlit uses an unlabelled radiogroup for segmented_control. */
          [role="radiogroup"] > button[data-variant="segmented_control"] {
            background: #1f2937 !important;
            border: 1px solid #475569 !important;
            color: #e5edf7 !important;
            box-shadow: none !important;
            transition: none !important;
          }
          [role="radiogroup"] > button[data-variant="segmented_control"][aria-checked="true"] {
            background: #1d4ed8 !important;
            border-color: #60a5fa !important;
            color: #ffffff !important;
          }
          [role="radiogroup"] > button[data-variant="segmented_control"] [data-testid="stMarkdownContainer"] p {
            color: inherit !important;
          }
          [data-testid="stSelectbox"] [data-baseweb="select"],
          [data-testid="stSelectbox"] [data-baseweb="select"] > div,
          [data-testid="stMultiSelect"] [data-baseweb="select"],
          [data-testid="stMultiSelect"] [data-baseweb="select"] > div,
          [data-baseweb="popover"], [data-baseweb="popover"] [role="listbox"],
          [role="listbox"] {
            background: #1f2937 !important; border-color: #475569 !important; color: #f3f4f6 !important;
          }
          /* Streamlit 1.5x uses React Aria groups for selectboxes. Keep the
             wrapper dark too, otherwise the native white input leaks through. */
          [data-testid="stSelectbox"] [role="group"],
          [data-testid="stMultiSelect"] [role="group"] {
            background: #1f2937 !important;
            border: 1px solid #475569 !important;
            color: #f3f4f6 !important;
            box-shadow: none !important;
          }
          [data-testid="stSelectbox"] [role="group"] input[role="combobox"],
          [data-testid="stMultiSelect"] [role="group"] input[role="combobox"] {
            background: transparent !important;
            color: #f3f4f6 !important;
            -webkit-text-fill-color: #f3f4f6 !important;
          }
          [data-testid="stSelectbox"] [role="group"] > button,
          [data-testid="stMultiSelect"] [role="group"] > button {
            background: transparent !important;
            border: 0 !important;
            color: #cbd5e1 !important;
            box-shadow: none !important;
          }
          [data-testid="stSelectbox"] [role="group"]:focus-within,
          [data-testid="stMultiSelect"] [role="group"]:focus-within {
            border-color: #60a5fa !important;
            box-shadow: 0 0 0 3px rgba(96, 165, 250, .20) !important;
          }
          [role="option"] { background: #1f2937 !important; color: #e5edf7 !important; }
          [role="option"][aria-selected="true"], [role="option"]:hover { background: #273449 !important; color: #ffffff !important; }
          [data-testid="stDownloadButton"] > button,
          [data-testid="stFileUploader"] button {
            background: #1f2937 !important; border-color: #475569 !important; color: #e5edf7 !important;
          }
          [data-testid="stDownloadButton"] > button:hover,
          [data-testid="stFileUploader"] button:hover {
            background: #273449 !important; border-color: #60a5fa !important; color: #ffffff !important;
          }
          /* These controls had light-mode key-specific rules with higher priority. */
          [class*="st-key-seller_suggestion"] button,
          [class*="st-key-open_"] button,
          [class*="st-key-collapse_sidebar"] button,
          [class*="st-key-expand_sidebar"] button,
          [data-testid="stPills"] button {
            background: #1f2937 !important; border-color: #475569 !important; color: #e5edf7 !important;
            box-shadow: none !important;
          }
          [class*="st-key-seller_suggestion"] button:hover,
          [class*="st-key-open_"] button:hover,
          [class*="st-key-collapse_sidebar"] button:hover,
          [class*="st-key-expand_sidebar"] button:hover,
          [data-testid="stPills"] button:hover {
            background: #273449 !important; border-color: #60a5fa !important; color: #ffffff !important;
          }
          [class*="st-key-open_"] button:disabled, [data-testid="stPills"] button:disabled {
            background: #1b2638 !important; border-color: #334155 !important; color: #94a3b8 !important; opacity: 1 !important;
          }
          [class*="st-key-open_"] button[kind="primary"],
          [class*="st-key-compact_open_"] button[kind="primary"] {
            background: #24385a !important; border: 1.5px solid #60a5fa !important;
            color: #ffffff !important; font-weight: 750 !important;
            box-shadow: 0 4px 14px rgba(96, 165, 250, .20) !important;
          }
          [class*="st-key-open_"] button[kind="primary"]:hover,
          [class*="st-key-compact_open_"] button[kind="primary"]:hover {
            background: #2d4a73 !important; border-color: #93c5fd !important;
          }
          [data-testid="stAlert"], [data-testid="stExpander"] details,
          [data-testid="stVerticalBlockBorderWrapper"] { background: #1b2638 !important; border-color: #475569 !important; }
          /* The settings panel is a native details/summary block in the
             sidebar, not an stExpander. Prevent its light summary strip. */
          [data-testid="stSidebar"] details,
          [data-testid="stSidebar"] details > summary {
            background: #1b2638 !important;
            border-color: #475569 !important;
            color: #f3f4f6 !important;
          }
          [data-testid="stSidebar"] details > summary:hover {
            background: #273449 !important;
          }
          /* Glide Data Grid is drawn on a canvas, so give it its own dark palette. */
          [data-testid="stDataFrame"], [data-testid="stDataEditor"] {
            --gdg-bg-cell: #1f2937 !important;
            --gdg-bg-cell-medium: #1f2937 !important;
            --gdg-bg-header: #273449 !important;
            --gdg-bg-header-has-focus: #334155 !important;
            --gdg-bg-bubble: #273449 !important;
            --gdg-text-dark: #e5edf7 !important;
            --gdg-text-medium: #cbd5e1 !important;
            --gdg-text-light: #94a3b8 !important;
            --gdg-text-header: #f8fafc !important;
            --gdg-border-color: #475569 !important;
            --gdg-horizontal-border-color: #334155 !important;
            --gdg-accent-color: #60a5fa !important;
          }
          .seller-eyebrow { color: #93c5fd !important; }
          .seller-subtitle { color: #b9c5d4 !important; }
        </style>
        """,
        unsafe_allow_html=True,
    )


def new_conversation_context(mode: str) -> dict[str, Any]:
    """Return isolated, empty workspace state for a newly-created chat."""
    return {
        "seller_uploaded_rows": None,
        "seller_uploaded_names": (),
        "seller_data_origin": None,
        "seller_library_scope": "demo" if mode == "learner" else "owner",
        "seller_demo_selected_ids": [],
        "seller_market_scenario_seed": random.SystemRandom().randint(1, 999_999_999),
        "seller_market_category_id": "appliance",
        "market_section": "So sánh giá",
        "market_price_product": None,
        "market_listing_shops": None,
        "seller_market_advisor_messages": [],
        "seller_advisor_handoffs": [],
        "seller_advisor_surface": "market",
        "seller_strategy_last_simulation": None,
        "strategy_section": "Radar cơ hội",
        "strategy_category_id": "appliance",
        "strategy_inventory_category": "appliance",
        "strategy_target_stock_months": 2.0,
    }


def snapshot_active_context() -> dict[str, Any]:
    """Copy the active chat's tools and data without sharing mutable lists."""
    return {
        key: deepcopy(st.session_state.get(key))
        for key in CONVERSATION_CONTEXT_KEYS
    }


def restore_conversation_context(conversation: dict[str, Any]) -> None:
    """Restore one conversation's data/tool context before its view renders."""
    context = conversation.get("context")
    if not isinstance(context, dict):
        context = new_conversation_context(str(conversation["mode"]))
    defaults = new_conversation_context(str(conversation["mode"]))
    for key in CONVERSATION_CONTEXT_KEYS:
        value = context.get(key, defaults[key])
        if key in CONVERSATION_WIDGET_KEYS and value is None:
            st.session_state.pop(key, None)
        else:
            st.session_state[key] = deepcopy(value)
    st.session_state.seller_market_advisor_open = False


def active_conversation() -> dict[str, Any] | None:
    chat_id = st.session_state.get("seller_active_chat_id")
    return next(
        (item for item in st.session_state.seller_conversations if item["id"] == chat_id),
        None,
    )


def conversation_data_label(conversation: dict[str, Any] | None = None) -> str:
    """Give users a plain-language indicator of which data belongs to a chat."""
    context: dict[str, Any]
    if conversation is None:
        context = snapshot_active_context()
    else:
        stored = conversation.get("context")
        context = stored if isinstance(stored, dict) else {}
    origin = context.get("seller_data_origin")
    if origin == "demo_library":
        return ui_text("Đã gắn bộ dữ liệu demo", "Demo data attached")
    if origin == "owner_library":
        return ui_text("Đã gắn dữ liệu shop đã lưu", "Saved shop data attached")
    if origin == "uploaded_csv":
        return ui_text("Đã gắn dữ liệu CSV của shop", "Uploaded shop data attached")
    return ui_text("Chưa gắn dữ liệu vận hành", "No operational data attached")


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
    if not first_question:
        adviser_messages = st.session_state.get("seller_market_advisor_messages", [])
        first_question = next(
            (item["content"] for item in adviser_messages if item["role"] == "user"),
            None,
        )
    if first_question:
        return human_title(str(first_question))
    return f"Chat {active_chat_type(mode)['name'].lower()}"


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
            conversation["context"] = snapshot_active_context()
            conversation["updated_at"] = datetime.now().isoformat(timespec="seconds")
            return


def start_conversation(mode: str) -> None:
    save_active_conversation()
    chat_id = f"{mode}_{len(st.session_state.seller_conversations) + 1}"
    st.session_state.seller_chat_mode = mode
    st.session_state.seller_active_chat_id = chat_id
    st.session_state.seller_show_chat_picker = False
    st.session_state.seller_view = "chat"
    new_context = new_conversation_context(mode)
    for key, value in new_context.items():
        if key in CONVERSATION_WIDGET_KEYS and value is None:
            st.session_state.pop(key, None)
        else:
            st.session_state[key] = deepcopy(value)
    clear_active_conversation()
    st.session_state.seller_conversations.append(
        {
            "id": chat_id,
            "mode": mode,
            "title": conversation_title([], mode),
            "messages": [],
            "context": snapshot_active_context(),
            "updated_at": datetime.now().isoformat(timespec="seconds"),
        }
    )


def open_conversation(chat_id: str) -> None:
    save_active_conversation()
    conversation = next(item for item in st.session_state.seller_conversations if item["id"] == chat_id)
    st.session_state.seller_active_chat_id = conversation["id"]
    st.session_state.seller_chat_mode = conversation["mode"]
    st.session_state.seller_messages = list(conversation["messages"])
    restore_conversation_context(conversation)
    st.session_state.seller_view = "chat"
    st.session_state.pop("seller_suggestion", None)
    request_scroll_to_latest()


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
    save_active_conversation()


def open_market_advisor(surface: str = "market") -> None:
    st.session_state.seller_market_advisor_open = True
    st.session_state.seller_advisor_surface = surface
    save_active_conversation()


def close_market_advisor() -> None:
    st.session_state.seller_market_advisor_open = False
    save_active_conversation()


def route_from_advisor(view: str) -> None:
    """Open the requested workspace while retaining the current chat context."""
    if view == "strategy":
        category = str(st.session_state.get("seller_market_category_id", "appliance"))
        st.session_state.strategy_category_id = category
        st.session_state.strategy_inventory_category = category
    st.session_state.seller_market_advisor_open = False
    st.session_state.seller_view = view
    save_active_conversation()


def latest_advisor_exchange() -> tuple[str, str] | None:
    """Return the latest complete question-and-answer pair from the strategy adviser."""
    messages = st.session_state.get("seller_market_advisor_messages", [])
    for index in range(len(messages) - 1, -1, -1):
        message = messages[index]
        if message.get("role") != "assistant":
            continue
        question = next(
            (
                str(previous["content"])
                for previous in reversed(messages[:index])
                if previous.get("role") == "user"
            ),
            "",
        )
        if question:
            return question, str(message["content"])
    return None


def handoff_advisor_to_main_chat() -> bool:
    """Store a concise adviser note in the active chat, without merging histories."""
    exchange = latest_advisor_exchange()
    if exchange is None or active_conversation() is None:
        return False
    question, answer = exchange
    handoffs: list[dict[str, str]] = st.session_state.seller_advisor_handoffs
    handoff = {
        "question": question,
        "answer": answer,
        "category_id": str(st.session_state.get("seller_market_category_id", "appliance")),
        "created_at": datetime.now().isoformat(timespec="seconds"),
    }
    if not handoffs or handoffs[-1].get("question") != question or handoffs[-1].get("answer") != answer:
        handoffs.append(handoff)
    st.session_state.seller_market_advisor_open = False
    st.session_state.seller_view = "chat"
    save_active_conversation()
    return True


@st.cache_data(max_entries=1, show_spinner=False)
def cached_market_categories() -> list[dict[str, Any]]:
    """Reuse the static 50-category demo catalogue across page reruns."""
    return market_categories()


@st.cache_data(max_entries=100, show_spinner=False)
def cached_marketplace(category_id: str, scenario_seed: int) -> dict[str, Any]:
    """Reuse the deterministic market scene until the seller creates a new one."""
    return simulated_marketplace(category_id, scenario_seed)


@st.cache_data(max_entries=1, show_spinner=False)
def cached_opportunity_radar() -> list[dict[str, Any]]:
    """The opportunity ranking is static demo reference data."""
    return opportunity_radar()


@st.cache_data(max_entries=150, show_spinner=False)
def cached_inventory_risk_analysis(
    category_id: str, scenario_seed: int, target_stock_months: float
) -> dict[str, Any]:
    """Avoid recalculating the same inventory scenario after unrelated UI clicks."""
    return inventory_risk_analysis(category_id, scenario_seed, target_stock_months)


def market_category_name(category_id: str) -> str:
    """Translate a saved category id into the seller-facing category name."""
    return next(
        (str(item["category"]) for item in cached_market_categories() if str(item["id"]) == category_id),
        "ngành hàng đang xem",
    )


def render_advisor_handoff() -> None:
    """Show adviser notes in the main chat without mixing the two histories."""
    handoffs = st.session_state.get("seller_advisor_handoffs", [])
    if not handoffs:
        return
    latest = handoffs[-1]
    category_name = market_category_name(str(latest.get("category_id", "")))
    with st.container(border=True):
        st.markdown("#### :material/link: Ghi chú từ Chiến lược gia AI")
        st.caption(
            f"Đã chuyển từ Chiến lược gia AI cho **{category_name}**. Đây là bản ghi chú để AI chính có ngữ cảnh; "
            "lịch sử của hai cửa sổ vẫn được lưu riêng."
        )
        st.markdown(f"**Bạn đã hỏi:** {latest['question']}")
        st.markdown(f"**Gợi ý chiến lược:** {latest['answer']}")
        with st.container(horizontal=True):
            if st.button("Mở lại Chiến lược gia AI", key="reopen_advisor_from_handoff", icon=":material/smart_toy:"):
                open_market_advisor("chat")
                st.rerun()
            if st.button("Hỏi AI chính cần kiểm tra gì", key="ask_main_from_handoff", icon=":material/fact_check:"):
                answer_excerpt = str(latest["answer"])[:700]
                st.session_state.seller_pending_main_prompt = (
                    f"Tôi đang cân nhắc một gợi ý cho ngành {category_name}: {answer_excerpt} "
                    "Trước khi thử, tôi cần kiểm tra chính sách Shopee hoặc số liệu vận hành nào? "
                    "Chỉ nêu điều có thể kiểm chứng, không cam kết kết quả kinh doanh."
                )
                st.rerun()


def render_workspace_context(surface: str) -> None:
    """Make the active chat/data binding visible when tools are opened."""
    conversation = active_conversation()
    if conversation is None:
        st.caption(ui_text(
            "Chưa chọn cuộc trò chuyện: kết quả hiện tại chưa được gắn vào lịch sử chat nào.",
            "No conversation is selected: these results are not attached to any chat history.",
        ))
        return
    workspace = ui_text("Phân tích thị trường", "Market analysis") if surface == "market" else ui_text("Chiến lược kinh doanh", "Business strategy")
    chat_type = active_chat_type(str(conversation["mode"]))
    st.caption(
        ui_text(
            f":material/link: {workspace} đang làm việc cho **{chat_type['name']} · {conversation['title']}** · **{conversation_data_label(conversation)}**. Chiến lược gia AI và kết quả ở đây được lưu riêng theo chat này.",
            f":material/link: {workspace} is working for **{chat_type['name']} · {conversation['title']}** · **{conversation_data_label(conversation)}**. The strategy adviser and these results are stored separately for this chat.",
        )
    )


def render_quick_guide(when_to_use: str, steps: list[str]) -> None:
    """Put a short, non-technical 'what to do next' guide on each workspace."""
    with st.container(border=True):
        st.markdown(f"**:material/help: {ui_text('Cách dùng nhanh', 'Quick guide')}** — {ui_text('Dùng phần này khi ', 'Use this area when ')}{when_to_use}")
        st.caption(" → ".join(f"{index + 1}. {step}" for index, step in enumerate(steps)))


def queue_selected_learner_question() -> None:
    """Send a dropdown selection straight into the main chat on this rerun."""
    selected = st.session_state.get("learner_question_picker")
    if not selected:
        return
    st.session_state.seller_pending_main_prompt = str(selected)
    # This callback runs before widgets render, so the picker can safely reset
    # and the same question remains selectable later.
    st.session_state.learner_question_picker = None


def render_learner_question_bank() -> None:
    """Keep beginner prompts compact: one picker, no long table."""
    language = str(st.session_state.get("seller_language", "vi"))
    question_key = "question_vi" if language == "vi" else "question_en"
    st.selectbox(
        ui_text("Chọn câu hỏi cho người mới", "Choose a new seller question"),
        [item[question_key] for item in LEARNER_QUESTION_BANK],
        index=None,
        placeholder=ui_text("Chọn câu hỏi muốn hỏi", "Choose a question to ask"),
        label_visibility="collapsed",
        key="learner_question_picker",
        on_change=queue_selected_learner_question,
    )


def open_chat_view() -> None:
    st.session_state.seller_view = "chat"
    if st.session_state.get("seller_active_chat_id"):
        request_scroll_to_latest()


def request_scroll_to_latest() -> None:
    """Queue one browser-side scroll after the selected chat has rendered."""
    st.session_state.seller_scroll_to_latest = True
    st.session_state.seller_chat_scroll_sequence += 1


def render_scroll_navigation() -> None:
    """Mount the global top button and scroll to the newest message after chat switches."""
    should_scroll = bool(st.session_state.pop("seller_scroll_to_latest", False))
    active = active_conversation()
    token = None
    if should_scroll and st.session_state.get("seller_view") == "chat" and active is not None:
        token = f"{active['id']}:{st.session_state.seller_chat_scroll_sequence}"
    _SCROLL_NAVIGATION(
        key="seller_scroll_navigation",
        data={
            "scroll_to_latest": bool(token),
            "scroll_token": token,
            "top_label": ui_text("Lên đầu trang", "Back to top"),
            "show_after": 180,
        },
        height=0,
    )


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


def human_title(question: str, limit: int = 44) -> str:
    text = " ".join(question.split())
    return text[:limit] + ("…" if len(text) > limit else "")


def sidebar_chat_label(conversation: dict[str, Any]) -> str:
    """Keep a recent-chat control compact without duplicating its active state."""
    chat_type = active_chat_type(str(conversation["mode"]))
    # The sidebar has a fixed 56 px card.  Trim before rendering as well as in
    # CSS, so its text remains one line on narrow displays and older browsers.
    return f"{chat_type['name']} · {human_title(str(conversation['title']), limit=16)}"


def data_note(source: str | None) -> str | None:
    if source == "uploaded_csv":
        return ui_text("Dữ liệu sử dụng: báo cáo bạn tải lên trong phiên này.", "Data used: reports uploaded in this session.")
    if source == "mock_shop_data":
        return ui_text("Dữ liệu sử dụng: dữ liệu mô phỏng phục vụ demo.", "Data used: simulated data for demonstration.")
    if source == "demo_library":
        return ui_text("Dữ liệu sử dụng: bộ dữ liệu demo trong Thư viện dữ liệu.", "Data used: demo data from Data library.")
    if source == "owner_library":
        return ui_text("Dữ liệu sử dụng: bảng dữ liệu cửa hàng đã lưu trên máy này.", "Data used: shop tables saved on this device.")
    return None


def data_requirement_note(requirement: str | None) -> str | None:
    """Make the answer's evidence contract visible to the seller.

    There are deliberately only two classes in the UI.  Tool names and
    internal planner intents are implementation details and should not make a
    user guess whether they need to upload a report.
    """
    if requirement == "shop_data_required":
        return ui_text(
            "Loại câu hỏi: cần dữ liệu shop để trả lời theo tình hình thực tế.",
            "Question type: shop data is required for a situation-specific answer.",
        )
    if requirement == "no_shop_data_required":
        return ui_text(
            "Loại câu hỏi: không cần dữ liệu shop.",
            "Question type: no shop data is required.",
        )
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
    if not result.get("show_summary_metrics", True):
        return
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
        requirement = data_requirement_note(message.get("data_requirement"))
        if requirement:
            st.caption(":material/fact_check: " + requirement)
        note = data_note(message.get("data_source"))
        if note:
            st.caption(":material/table_chart: " + note)
        confidence = message.get("confidence")
        if confidence:
            st.caption(f":material/verified: Độ chắc chắn: {confidence}")
        render_sources(message.get("citations", []))


def missing_data_response(question: str) -> dict[str, Any]:
    """Return the exact table requirement instead of a generic data warning."""
    guidance = AgentRunner._data_request_guidance(normalize(question))
    return {
        "answer": "**Bạn hãy tạo hoặc tải dữ liệu cần thiết trước khi hỏi số liệu của shop.**\n\n" + guidance,
        "citations": [],
        "data_source": None,
        "confidence": "Chưa đủ dữ liệu",
        "data_requirement": "shop_data_required",
    }


def question_with_chat_context(question: str) -> str:
    """Resolve short follow-ups such as “ví dụ” from the current chat only."""
    normalized = normalize(question)
    follow_up_starts = (
        "vi du", "cho vi du", "them vi du", "giai thich them", "tai sao",
        "con cach nao", "cu the hon",
    )
    if not any(normalized.startswith(prefix) for prefix in follow_up_starts):
        return question
    prior_questions = [
        str(message.get("content", "")).strip()
        for message in st.session_state.get("seller_messages", [])
        if message.get("role") == "user" and str(message.get("content", "")).strip()
    ]
    if prior_questions and prior_questions[-1] == question.strip():
        prior_questions.pop()
    if not prior_questions:
        return question
    return f"{prior_questions[-1]}\n\nNgười dùng hỏi tiếp: {question}"


def answer_question(question: str) -> dict[str, Any]:
    effective_question = question_with_chat_context(question)
    plan = Planner().plan(effective_question)
    # In a New seller chat, the curated fundamentals are general guidance.
    # They must not be blocked as if the user had asked for their own shop's
    # metrics merely because they contain words such as "đơn hàng" or
    # "quảng cáo". Owner questions and all data-specific questions still use
    # the normal private-data guard.
    is_basic_learner_guidance = (
        st.session_state.get("seller_chat_mode") == "learner"
        and bool(AgentRunner._learner_guidance_answer(effective_question))
    )
    requires_shop_data = plan.needs_private_shop_data and not is_basic_learner_guidance
    if requires_shop_data and not is_uploaded():
        return missing_data_response(effective_question)
    result = active_runner().run(effective_question)
    result["question"] = question
    # Outside Eslabong's scope is deliberately not presented as either class:
    # “không cần dữ liệu” must never imply that the bot can answer weather,
    # health, or other unrelated questions.
    result["data_requirement"] = (
        None if plan.intent == "out_of_scope"
        else "shop_data_required" if requires_shop_data else "no_shop_data_required"
    )
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
    "purchase_orders.csv": {
        "title": "Đơn nhập hàng (tùy chọn)",
        "help": "Theo dõi nhà cung cấp, giá nhập, số lượng và hàng đang về.",
        "columns": ["purchase_order_id", "order_date", "supplier_name", "sku", "quantity", "unit_cost_vnd", "expected_arrival_date", "status"],
    },
    "returns.csv": {
        "title": "Hoàn hàng (tùy chọn)",
        "help": "Ghi nhận nguyên nhân, số lượng và tiền hoàn để tìm vấn đề cần xử lý.",
        "columns": ["return_id", "order_id", "request_date", "sku", "quantity", "reason", "status", "refund_amount_vnd"],
    },
    "reviews.csv": {
        "title": "Đánh giá khách hàng (tùy chọn)",
        "help": "Theo dõi điểm đánh giá và vấn đề khách nêu để cải thiện sản phẩm.",
        "columns": ["review_id", "review_date", "sku", "rating", "sentiment", "issue_type", "comment"],
    },
    "operating_costs.csv": {
        "title": "Chi phí vận hành (tùy chọn)",
        "help": "Ghi chi phí thật như đóng gói, nhân sự và kho bãi để không nhầm lãi góp với lãi sau vận hành.",
        "columns": ["cost_id", "month", "cost_category", "amount_vnd", "note"],
    },
    "inventory_movements.csv": {
        "title": "Biến động kho (tùy chọn)",
        "help": "Ghi hàng nhập, bán ra và hàng lỗi/hủy. Bảng này hỗ trợ rà soát kho, không thay thế kiểm kê thực tế.",
        "columns": ["movement_id", "movement_date", "sku", "movement_type", "quantity", "reference", "note"],
    },
    "quality_checks.csv": {
        "title": "Kiểm tra chất lượng lô hàng (tùy chọn)",
        "help": "Theo dõi số hàng đã kiểm, hàng lỗi và tình trạng phản hồi nhà cung cấp.",
        "columns": ["check_id", "check_date", "purchase_order_id", "sku", "inspected_quantity", "defective_quantity", "defect_type", "status"],
    },
    "cash_flow.csv": {
        "title": "Dòng tiền (tùy chọn)",
        "help": "Ghi tiền thu và chi thực tế để nhận biết thiếu tiền mặt; đây không thay thế sổ sách kế toán.",
        "columns": ["cash_flow_id", "date", "direction", "category", "amount_vnd", "reference", "note"],
    },
    "supplier_performance.csv": {
        "title": "Hiệu quả nhà cung cấp (tùy chọn)",
        "help": "So sánh giao đúng hẹn, tỷ lệ lỗi và thời gian giao giữa các nguồn hàng đã có dữ liệu.",
        "columns": ["supplier_id", "supplier_name", "month", "on_time_delivery_rate_percent", "defect_rate_percent", "average_lead_time_days", "order_count"],
    },
    "customer_segments.csv": {
        "title": "Nhóm khách hàng (tùy chọn)",
        "help": "Chỉ nhập số liệu tổng hợp để theo dõi khách quay lại, không lưu thông tin cá nhân khách hàng.",
        "columns": ["month", "segment_name", "customer_count", "order_count", "repeat_order_count", "gmv_vnd"],
    },
    "product_funnel.csv": {
        "title": "Hiệu quả từng sản phẩm (tùy chọn)",
        "help": "Ghi lượt xem, thêm giỏ và đơn để xác định bước cần kiểm tra ở mỗi sản phẩm.",
        "columns": ["month", "sku", "views", "add_to_cart_count", "order_count"],
    },
    "co_purchase.csv": {
        "title": "Sản phẩm mua cùng (tùy chọn)",
        "help": "Ghi số đơn đã mua cùng một cặp sản phẩm theo kỳ. AI chỉ dùng bảng này để chọn cặp đáng thử, không cam kết combo sẽ tăng doanh số.",
        "columns": ["month", "sku", "paired_sku", "joint_order_count"],
    },
    "price_promotions.csv": {
        "title": "Giá và khuyến mãi theo SKU (tùy chọn)",
        "help": "Ghi giá niêm yết, giá cuối và nguồn mã giảm giá theo ngày để AI phân biệt số liệu đã xảy ra với khuyến nghị thử nghiệm.",
        "columns": ["date", "sku", "list_price_vnd", "final_price_vnd", "seller_discount_vnd", "voucher_source", "campaign_name"],
    },
    "ads_sku_daily.csv": {
        "title": "Quảng cáo theo SKU/ngày (tùy chọn)",
        "help": "Ghi hiệu quả theo từng SKU thay vì chỉ tổng chiến dịch. Không nhập dữ liệu định danh khách hàng.",
        "columns": ["date", "campaign_id", "sku", "impressions", "clicks", "spend_vnd", "add_to_cart_count", "attributed_orders", "attributed_revenue_vnd"],
    },
    "inventory_batches.csv": {
        "title": "Tuổi tồn kho theo lô (tùy chọn)",
        "help": "Ghi ngày nhập và số còn lại của từng lô để AI cảnh báo hàng nằm lâu; vẫn cần kiểm kê thực tế trước khi xử lý hàng.",
        "columns": ["batch_id", "sku", "received_date", "available_units", "unit_cost_vnd"],
    },
    "search_performance.csv": {"title": "Hiệu quả tìm kiếm (tùy chọn)", "help": "Theo dõi từ khóa, lượt hiển thị, vị trí và lượt nhấp; không dùng để khẳng định một từ khóa chắc chắn tạo ra đơn.", "columns": ["date", "sku", "search_term", "impressions", "clicks", "average_position"]},
    "shipping_performance.csv": {"title": "Vận chuyển (tùy chọn)", "help": "Theo dõi giao trễ, lý do hủy và thời gian xử lý theo đơn để tìm điểm vận hành cần kiểm tra.", "columns": ["order_id", "order_date", "status", "is_late", "cancellation_reason", "processing_hours"]},
    "settlements.csv": {"title": "Đối soát thanh toán (tùy chọn)", "help": "Đối chiếu số tiền Shopee phải trả, phí thực tế và tiền đã nhận; vẫn cần sao kê và hóa đơn gốc.", "columns": ["settlement_id", "settlement_date", "payout_date", "shopee_payable_vnd", "actual_fee_vnd", "received_amount_vnd", "status"]},
    "competitor_catalog.csv": {"title": "Danh mục đối thủ (tham khảo)", "help": "Chỉ nhập dữ liệu quan sát/ước tính. Eslabong không coi đây là dữ liệu trực tiếp từ Shopee hoặc bằng chứng doanh số của đối thủ.", "columns": ["observed_date", "reference_sku", "competitor_shop", "product_name", "price_vnd", "rating", "review_count", "estimated_monthly_units"]},
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
    "purchase_order_id": "Mã đơn nhập", "supplier_name": "Nhà cung cấp", "unit_cost_vnd": "Giá nhập/đơn vị (VND)",
    "expected_arrival_date": "Ngày dự kiến về", "return_id": "Mã hoàn hàng", "request_date": "Ngày yêu cầu hoàn",
    "reason": "Lý do", "refund_amount_vnd": "Tiền hoàn (VND)", "review_id": "Mã đánh giá",
    "review_date": "Ngày đánh giá", "rating": "Số sao", "sentiment": "Cảm xúc", "issue_type": "Vấn đề", "comment": "Nhận xét",
    "cost_id": "Mã chi phí", "cost_category": "Nhóm chi phí", "amount_vnd": "Số tiền (VND)", "note": "Ghi chú",
    "movement_id": "Mã biến động", "movement_date": "Ngày biến động", "movement_type": "Loại biến động", "reference": "Mã tham chiếu",
    "check_id": "Mã kiểm tra", "check_date": "Ngày kiểm tra", "inspected_quantity": "Số lượng đã kiểm", "defective_quantity": "Số lượng lỗi", "defect_type": "Loại lỗi",
    "cash_flow_id": "Mã dòng tiền", "date": "Ngày ghi nhận", "direction": "Thu / chi", "amount_vnd": "Số tiền (VND)",
    "supplier_id": "Mã nhà cung cấp", "supplier_name": "Tên nhà cung cấp", "on_time_delivery_rate_percent": "Giao đúng hẹn (%)", "defect_rate_percent": "Tỷ lệ lỗi (%)", "average_lead_time_days": "Số ngày giao trung bình",
    "segment_name": "Nhóm khách", "customer_count": "Số khách", "repeat_order_count": "Đơn mua lại", "gmv_vnd": "GMV (VND)",
    "views": "Lượt xem", "add_to_cart_count": "Lượt thêm giỏ", "order_count": "Số đơn",
    "paired_sku": "Mã sản phẩm mua cùng", "joint_order_count": "Số đơn mua cùng",
    "batch_id": "Mã lô", "received_date": "Ngày nhập kho", "available_units": "Số lượng còn lại",
    "final_price_vnd": "Giá sau khuyến mãi (VND)", "voucher_source": "Nguồn mã giảm giá", "campaign_name": "Tên chương trình",
    "impressions": "Lượt hiển thị", "clicks": "Lượt nhấp", "attributed_orders": "Số đơn quy gán",
    "search_term": "Từ khóa", "average_position": "Vị trí trung bình", "is_late": "Giao trễ", "cancellation_reason": "Lý do hủy", "processing_hours": "Số giờ xử lý",
    "settlement_id": "Mã đối soát", "settlement_date": "Ngày đối soát", "payout_date": "Ngày nhận tiền", "shopee_payable_vnd": "Tiền Shopee phải trả (VND)", "actual_fee_vnd": "Phí thực tế (VND)", "received_amount_vnd": "Tiền đã nhận (VND)",
    "observed_date": "Ngày quan sát", "reference_sku": "SKU tham chiếu", "competitor_shop": "Shop đối thủ", "price_vnd": "Giá (VND)", "estimated_monthly_units": "Lượt bán ước tính/tháng",
}

# Các mẫu dùng tiếng Việt không dấu để người dùng có thể tự lập bảng trong
# Excel mà không phải học tên trường kỹ thuật. Hệ thống vẫn chấp nhận cả cột
# tiếng Việt có dấu và schema kỹ thuật cũ để không làm hỏng các tệp đã có.
VIETNAMESE_UPLOAD_TEMPLATES = {
    "orders.csv": {
        "title": "Đơn hàng",
        "columns": ["ma_don_hang", "ngay_dat_hang", "trang_thai", "ma_san_pham", "so_luong", "gia_tri_hang_hoa_vnd", "giam_gia_nguoi_ban_vnd", "tro_gia_san_vnd", "phi_giao_dich_uoc_tinh_vnd", "phi_dich_vu_uoc_tinh_vnd"],
    },
    "products.csv": {
        "title": "Sản phẩm",
        "columns": ["ma_san_pham", "ten_san_pham", "nganh_hang", "gia_von_don_vi_vnd", "gia_niem_yet_vnd"],
    },
    "inventory.csv": {
        "title": "Tồn kho",
        "columns": ["ma_san_pham", "ton_thuc_te", "da_giu_cho", "nguong_nhap_them", "ngay_cap_nhat"],
    },
}

EXCEL_SHEET_NAMES = {
    "orders.csv": "Don hang", "products.csv": "San pham", "inventory.csv": "Ton kho",
    "ads.csv": "Quang cao", "purchase_orders.csv": "Don nhap hang", "returns.csv": "Hoan hang",
    "reviews.csv": "Danh gia", "operating_costs.csv": "Chi phi van hanh",
    "inventory_movements.csv": "Bien dong kho", "quality_checks.csv": "Kiem tra chat luong",
    "cash_flow.csv": "Dong tien", "supplier_performance.csv": "Nha cung cap",
    "customer_segments.csv": "Nhom khach hang", "product_funnel.csv": "Hieu qua san pham",
    "co_purchase.csv": "San pham mua cung",
    "price_promotions.csv": "Gia khuyen mai", "ads_sku_daily.csv": "Quang cao SKU ngay",
    "inventory_batches.csv": "Tuoi ton kho",
    "search_performance.csv": "Hieu qua tim kiem", "shipping_performance.csv": "Van chuyen", "settlements.csv": "Doi soat thanh toan", "competitor_catalog.csv": "Danh muc doi thu",
}


@st.cache_data(show_spinner=False)
def vietnamese_excel_template(columns: tuple[str, ...]) -> bytes:
    """Create a blank .xlsx template with Vietnamese, no-accent headers."""
    output = BytesIO()
    pd.DataFrame(columns=list(columns)).to_excel(output, index=False, engine="openpyxl")
    return output.getvalue()


@st.cache_data(show_spinner=False)
def vietnamese_excel_export(
    rows_by_name: dict[str, list[dict[str, str]]],
    include_empty_sheets: bool = True,
) -> bytes:
    """Export an editable workbook with every supported Eslabong sheet.

    A header-only optional sheet is intentional: it lets a shop add that
    report later without having to create a correctly named tab.  The importer
    ignores those blank optional sheets, rather than treating them as data.
    """
    status_labels = {
        "completed": "Hoàn thành", "cancelled": "Đã hủy", "received": "Đã nhận",
        "confirmed": "Đã xác nhận", "under_review": "Đang xem xét",
    }
    output = BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        export_names = (
            REQUIRED_UPLOAD_COLUMNS
            if include_empty_sheets
            else {name: None for name in rows_by_name}
        )
        for name in export_names:
            rows = rows_by_name.get(name, [])
            aliases = VIETNAMESE_COLUMN_ALIASES.get(name, {})
            rename_map = {
                field: choices[0] if choices else field
                for field, choices in aliases.items()
            }
            exported_rows = [
                {
                    field: status_labels.get(str(value), value) if field == "status" else value
                    for field, value in row.items()
                }
                for row in rows
            ]
            frame = pd.DataFrame(exported_rows).rename(columns=rename_map)
            preferred_columns = [rename_map.get(field, field) for field in aliases]
            other_columns = [column for column in frame.columns if column not in preferred_columns]
            frame = frame.reindex(columns=[*preferred_columns, *other_columns])
            frame.to_excel(writer, sheet_name=EXCEL_SHEET_NAMES.get(name, name[:31]), index=False)
    return output.getvalue()


@st.cache_data(show_spinner=False)
def vietnamese_sample_workbook(version: str) -> bytes:
    """Provide a complete, populated, Vietnamese practice workbook.

    ``version`` deliberately participates in the cache key so an older demo
    file cannot survive a schema expansion.
    """
    del version
    return vietnamese_excel_export(
        build_demo_rows(["phone-accessories", "appliance"], seed=20260930),
        include_empty_sheets=True,
    )


def library_repository() -> ShopDataLibrary:
    return ShopDataLibrary()


def demo_primary_category_id(
    rows: dict[str, list[dict[str, str]]],
    selected_ids: list[str],
) -> str | None:
    """Choose a stable market category from the demo stored for this chat."""
    compatible_ids = {str(item["id"]) for item in market_categories()}
    selected = next((item for item in selected_ids if item in compatible_ids), None)
    if selected is not None:
        return selected
    stored_categories = {
        str(row.get("category", "")).strip()
        for row in rows.get("products.csv", [])
    }
    return next(
        (
            str(item["id"])
            for item in demo_catalog()
            if str(item["id"]) in compatible_ids
            and str(item["category"]) in stored_categories
        ),
        None,
    )


def activate_library_data(scope: str) -> None:
    """Attach one saved data shelf to the active chat, rather than only opening it."""
    rows = library_repository().load(scope)
    if rows is None:
        st.session_state.seller_upload_error = "Hãy lưu đủ bảng dữ liệu trước khi dùng trong chat."
        return
    # Older demo shelves predate the four operational tables added later.  A
    # saved chat must not silently fall back to RAG just because its local demo
    # payload was created before those tables existed.
    if scope == "demo":
        new_tables = {
            "search_performance.csv", "shipping_performance.csv",
            "settlements.csv", "competitor_catalog.csv",
        }
        missing_tables = new_tables - set(rows)
        if missing_tables:
            selected_ids = list(st.session_state.get("seller_demo_selected_ids", []))
            current_demo = build_demo_rows(selected_ids or None, seed=20260930)
            rows.update({name: current_demo[name] for name in missing_tables})
            rows = library_repository().save("demo", rows)
    expected_mode = "learner" if scope == "demo" else "owner"
    selected_demo_ids = list(st.session_state.get("seller_demo_selected_ids", []))
    active_mode = st.session_state.get("seller_chat_mode")
    if active_mode is None or active_conversation() is None:
        start_conversation(expected_mode)
    elif active_mode != expected_mode:
        st.session_state.seller_upload_error = (
            "Bộ demo chỉ gắn với chat Người mới; dữ liệu cửa hàng chỉ gắn với chat Chủ shop. "
            "Hãy mở đúng loại chat trước."
        )
        return
    st.session_state.seller_uploaded_rows = rows
    st.session_state.seller_uploaded_names = tuple(rows)
    st.session_state.seller_data_origin = f"{scope}_library"
    if scope == "demo":
        primary_category = demo_primary_category_id(rows, selected_demo_ids)
        if primary_category is not None:
            st.session_state.seller_market_category_id = primary_category
            st.session_state.strategy_category_id = primary_category
            st.session_state.strategy_inventory_category = primary_category
    st.session_state.seller_upload_message = (
        "Đã dùng bộ dữ liệu demo cho cuộc trò chuyện này."
        if scope == "demo"
        else "Đã dùng dữ liệu cửa hàng đã lưu cho cuộc trò chuyện này."
    )
    st.session_state.seller_view = "chat"
    save_active_conversation()


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
            f"{float(strongest_product['product_score']):.1f}%, lượng bán mô phỏng "
            f"{int(strongest_product['units_sold_12m']):,} trong 12 tháng.\n\n"
            "**Hướng thử trước:** giữ sẵn tồn kho cho sản phẩm này, kiểm tra ảnh/mô tả và thử ghép nó với một sản phẩm bổ trợ. "
            "Đây là gợi ý từ dữ liệu demo, không phải dự báo doanh số thật."
        )
    if any(token in text for token in ("doanh thu", "gmv", "yếu", "mạnh", "cạnh tranh", "shop")):
        gmv_gap = float(leader["gmv_12m_vnd"]) - float(own_shop["gmv_12m_vnd"])
        return (
            f"Mốc để học hỏi là **{leader['shop_name']}**: GMV cao hơn shop bạn {currency(gmv_gap)}, "
            f"điểm shop {float(leader['shop_score']):.1f}% và {int(leader['review_count']):,} lượt đánh giá.\n\n"
            "**Hướng đi:** ưu tiên tăng chất lượng trang sản phẩm và trải nghiệm sau mua để có đánh giá tốt, rồi mới mở rộng quảng cáo. "
            "So sánh từng sản phẩm ở tab “Sản phẩm cùng thị trường” để chọn nơi cần cải thiện."
        )
    if any(token in text for token in ("tóm tắt", "tổng quan", "toàn bộ")):
        return (
            f"**Bản đồ hành động cho ngành {category}:** shop bạn có {int(own_shop['listing_count'])} sản phẩm, "
            f"giá trung bình {currency(float(own_shop['average_price_vnd']))}, "
            f"GMV 12 tháng {currency(float(own_shop['gmv_12m_vnd']))} và điểm shop {float(own_shop['shop_score']):.1f}%.\n\n"
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


def advisor_marketplace(surface: str) -> tuple[str, dict[str, Any]]:
    """Use the selected conversation's reproducible market scene for advice."""
    catalog = cached_market_categories()
    known_ids = {str(item["id"]) for item in catalog}
    category_id: str | None = None
    simulation = st.session_state.get("seller_strategy_last_simulation")
    if surface == "strategy" and isinstance(simulation, dict):
        category_id = str(simulation.get("category_id") or "")
    if category_id not in known_ids:
        category_id = str(st.session_state.get("seller_market_category_id") or "")
    if category_id not in known_ids:
        category_id = str(catalog[0]["id"])
    category = next(item for item in catalog if str(item["id"]) == category_id)
    return str(category["category"]), cached_marketplace(
        category_id, int(st.session_state.seller_market_scenario_seed)
    )


def render_advisor_entry(surface: str, key: str) -> None:
    """Put the adviser at the workspace header, where its chat binding is visible."""
    st.button(
        ui_text("Chiến lược gia AI", "AI strategist"),
        key=key,
        icon=":material/smart_toy:",
        width="stretch",
        on_click=open_market_advisor,
        args=(surface,),
    )


def render_advisor_launcher(surface: str) -> None:
    """Render the adviser only after the user intentionally opens it from a header."""
    if st.session_state.seller_market_advisor_open:
        category, marketplace = advisor_marketplace(surface)
        render_market_advisor_dialog(category, marketplace)


@st.dialog("Chiến lược gia AI", width="large")
def render_market_advisor_dialog(category: str, marketplace: dict[str, Any]) -> None:
    active = active_conversation()
    surface = str(st.session_state.get("seller_advisor_surface", "market"))
    surface_label = {
        "chat": "Trung chuyển từ chat chính",
        "market": "Đang xem Phân tích thị trường",
        "strategy": "Đang xem Chiến lược kinh doanh",
    }.get(surface, "Đang tư vấn")
    if active is not None:
        st.caption(
            f"**{surface_label}** · Đang liên kết với **{CHAT_TYPES[active['mode']]['name']} · {active['title']}**. "
            f"Dữ liệu của chat này: **{conversation_data_label(active)}**. Lịch sử trong cửa sổ này chỉ thuộc chat đang chọn."
        )
    st.caption("Hỏi về giá, sản phẩm hoặc hướng phát triển. Chiến lược gia AI dùng kịch bản thị trường đang xem để gợi ý bước tiếp theo; không tự thay đổi dữ liệu hay hoạt động của shop.")
    with st.container(horizontal=True):
        if surface != "chat":
            if st.button("Mở chat chính", key="advisor_to_chat", icon=":material/chat:"):
                route_from_advisor("chat")
                st.rerun()
        if surface != "market":
            if st.button("Mở thị trường", key="advisor_to_market", icon=":material/insights:"):
                route_from_advisor("market")
                st.rerun()
        if surface != "strategy":
            if st.button("Mở chiến lược", key="advisor_to_strategy", icon=":material/rocket_launch:"):
                route_from_advisor("strategy")
                st.rerun()
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
                    save_active_conversation()
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
        save_active_conversation()
        st.rerun()
    if messages and active is not None:
        st.caption("Muốn dùng kết quả này ở AI chính? Gửi ghi chú sẽ giữ cửa sổ này là một lịch sử riêng, đồng thời lưu bản tóm tắt vào đúng chat đang mở.")
        if st.button("Gửi ghi chú sang chat chính", key="advisor_handoff_to_chat", icon=":material/send:", type="primary"):
            if handoff_advisor_to_main_chat():
                st.rerun()
            st.warning("Hãy gửi ít nhất một câu hỏi để có nội dung cần bàn giao.", icon=":material/info:")
    elif messages:
        st.caption("Tạo hoặc mở một cuộc trò chuyện trước khi gửi ghi chú sang AI chính để hệ thống biết phải lưu vào lịch sử nào.")
    if st.button("Đóng trợ lý", key="close_market_advisor", icon=":material/close:"):
        close_market_advisor()
        st.rerun()


def render_strategy_workspace() -> None:
    """Help a seller turn market signals into a small, measurable experiment."""
    st.markdown('<div class="seller-eyebrow">CHIẾN LƯỢC KINH DOANH · DEMO</div>', unsafe_allow_html=True)
    header, adviser, back = st.columns([6, 2, 2], vertical_alignment="center")
    with header:
        st.title(ui_text("Chiến lược kinh doanh", "Business strategy"))
        st.caption(ui_text("Tìm cơ hội, mô phỏng phương án và tạo kế hoạch hành động. Kết quả là ước tính để chọn thử nghiệm nhỏ, không phải cam kết doanh thu.", "Find opportunities, simulate options, and create an action plan. Results are estimates for small tests, not revenue promises."))
    with adviser:
        render_advisor_entry("strategy", "strategy_open_advisor")
    with back:
        st.button(ui_text("Quay lại chat", "Back to chat"), key="strategy_back_to_chat", icon=":material/chat:", width="stretch", on_click=open_chat_view)

    render_workspace_context("strategy")
    render_quick_guide(
        ui_text("bạn muốn thử một cách bán hàng mới nhưng chưa muốn quyết định nhập nhiều hàng hoặc tăng chi phí ngay.", "you want to test a new selling approach before committing substantial inventory or spend."),
        ui_text(
            ["Mở tab Mô phỏng chiến lược", "Chọn ngành hàng và thay đổi nhỏ muốn thử", "Bấm Phân tích phương án, rồi xem Vốn & tồn kho và Kế hoạch 30 ngày"],
            ["Open Strategy simulation", "Select a category and a small change to test", "Select Analyze plan, then review Capital & inventory and the 30-day plan"],
        ),
    )
    st.info("Không gian này dùng dữ liệu mô phỏng minh bạch. Khi có dữ liệu shop thật, cùng khung quyết định này có thể dùng để phân tích kết quả thực tế.", icon=":material/lightbulb:")
    with st.expander("Nguồn phương pháp và nguyên tắc an toàn", icon=":material/menu_book:"):
        st.markdown("**AI không cam kết doanh thu hoặc tự thay đổi hoạt động của shop.** Mọi đề xuất dưới 90% mức bằng chứng chỉ được trình bày là giả thuyết thử nghiệm nhỏ.")
        for source in STRATEGY_EVIDENCE:
            st.markdown(f"- [{source['title']}]({source['url']}) — {source['author']}, {source['year']}. {source['use']}\n  *Ví dụ áp dụng:* {source['adoption']}")
    strategy_sections = ["Radar cơ hội", "Mô phỏng chiến lược", "Vốn & tồn kho", "Kế hoạch 30 ngày"]
    strategy_section = st.segmented_control(
        "Nội dung chiến lược",
        options=strategy_sections,
        default="Radar cơ hội",
        key="strategy_section",
        label_visibility="collapsed",
        width="stretch",
    )

    if strategy_section == "Radar cơ hội":
        st.subheader("Radar cơ hội mặt hàng")
        st.caption("Điểm cơ hội cân bằng lượng bán, doanh thu, mức giá, review tích cực và độ bền xu hướng trong bộ dữ liệu demo.")
        radar = cached_opportunity_radar()
        radar_frame = pd.DataFrame(radar).rename(columns={
            "rank": "Xếp hạng", "category": "Ngành hàng", "lead_product": "Sản phẩm gợi ý",
            "units_sold_estimate": "Lượng bán ước tính", "estimated_revenue_vnd": "Doanh thu ước tính",
            "positive_review_score": "Đánh giá tích cực", "longevity_score": "Độ bền xu hướng",
            "opportunity_score": "Điểm cơ hội", "recommendation": "Khuyến nghị",
        })
        themed_dataframe(
            radar_frame[["Xếp hạng", "Ngành hàng", "Sản phẩm gợi ý", "Lượng bán ước tính", "Doanh thu ước tính", "Đánh giá tích cực", "Độ bền xu hướng", "Điểm cơ hội", "Khuyến nghị"]].head(12),
            hide_index=True,
            width="stretch",
            column_config={
                "Doanh thu ước tính": st.column_config.NumberColumn(format="%,d đ"),
                "Điểm cơ hội": st.column_config.ProgressColumn(min_value=0, max_value=100, format="%.1f"),
                "Đánh giá tích cực": st.column_config.ProgressColumn(min_value=0, max_value=100, format="%.1f"),
                "Độ bền xu hướng": st.column_config.ProgressColumn(min_value=0, max_value=100, format="%.1f"),
            },
        )
        st.caption("Dùng radar để chọn ngành cần thử trước; không dùng một mình để quyết định nhập hàng lớn.")
        radar_options = {str(item["category_id"]): f"#{int(item['rank'])} · {item['category']} · {item['recommendation']}" for item in radar[:12]}
        chosen_radar_category = st.selectbox("Chọn một cơ hội để mô phỏng", options=list(radar_options), format_func=lambda item: radar_options[str(item)], key="strategy_radar_category")
        if st.button("Dùng ngành này để tạo phương án", key="strategy_use_radar_category", icon=":material/rocket_launch:"):
            st.session_state.strategy_category_id = chosen_radar_category
            save_active_conversation()
            st.toast("Đã chọn ngành hàng trong tab Mô phỏng chiến lược.", icon=":material/check_circle:")

    if strategy_section == "Mô phỏng chiến lược":
        st.subheader("Mô phỏng một phương án kinh doanh")
        st.caption("Chọn một thay đổi nhỏ. AI ước tính tương quan với kịch bản hiện tại để giúp bạn so sánh phương án, không thay thế số liệu thực tế.")
        catalog = cached_market_categories()
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
                save_active_conversation()
        simulation = st.session_state.seller_strategy_last_simulation
        if simulation:
            with st.container(border=True):
                st.markdown(f"**Giả thuyết cần kiểm chứng: {simulation['lead_product']}**")
                with st.container(horizontal=True):
                    st.metric("GMV hiện tại trong demo", currency(float(simulation["baseline_gmv_vnd"])), border=True)
                    st.metric("GMV minh họa theo phương án", currency(float(simulation["estimated_gmv_vnd"])), f"{float(simulation['gmv_change_percent']):+.1f}%", border=True)
                    st.metric("Lượng bán minh họa", f"{int(simulation['estimated_units']):,}", border=True)
                    st.metric("Mức bằng chứng", f"{int(simulation['evidence_score'])}%", border=True)
                st.warning(f"**{simulation['evidence_label']}** — {simulation['language_policy']}", icon=":material/gpp_maybe:")
                st.markdown(f"**Mức rủi ro:** {simulation['risk']}")
                st.markdown(f"**Cách thử an toàn:** {simulation['action']}")
                st.markdown("**Điều kiện dừng:**")
                for condition in simulation["stop_conditions"]:
                    st.markdown(f"- {condition}")
        else:
            st.caption("Chưa có phương án được mô phỏng. Hãy chọn thay đổi và bấm “Phân tích phương án”.")

    if strategy_section == "Vốn & tồn kho":
        st.subheader("Vốn & tồn kho: nên nhập gì, dừng gì?")
        st.caption("Xem từng sản phẩm để tránh giữ vốn ở hàng bán chậm và chỉ nhập nhỏ khi có dấu hiệu sắp hết hàng.")
        catalog = cached_market_categories()
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
        inventory_result = cached_inventory_risk_analysis(
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
        themed_dataframe(
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

    if strategy_section == "Kế hoạch 30 ngày":
        st.subheader("Kế hoạch hành động 30 ngày")
        simulation = st.session_state.seller_strategy_last_simulation
        if not simulation:
            st.info("Hãy tạo một phương án trong tab “Mô phỏng chiến lược” trước; kế hoạch sẽ tự dùng phương án đó.", icon=":material/arrow_back:")
        else:
            plan = pd.DataFrame(action_plan(simulation))
            themed_dataframe(plan, hide_index=True, width="stretch")
            st.caption("Nguyên tắc: chỉ thay đổi một vài yếu tố trong một kỳ để biết kết quả đến từ đâu.")

    render_advisor_launcher("strategy")


def render_market_intelligence() -> None:
    """Show a useful but explicitly simulated market-analysis workspace."""
    st.markdown(f'<div class="seller-eyebrow">{ui_text("PHÂN TÍCH THỊ TRƯỜNG · BẢN MÔ PHỎNG", "MARKET ANALYSIS · DEMO")}</div>', unsafe_allow_html=True)
    header, adviser, back = st.columns([6, 2, 2], vertical_alignment="center")
    with header:
        st.title(ui_text("Phân tích thị trường", "Market analysis"))
        st.caption(ui_text("So sánh giá, shop tham chiếu và hướng thử nghiệm cho một ngành hàng.", "Compare prices, reference shops, and test directions for a product category."))
    with adviser:
        render_advisor_entry("market", "market_open_advisor")
    with back:
        st.button(ui_text("Quay lại chat", "Back to chat"), key="market_back_to_chat", icon=":material/chat:", width="stretch", on_click=open_chat_view)

    render_workspace_context("market")
    render_quick_guide(
        ui_text("bạn muốn xem giá, doanh thu và sản phẩm của shop mình so với các shop cùng ngành hàng.", "you want to compare your shop's prices, revenue, and products with similar shops."),
        ui_text(
            ["Chọn ngành hàng", "Chọn đúng sản phẩm cần kiểm tra giá", "Xem bảng/biểu đồ hoặc bấm AI để hỏi hướng cải thiện"],
            ["Choose a category", "Choose the exact product to check", "Review the table/chart or ask AI for an improvement direction"],
        ),
    )
    st.warning(
        ui_text(
            "Đây là dữ liệu thị trường mô phỏng: giá, cửa hàng tham chiếu và tín hiệu xu hướng đều có thể lặp lại khi trình bày. Hệ thống chưa kết nối Shopee, YouTube, Facebook/Instagram hoặc TikTok để lấy dữ liệu trực tiếp.",
            "This is simulated market data: prices, reference shops, and trend signals are repeatable for demonstrations. The system is not connected to Shopee, YouTube, Facebook/Instagram, or TikTok for live data.",
        ),
        icon=":material/info:",
    )
    catalog = cached_market_categories()
    labels = {
        str(item["id"]): f"{item['category']} · {item['product_count']} {ui_text('sản phẩm demo', 'demo products')}"
        for item in catalog
    }
    category_id = st.selectbox(
        ui_text("Chọn ngành hàng để phân tích", "Choose a category to analyze"),
        options=list(labels),
        format_func=lambda item: labels[str(item)],
        key="seller_market_category_id",
    )
    selected = next(item for item in catalog if item["id"] == category_id)
    st.button(
        ui_text("Tạo lại shop và thị trường demo", "Regenerate demo shop and market"),
        key="refresh_market_scenario",
        icon=":material/autorenew:",
        on_click=refresh_market_scenario,
    )
    marketplace = cached_marketplace(
        str(category_id), int(st.session_state.seller_market_scenario_seed)
    )
    listings = pd.DataFrame(marketplace["listings"])
    product_names = sorted(listings["product_name"].unique().tolist())
    selected_product = st.selectbox(
        ui_text("Chọn sản phẩm để so sánh giá", "Choose a product to compare prices"),
        options=product_names,
        key="market_price_product",
        help=ui_text("Giá và bảng bên dưới chỉ so sánh đúng sản phẩm này giữa các shop.", "The prices and table below compare this exact product across shops."),
    )
    product_rows = listings[listings["product_name"] == selected_product].copy()
    own_product = product_rows[product_rows["shop_type"] == "Shop của bạn"].iloc[0]
    comparable_prices = product_rows[product_rows["shop_type"] != "Shop của bạn"]["listed_price_vnd"]
    product_lower_price = float(comparable_prices.min())
    product_typical_price = float(comparable_prices.median())
    product_upper_price = float(comparable_prices.max())
    product_own_price = float(own_product["listed_price_vnd"])
    if product_own_price < product_lower_price:
        product_position = ui_text("Thấp hơn giá các shop cùng sản phẩm", "Below comparable-shop prices")
    elif product_own_price > product_upper_price:
        product_position = ui_text("Cao hơn giá các shop cùng sản phẩm", "Above comparable-shop prices")
    else:
        product_position = ui_text("Nằm trong vùng giá cạnh tranh", "Within the competitive price range")

    with st.container(horizontal=True):
        st.metric(ui_text("Giá thấp cùng sản phẩm", "Lowest comparable price"), currency(product_lower_price), help=ui_text("Mức giá thấp nhất của đúng sản phẩm đang chọn tại 7 shop tham chiếu.", "The lowest price for this exact product across seven reference shops."), border=True)
        st.metric(ui_text("Mặt bằng giá", "Typical price"), currency(product_typical_price), help=ui_text("Giá ở giữa của 7 shop cùng bán sản phẩm đang chọn.", "The median price for this exact product across comparable shops."), border=True)
        st.metric(ui_text("Giá cao cùng sản phẩm", "Highest comparable price"), currency(product_upper_price), help=ui_text("Mức giá cao nhất của đúng sản phẩm đang chọn tại 7 shop tham chiếu.", "The highest price for this exact product across seven reference shops."), border=True)
    with st.container(horizontal=True):
        st.metric(ui_text("Giá shop của bạn", "Your shop price"), currency(product_own_price), help=ui_text("Giá của đúng sản phẩm đang chọn tại Shop của bạn · Demo.", "The price of this exact product in Your shop · Demo."), border=True)
        st.metric(ui_text("Vị trí giá", "Price position"), product_position, help=ui_text("So sánh trực tiếp cùng một sản phẩm, không phải giá trung bình của cả shop.", "A direct comparison of the same product, not an average across the full shop."), border=True)
    st.caption(ui_text("Đang so sánh từng sản phẩm. Chọn sản phẩm khác để kiểm tra giá khác; bấm “Tạo lại shop và thị trường demo” để tạo bộ shop mới.", "This is a product-by-product comparison. Choose another product to check its price, or regenerate the demo market for a new scenario."))
    with st.container(border=True):
        st.markdown("**" + ui_text("Cách đọc nhanh", "How to read this") + "**")
        st.write(ui_text("1. Chọn đúng sản phẩm muốn kiểm tra.  2. So giá shop của bạn với 7 shop cùng bán sản phẩm đó.  3. Xem bảng chi tiết trước khi quyết định đổi giá.", "1. Choose the exact product.  2. Compare your price with seven shops selling that product.  3. Review the detail table before changing a price."))

    market_sections = ["So sánh giá", "So sánh shop", "Sản phẩm cùng thị trường"]
    market_section = st.segmented_control(
        "Nội dung phân tích thị trường",
        options=market_sections,
        default="So sánh giá",
        key="market_section",
        format_func=lambda item: {
            "So sánh giá": ui_text("So sánh giá", "Price comparison"),
            "So sánh shop": ui_text("So sánh shop", "Shop comparison"),
            "Sản phẩm cùng thị trường": ui_text("Sản phẩm cùng thị trường", "Products in this market"),
        }[str(item)],
        label_visibility="collapsed",
        width="stretch",
    )
    if market_section == "So sánh giá":
        st.subheader(selected_product)
        st.write(ui_text("Mỗi cột là giá của đúng sản phẩm này tại một shop. Cột đỏ là Shop của bạn.", "Each bar is the price of this exact product at one shop. The red bar is Your shop."))
        chart_data = product_rows.copy()
        chart_data["display_shop_name"] = chart_data["shop_name"].map(market_shop_name_label)
        price_chart = (
            alt.Chart(chart_data)
            .mark_bar(cornerRadiusEnd=4)
            .encode(
                x=alt.X("listed_price_vnd:Q", title=ui_text("Giá niêm yết (VND)", "Listed price (VND)"), axis=alt.Axis(format=",d")),
                y=alt.Y("display_shop_name:N", sort="-x", title=None),
                color=alt.condition(alt.datum.shop_type == "Shop của bạn", alt.value("#ee4d2d"), alt.value("#f7a28f")),
                tooltip=[alt.Tooltip("display_shop_name:N", title=ui_text("Cửa hàng", "Shop")), alt.Tooltip("listed_price_vnd:Q", title=ui_text("Giá", "Price"), format=",d"), alt.Tooltip("rating:Q", title=ui_text("Đánh giá", "Rating"), format=".2f")],
            )
            .properties(height=300)
        )
        st.altair_chart(dark_mode_chart(price_chart), width="stretch")
        column_labels = {
            "shop_name": ui_text("Cửa hàng", "Shop"), "shop_type": ui_text("Loại cửa hàng", "Shop type"),
            "listed_price_vnd": ui_text("Giá", "Price"), "rating": ui_text("Đánh giá", "Rating"),
            "review_count": ui_text("Số đánh giá", "Reviews"), "units_sold_12m": ui_text("Lượng bán 12T", "Units sold (12 mo.)"),
            "gmv_12m_vnd": ui_text("GMV 12T", "GMV (12 mo.)"),
        }
        product_table = product_rows.rename(columns=column_labels)
        product_table[column_labels["shop_name"]] = product_table[column_labels["shop_name"]].map(market_shop_name_label)
        product_table[column_labels["shop_type"]] = product_table[column_labels["shop_type"]].map(market_shop_type_label)
        product_columns = list(column_labels.values())
        themed_dataframe(product_table[product_columns], hide_index=True, width="stretch", column_config={column_labels["listed_price_vnd"]: st.column_config.NumberColumn(format="%,d đ"), column_labels["gmv_12m_vnd"]: st.column_config.NumberColumn(format="%,d đ")})
        st.caption(
            ui_text(f"So sánh đúng một sản phẩm ở Shop của bạn và 7 shop tham chiếu mô phỏng; snapshot demo {MARKET_SNAPSHOT_DATE}.", f"This compares the same product in Your shop and seven simulated reference shops; demo snapshot {MARKET_SNAPSHOT_DATE}.")
        )

    if market_section == "So sánh shop":
        shops = pd.DataFrame(marketplace["shops"])
        st.caption(ui_text(f"So sánh shop của bạn với {marketplace['reference_count']} shop tương tự trong cùng ngành hàng. Mỗi lần tạo lại sẽ có một kịch bản demo mới.", f"Compare Your shop with {marketplace['reference_count']} similar shops in the same category. Regenerating creates a new demo scenario."))
        shops["display_shop_name"] = shops["shop_name"].map(market_shop_name_label)
        shops["display_shop_type"] = shops["shop_type"].map(market_shop_type_label)
        shop_chart = alt.Chart(shops).mark_arc(innerRadius=58, padAngle=0.02).encode(
            theta=alt.Theta("gmv_12m_vnd:Q", title=ui_text("GMV 12 tháng", "GMV (12 mo.)")),
            color=alt.Color("display_shop_name:N", title=ui_text("Cửa hàng", "Shop"), scale=alt.Scale(scheme="set2")),
            tooltip=[
                alt.Tooltip("display_shop_name:N", title=ui_text("Tên shop", "Shop name")),
                alt.Tooltip("display_shop_type:N", title=ui_text("Quy mô shop", "Shop size")),
                alt.Tooltip("average_price_vnd:Q", title=ui_text("Giá bán trung bình", "Average selling price"), format=",d"),
                alt.Tooltip("gmv_12m_vnd:Q", title=ui_text("Tổng doanh thu 12 tháng", "Total revenue (12 mo.)"), format=",d"),
                alt.Tooltip("shop_score:Q", title=ui_text("Điểm đánh giá shop", "Shop score"), format=".1f"),
            ],
        ).properties(height=340)
        st.markdown("**" + ui_text("Tỷ trọng doanh thu 12 tháng của các shop", "12-month revenue share by shop") + "**")
        st.caption(ui_text("Miếng lớn hơn nghĩa là shop đó có GMV cao hơn trong bộ dữ liệu đang xem.", "A larger slice means that shop has higher GMV in the data currently shown."))
        st.altair_chart(dark_mode_chart(shop_chart), width="stretch")
        table = shops.rename(columns={"shop_name": "Cửa hàng", "shop_type": "Quy mô", "listing_count": "Số sản phẩm", "units_sold_12m": "Lượng bán 12T", "gmv_12m_vnd": "GMV 12T", "average_price_vnd": "Giá TB", "rating": "Đánh giá", "review_count": "Số đánh giá", "shop_score": "Điểm cửa hàng"})
        table["Cửa hàng"] = table["Cửa hàng"].map(market_shop_name_label)
        table["Quy mô"] = table["Quy mô"].map(market_shop_type_label)
        themed_dataframe(table[["Cửa hàng", "Quy mô", "Số sản phẩm", "Lượng bán 12T", "GMV 12T", "Giá TB", "Đánh giá", "Số đánh giá", "Điểm cửa hàng"]], hide_index=True, width="stretch", column_config={"GMV 12T": st.column_config.NumberColumn(format="%,d đ"), "Giá TB": st.column_config.NumberColumn(format="%,d đ"), "Điểm cửa hàng": st.column_config.ProgressColumn(min_value=0, max_value=100, format="%.1f")})
        with st.expander(ui_text("“Shop dẫn đầu” nghĩa là gì?", "What does “Leading shop” mean?"), icon=":material/info:"):
            st.write(ui_text("Đây là một shop tham chiếu mô phỏng có tín hiệu mạnh hơn trong kịch bản đang xem, thường có lượng bán, đánh giá hoặc GMV tương đối cao. Đây không phải shop thật, không phải xếp hạng Shopee và không khẳng định kết quả kinh doanh thực tế.", "This is a simulated reference shop with stronger signals in the current scenario, often relatively higher units sold, ratings, or GMV. It is not a real shop, a Shopee ranking, or a guarantee of business results."))

    if market_section == "Sản phẩm cùng thị trường":
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
        st.altair_chart(dark_mode_chart(product_chart), width="stretch")
        display = shown.rename(columns={"shop_name": "Cửa hàng", "shop_type": "Quy mô", "product_name": "Sản phẩm", "listed_price_vnd": "Giá", "units_sold_12m": "Lượng bán 12T", "gmv_12m_vnd": "GMV 12T", "rating": "Đánh giá", "review_count": "Số đánh giá", "product_score": "Điểm sản phẩm", "data_scope": "Nguồn dữ liệu"})
        display["Cửa hàng"] = display["Cửa hàng"].map(market_shop_name_label)
        display["Quy mô"] = display["Quy mô"].map(market_shop_type_label)
        themed_dataframe(display[["Cửa hàng", "Quy mô", "Sản phẩm", "Giá", "Lượng bán 12T", "GMV 12T", "Đánh giá", "Số đánh giá", "Điểm sản phẩm", "Nguồn dữ liệu"]], hide_index=True, width="stretch", column_config={"Giá": st.column_config.NumberColumn(format="%,d đ"), "GMV 12T": st.column_config.NumberColumn(format="%,d đ"), "Điểm sản phẩm": st.column_config.ProgressColumn(min_value=0, max_value=100, format="%.1f")})
        st.info("Điểm sản phẩm cân bằng lượng bán, GMV và review. Nó không phải dự báo chắc chắn; dùng để chọn mặt hàng cần thử trước.", icon=":material/insights:")

    render_advisor_launcher("market")

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
        "purchase_orders.csv": [
            row for row in rows.get("purchase_orders.csv", [])
            if row["sku"] in selected_sku_values and row["order_date"][:7] in selected_month_values
        ],
        "returns.csv": [
            row for row in rows.get("returns.csv", [])
            if row["sku"] in selected_sku_values and row["request_date"][:7] in selected_month_values
        ],
        "reviews.csv": [
            row for row in rows.get("reviews.csv", [])
            if row["sku"] in selected_sku_values and row["review_date"][:7] in selected_month_values
        ],
        "operating_costs.csv": [
            row for row in rows.get("operating_costs.csv", [])
            if row["month"] in selected_month_values
        ],
        "inventory_movements.csv": [
            row for row in rows.get("inventory_movements.csv", [])
            if row["sku"] in selected_sku_values and row["movement_date"][:7] in selected_month_values
        ],
        "quality_checks.csv": [
            row for row in rows.get("quality_checks.csv", [])
            if row["sku"] in selected_sku_values and row["check_date"][:7] in selected_month_values
        ],
        "cash_flow.csv": [
            row for row in rows.get("cash_flow.csv", [])
            if row["date"][:7] in selected_month_values
        ],
        "supplier_performance.csv": [
            row for row in rows.get("supplier_performance.csv", [])
            if row["month"] in selected_month_values
        ],
        "customer_segments.csv": [
            row for row in rows.get("customer_segments.csv", [])
            if row["month"] in selected_month_values
        ],
        "product_funnel.csv": [
            row for row in rows.get("product_funnel.csv", [])
            if row["sku"] in selected_sku_values and row["month"] in selected_month_values
        ],
        "co_purchase.csv": [
            row for row in rows.get("co_purchase.csv", [])
            if row["sku"] in selected_sku_values
            and row["paired_sku"] in selected_sku_values
            and row["month"] in selected_month_values
        ],
    }


def optional_dashboard_summary(
    tool: ShopDataTool,
    method_name: str,
    empty_summary: dict[str, Any],
) -> tuple[dict[str, Any], bool]:
    """Return an optional dashboard summary without taking down the whole report.

    Some saved shops were created before the extended operating tables existed.
    During an incremental cloud deployment the UI can also arrive before the
    matching data-tool method.  In both cases the honest state is "not ready",
    never a fabricated zero and never a broken dashboard.
    """
    method = getattr(tool, method_name, None)
    if not callable(method):
        return dict(empty_summary), False
    try:
        return method(), True
    except (AttributeError, KeyError, ValueError):
        return dict(empty_summary), False


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
    profitability = tool.profitability_summary()
    returns = tool.returns_summary()
    reviews = tool.review_summary()
    procurement = tool.procurement_summary()
    operating_costs, has_operating_costs = optional_dashboard_summary(
        tool,
        "operating_cost_summary",
        {"total_operating_cost_vnd": 0},
    )
    movements, has_movements = optional_dashboard_summary(
        tool,
        "inventory_movement_summary",
        {"damaged_unit_count": 0, "inbound_unit_count": 0, "outbound_unit_count": 0},
    )
    quality, has_quality = optional_dashboard_summary(
        tool,
        "quality_summary",
        {"defect_rate_percent": None, "inspected_unit_count": 0, "check_count": 0},
    )
    cash_flow, has_cash_flow = optional_dashboard_summary(
        tool,
        "cash_flow_summary",
        {"net_cash_movement_vnd": 0},
    )
    suppliers, has_suppliers = optional_dashboard_summary(
        tool,
        "supplier_performance_summary",
        {"best_supplier": None},
    )
    customers, has_customers = optional_dashboard_summary(
        tool,
        "customer_retention_summary",
        {"repeat_order_rate_percent": None},
    )
    funnel, has_funnel = optional_dashboard_summary(
        tool,
        "product_funnel_summary",
        {"total_add_to_cart_count": 0},
    )

    with st.container(horizontal=True):
        st.metric("Doanh thu sau phí ước tính", currency(number(sales["net_revenue_after_estimated_fees_vnd"])), border=True)
        st.metric("Đơn hoàn tất", f"{sales['completed_order_count']}", border=True)
        st.metric("Sản phẩm cần nhập thêm", f"{inventory['alert_count']}", border=True)
        st.metric("ROAS quảng cáo", f"{number(ads['roas']):.2f}", border=True)
        st.metric("Lãi góp ước tính", currency(number(profitability["estimated_contribution_vnd"])), border=True)
        st.metric(
            "Chi phí vận hành đã nhập",
            currency(number(operating_costs["total_operating_cost_vnd"])) if has_operating_costs else "Chưa có dữ liệu",
            border=True,
        )

    unavailable_summaries = [
        label for label, available in [
            ("chi phí vận hành", has_operating_costs),
            ("biến động kho", has_movements),
            ("kiểm tra chất lượng", has_quality),
            ("dòng tiền", has_cash_flow),
            ("nhà cung cấp", has_suppliers),
            ("khách quay lại", has_customers),
            ("hành trình mua hàng", has_funnel),
        ] if not available
    ]
    if unavailable_summaries:
        st.info(
            "Một số chỉ số mở rộng chưa sẵn sàng để hiển thị: "
            + ", ".join(unavailable_summaries)
            + ". Chúng không được tính là 0.",
            icon=":material/info:",
        )

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
            st.altair_chart(dark_mode_chart(bar), width="stretch")
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
                st.altair_chart(dark_mode_chart(pie), width="stretch")

    completed["Tháng"] = completed["order_date"].str.slice(0, 7)
    monthly = completed.groupby("Tháng", as_index=False)["gross_merchandise_value_vnd"].sum().rename(columns={"gross_merchandise_value_vnd": "GMV"})
    with st.container(border=True):
        st.markdown("**So sánh doanh thu theo kỳ**")
        if len(monthly) > 1:
            monthly_chart = alt.Chart(monthly).mark_bar(color="#EE4D2D", cornerRadiusTopLeft=5, cornerRadiusTopRight=5).encode(
                x=alt.X("Tháng:N", title=None),
                y=alt.Y("GMV:Q", title="GMV (VND)"),
                tooltip=[alt.Tooltip("Tháng:N"), alt.Tooltip("GMV:Q", format=",.0f")],
            )
            st.altair_chart(dark_mode_chart(monthly_chart), width="stretch")
        else:
            st.caption("Thêm đơn hàng của ít nhất hai tháng để so sánh biến động doanh thu.")

    details_col, alerts_col = st.columns(2)
    with details_col:
        with st.container(border=True):
            st.markdown("**Hiệu quả ước tính theo sản phẩm**")
            themed_dataframe(
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
                themed_dataframe(
                    alerts[["product_name", "available_units", "reorder_point", "shortfall_units"]],
                    hide_index=True,
                    column_config={
                        "product_name": "Sản phẩm",
                        "available_units": "Có thể bán",
                        "reorder_point": "Ngưỡng nhập",
                        "shortfall_units": "Thiếu so với ngưỡng",
                    },
                )

    returns_col, reviews_col, purchase_col = st.columns(3)
    with returns_col:
        with st.container(border=True):
            st.markdown("**Hoàn hàng**")
            st.metric("Yêu cầu hoàn", returns["return_request_count"])
            if returns["reasons"]:
                st.caption("Lý do nhiều nhất: " + next(iter(returns["reasons"])))
            else:
                st.caption("Chưa có dữ liệu hoàn hàng.")
    with reviews_col:
        with st.container(border=True):
            st.markdown("**Đánh giá khách hàng**")
            score = "—" if reviews["average_rating"] is None else f"{reviews['average_rating']:.2f}/5"
            st.metric("Điểm trung bình", score)
            st.caption(f"Đánh giá từ 3 sao trở xuống: {reviews['low_rating_count']}")
    with purchase_col:
        with st.container(border=True):
            st.markdown("**Hàng đang về**")
            st.metric("Đơn nhập còn mở", procurement["open_purchase_order_count"])
            st.caption(f"Số lượng dự kiến về: {procurement['open_unit_count']}")

    movement_col, quality_col = st.columns(2)
    with movement_col:
        with st.container(border=True):
            st.markdown("**Biến động kho đã ghi nhận**")
            st.metric("Hàng lỗi / hủy", movements["damaged_unit_count"] if has_movements else "Chưa có dữ liệu")
            if has_movements:
                st.caption(f"Nhập kho: {movements['inbound_unit_count']} · Bán ra: {movements['outbound_unit_count']}")
            else:
                st.caption("Chưa có bảng biến động kho để đối chiếu.")
    with quality_col:
        with st.container(border=True):
            st.markdown("**Chất lượng lô hàng**")
            rate = "Chưa có dữ liệu" if not has_quality else ("—" if quality["defect_rate_percent"] is None else f"{quality['defect_rate_percent']:.2f}%")
            st.metric("Tỷ lệ lỗi đã kiểm", rate)
            if has_quality:
                st.caption(f"Đã kiểm {quality['inspected_unit_count']} sản phẩm ở {quality['check_count']} lô.")
            else:
                st.caption("Chưa có bảng kiểm tra chất lượng để đối chiếu.")

    with st.container(border=True):
        st.markdown("**Dòng tiền và sức khỏe bán hàng**")
        with st.container(horizontal=True):
            cash_net = number(cash_flow["net_cash_movement_vnd"])
            st.metric("Dòng tiền ròng đã ghi", currency(cash_net) if has_cash_flow else "Chưa có dữ liệu", border=True)
            repeat_rate = "Chưa có dữ liệu" if not has_customers else ("—" if customers["repeat_order_rate_percent"] is None else f"{customers['repeat_order_rate_percent']:.2f}%")
            st.metric("Đơn mua lại", repeat_rate, border=True)
            best_supplier = suppliers["best_supplier"]
            supplier_score = "Chưa có dữ liệu" if not has_suppliers else ("—" if best_supplier is None else f"{best_supplier['on_time_delivery_rate_percent']:.1f}%")
            st.metric("Giao đúng hẹn tốt nhất", supplier_score, border=True)
            cart_count = f"{funnel['total_add_to_cart_count']:,}" if has_funnel else "Chưa có dữ liệu"
            st.metric("Lượt thêm giỏ", cart_count, border=True)
        st.caption("Các chỉ số chỉ tổng hợp dữ liệu đã nhập; hãy mở bảng tương ứng để kiểm tra từng giao dịch hoặc từng sản phẩm.")


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
                    themed_dataframe(
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
    with st.expander(ui_text("Giải thích nhanh: SKU, GMV và ROAS", "Quick definitions: SKU, GMV, and ROAS"), icon=":material/help:"):
        st.markdown(ui_text(
            """
**SKU — mã riêng của từng sản phẩm**

SKU giúp phân biệt và nối đúng *một sản phẩm* với đơn hàng và tồn kho của nó. Ví dụ, `FRUIT-TAO-001` có thể là mã của giỏ táo; nhờ mã này, AI biết được giỏ táo đã bán bao nhiêu và còn bao nhiêu trong kho.

**GMV — tổng tiền hàng đã bán**

GMV là tổng giá trị đơn hoàn tất trước khi trừ khuyến mãi của shop và các khoản phí ước tính. Ví dụ: khách mua 2 sản phẩm, mỗi sản phẩm 250.000 đ → **GMV = 500.000 đ**. GMV chưa phải lợi nhuận, vì còn giá vốn, khuyến mãi và phí.

**ROAS — hiệu quả của tiền quảng cáo**

ROAS = doanh thu quy gán từ quảng cáo ÷ tiền chạy quảng cáo. Ví dụ: chi 100.000 đ quảng cáo và tạo ra 400.000 đ doanh thu → **ROAS = 4,0**. Nghĩa là mỗi 1 đ quảng cáo mang về 4 đ doanh thu; chỉ số này cũng chưa trừ giá vốn hay phí.

:small[Mẹo nhớ: SKU = mã sản phẩm · GMV = tổng tiền hàng bán · ROAS = số tiền thu về trên mỗi đồng quảng cáo.]
""",
            """
**SKU — a unique product code**

SKU distinguishes one product and links it to its orders and inventory. For example, `FRUIT-TAO-001` can identify an apple basket, allowing AI to find its sold quantity and remaining stock.

**GMV — total value of completed merchandise sales**

GMV is the gross value of completed orders before the shop's discount and estimated fees. Example: 2 products at 250,000 VND each → **GMV = 500,000 VND**. GMV is not profit because product cost, discounts, and fees still apply.

**ROAS — advertising return on spend**

ROAS = revenue attributed to ads ÷ ad spend. Example: 100,000 VND in ads produces 400,000 VND revenue → **ROAS = 4.0**. Each 1 VND of advertising generated 4 VND in attributed revenue; this still excludes product cost and fees.

:small[Remember: SKU = product code · GMV = gross merchandise sales · ROAS = revenue per advertising unit spent.]
""",
        ))


def render_data_library() -> None:
    """The persistent local shop-data workspace, reached via the bookshelf."""
    st.markdown(f'<div class="seller-eyebrow">{ui_text("THƯ VIỆN DỮ LIỆU", "DATA LIBRARY")}</div>', unsafe_allow_html=True)
    header, back = st.columns([8, 2], vertical_alignment="center")
    with header:
        st.title(ui_text("Dữ liệu và báo cáo quản lý", "Data and management reports"))
        st.caption(ui_text("Tạo bảng trực tiếp, lưu trên máy này và dùng lại cho các cuộc trò chuyện.", "Create tables directly, save them on this device, and reuse them in conversations."))
    with back:
        st.button(ui_text("Quay lại chat", "Back to chat"), icon=":material/chat:", width="stretch", on_click=open_chat_view)

    render_quick_guide(
        ui_text("bạn cần tạo, sửa hoặc chọn dữ liệu để AI phân tích cho đúng cuộc trò chuyện đang mở.", "you need to create, edit, or select data for AI to analyze in the current conversation."),
        ui_text(
            ["Chọn Bộ demo nếu muốn tập thử, hoặc Dữ liệu shop nếu là chủ shop", "Tạo/chỉnh sửa các bảng đơn hàng, sản phẩm và tồn kho", "Bấm Dùng dữ liệu shop trong chat để gắn dữ liệu vào chat hiện tại"],
            ["Choose Demo data to practice, or Shop data if you own the shop", "Create or edit orders, products, and inventory tables", "Select Use shop data in chat to attach it to the current chat"],
        ),
    )
    scope = st.segmented_control(
        "Không gian dữ liệu",
        options=["demo", "owner"],
        format_func=lambda value: ui_text("Bộ demo · Người mới", "Demo data · New seller") if value == "demo" else ui_text("Dữ liệu shop · Chủ shop", "Shop data · Shop owner"),
        key="seller_library_scope",
        required=True,
        width="stretch",
    )
    scope = str(scope or "owner")
    library = library_repository()
    saved_rows = library.load(scope)
    is_demo = scope == "demo"
    scope_title = ui_text("Bộ dữ liệu demo cho người mới", "Demo data for a new seller") if is_demo else ui_text("Dữ liệu vận hành của chủ shop", "Shop operational data")
    scope_note = ui_text(
        "Dùng để tập thao tác, kiểm tra biểu đồ và thử các câu hỏi phân tích. Đây không phải dữ liệu shop thật.",
        "Use it to practice, review charts, and test analytical questions. This is not real shop data.",
    ) if is_demo else ui_text(
        "Dùng để quản lý bảng do chủ shop nhập trực tiếp trên ứng dụng. Dữ liệu được lưu cục bộ trên máy này.",
        "Use it to manage tables entered directly in the app. Data is stored locally on this device.",
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
            with st.container(horizontal=True):
                st.button(
                    "Dùng bộ demo cho chat đang mở",
                    key="attach_demo_to_current_chat",
                    icon=":material/link:",
                    type="primary",
                    on_click=activate_library_data,
                    args=(scope,),
                )
                st.button(
                    "Xem thị trường cùng ngành",
                    key="open_demo_market",
                    icon=":material/insights:",
                    on_click=open_market_intelligence,
                )
            st.caption(
                "Nút đầu tiên gắn dữ liệu vào chat đang mở. Phân tích thị trường và Chiến lược "
                "giữ ngành hàng của chat đó."
            )
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
        st.subheader(ui_text("Dữ liệu bán hàng", "Sales data"))
        st.caption(ui_text("Dữ liệu này giúp AI phân tích hoạt động kinh doanh của shop.", "This data helps the AI analyze shop operations."))

    if is_uploaded():
        rows = st.session_state.seller_uploaded_rows
        labels = {
            "orders.csv": "Đơn hàng",
            "products.csv": "Sản phẩm",
            "inventory.csv": "Tồn kho",
            "ads.csv": "Quảng cáo",
            "purchase_orders.csv": "Đơn nhập hàng",
            "returns.csv": "Hoàn hàng",
            "reviews.csv": "Đánh giá khách hàng",
            "operating_costs.csv": "Chi phí vận hành",
            "inventory_movements.csv": "Biến động kho",
            "quality_checks.csv": "Kiểm tra chất lượng",
            "cash_flow.csv": "Dòng tiền",
            "supplier_performance.csv": "Hiệu quả nhà cung cấp",
            "customer_segments.csv": "Nhóm khách hàng",
            "product_funnel.csv": "Hiệu quả từng sản phẩm",
            "co_purchase.csv": "Sản phẩm mua cùng",
            "price_promotions.csv": "Giá và khuyến mãi theo SKU",
            "ads_sku_daily.csv": "Quảng cáo theo SKU/ngày",
            "inventory_batches.csv": "Tuổi tồn kho theo lô",
            "search_performance.csv": "Hiệu quả tìm kiếm",
            "shipping_performance.csv": "Vận chuyển",
            "settlements.csv": "Đối soát thanh toán",
            "competitor_catalog.csv": "Danh mục đối thủ",
        }
        for name in st.session_state.seller_uploaded_names:
            st.success(
                f"{labels.get(name, name)} — {len(rows.get(name, []))} bản ghi — Sẵn sàng",
                icon=":material/check_circle:",
            )
        st.download_button(
            ui_text("Tải bộ dữ liệu đang dùng (.xlsx)", "Download current data (.xlsx)"),
            data=vietnamese_excel_export(rows),
            file_name="du_lieu_eslabong_co_the_chinh_sua.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            icon=":material/download:",
            width="stretch",
            help=ui_text("Tải toàn bộ bảng đang gắn với chat này về máy. Bạn có thể sửa rồi tải lại; tên cột trong tệp là tiếng Việt không dấu.", "Download every table attached to this chat. Edit it, then upload it again; headers are Vietnamese without accents."),
        )
        st.caption(ui_text(
            "Tệp xuất luôn có đủ 22 trang dữ liệu. Trang chỉ có hàng tiêu đề là bảng chưa có dữ liệu; khi nạp lại, hệ thống sẽ bỏ qua trang tùy chọn đó thay vì coi là dữ liệu. Muốn kiểm thử đủ chức năng, hãy dùng Bộ kiểm thử đầy đủ bên dưới.",
            "The export always contains all 22 data sheets. A sheet with headers only has no data; on re-import, optional blank sheets are ignored. For a full functional test, use the complete test package below.",
        ))
        if st.button(ui_text("Thay dữ liệu shop", "Replace shop data"), icon=":material/upload_file:"):
            st.session_state.seller_uploaded_rows = None
            st.session_state.seller_uploaded_names = ()
            st.session_state.seller_data_origin = None
            clear_active_conversation()
            save_active_conversation()
            st.rerun()
        return

    st.info(
        ui_text("Chưa có dữ liệu shop. Thêm báo cáo để AI phân tích doanh thu, tồn kho và quảng cáo.", "No shop data yet. Add reports so the AI can analyze revenue, inventory, and advertising."),
        icon=":material/info:",
    )
    st.caption(
        ui_text("Bạn có thể tải CSV UTF-8 hoặc Excel (.xlsx). Tên cột được viết tiếng Việt có dấu hoặc không dấu đều dùng được; ví dụ `ma_san_pham` nghĩa là **Mã sản phẩm**.", "You can upload UTF-8 CSV or Excel (.xlsx). Vietnamese headers with or without accents are accepted; for example, `ma_san_pham` means **Product code**.")
    )
    with st.container(border=True):
        st.markdown("#### " + ui_text("Dữ liệu thử tiếng Việt", "Vietnamese sample data"))
        st.caption(ui_text(
            "Bộ kiểm thử có dữ liệu hợp lệ ở cả 22 bảng: đơn hàng, tồn kho, giá–khuyến mãi, quảng cáo, tìm kiếm, vận chuyển, đối soát và danh mục đối thủ. Không phải file mẫu chỉ có tiêu đề trang.",
            "The test package has valid rows in all 22 tables: orders, inventory, promotions, ads, search, shipping, settlements, and competitor catalogue. It is not a header-only template.",
        ))
        st.download_button(
            ui_text("Tải bộ kiểm thử đầy đủ (.xlsx)", "Download complete test data (.xlsx)"),
            data=vietnamese_sample_workbook(DEMO_WORKBOOK_VERSION),
            file_name="du_lieu_thu_eslabong_day_du_20261002.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            icon=":material/download:",
        )

    st.markdown("#### " + ui_text("Nạp một file Excel", "Upload one Excel workbook"))
    st.caption(ui_text(
        "Chọn bộ kiểm thử vừa tải hoặc file đã xuất từ chat. Hệ thống tự đọc các trang có dữ liệu; ba trang Đơn hàng, Sản phẩm và Tồn kho là bắt buộc.",
        "Choose the downloaded test package or a workbook exported from chat. The app reads sheets that contain data; Orders, Products, and Inventory are required.",
    ))
    exported_workbook = st.file_uploader(
        ui_text("Chọn file Excel (.xlsx)", "Choose an Excel file (.xlsx)"),
        type=["xlsx"], key="seller_workbook_upload",
    )
    if st.button(
        ui_text("Dùng file này", "Use this file"), key="seller_use_workbook",
        icon=":material/upload_file:", disabled=exported_workbook is None,
    ):
        try:
            tool = ShopDataTool.from_uploaded_workbook(exported_workbook.getvalue())
        except ShopDataValidationError as exc:
            st.error(str(exc), icon=":material/error:")
            return
        st.session_state.seller_uploaded_rows = tool.uploaded_rows
        st.session_state.seller_uploaded_names = tuple(tool.uploaded_rows or {})
        st.session_state.seller_data_origin = "uploaded_csv"
        if st.session_state.get("seller_chat_mode") is None:
            start_conversation("owner")
        clear_active_conversation()
        save_active_conversation()
        missing_optional = sorted(OPTIONAL_UPLOAD_FILES - set(tool.uploaded_rows or {}))
        if missing_optional:
            st.session_state.seller_upload_message = ui_text(
                f"Đã nạp dữ liệu Excel. Có {len(missing_optional)} bảng mở rộng chưa có dòng dữ liệu; AI sẽ nói rõ bảng cần tạo khi bạn hỏi về chúng.",
                f"Excel data loaded. {len(missing_optional)} optional tables have no rows; the AI will name the table to create when you ask about one.",
            )
        else:
            st.session_state.seller_upload_message = ui_text(
                "Đã nạp bộ dữ liệu Excel đầy đủ: 22 bảng đều có dữ liệu.",
                "Complete Excel test data loaded: all 22 tables contain data.",
            )
        st.rerun()

    with st.expander(ui_text("Nhập từng bảng riêng (nâng cao)", "Upload separate tables (advanced)"), icon=":material/tune:"):
        st.caption(ui_text("Chỉ cần ba bảng bắt buộc. Mở phần mở rộng khi bạn có thêm báo cáo quảng cáo, hoàn hàng hoặc chi phí.", "Only three tables are required. Open the extra fields when you also have advertising, returns, or cost reports."))
        show_optional = st.toggle(ui_text("Thêm bảng mở rộng", "Add optional tables"), key="seller_show_optional_uploads")
        ads = purchase_orders = returns = reviews = operating_costs = None
        inventory_movements = quality_checks = cash_flow = supplier_performance = None
        customer_segments = product_funnel = co_purchase = price_promotions = ads_sku_daily = inventory_batches = None
        search_performance = shipping_performance = settlements = competitor_catalog = None
        with st.form("seller_upload_form", border=False):
            orders = st.file_uploader(ui_text("Đơn hàng (bắt buộc)", "Orders (required)"), type=["csv", "xlsx"])
            products = st.file_uploader(ui_text("Sản phẩm và giá vốn (bắt buộc)", "Products and costs (required)"), type=["csv", "xlsx"])
            inventory = st.file_uploader(ui_text("Tồn kho (bắt buộc)", "Inventory (required)"), type=["csv", "xlsx"])
            if show_optional:
                ads = st.file_uploader(ui_text("Quảng cáo", "Advertising"), type=["csv", "xlsx"])
                purchase_orders = st.file_uploader(ui_text("Đơn nhập hàng", "Purchase orders"), type=["csv", "xlsx"])
                returns = st.file_uploader(ui_text("Hoàn hàng", "Returns"), type=["csv", "xlsx"])
                reviews = st.file_uploader(ui_text("Đánh giá khách hàng", "Customer reviews"), type=["csv", "xlsx"])
                operating_costs = st.file_uploader(ui_text("Chi phí vận hành", "Operating costs"), type=["csv", "xlsx"])
                inventory_movements = st.file_uploader(ui_text("Biến động kho", "Inventory movements"), type=["csv", "xlsx"])
                quality_checks = st.file_uploader(ui_text("Kiểm tra chất lượng lô hàng", "Quality checks"), type=["csv", "xlsx"])
                cash_flow = st.file_uploader(ui_text("Dòng tiền", "Cash flow"), type=["csv", "xlsx"])
                supplier_performance = st.file_uploader(ui_text("Hiệu quả nhà cung cấp", "Supplier performance"), type=["csv", "xlsx"])
                customer_segments = st.file_uploader(ui_text("Nhóm khách hàng", "Customer segments"), type=["csv", "xlsx"])
                product_funnel = st.file_uploader(ui_text("Hiệu quả từng sản phẩm", "Product funnel"), type=["csv", "xlsx"])
                co_purchase = st.file_uploader(ui_text("Sản phẩm mua cùng", "Products purchased together"), type=["csv", "xlsx"])
                st.caption(ui_text("Bộ phân tích nâng cao", "Advanced analysis"))
                price_promotions = st.file_uploader(ui_text("Giá và khuyến mãi theo SKU", "Price and promotions by SKU"), type=["csv", "xlsx"])
                ads_sku_daily = st.file_uploader(ui_text("Quảng cáo theo SKU/ngày", "Advertising by SKU/day"), type=["csv", "xlsx"])
                inventory_batches = st.file_uploader(ui_text("Tuổi tồn kho theo lô", "Inventory age by batch"), type=["csv", "xlsx"])
                search_performance = st.file_uploader(ui_text("Hiệu quả tìm kiếm", "Search performance"), type=["csv", "xlsx"])
                shipping_performance = st.file_uploader(ui_text("Vận chuyển", "Shipping performance"), type=["csv", "xlsx"])
                settlements = st.file_uploader(ui_text("Đối soát thanh toán", "Settlement reconciliation"), type=["csv", "xlsx"])
                competitor_catalog = st.file_uploader(ui_text("Danh mục đối thủ (tham khảo)", "Competitor catalogue (reference)"), type=["csv", "xlsx"])
            submitted = st.form_submit_button(ui_text("Thêm dữ liệu", "Add data"), icon=":material/upload_file:", width="stretch")
    if not submitted:
        return
    files = {
        "orders.csv": orders,
        "products.csv": products,
        "inventory.csv": inventory,
        "ads.csv": ads,
        "purchase_orders.csv": purchase_orders,
        "returns.csv": returns,
        "reviews.csv": reviews,
        "operating_costs.csv": operating_costs,
        "inventory_movements.csv": inventory_movements,
        "quality_checks.csv": quality_checks,
        "cash_flow.csv": cash_flow,
        "supplier_performance.csv": supplier_performance,
        "customer_segments.csv": customer_segments,
        "product_funnel.csv": product_funnel,
        "co_purchase.csv": co_purchase,
        "price_promotions.csv": price_promotions,
        "ads_sku_daily.csv": ads_sku_daily,
        "inventory_batches.csv": inventory_batches,
        "search_performance.csv": search_performance,
        "shipping_performance.csv": shipping_performance,
        "settlements.csv": settlements,
        "competitor_catalog.csv": competitor_catalog,
    }
    missing = [name for name in REQUIRED_FILES if files[name] is None]
    if missing:
        labels = {"orders.csv": "Đơn hàng", "products.csv": "Sản phẩm và giá vốn", "inventory.csv": "Tồn kho"}
        st.error("Bạn cần thêm đủ: " + ", ".join(labels[name] for name in missing), icon=":material/error:")
        return
    try:
        content = {name: item.getvalue() for name, item in files.items() if item is not None}
        tool = ShopDataTool.from_uploaded_files(content)
    except ShopDataValidationError as exc:
        st.error(str(exc), icon=":material/error:")
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


@st.dialog(ui_text("Chọn loại cuộc trò chuyện", "Choose conversation type"))
def choose_chat_type() -> None:
    st.write(ui_text("Chọn đúng vai trò để AI gợi ý câu hỏi phù hợp.", "Choose a role so the AI can suggest relevant questions."))
    learner_column, owner_column = st.columns(2, gap="medium")
    with learner_column:
        with st.container(border=True):
            st.markdown("#### :material/school: " + ui_text("Người mới tìm hiểu", "New seller"))
            st.caption(ui_text("Dành cho người chuẩn bị tạo shop hoặc mới bắt đầu bán trên Shopee.", "For people preparing to open a shop or starting to sell on Shopee."))
            if st.button(ui_text("Bắt đầu với vai trò người mới", "Start as a new seller"), key="choose_learner", type="primary", width="stretch"):
                start_conversation("learner")
                st.rerun()
    with owner_column:
        with st.container(border=True):
            st.markdown("#### :material/storefront: " + ui_text("Chủ shop", "Shop owner"))
            st.caption(ui_text("Dành cho chủ shop cần hỏi doanh thu, chính sách và vận hành bán hàng.", "For shop owners asking about revenue, policies, and operations."))
            if st.button(ui_text("Bắt đầu với vai trò chủ shop", "Start as a shop owner"), key="choose_owner", width="stretch"):
                start_conversation("owner")
                st.rerun()


def render_assistant() -> None:
    if st.session_state.get("seller_upload_message"):
        st.toast(st.session_state.seller_upload_message, icon=":material/check_circle:")
        st.session_state.seller_upload_message = None

    mode = st.session_state.get("seller_chat_mode")
    if mode not in CHAT_TYPES or not st.session_state.get("seller_active_chat_id"):
        st.markdown('<div class="seller-eyebrow">ESLABONG</div>', unsafe_allow_html=True)
        st.title(ui_text("Bắt đầu cuộc trò chuyện", "Start a conversation"))
        st.markdown(f'<div class="seller-subtitle">{ui_text("Chọn loại cuộc trò chuyện để AI hỗ trợ đúng nhu cầu của bạn.", "Choose a conversation type so the AI can support the right need.")}</div>', unsafe_allow_html=True)
        st.space("small")
        with st.container(border=True):
            st.markdown("#### " + ui_text("Bạn muốn hỏi với vai trò nào?", "Which role are you asking as?"))
            st.caption(ui_text("Bạn có thể tạo nhiều cuộc trò chuyện; mỗi cuộc được đánh dấu riêng là Người mới hoặc Chủ shop.", "You can create multiple chats; each is marked as a New seller or Shop owner chat."))
            st.button(ui_text("Cuộc trò chuyện mới", "New chat"), key="new_chat_main", type="primary", icon=":material/add_comment:", on_click=show_chat_picker)
        render_quick_guide(
            ui_text("bạn bắt đầu sử dụng AI hoặc muốn tạo một chủ đề hỏi mới.", "you are starting with AI or want a new topic."),
            ui_text(
                ["Bấm Cuộc trò chuyện mới", "Chọn Người mới hoặc Chủ shop", "Gõ câu hỏi hoặc dùng câu hỏi gợi ý"],
                ["Select New chat", "Choose New seller or Shop owner", "Type a question or use a suggested question"],
            ),
        )
        return

    chat_type = active_chat_type(mode)
    conversation = active_conversation()
    st.markdown('<div class="seller-eyebrow">ESLABONG</div>', unsafe_allow_html=True)
    chat_header, adviser = st.columns([8, 2], vertical_alignment="center")
    with chat_header:
        st.subheader(f"{chat_type['icon']} {chat_type['name']}")
        st.caption(chat_type["description"])
    with adviser:
        render_advisor_entry("chat", "chat_open_advisor")
    if conversation is not None:
        st.caption(
            f":material/forum: **{conversation['title']}** · "
            f":material/link: **{conversation_data_label(conversation)}** · "
            "Lịch sử, dữ liệu và Chiến lược gia AI được tách riêng cho cuộc trò chuyện này."
        )
    render_quick_guide(
        ui_text("bạn muốn hỏi chính sách Shopee, doanh thu, tồn kho hoặc cần AI hướng dẫn bước tiếp theo.", "you want help with Shopee policies, revenue, inventory, or the next step."),
        ui_text(
            ["Nếu cần số liệu, bấm Thư viện dữ liệu để gắn dữ liệu cho chat này", "Gõ câu hỏi vào ô dưới cùng", "Mở Chiến lược gia AI ở đầu chat khi cần trao đổi về Thị trường hoặc Chiến lược"],
            ["If you need figures, open Data library and attach data to this chat", "Type your question in the bottom field", "Open AI strategist at the top when you need to discuss Market or Strategy"],
        ),
    )

    if mode == "owner" and not is_uploaded():
        with st.container(border=True):
            st.markdown("**Chưa có dữ liệu vận hành cho chat này**")
            st.caption("Tạo bảng trực tiếp trong Thư viện dữ liệu để quản lý và phân tích; tải CSV chỉ là lựa chọn phụ.")
            st.button("Mở thư viện dữ liệu", key="open_library_from_chat", icon=":material/auto_stories:", on_click=open_data_library)
        with st.expander("Nhập từ CSV (tùy chọn)", icon=":material/upload_file:"):
            render_data_upload(inline=True)
    elif mode == "owner":
        with st.expander(ui_text("Dữ liệu đang gắn với chat", "Data attached to this chat"), icon=":material/table_chart:"):
            render_data_upload(inline=True)
    elif mode == "learner" and not is_uploaded():
        with st.container(horizontal=True):
            st.button(
                ui_text("Dùng bộ dữ liệu demo để thử phân tích", "Use demo data for analysis"),
                key="open_demo_library_from_chat",
                icon=":material/auto_stories:",
                on_click=open_data_library,
            )
            with st.popover(
                ui_text("Bộ câu hỏi người mới", "New seller questions"),
                icon=":material/menu_book:",
            ):
                render_learner_question_bank()

    render_advisor_handoff()

    for message in st.session_state.seller_messages:
        if message["role"] == "user":
            with st.chat_message("user", avatar=":material/person:"):
                st.write(message["content"])
        else:
            render_answer(message)

    render_advisor_launcher("chat")

    prompt: str | None = st.session_state.pop("seller_pending_main_prompt", None)
    if not st.session_state.seller_messages and mode == "owner":
        choice = st.pills("Câu hỏi gợi ý", list(SUGGESTIONS[mode]), selection_mode="single", label_visibility="collapsed", key="seller_suggestion")
        if choice:
            prompt = SUGGESTIONS[mode][str(choice)]

    # A conversation composer belongs to the app bottom. Rendering it inline
    # made it appear between old messages after a saved chat was restored.
    with st.bottom:
        typed_prompt = st.chat_input(
            ui_text("Nhập câu hỏi…", "Type a question…"),
            key="seller_chat_input",
            submit_mode="disable",
            height="content",
        )
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
        requirement = data_requirement_note(result.get("data_requirement"))
        if requirement:
            st.caption(":material/fact_check: " + requirement)
        note = data_note(result.get("data_source"))
        if note:
            st.caption(":material/table_chart: " + note)
        st.caption(f":material/verified: Độ chắc chắn: {result['confidence']}")
        render_sources(result.get("citations", []))
    st.session_state.seller_messages.append({"role": "assistant", **result})
    save_active_conversation()


initialise_state()
render_color_mode_css()
render_sidebar_layout_css()
with st.sidebar:
    compact = st.session_state.seller_sidebar_compact
    if compact:
        if st.button(" ", key="expand_sidebar", icon=":material/chevron_right:", help=ui_text("Mở rộng danh sách chat", "Expand chat list"), width="stretch"):
            toggle_sidebar_compact()
            st.rerun()
        st.button(" ", key="compact_new_chat", icon=":material/add_comment:", help=ui_text("Cuộc trò chuyện mới", "New chat"), width="stretch", on_click=show_chat_picker)
        st.button(" ", key="compact_data_library", icon=":material/auto_stories:", help=ui_text("Thư viện dữ liệu", "Data library"), width="stretch", on_click=open_data_library)
        st.button(" ", key="compact_market_intelligence", icon=":material/insights:", help=ui_text("Phân tích thị trường", "Market analysis"), width="stretch", on_click=open_market_intelligence)
        st.button(" ", key="compact_strategy_workspace", icon=":material/rocket_launch:", help=ui_text("Chiến lược kinh doanh", "Business strategy"), width="stretch", on_click=open_strategy_workspace)
        for conversation in reversed(st.session_state.seller_conversations[-5:]):
            chat_type = active_chat_type(conversation["mode"])
            label = f"{chat_type['name']} · {conversation['title']} · {conversation_data_label(conversation)}"
            is_active = conversation["id"] == st.session_state.get("seller_active_chat_id")
            st.button(
                " ",
                key=f"compact_open_{conversation['id']}",
                icon=chat_type["icon"],
                type="primary" if is_active else "secondary",
                help=label,
                width="stretch",
                on_click=open_conversation,
                args=(conversation["id"],),
            )
    else:
        with st.container(horizontal=True, horizontal_alignment="distribute"):
            st.markdown("### :material/storefront: Eslabong")
            if st.button(" ", key="collapse_sidebar", icon=":material/chevron_left:", help=ui_text("Thu gọn danh sách chat", "Collapse chat list")):
                toggle_sidebar_compact()
                st.rerun()
        st.button(ui_text("Cuộc trò chuyện mới", "New chat"), icon=":material/add_comment:", width="stretch", on_click=show_chat_picker)
        st.button(ui_text("Thư viện dữ liệu", "Data library"), key="open_data_library", icon=":material/auto_stories:", width="stretch", on_click=open_data_library)
        st.button(ui_text("Phân tích thị trường", "Market analysis"), key="open_market_intelligence", icon=":material/insights:", width="stretch", on_click=open_market_intelligence)
        st.button(ui_text("Chiến lược kinh doanh", "Business strategy"), key="open_strategy_workspace", icon=":material/rocket_launch:", width="stretch", on_click=open_strategy_workspace)
        st.caption(ui_text("Cuộc trò chuyện gần đây", "Recent chats"))
        for conversation in reversed(st.session_state.seller_conversations[-5:]):
            chat_type = active_chat_type(conversation["mode"])
            is_active = conversation["id"] == st.session_state.get("seller_active_chat_id")
            st.button(
                sidebar_chat_label(conversation),
                key=f"open_{conversation['id']}",
                icon=chat_type["icon"],
                type="primary" if is_active else "secondary",
                width="stretch",
                on_click=open_conversation,
                args=(conversation["id"],),
            )
    with st.expander(ui_text("Cài đặt", "Settings"), icon=":material/settings:"):
        st.selectbox(
            ui_text("Ngôn ngữ giao diện", "Interface language"),
            options=("vi", "en"),
            format_func=lambda value: "Tiếng Việt" if value == "vi" else "English",
            key="seller_language",
        )
        st.toggle(
            ui_text("Chế độ đêm dịu mắt", "Comfortable dark mode"),
            key="seller_dark_mode",
        )
        st.caption(ui_text("Cài đặt chỉ áp dụng cho tab đang mở.", "Settings apply only to this browser tab."))
        st.caption("Bản dữ liệu: 2026.10.02-full-export")

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

render_scroll_navigation()
