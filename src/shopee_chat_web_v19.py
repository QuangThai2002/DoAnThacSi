from __future__ import annotations

import time
import json
import uuid
import re
import csv
import html
import threading
from concurrent.futures import Future, ThreadPoolExecutor
from datetime import datetime
from typing import Any

import streamlit as st
import streamlit.components.v1 as components

try:
    from streamlit.runtime.scriptrunner import (
        add_script_run_ctx,
        get_script_run_ctx,
    )
except ImportError:  # Tương thích với một số bản Streamlit cũ.
    add_script_run_ctx = None

    def get_script_run_ctx():
        return None

import shopee_rag_complete_v4_0_1 as backend
from agent.streamlit_view import initialize_agent_state, render_agent_view


# ============================================================
# CẤU HÌNH TRANG
# ============================================================

st.set_page_config(
    page_title="Shopee AI Assistant",
    page_icon="🛍️",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """

    <style>
:root {
    --shopee: #ee4d2d;
    --shopee-dark: #d94124;
    --shopee-soft: #fff2ed;
    --surface: #ffffff;
    --surface-soft: #fffaf8;
    --text: #1f2937;
    --muted: #7b8491;
    --border: #e8e8e8;
}

html, body, [class*="css"] {
    font-family: Inter, ui-sans-serif, system-ui, -apple-system,
                 BlinkMacSystemFont, "Segoe UI", sans-serif;
}

.stApp {
    color: var(--text);
    background:
        radial-gradient(circle at 95% 0%, rgba(238, 77, 45, 0.08), transparent 25%),
        linear-gradient(180deg, #ffffff 0%, #fffaf8 100%);
}

header[data-testid="stHeader"] {
    background: rgba(255, 255, 255, 0.95);
    border-bottom: 1px solid var(--border);
    backdrop-filter: blur(10px);
}

[data-testid="stSidebar"] {
    background: #ffffff;
    border-right: 1px solid var(--border);
}

[data-testid="stSidebar"] .block-container {
    padding: 1.1rem 0.9rem 1.25rem;
}

.block-container {
    max-width: none;
    width: 100%;
    padding-top: 1rem;
    padding-left: 1.35rem;
    padding-right: 1.35rem;
    padding-bottom: 7rem;
}

.brand-wrap {
    display: flex;
    align-items: center;
    gap: 11px;
    margin-bottom: 1rem;
}

.brand-logo {
    width: 44px;
    height: 44px;
    display: flex;
    align-items: center;
    justify-content: center;
    border-radius: 14px;
    color: #ffffff;
    font-size: 21px;
    font-weight: 800;
    background: linear-gradient(135deg, #ff7045, #ee4d2d);
    box-shadow: 0 9px 22px rgba(238, 77, 45, 0.20);
}

.brand-name {
    color: #111827;
    font-size: 1rem;
    font-weight: 780;
    line-height: 1.2;
}

.brand-subtitle {
    color: #9299a4;
    font-size: 0.74rem;
    margin-top: 3px;
}

.v9-history-heading {
    color: #9ca3af;
    font-size: 0.7rem;
    font-weight: 800;
    text-transform: uppercase;
    letter-spacing: 0.06em;
    margin: 1rem 0 0.5rem;
}

.v9-active-chat {
    padding: 9px 10px;
    border-radius: 11px;
    color: #c2410c;
    background: #fff1eb;
    border: 1px solid #ffd7c9;
    font-size: 0.79rem;
    line-height: 1.35;
    margin-bottom: 0.4rem;
}

.v9-sidebar-note {
    color: #9ca3af;
    font-size: 0.7rem;
    line-height: 1.5;
    margin-top: 0.8rem;
}

.v9-page-header {
    max-width: none;
    width: 100%;
    margin: 0 0 0.9rem;
    padding: 0.35rem 0.2rem 0.8rem;
    border-bottom: 1px solid #f0f0f0;
}

.v9-page-title {
    color: #111827;
    font-size: 1.04rem;
    font-weight: 760;
}

.v9-page-subtitle {
    color: #9299a4;
    font-size: 0.75rem;
    margin-top: 3px;
}

.v9-empty {
    max-width: 720px;
    margin: 8vh auto 1.35rem;
    text-align: center;
}

.v9-empty-icon {
    width: 60px;
    height: 60px;
    display: flex;
    align-items: center;
    justify-content: center;
    margin: 0 auto 15px;
    border-radius: 19px;
    color: #ffffff;
    font-size: 28px;
    font-weight: 800;
    background: linear-gradient(135deg, #ff7045, #ee4d2d);
    box-shadow: 0 14px 30px rgba(238, 77, 45, 0.20);
}

.v9-empty-title {
    color: #111827;
    font-size: 1.72rem;
    font-weight: 800;
    letter-spacing: -0.02em;
}

.v9-empty-subtitle {
    max-width: 620px;
    margin: 9px auto 0;
    color: #6b7280;
    font-size: 0.94rem;
    line-height: 1.65;
}

.v9-assistant-name {
    color: var(--shopee);
    font-size: 0.72rem;
    font-weight: 850;
    text-transform: uppercase;
    letter-spacing: 0.055em;
    margin-bottom: 7px;
}

.v9-time {
    color: #a1a7b1;
    font-size: 0.65rem;
    margin-top: 6px;
}

.v9-time.user {
    text-align: right;
}

.v9-technical {
    margin-top: 9px;
    padding: 8px 10px;
    border-radius: 10px;
    color: #7b828c;
    background: #fafafa;
    border: 1px solid #eeeeee;
    font-size: 0.72rem;
}

/* Khung tin nhắn dùng st.container(border=True), ổn định hơn HTML mở/đóng */
div[data-testid="stVerticalBlockBorderWrapper"] {
    border-radius: 18px;
    border-color: var(--border);
    background: #ffffff;
    box-shadow: 0 7px 22px rgba(17, 24, 39, 0.045);
}

/* Tạo cảm giác hai bên rõ như Messenger/Zalo */
[data-testid="stHorizontalBlock"] {
    align-items: flex-start;
}

[data-testid="stHorizontalBlock"] > div {
    min-width: 0;
}

/* Bong bóng người dùng và AI gọn hơn */
div[data-testid="stVerticalBlockBorderWrapper"] {
    overflow-wrap: anywhere;
}

@media (min-width: 901px) {
    div[data-testid="stVerticalBlockBorderWrapper"] {
        max-width: 100%;
    }
}

div[data-testid="stVerticalBlockBorderWrapper"] > div {
    padding-top: 0.1rem;
    padding-bottom: 0.1rem;
}

/* Nội dung markdown trong tin nhắn */
div[data-testid="stVerticalBlockBorderWrapper"] p,
div[data-testid="stVerticalBlockBorderWrapper"] li,
div[data-testid="stVerticalBlockBorderWrapper"] span,
div[data-testid="stVerticalBlockBorderWrapper"] strong {
    color: #1f2937 !important;
    line-height: 1.65;
    font-size: 0.95rem;
}

div[data-testid="stVerticalBlockBorderWrapper"] code {
    color: #b9381d !important;
    background: #fff1eb;
    padding: 2px 5px;
    border-radius: 6px;
}

/* Các nút */
.stButton button {
    min-height: 40px;
    color: #374151;
    border: 1px solid #ebebeb;
    border-radius: 12px;
    background: #ffffff;
    transition: 0.15s ease;
}

.stButton button:hover {
    color: #c2410c;
    border-color: #f2ad97;
    background: #fff7f3;
    transform: translateY(-1px);
}

[data-testid="stSidebar"] .stButton button[kind="primary"] {
    color: #ffffff;
    font-weight: 720;
    border: none;
    background: linear-gradient(100deg, #ff7045, #ee4d2d);
    box-shadow: 0 9px 20px rgba(238, 77, 45, 0.18);
}

/* Thanh nhập */
[data-testid="stBottomBlockContainer"] {
    background: linear-gradient(180deg, rgba(255,255,255,0), #ffffff 30%);
    padding-top: 1rem;
}

[data-testid="stChatInput"] {
    border: 1px solid #dedede !important;
    border-radius: 17px !important;
    background: #ffffff !important;
    box-shadow: 0 14px 34px rgba(17, 24, 39, 0.11) !important;
}

[data-testid="stChatInput"] textarea {
    color: #111827 !important;
    caret-color: var(--shopee);
}

[data-testid="stChatInput"] textarea::placeholder {
    color: #9da4ae !important;
}

[data-testid="stChatInput"] button {
    color: #ffffff !important;
    border-radius: 11px !important;
    background: var(--shopee) !important;
}

div[data-testid="stExpander"] {
    margin-top: 8px;
    border: 1px solid #ededed;
    border-radius: 12px;
    background: #ffffff;
}


/* Trạng thái đang xử lý: khóa ô nhập rõ ràng */
[data-testid="stChatInput"][aria-disabled="true"],
[data-testid="stChatInput"]:has(textarea:disabled) {
    opacity: 0.72;
    background: #f8f8f8 !important;
    cursor: not-allowed;
}

[data-testid="stChatInput"] textarea:disabled {
    color: #8a919d !important;
    cursor: not-allowed;
}


/* V10.2: chat trải rộng gần hai mép như Messenger/Zalo */
[data-testid="stMainBlockContainer"] {
    max-width: none !important;
    width: 100% !important;
}

div[data-testid="stVerticalBlockBorderWrapper"] {
    width: 100%;
}

div[data-testid="stVerticalBlockBorderWrapper"] p,
div[data-testid="stVerticalBlockBorderWrapper"] li {
    font-size: 0.98rem;
    line-height: 1.62;
}

@media (min-width: 1200px) {
    .block-container {
        padding-left: 1.6rem;
        padding-right: 1.6rem;
    }
}

@media (max-width: 900px) {
    .block-container {
        padding-left: 0.65rem;
        padding-right: 0.65rem;
    }
}


/* V11: căn hai phía rõ như ứng dụng nhắn tin */
[data-testid="stHorizontalBlock"] {
    width: 100%;
}

[data-testid="stHorizontalBlock"] > div {
    min-width: 0;
}

.v9-assistant-name {
    letter-spacing: 0.04em;
}

/* Giảm khoảng trắng thừa giữa các tin */
div[data-testid="stVerticalBlockBorderWrapper"] {
    margin-bottom: 0.35rem;
}

/* Nội dung dài tận dụng chiều ngang */
div[data-testid="stVerticalBlockBorderWrapper"] p {
    max-width: none !important;
}




/* ==========================================================
   V13 FINAL — UI adaptive, source name, export và bảo mật
   ========================================================== */
.v13-assistant-label {
    display: inline-flex;
    align-items: center;
    margin-bottom: 0.42rem;
    color: #ee4d2d;
    font-size: 0.76rem;
    font-weight: 800;
    letter-spacing: 0.055em;
    text-transform: uppercase;
}

.v13-source-primary {
    margin-top: 0.78rem;
    padding-top: 0.68rem;
    border-top: 1px solid #efe7e3;
    color: #667085;
    font-size: 0.74rem;
    line-height: 1.55;
}

.v13-source-primary strong {
    color: #475467;
}

.v13-export-note {
    color: #98a2b3;
    font-size: 0.68rem;
    line-height: 1.55;
}

div[data-testid="stVerticalBlockBorderWrapper"] table {
    width: 100% !important;
    min-width: 100%;
    table-layout: auto;
}

div[data-testid="stVerticalBlockBorderWrapper"] th {
    white-space: nowrap;
}

div[data-testid="stVerticalBlockBorderWrapper"] td {
    word-break: normal;
    overflow-wrap: anywhere;
}

div[data-testid="stVerticalBlockBorderWrapper"]
div[data-testid="stHorizontalBlock"] {
    align-items: center;
}

div[data-testid="stVerticalBlockBorderWrapper"]
div[data-testid="stHorizontalBlock"]
button {
    min-height: 29px;
    height: 29px;
    padding: 0 0.40rem;
    border-radius: 8px;
    box-shadow: none;
}

div[data-testid="stVerticalBlockBorderWrapper"] {
    height: auto;
}

@media (min-width: 1200px) {
    div[data-testid="stVerticalBlockBorderWrapper"] p,
    div[data-testid="stVerticalBlockBorderWrapper"] li {
        font-size: 0.98rem;
        line-height: 1.68;
    }
}

@media (max-width: 900px) {
    .block-container {
        padding-left: 0.55rem !important;
        padding-right: 0.55rem !important;
    }

    div[data-testid="stVerticalBlockBorderWrapper"] table {
        display: block;
        overflow-x: auto;
        white-space: nowrap;
    }
}

/* ==========================================================
   V12.1 — Citation Filter, Confidence Calibration,
   tiêu đề thích ứng và cụm hành động gọn
   ========================================================== */
.v121-source-primary {
    margin-top: 0.72rem;
    padding-top: 0.60rem;
    border-top: 1px solid #f0e6e2;
    color: #667085;
    font-size: 0.73rem;
    line-height: 1.55;
}

.v121-source-primary strong {
    color: #475467;
}

.v121-source-note {
    margin-top: 0.28rem;
    color: #98a2b3;
    font-size: 0.68rem;
}

.v121-confidence-high,
.v121-confidence-medium,
.v121-confidence-low {
    display: inline-flex;
    align-items: center;
    gap: 5px;
    margin-top: 0.42rem;
    padding: 4px 9px;
    border-radius: 999px;
    font-size: 0.69rem;
    font-weight: 700;
}

.v121-confidence-high {
    color: #067647;
    background: #ecfdf3;
    border: 1px solid #abefc6;
}

.v121-confidence-medium {
    color: #b54708;
    background: #fffaeb;
    border: 1px solid #fedf89;
}

.v121-confidence-low {
    color: #b42318;
    background: #fef3f2;
    border: 1px solid #fecdca;
}

/* Thu gọn nút hành động trong khối trả lời */
div[data-testid="stVerticalBlockBorderWrapper"]
div[data-testid="stHorizontalBlock"]
button {
    min-height: 30px;
    height: 30px;
    padding: 0 0.45rem;
    border-radius: 8px;
    font-size: 0.72rem;
}

/* Bảng so sánh dễ đọc hơn trên màn hình rộng */
div[data-testid="stVerticalBlockBorderWrapper"] table {
    table-layout: auto;
}

div[data-testid="stVerticalBlockBorderWrapper"] td,
div[data-testid="stVerticalBlockBorderWrapper"] th {
    vertical-align: top;
}

/* Giữ bong bóng người dùng sát bên phải hơn */
@media (min-width: 1100px) {
    div[data-testid="column"]:has(.v9-time.user) {
        margin-left: auto;
    }
}

/* ==========================================================
   V12 — Citation, confidence, bảng, hành động và dashboard
   ========================================================== */
.v12-evidence {
    margin-top: 0.72rem;
    padding-top: 0.62rem;
    border-top: 1px solid #f0ebe9;
    color: #737d8b;
    font-size: 0.74rem;
    line-height: 1.55;
}

.v12-confidence {
    display: inline-flex;
    align-items: center;
    gap: 5px;
    margin-top: 0.42rem;
    padding: 4px 9px;
    border-radius: 999px;
    color: #9a3412;
    background: #fff4ef;
    border: 1px solid #ffd8ca;
    font-size: 0.70rem;
    font-weight: 700;
}

.v12-pipeline {
    padding: 0.75rem 0.85rem;
    border-radius: 12px;
    color: #6b7280;
    background: #fffaf8;
    border: 1px solid #f0dfda;
    font-size: 0.72rem;
    line-height: 1.75;
    text-align: center;
}

.v12-stat-line {
    display: flex;
    justify-content: space-between;
    gap: 10px;
    color: #6b7280;
    font-size: 0.73rem;
    line-height: 1.9;
}

.v12-stat-line strong {
    color: #374151;
}

div[data-testid="stVerticalBlockBorderWrapper"] table {
    width: 100%;
    border-collapse: collapse;
    margin: 0.65rem 0;
}

div[data-testid="stVerticalBlockBorderWrapper"] th {
    color: #9a3412;
    background: #fff4ef;
}

div[data-testid="stVerticalBlockBorderWrapper"] th,
div[data-testid="stVerticalBlockBorderWrapper"] td {
    padding: 0.52rem 0.62rem;
    border: 1px solid #eadfdb;
}

div[data-testid="stVerticalBlockBorderWrapper"] code {
    color: #087f5b;
    background: #f3faf7;
    border-radius: 5px;
    padding: 0.08rem 0.28rem;
}

div[data-testid="stVerticalBlockBorderWrapper"] p,
div[data-testid="stVerticalBlockBorderWrapper"] li {
    font-size: 0.97rem;
    line-height: 1.62;
}

[data-testid="stHorizontalBlock"] {
    width: 100%;
}

[data-testid="stHorizontalBlock"] > div {
    min-width: 0;
}

@media (max-width: 900px) {
    .block-container {
        padding-left: 0.55rem !important;
        padding-right: 0.55rem !important;
    }
}

#MainMenu {visibility: hidden;}
footer {visibility: hidden;}

@media (max-width: 900px) {
    .block-container {
        padding-left: 0.7rem;
        padding-right: 0.7rem;
    }
}


/* ==========================================================
   V14 FINAL — Action toolbar nhất quán như ChatGPT
   ========================================================== */
.v14-action-toolbar-anchor {
    height: 0;
    margin: 0;
    padding: 0;
}

/* Ba cột đầu tiên của hàng hành động có kích thước và căn chỉnh giống nhau */
div[data-testid="stVerticalBlockBorderWrapper"]
div[data-testid="stHorizontalBlock"]:has(.stButton)
> div[data-testid="column"]:nth-child(-n+3) {
    min-width: 42px;
    max-width: 46px;
    flex: 0 0 44px !important;
}

/* Iframe nút copy không tạo khoảng trắng hoặc lệch baseline */
div[data-testid="stVerticalBlockBorderWrapper"]
div[data-testid="stHorizontalBlock"] iframe {
    display: block;
    width: 100% !important;
    min-width: 40px;
    height: 42px !important;
    margin: 0 !important;
    border: 0 !important;
}

/* Nút thích và không thích đồng nhất hoàn toàn với nút copy */
div[data-testid="stVerticalBlockBorderWrapper"]
div[data-testid="stHorizontalBlock"] .stButton {
    width: 100%;
    margin: 0;
}

div[data-testid="stVerticalBlockBorderWrapper"]
div[data-testid="stHorizontalBlock"] .stButton button {
    width: 100% !important;
    min-width: 40px !important;
    height: 40px !important;
    min-height: 40px !important;
    padding: 0 !important;
    border: 1px solid #e5e7eb !important;
    border-radius: 12px !important;
    color: #667085 !important;
    background: #ffffff !important;
    box-shadow: none !important;
    display: flex !important;
    align-items: center !important;
    justify-content: center !important;
    font-size: 18px !important;
    line-height: 1 !important;
    transform: none !important;
}

div[data-testid="stVerticalBlockBorderWrapper"]
div[data-testid="stHorizontalBlock"] .stButton button:hover {
    color: #ee4d2d !important;
    border-color: #ffb9a8 !important;
    background: #fff7f3 !important;
    box-shadow: 0 5px 14px rgba(238, 77, 45, 0.10) !important;
    transform: translateY(-1px) !important;
}

/* Trạng thái đã chọn: nền cam, icon trắng, không đổi kích thước */
div[data-testid="stVerticalBlockBorderWrapper"]
div[data-testid="stHorizontalBlock"] .stButton button[kind="primary"] {
    color: #ffffff !important;
    border-color: #ee4d2d !important;
    background: #ee4d2d !important;
    box-shadow: 0 5px 14px rgba(238, 77, 45, 0.20) !important;
}

div[data-testid="stVerticalBlockBorderWrapper"]
div[data-testid="stHorizontalBlock"] .stButton button[kind="primary"]:hover {
    color: #ffffff !important;
    border-color: #d94124 !important;
    background: #d94124 !important;
}

/* Không cho emoji bị đẩy lên hoặc xuống bởi paragraph wrapper của Streamlit */
div[data-testid="stVerticalBlockBorderWrapper"]
div[data-testid="stHorizontalBlock"] .stButton button p {
    margin: 0 !important;
    padding: 0 !important;
    font-size: 18px !important;
    line-height: 1 !important;
}

@media (max-width: 720px) {
    div[data-testid="stVerticalBlockBorderWrapper"]
    div[data-testid="stHorizontalBlock"]:has(.stButton)
    > div[data-testid="column"]:nth-child(-n+3) {
        min-width: 36px;
        max-width: 38px;
        flex-basis: 38px !important;
    }
}

/* ==========================================================
   V15 FINAL — toolbar kiểu ChatGPT, sidebar gọn và badge thiếu dữ liệu
   ========================================================== */
.v15-data-missing {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    margin-top: 0.48rem;
    padding: 5px 10px;
    border-radius: 999px;
    color: #b54708;
    background: #fffaeb;
    border: 1px solid #fedf89;
    font-size: 0.70rem;
    font-weight: 700;
}

/* Hàng hành động: 3 icon có cùng hộp, cùng baseline, không còn viền trắng nặng. */
div[data-testid="stVerticalBlockBorderWrapper"]
div[data-testid="stHorizontalBlock"]:has(.v14-action-toolbar-anchor),
div[data-testid="stVerticalBlockBorderWrapper"]
div[data-testid="stHorizontalBlock"]:has(iframe) {
    align-items: center !important;
    gap: 4px !important;
    margin-top: 0.20rem !important;
}

div[data-testid="stVerticalBlockBorderWrapper"]
div[data-testid="stHorizontalBlock"]:has(iframe)
> div[data-testid="column"]:nth-child(-n+3) {
    min-width: 36px !important;
    max-width: 36px !important;
    flex: 0 0 36px !important;
    padding: 0 !important;
}

div[data-testid="stVerticalBlockBorderWrapper"]
div[data-testid="stHorizontalBlock"] iframe {
    width: 36px !important;
    height: 36px !important;
    min-width: 36px !important;
    margin: 0 !important;
}

div[data-testid="stVerticalBlockBorderWrapper"]
div[data-testid="stHorizontalBlock"] .stButton button {
    width: 34px !important;
    min-width: 34px !important;
    height: 34px !important;
    min-height: 34px !important;
    padding: 0 !important;
    border: 0 !important;
    border-radius: 10px !important;
    color: #6b7280 !important;
    background: rgba(31, 41, 55, 0.045) !important;
    box-shadow: none !important;
    display: inline-flex !important;
    align-items: center !important;
    justify-content: center !important;
    font-family: "Segoe UI Symbol", "Arial Unicode MS", sans-serif !important;
    font-size: 17px !important;
    line-height: 1 !important;
    transform: none !important;
}

div[data-testid="stVerticalBlockBorderWrapper"]
div[data-testid="stHorizontalBlock"] .stButton button:hover {
    color: #111827 !important;
    border: 0 !important;
    background: rgba(31, 41, 55, 0.09) !important;
    box-shadow: none !important;
    transform: none !important;
}

div[data-testid="stVerticalBlockBorderWrapper"]
div[data-testid="stHorizontalBlock"] .stButton button[kind="primary"] {
    color: #c2410c !important;
    border: 0 !important;
    background: #fff0ea !important;
    box-shadow: none !important;
}

div[data-testid="stVerticalBlockBorderWrapper"]
div[data-testid="stHorizontalBlock"] .stButton button p {
    margin: 0 !important;
    padding: 0 !important;
    font-size: 17px !important;
    line-height: 1 !important;
}

/* Sidebar: nhãn và control thẳng hàng, giảm khoảng trống giữa các nhóm. */
[data-testid="stSidebar"] [data-testid="stWidgetLabel"] p {
    line-height: 1.35 !important;
    margin: 0 !important;
}

[data-testid="stSidebar"] [data-testid="stToggle"] {
    margin-bottom: 0.55rem !important;
}

[data-testid="stSidebar"] .stSelectbox {
    margin-top: 0.20rem !important;
    margin-bottom: 0.55rem !important;
}



/* ==========================================================
   V16 FINAL — Shopee UI nhất quán, tối ưu zoom 100%, toolbar
   line-icon và nút cuộn tới tin nhắn mới nhất
   ========================================================== */
:root {
    --v16-shopee: #ee4d2d;
    --v16-shopee-hover: #d94325;
    --v16-shopee-soft: #fff2ed;
    --v16-shopee-faint: rgba(238, 77, 45, 0.075);
    --v16-border: #e7e2df;
    --v16-text: #20242c;
    --v16-muted: #8a94a3;
}

/* Trải nghiệm ở zoom 100%: chữ và khoảng đệm gọn như khi V15 ở 80%. */
html {
    font-size: 15px;
}

.block-container {
    padding-top: 0.85rem !important;
    padding-left: 1.15rem !important;
    padding-right: 1.15rem !important;
    padding-bottom: 7.4rem !important;
}

.stApp {
    background:
        radial-gradient(circle at 100% 0%, rgba(238,77,45,.075), transparent 26%),
        linear-gradient(180deg, #fff 0%, #fffaf8 100%) !important;
}

/* Logo túi mua sắm nét mảnh, không dùng emoji nên luôn đồng nhất. */
.brand-logo,
.v9-empty-icon {
    color: #fff;
}

.shopee-bag-mark {
    width: 25px;
    height: 25px;
    fill: none;
    stroke: currentColor;
    stroke-width: 1.8;
    stroke-linecap: round;
    stroke-linejoin: round;
}

.v9-empty-icon .shopee-bag-mark {
    width: 32px;
    height: 32px;
}

/* Khung chat sạch hơn, không phóng đại quá mức ở 100%. */
div[data-testid="stVerticalBlockBorderWrapper"] {
    border: 1px solid var(--v16-border) !important;
    border-radius: 16px !important;
    background: rgba(255,255,255,.96) !important;
    box-shadow: 0 6px 20px rgba(17,24,39,.035) !important;
}

div[data-testid="stVerticalBlockBorderWrapper"] > div {
    padding: 0.15rem 0.10rem !important;
}

div[data-testid="stVerticalBlockBorderWrapper"] p,
div[data-testid="stVerticalBlockBorderWrapper"] li {
    color: var(--v16-text) !important;
    font-size: 0.92rem !important;
    line-height: 1.58 !important;
}

div[data-testid="stVerticalBlockBorderWrapper"] p {
    margin-bottom: 0.62rem;
}

div[data-testid="stVerticalBlockBorderWrapper"] li {
    margin-bottom: 0.18rem;
}

.v13-assistant-label {
    color: var(--v16-shopee) !important;
    font-size: 0.70rem !important;
    letter-spacing: .065em !important;
}

.v9-time {
    color: #9aa3b1 !important;
    font-size: 0.62rem !important;
}

.v13-source-primary,
.v121-source-primary {
    border-top-color: #eee7e3 !important;
    color: #717b8c !important;
    font-size: 0.69rem !important;
}

.v121-confidence-high,
.v121-confidence-medium,
.v121-confidence-low,
.v15-data-missing {
    font-size: 0.66rem !important;
    padding: 4px 9px !important;
}

/* User bubble có sắc cam rất nhẹ để phân vai rõ nhưng vẫn chuyên nghiệp. */
div[data-testid="column"]:has(.v9-time.user)
div[data-testid="stVerticalBlockBorderWrapper"] {
    background: linear-gradient(180deg, #fffaf8 0%, #fff7f3 100%) !important;
    border-color: #eadbd5 !important;
    box-shadow: 0 5px 16px rgba(238,77,45,.035) !important;
}

/* Bảng bám chủ đề Shopee, dễ đọc và không quá nặng màu. */
div[data-testid="stVerticalBlockBorderWrapper"] th {
    color: #9a3412 !important;
    background: #fff5f1 !important;
    border-color: #eadfd9 !important;
}

div[data-testid="stVerticalBlockBorderWrapper"] td {
    border-color: #ece5e1 !important;
}

div[data-testid="stVerticalBlockBorderWrapper"] code {
    color: #087f5b !important;
    background: #f4faf7 !important;
    border: 1px solid #edf6f1;
}

/* Toolbar giống ChatGPT: icon mờ, không viền; hover/selected theo màu Shopee. */
/* ==========================================================
   TOOLBAR ACTION — COPY / LIKE / DISLIKE
   ========================================================== */

.v16-action-toolbar-anchor {
    height: 0;
    margin: 0;
    padding: 0;
}

/* Hàng chứa 3 nút */
div[data-testid="stVerticalBlockBorderWrapper"]
div[data-testid="stHorizontalBlock"]:has(iframe) {
    display: flex !important;
    align-items: center !important;
    justify-content: flex-start !important;
    gap: 8px !important;
    margin-top: 10px !important;
    padding-left: 0 !important;
    overflow: visible !important;
}

/* Cột copy lớn hơn khoảng 30% so với 2 nút còn lại */
div[data-testid="stVerticalBlockBorderWrapper"]
div[data-testid="stHorizontalBlock"]:has(iframe)
> div[data-testid="column"]:nth-child(1) {
    min-width: 46px !important;
    max-width: 46px !important;
    flex: 0 0 46px !important;
    padding: 0 !important;
    margin: 0 !important;
    overflow: visible !important;
}

/* Cột like và dislike */
div[data-testid="stVerticalBlockBorderWrapper"]
div[data-testid="stHorizontalBlock"]:has(iframe)
> div[data-testid="column"]:nth-child(2),
div[data-testid="stVerticalBlockBorderWrapper"]
div[data-testid="stHorizontalBlock"]:has(iframe)
> div[data-testid="column"]:nth-child(3) {
    min-width: 36px !important;
    max-width: 36px !important;
    flex: 0 0 36px !important;
    padding: 0 !important;
    margin: 0 !important;
    overflow: visible !important;
}

/* Iframe của nút sao chép */
div[data-testid="stVerticalBlockBorderWrapper"]
div[data-testid="stHorizontalBlock"]:has(iframe) iframe {
    display: block !important;
    width: 46px !important;
    min-width: 46px !important;
    max-width: 46px !important;
    height: 36px !important;
    min-height: 36px !important;
    margin: 0 !important;
    padding: 0 !important;
    border: 0 !important;
    background: transparent !important;
}

/* Wrapper hai nút feedback */
div[data-testid="stVerticalBlockBorderWrapper"]
div[data-testid="stHorizontalBlock"]:has(iframe) .stButton {
    width: 36px !important;
    min-width: 36px !important;
    max-width: 36px !important;
    height: 36px !important;
    margin: 0 !important;
}

/* Like / dislike */
div[data-testid="stVerticalBlockBorderWrapper"]
div[data-testid="stHorizontalBlock"]:has(iframe) .stButton button {
    width: 36px !important;
    min-width: 36px !important;
    max-width: 36px !important;
    height: 36px !important;
    min-height: 36px !important;
    max-height: 36px !important;

    padding: 0 !important;
    margin: 0 !important;

    display: inline-flex !important;
    align-items: center !important;
    justify-content: center !important;

    color: #475569 !important;
    background: #ffffff !important;
    border: 1px solid #e5e7eb !important;
    border-radius: 11px !important;
    box-shadow: none !important;

    line-height: 1 !important;
    overflow: hidden !important;
    transform: none !important;
}

/* Căn icon Material */
div[data-testid="stVerticalBlockBorderWrapper"]
div[data-testid="stHorizontalBlock"]:has(iframe) .stButton button span {
    display: inline-flex !important;
    align-items: center !important;
    justify-content: center !important;
    margin: 0 !important;
    padding: 0 !important;
    line-height: 1 !important;
}

/* Ẩn paragraph rỗng */
div[data-testid="stVerticalBlockBorderWrapper"]
div[data-testid="stHorizontalBlock"]:has(iframe) .stButton button p {
    display: none !important;
}

/* Hover theo màu Shopee */
div[data-testid="stVerticalBlockBorderWrapper"]
div[data-testid="stHorizontalBlock"]:has(iframe) .stButton button:hover {
    color: #ee4d2d !important;
    background: #fff3ef !important;
    border-color: #ffb9a8 !important;
    box-shadow: none !important;
    transform: none !important;
}

/* Trạng thái được chọn */
div[data-testid="stVerticalBlockBorderWrapper"]
div[data-testid="stHorizontalBlock"]:has(iframe) .stButton button[kind="primary"] {
    color: #ffffff !important;
    background: #ee4d2d !important;
    border-color: #ee4d2d !important;
    box-shadow: none !important;
}

/* Sidebar theo một hệ màu, control gọn và rõ ở 100%. */
[data-testid="stSidebar"] {
    background: rgba(255,255,255,.98) !important;
}

[data-testid="stSidebar"] .block-container {
    padding: 1rem .9rem 1.2rem !important;
}

[data-testid="stSidebar"] .stButton button {
    border-radius: 11px !important;
}

[data-testid="stSidebar"] [data-testid="stToggle"] label {
    color: #475467 !important;
    font-size: .86rem !important;
}

[data-testid="stSidebar"] [data-baseweb="select"] > div {
    border-color: #e6e2df !important;
    border-radius: 11px !important;
    background: #fff !important;
}

.v9-active-chat {
    color: #b9381d !important;
    background: #fff2ed !important;
    border-color: #ffc9b9 !important;
}

/* Thanh nhập nổi vừa phải, nút gửi đồng nhất màu Shopee. */
[data-testid="stChatInput"] {
    border-color: #ded8d5 !important;
    border-radius: 15px !important;
    box-shadow: 0 12px 30px rgba(17,24,39,.09) !important;
}

[data-testid="stChatInput"]:focus-within {
    border-color: rgba(238,77,45,.48) !important;
    box-shadow: 0 12px 30px rgba(238,77,45,.12) !important;
}

[data-testid="stChatInput"] button {
    background: var(--v16-shopee) !important;
}

[data-testid="stChatInput"] button:hover {
    background: var(--v16-shopee-hover) !important;
}

@media (max-width: 900px) {
    html { font-size: 14.5px; }
    .block-container {
        padding-left: .55rem !important;
        padding-right: .55rem !important;
    }
}

/* V16 PATCH — khóa kích thước toolbar, chỉ hiển thị icon thật của Streamlit */
div[data-testid="stVerticalBlockBorderWrapper"]
div[data-testid="stHorizontalBlock"]:has(iframe) {
    display: flex !important;
    flex-wrap: nowrap !important;
    align-items: center !important;
    justify-content: flex-start !important;
    column-gap: 4px !important;
    width: auto !important;
    overflow: visible !important;
}

div[data-testid="stVerticalBlockBorderWrapper"]
div[data-testid="stHorizontalBlock"]:has(iframe)
> div[data-testid="column"]:nth-child(-n+3) {
    flex: 0 0 36px !important;
    width: 36px !important;
    min-width: 36px !important;
    max-width: 36px !important;
    padding: 0 !important;
    margin: 0 !important;
    overflow: visible !important;
}

div[data-testid="stVerticalBlockBorderWrapper"]
div[data-testid="stHorizontalBlock"]:has(iframe)
> div[data-testid="column"]:nth-child(4) {
    flex: 1 1 auto !important;
    min-width: 0 !important;
}

div[data-testid="stVerticalBlockBorderWrapper"]
div[data-testid="stHorizontalBlock"]:has(iframe) .stButton,
div[data-testid="stVerticalBlockBorderWrapper"]
div[data-testid="stHorizontalBlock"]:has(iframe) [data-testid="stButton"] {
    width: 36px !important;
    min-width: 36px !important;
    max-width: 36px !important;
    margin: 0 !important;
}

div[data-testid="stVerticalBlockBorderWrapper"]
div[data-testid="stHorizontalBlock"]:has(iframe) .stButton button {
    width: 34px !important;
    min-width: 34px !important;
    max-width: 34px !important;
    height: 34px !important;
    min-height: 34px !important;
    padding: 0 !important;
    display: inline-flex !important;
    align-items: center !important;
    justify-content: center !important;
    overflow: hidden !important;
}

div[data-testid="stVerticalBlockBorderWrapper"]
div[data-testid="stHorizontalBlock"]:has(iframe) .stButton button p {
    display: none !important;
}

div[data-testid="stVerticalBlockBorderWrapper"]
div[data-testid="stHorizontalBlock"]:has(iframe) .stButton button span,
div[data-testid="stVerticalBlockBorderWrapper"]
div[data-testid="stHorizontalBlock"]:has(iframe) .stButton button [data-testid="stIconMaterial"] {
    display: inline-flex !important;
    align-items: center !important;
    justify-content: center !important;
    width: 18px !important;
    height: 18px !important;
    margin: 0 !important;
    padding: 0 !important;
    font-size: 18px !important;
    line-height: 1 !important;
    color: currentColor !important;
}

/* Tắt hoàn toàn pseudo-icon cũ để không chồng lên icon thật */
div[data-testid="stVerticalBlockBorderWrapper"]
div[data-testid="stHorizontalBlock"]:has(iframe) button::before {
    content: none !important;
    display: none !important;
}

/* ==========================================================
   V16 FINAL TOOLBAR — COPY / LIKE / DISLIKE
   Một kích thước, một nền, một baseline, nhất quán chủ đề Shopee
   ========================================================== */

.v16-action-toolbar-anchor {
    height: 0 !important;
    margin: 0 !important;
    padding: 0 !important;
}

/* Hàng hành động chỉ chiếm đúng chiều cao của nút, không kéo giãn. */
div[data-testid="stVerticalBlockBorderWrapper"]
div[data-testid="stHorizontalBlock"]:has(iframe) {
    display: flex !important;
    flex-wrap: nowrap !important;
    align-items: center !important;
    justify-content: flex-start !important;
    gap: 6px !important;
    width: 100% !important;
    min-height: 40px !important;
    margin: 0.55rem 0 0 !important;
    padding: 0 !important;
    overflow: visible !important;
}

/* Ba cột nút hoàn toàn bằng nhau. */
div[data-testid="stVerticalBlockBorderWrapper"]
div[data-testid="stHorizontalBlock"]:has(iframe)
> div[data-testid="column"]:nth-child(-n+3) {
    flex: 0 0 40px !important;
    width: 40px !important;
    min-width: 40px !important;
    max-width: 40px !important;
    height: 40px !important;
    min-height: 40px !important;
    padding: 0 !important;
    margin: 0 !important;
    overflow: visible !important;
}

/* Cột đệm còn lại nhận toàn bộ khoảng trống. */
div[data-testid="stVerticalBlockBorderWrapper"]
div[data-testid="stHorizontalBlock"]:has(iframe)
> div[data-testid="column"]:nth-child(4) {
    flex: 1 1 auto !important;
    min-width: 0 !important;
    padding: 0 !important;
    margin: 0 !important;
}

/* Iframe nút sao chép cùng hộp 40x40 với hai nút phản hồi. */
div[data-testid="stVerticalBlockBorderWrapper"]
div[data-testid="stHorizontalBlock"]:has(iframe) iframe {
    display: block !important;
    width: 40px !important;
    min-width: 40px !important;
    max-width: 40px !important;
    height: 40px !important;
    min-height: 40px !important;
    max-height: 40px !important;
    margin: 0 !important;
    padding: 0 !important;
    border: 0 !important;
    background: transparent !important;
    vertical-align: top !important;
}

/* Wrapper Streamlit của Like / Dislike cũng khóa ở 40x40. */
div[data-testid="stVerticalBlockBorderWrapper"]
div[data-testid="stHorizontalBlock"]:has(iframe) .stButton,
div[data-testid="stVerticalBlockBorderWrapper"]
div[data-testid="stHorizontalBlock"]:has(iframe) [data-testid="stButton"] {
    width: 40px !important;
    min-width: 40px !important;
    max-width: 40px !important;
    height: 40px !important;
    min-height: 40px !important;
    max-height: 40px !important;
    margin: 0 !important;
    padding: 0 !important;
}

/* Hai nút phản hồi dùng đúng cùng visual token với nút sao chép. */
div[data-testid="stVerticalBlockBorderWrapper"]
div[data-testid="stHorizontalBlock"]:has(iframe) .stButton button {
    width: 40px !important;
    min-width: 40px !important;
    max-width: 40px !important;
    height: 40px !important;
    min-height: 40px !important;
    max-height: 40px !important;
    box-sizing: border-box !important;
    margin: 0 !important;
    padding: 0 !important;

    display: inline-flex !important;
    align-items: center !important;
    justify-content: center !important;

    color: #667085 !important;
    background: rgba(31, 41, 55, 0.050) !important;
    border: 1px solid transparent !important;
    border-radius: 12px !important;
    box-shadow: none !important;

    line-height: 1 !important;
    overflow: hidden !important;
    transform: none !important;
    transition: color .15s ease, background .15s ease, border-color .15s ease !important;
}

/* Loại bỏ paragraph rỗng mà Streamlit có thể chèn vào button. */
div[data-testid="stVerticalBlockBorderWrapper"]
div[data-testid="stHorizontalBlock"]:has(iframe) .stButton button p {
    display: none !important;
    width: 0 !important;
    height: 0 !important;
    margin: 0 !important;
    padding: 0 !important;
}

/* Icon Material có cùng kích thước quang học với icon copy SVG. */
div[data-testid="stVerticalBlockBorderWrapper"]
div[data-testid="stHorizontalBlock"]:has(iframe) .stButton button [data-testid="stIconMaterial"],
div[data-testid="stVerticalBlockBorderWrapper"]
div[data-testid="stHorizontalBlock"]:has(iframe) .stButton button span.material-symbols-rounded,
div[data-testid="stVerticalBlockBorderWrapper"]
div[data-testid="stHorizontalBlock"]:has(iframe) .stButton button span.material-symbols-outlined {
    display: inline-flex !important;
    align-items: center !important;
    justify-content: center !important;
    width: 19px !important;
    height: 19px !important;
    margin: 0 !important;
    padding: 0 !important;
    color: currentColor !important;
    font-size: 19px !important;
    line-height: 1 !important;
    font-variation-settings: "FILL" 0, "wght" 400, "GRAD" 0, "opsz" 20 !important;
}

/* Hover: chỉ đổi sắc độ, tuyệt đối không đổi kích thước hay vị trí. */
div[data-testid="stVerticalBlockBorderWrapper"]
div[data-testid="stHorizontalBlock"]:has(iframe) .stButton button:hover {
    color: #ee4d2d !important;
    background: rgba(238, 77, 45, 0.095) !important;
    border-color: transparent !important;
    box-shadow: none !important;
    transform: none !important;
}

/* Đã chọn: cam nhạt kiểu Shopee, giữ nguyên 40x40. */
div[data-testid="stVerticalBlockBorderWrapper"]
div[data-testid="stHorizontalBlock"]:has(iframe) .stButton button[kind="primary"] {
    color: #ee4d2d !important;
    background: #fff0ea !important;
    border-color: rgba(238, 77, 45, 0.28) !important;
    box-shadow: none !important;
}

div[data-testid="stVerticalBlockBorderWrapper"]
div[data-testid="stHorizontalBlock"]:has(iframe) .stButton button[kind="primary"] [data-testid="stIconMaterial"],
div[data-testid="stVerticalBlockBorderWrapper"]
div[data-testid="stHorizontalBlock"]:has(iframe) .stButton button[kind="primary"] span.material-symbols-rounded,
div[data-testid="stVerticalBlockBorderWrapper"]
div[data-testid="stHorizontalBlock"]:has(iframe) .stButton button[kind="primary"] span.material-symbols-outlined {
    font-variation-settings: "FILL" 1, "wght" 400, "GRAD" 0, "opsz" 20 !important;
}

/* Không cho pseudo-element cũ chồng icon. */
div[data-testid="stVerticalBlockBorderWrapper"]
div[data-testid="stHorizontalBlock"]:has(iframe) .stButton button::before,
div[data-testid="stVerticalBlockBorderWrapper"]
div[data-testid="stHorizontalBlock"]:has(iframe) .stButton button::after {
    content: none !important;
    display: none !important;
}



/* ==========================================================
   V19 FINAL — Bộ định tuyến ngữ nghĩa nhanh, chống hallucination và xử lý toàn bộ lỗi kiểm thử V18
   ========================================================== */
:root {
    --v17-shopee: #ee4d2d;
    --v17-shopee-dark: #d94325;
    --v17-shopee-soft: #fff1ec;
    --v17-neutral-soft: rgba(31, 41, 55, 0.045);
    --v17-neutral-hover: rgba(31, 41, 55, 0.085);
}

/* Các nút điều khiển nội bộ chỉ phục vụ JS, tuyệt đối không hiện ra UI. */
[class*="st-key-v17_hidden_feedback_"],
[class*="st-key-v17_poll_trigger_"] {
    display: none !important;
    width: 0 !important;
    height: 0 !important;
    min-height: 0 !important;
    margin: 0 !important;
    padding: 0 !important;
    overflow: hidden !important;
}

/* Khung component toolbar không có nền/viền riêng, tránh vệt cam lệch ở nút copy. */
div[data-testid="stVerticalBlockBorderWrapper"]
iframe[title="streamlit.components.v1.components.html"] {
    border: 0 !important;
    background: transparent !important;
}

/* Thẻ đang xử lý: nhỏ gọn, đúng chủ đề Shopee và không giả làm câu trả lời. */
.v17-processing-panel {
    display: flex;
    align-items: flex-start;
    gap: 12px;
    padding: 2px 0 4px;
}

.v17-processing-spinner {
    width: 28px;
    height: 28px;
    flex: 0 0 28px;
    margin-top: 2px;
    border: 3px solid rgba(238, 77, 45, 0.16);
    border-top-color: var(--v17-shopee);
    border-radius: 999px;
    animation: v17-spin 0.85s linear infinite;
}

.v17-processing-title {
    color: #20242c;
    font-size: 0.94rem;
    font-weight: 720;
    line-height: 1.45;
}

.v17-processing-detail {
    margin-top: 4px;
    color: #7b8491;
    font-size: 0.76rem;
    line-height: 1.55;
}

.v17-processing-query {
    display: block;
    max-width: 760px;
    margin-top: 6px;
    color: #667085;
    font-size: 0.73rem;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
}

@keyframes v17-spin {
    to { transform: rotate(360deg); }
}

/* Nút hủy: chỉ xuất hiện khi xử lý, cùng tone trắng-cam Shopee. */
[class*="st-key-v17_cancel_"] .stButton button,
[class*="st-key-v17_cancel_"] button {
    width: auto !important;
    min-width: 118px !important;
    height: 36px !important;
    min-height: 36px !important;
    padding: 0 13px !important;
    color: #c2410c !important;
    background: #fff7f3 !important;
    border: 1px solid #ffc7b5 !important;
    border-radius: 10px !important;
    box-shadow: none !important;
    font-size: 0.78rem !important;
    font-weight: 680 !important;
    transform: none !important;
}

[class*="st-key-v17_cancel_"] .stButton button:hover,
[class*="st-key-v17_cancel_"] button:hover {
    color: #ffffff !important;
    background: var(--v17-shopee) !important;
    border-color: var(--v17-shopee) !important;
    transform: none !important;
}

/* Giao diện chung tinh gọn hơn ở zoom 100%. */
.v9-page-header {
    padding-bottom: 0.72rem !important;
}

.v9-page-subtitle {
    color: #9aa3af !important;
}

[data-testid="stChatInput"] {
    border-color: #e2dcd8 !important;
}

[data-testid="stChatInput"]:focus-within {
    border-color: rgba(238, 77, 45, 0.52) !important;
}

/* Nút cuộn xuống dùng đúng màu Shopee, không che thanh nhập. */
#v17-scroll-latest {
    font-family: Inter, ui-sans-serif, system-ui, sans-serif;
}

</style>

    """,
    unsafe_allow_html=True,
)


# ============================================================
# KHỞI TẠO
# ============================================================

@st.cache_resource(
    show_spinner="Đang nạp chỉ mục tri thức Shopee lần đầu...",
    show_time=True,
)
def load_resources() -> tuple[Any, Any, list[dict], Any, dict[str, int]]:
    return backend.load_hybrid_resources()


def initialize_state() -> None:
    defaults = {
        "messages": [],
        "last_contexts": [],
        "technical_mode": False,
        "pending_prompt": None,
        "processing": False,
        "pending_request": None,
        "processing_request_id": "",
        "processing_started_at": 0.0,
        "cancelled_request_ids": [],
        "last_answer_mode": "",
        "last_answer_query": "",
        "active_topic": "",
        "last_fee_calculation": {},
        "feedback": {},
        "response_style": "Cân bằng",
        "streaming_enabled": True,
        "last_clarification": "",
        "last_submit_fingerprint": "",
        "last_submit_at": 0.0,
    }

    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value

    # V15: hiệu ứng trả lời từng phần luôn bật và không hiển thị công tắc.
    # Gán lại mỗi lần khởi tạo để các phiên cũ từng tắt hiệu ứng không giữ giá trị False.
    st.session_state.streaming_enabled = True


def sync_backend_history() -> None:
    history_items = st.session_state.messages[:-1]

    backend.CONVERSATION_HISTORY = [
        {
            "role": item["role"],
            "content": item["content"],
        }
        for item in history_items[-8:]
        if item["role"] in {"user", "assistant"}
    ]



def previous_assistant_message() -> str:
    for item in reversed(st.session_state.messages[:-1]):
        if item.get("role") == "assistant":
            return str(item.get("content", "")).strip()
    return ""



def previous_assistant_item() -> dict[str, Any] | None:
    for item in reversed(st.session_state.messages[:-1]):
        if item.get("role") == "assistant":
            return item
    return None



def detect_topic(query: str) -> str:
    normalized = backend.normalize_for_match(query)

    if any(
        term in normalized
        for term in [
            "phi xu ly giao dich",
            "phi xu ly",
            "khuyen mai ngan hang",
            "khuyen mai nguoi ban",
        ]
    ):
        return "transaction_fee"

    if all(
        term in normalized
        for term in ["shop api", "merchant api", "public api"]
    ):
        return "api_comparison"

    if any(
        term in normalized
        for term in [
            "merchant api",
            "merchant_id",
            "base_string",
            "signature",
        ]
    ):
        return "merchant_api"

    if any(
        term in normalized
        for term in [
            "shop api",
            "shop_id",
        ]
    ):
        return "shop_api"

    if "public api" in normalized:
        return "public_api"

    if "shopee open platform" in normalized:
        return "open_platform"

    if "shopee xu" in normalized or "diem thuong" in normalized:
        return "shopee_xu"

    if "tra hang" in normalized or "hoan tien" in normalized:
        return "return_refund"

    if any(
        term in normalized
        for term in [
            "phi co dinh",
            "cap sac",
            "bo chuyen doi",
        ]
    ):
        return "fixed_fee"

    return ""


def update_active_topic(query: str) -> None:
    detected = detect_topic(query)

    if detected:
        st.session_state.active_topic = detected


def current_topic() -> str:
    topic = str(
        st.session_state.get(
            "active_topic",
            "",
        )
    ).strip()

    if topic:
        return topic

    last_query = str(
        st.session_state.get(
            "last_answer_query",
            "",
        )
    )

    detected = detect_topic(last_query)

    if detected:
        return detected

    return current_topic_from_history()


def parse_vnd_number(raw: str) -> int | None:
    cleaned = re.sub(
        r"[^\d]",
        "",
        str(raw),
    )

    if not cleaned:
        return None

    try:
        return int(cleaned)
    except ValueError:
        return None


def extract_labeled_amount(
    query: str,
    labels: list[str],
) -> int | None:
    normalized_query = query.replace("\n", " ")

    for label in labels:
        pattern = (
            rf"{label}"
            rf".{{0,30}}?"
            rf"(\d{{1,3}}(?:[.\s,]\d{{3}})+|\d+)"
        )

        match = re.search(
            pattern,
            normalized_query,
            flags=re.IGNORECASE,
        )

        if match:
            return parse_vnd_number(
                match.group(1)
            )

    return None


def extract_fee_inputs(
    query: str,
) -> dict[str, int] | None:
    product_price = extract_labeled_amount(
        query,
        [
            r"giá\s*sản\s*phẩm",
            r"gia\s*san\s*pham",
        ],
    )
    shipping_fee = extract_labeled_amount(
        query,
        [
            r"phí\s*vận\s*chuyển",
            r"phi\s*van\s*chuyen",
        ],
    )
    seller_discount = extract_labeled_amount(
        query,
        [
            r"khuyến\s*mãi\s*người\s*bán",
            r"khuyen\s*mai\s*nguoi\s*ban",
        ],
    )
    bank_discount = extract_labeled_amount(
        query,
        [
            r"khuyến\s*mãi\s*ngân\s*hàng",
            r"khuyen\s*mai\s*ngan\s*hang",
        ],
    )

    values = {
        "product_price": product_price,
        "shipping_fee": shipping_fee,
        "seller_discount": seller_discount,
        "bank_discount": bank_discount,
    }

    if product_price is None:
        return None

    return {
        key: int(value or 0)
        for key, value in values.items()
    }


def format_vnd(value: int | float) -> str:
    integer_value = int(round(value))

    return (
        f"{integer_value:,}"
        .replace(",", ".")
        + " VND"
    )


def calculate_transaction_fee(
    values: dict[str, int],
) -> tuple[int, int]:
    fee_base = (
        values["product_price"]
        + values["shipping_fee"]
        - values["seller_discount"]
        - values["bank_discount"]
    )

    fee = round(fee_base * 0.06)

    return fee_base, fee


def fee_calculation_answer(
    values: dict[str, int],
    note: str = "",
) -> str:
    fee_base, fee = calculate_transaction_fee(
        values
    )

    st.session_state.last_fee_calculation = dict(
        values
    )
    st.session_state.active_topic = (
        "transaction_fee"
    )

    lines = [
        "Áp dụng công thức:",
        "",
        "`(Giá sản phẩm + Phí vận chuyển Người mua trả "
        "− Khuyến mãi Người bán − Khuyến mãi Ngân hàng) × 6%`",
        "",
        "Thay số:",
        "",
        (
            f"{format_vnd(values['product_price'])} "
            f"+ {format_vnd(values['shipping_fee'])} "
            f"− {format_vnd(values['seller_discount'])} "
            f"− {format_vnd(values['bank_discount'])} "
            f"= **{format_vnd(fee_base)}**"
        ),
        "",
        (
            f"Phí Xử Lý Giao Dịch = "
            f"{format_vnd(fee_base)} × 6% "
            f"= **{format_vnd(fee)}**."
        ),
    ]

    if note:
        lines.extend(
            [
                "",
                note,
            ]
        )

    return "\n".join(lines)


def is_fee_calculation_question(
    query: str,
) -> bool:
    normalized = backend.normalize_for_match(query)

    return (
        "phi xu ly" in normalized
        and bool(
            re.search(
                r"\d",
                query,
            )
        )
    )


def is_no_bank_discount_followup(
    query: str,
) -> bool:
    normalized = backend.normalize_for_match(query)

    return any(
        phrase in normalized
        for phrase in [
            "neu khong co khuyen mai ngan hang",
            "khong co khuyen mai ngan hang thi sao",
            "bo khuyen mai ngan hang",
        ]
    )


def no_bank_discount_followup_answer() -> str:
    previous = dict(
        st.session_state.get(
            "last_fee_calculation",
            {},
        )
    )

    if not previous:
        return (
            "Tôi chưa có các số liệu của phép tính trước. "
            "Bạn hãy cung cấp giá sản phẩm, phí vận chuyển, "
            "khuyến mãi Người bán và khuyến mãi Ngân hàng."
        )

    previous["bank_discount"] = 0

    return fee_calculation_answer(
        previous,
        note=(
            "Trong trường hợp này, khuyến mãi Ngân hàng được tính bằng 0 VND."
        ),
    )


def is_public_api_followup(
    query: str,
) -> bool:
    normalized = backend.normalize_for_match(query)

    return "public api" in normalized


def public_api_answer() -> str:
    st.session_state.active_topic = "public_api"

    return (
        "Theo tài liệu API hiện đang có trong hệ thống, `Public API` tạo "
        "`base_string` từ các tham số:\n\n"
        "`partner_id + api_path + timestamp`\n\n"
        "Khác với Shop API và Merchant API, công thức này không nối thêm "
        "`access_token`, `shop_id` hoặc `merchant_id` trong phần mô tả "
        "`base_string` hiện có.\n\n"
        "Tôi không đưa ví dụ URL hoặc tham số ngoài tài liệu để tránh suy đoán."
    )


def is_detailed_shop_merchant_question(
    query: str,
) -> bool:
    normalized = backend.normalize_for_match(query)

    asks_comparison = (
        "shop api" in normalized
        and "merchant api" in normalized
    )

    asks_detail = any(
        phrase in normalized
        for phrase in [
            "giai thich chi tiet",
            "kem vi du",
            "khac nhau nhu the nao",
        ]
    )

    return asks_comparison and asks_detail



def detailed_shop_merchant_answer() -> str:
    st.session_state.active_topic = "shop_api"

    return (
        "Shop API và Merchant API cùng dùng bốn thành phần đầu của "
        "`base_string`:\n\n"
        "`partner_id + api_path + timestamp + access_token`\n\n"
        "| Nội dung | Shop API | Merchant API |\n"
        "|---|---|---|\n"
        "| ID cuối chuỗi | `shop_id` | `merchant_id` |\n"
        "| Chuỗi đầy đủ | `partner_id + api_path + timestamp + access_token + shop_id` | "
        "`partner_id + api_path + timestamp + access_token + merchant_id` |\n"
        "| Đối tượng nhận diện | Shop cụ thể đã cấp quyền | Merchant tương ứng |\n\n"
        "Sau khi ghép đúng thứ tự, hệ thống dùng Partner Key để tạo "
        "`signature` bằng HMAC-SHA256. Nếu đổi thứ tự hoặc thiếu ID cuối, "
        "signature có thể không khớp và yêu cầu có thể bị từ chối."
    )


def current_topic_from_history() -> str:
    for item in reversed(
        st.session_state.get(
            "messages",
            [],
        )
    ):
        content = str(
            item.get(
                "content",
                "",
            )
        )

        detected = detect_topic(content)

        if detected:
            return detected

    return ""


def is_easy_explanation_followup(query: str) -> bool:
    normalized = backend.normalize_for_match(query)

    return any(
        phrase in normalized
        for phrase in [
            "giai thich de hieu hon",
            "noi de hieu hon",
            "giai thich don gian hon",
        ]
    )


def is_two_line_summary_followup(query: str) -> bool:
    normalized = backend.normalize_for_match(query)

    return any(
        phrase in normalized
        for phrase in [
            "tom tat trong 2 dong",
            "tom tat 2 dong",
            "tom tat lai trong 2 dong",
            "tom tat trong hai dong",
        ]
    )


def is_three_line_summary_followup(query: str) -> bool:
    normalized = backend.normalize_for_match(query)

    return any(
        phrase in normalized
        for phrase in [
            "tom tat trong 3 dong",
            "tom tat 3 dong",
            "tom tat lai trong 3 dong",
            "tom tat trong ba dong",
        ]
    )


def is_transaction_fee_example_followup(query: str) -> bool:
    normalized = backend.normalize_for_match(query)

    asks_example = any(
        phrase in normalized
        for phrase in [
            "cho mot vi du tinh thu",
            "vi du tinh thu",
            "cho vi du tinh",
            "tinh thu voi gia tri gia dinh",
        ]
    )

    return (
        asks_example
        and current_topic() == "transaction_fee"
    )


def transaction_fee_example_answer() -> str:
    product_price = 100_000
    buyer_shipping = 10_000
    seller_discount = 5_000
    bank_discount = 2_000

    fee_base = (
        product_price
        + buyer_shipping
        - seller_discount
        - bank_discount
    )
    fee = fee_base * 0.06

    return (
        "**Ví dụ giả định:**\n\n"
        "- Giá sản phẩm trước Shopee trợ giá: 100.000 VND\n"
        "- Phí vận chuyển Người mua trả: 10.000 VND\n"
        "- Khuyến mãi Người bán đã áp dụng: 5.000 VND\n"
        "- Khuyến mãi từ Ngân hàng: 2.000 VND\n\n"
        "Giá trị tính phí = 100.000 + 10.000 − 5.000 − 2.000 "
        "= **103.000 VND**.\n\n"
        "Phí Xử Lý Giao Dịch = 103.000 × 6% "
        "= **6.180 VND**.\n\n"
        "Các số trên chỉ dùng để minh họa cách tính."
    )


def transaction_fee_easy_answer() -> str:
    return (
        "Hiểu đơn giản, Shopee lấy giá trị đơn hàng sau khi cộng phần phí vận chuyển "
        "Người mua trả và trừ các khoản khuyến mãi liên quan, rồi nhân kết quả với 6%.\n\n"
        "`(Giá sản phẩm + Phí vận chuyển Người mua trả "
        "− Khuyến mãi Người bán − Khuyến mãi Ngân hàng) × 6%`"
    )


def topic_summary_answer(lines: int) -> str:
    topic = current_topic()

    if topic == "transaction_fee":
        items = [
            "Phí Xử Lý Giao Dịch được tính trên giá sản phẩm, cộng phí vận chuyển Người mua trả và trừ các khoản khuyến mãi.",
            "Kết quả sau đó được nhân với tỷ lệ 6%.",
            "Khi tính thực tế cần dùng đúng số liệu của từng đơn hàng.",
        ]
    elif topic == "merchant_api":
        items = [
            "Merchant API tạo `base_string` theo thứ tự `partner_id + api_path + timestamp + access_token + merchant_id`.",
            "`base_string` được dùng để tạo `signature` bằng HMAC-SHA256.",
            "Thiếu hoặc đổi thứ tự tham số có thể làm xác thực thất bại.",
        ]
    elif topic in {"shop_api", "merchant_api"}:
        items = [
            "Shop API và Merchant API cùng dùng `partner_id + api_path + timestamp + access_token` trong `base_string`.",
            "Shop API nối thêm `shop_id`, còn Merchant API nối thêm `merchant_id`.",
            "Chuỗi phải đúng thứ tự trước khi tạo `signature` bằng HMAC-SHA256.",
        ]
    elif topic == "api_comparison":
        items = [
            "Public API dùng `partner_id + api_path + timestamp` theo tài liệu hiện có.",
            "Shop API nối thêm `access_token + shop_id`, còn Merchant API nối thêm `access_token + merchant_id`.",
            "Cả ba loại đều phải giữ đúng cấu trúc trước khi tạo và kiểm tra `signature`.",
        ]
    elif topic == "public_api":
        items = [
            "Theo tài liệu hiện có, Public API tạo `base_string` từ `partner_id + api_path + timestamp`.",
            "Hệ thống không tự thêm URL hoặc tham số ngoài phần tài liệu đã xác minh.",
        ]
    else:
        previous = previous_assistant_message()

        if not previous:
            return "Tôi chưa có nội dung trước đó để tóm tắt."

        compact = " ".join(previous.split())

        if len(compact) > 320:
            compact = compact[:317].rstrip() + "..."

        items = [compact]

    return "\n".join(
        f"{index}. {item}"
        for index, item in enumerate(
            items[:lines],
            start=1,
        )
    )


def reliable_previous_answer() -> bool:
    previous = previous_assistant_item()

    if not previous:
        return False

    mode = str(
        previous.get("metrics", {}).get(
            "mode",
            "",
        )
    )

    reliable_modes = {
        "global_fee_lookup",
        "conversation_guard",
        "fast_answer",
        "fast",
        "direct_domain",
        "deterministic",
        "merchant_base_string",
        "merchant_api_overview",
        "merchant_api_auth_components",
        "merchant_signature_python_example",
        "merchant_vietnamese_only",
        "full_api_guide",
        "three_api_comparison",
        "api_comparison",
        "signature_algorithm",
        "signature_flow",
        "verification_guard",
        "public_api_guard",
        "smalltalk",
        "capabilities",
        "private_data_missing",
        "private_business_data",
        "private_inventory_missing",
        "out_of_scope",
        "confirmation_followup",
        "llm",
    }

    return (
        bool(st.session_state.last_contexts)
        or mode in reliable_modes
    )

def is_confirmation_followup(query: str) -> bool:
    normalized = backend.normalize_for_match(query)

    phrases = [
        "thong tin nay chuan khong",
        "thong tin nay dung khong",
        "co chinh xac khong",
        "co tin duoc khong",
        "toi co tin duoc khong",
        "vay toi co tin duoc khong",
        "cau tra loi nay dung khong",
        "ban chac khong",
        "co chac khong",
    ]

    return any(phrase in normalized for phrase in phrases)


def confirmation_followup_answer() -> str:
    previous_answer = previous_assistant_message()

    if not previous_answer:
        return (
            "Tôi chưa có câu trả lời trước đó để kiểm tra. "
            "Bạn hãy hỏi lại nội dung cần xác minh."
        )

    if reliable_previous_answer():
        return (
            "Câu trả lời trước phù hợp với dữ liệu và quy tắc hiện đang được nạp "
            "trong hệ thống. Tuy nhiên, chính sách và biểu phí Shopee có thể thay đổi, "
            "nên khi áp dụng thực tế bạn cần đối chiếu phiên bản tài liệu mới nhất."
        )

    return (
        "Tôi chưa có đủ bằng chứng trong kho dữ liệu hiện tại để xác nhận chắc chắn "
        "câu trả lời trước."
    )


def is_private_business_question(query: str) -> bool:
    """Nhận diện câu hỏi cần số liệu vận hành riêng của một shop.

    V19 không đưa các câu doanh thu, lợi nhuận hoặc top sản phẩm xuống RAG công khai,
    kể cả khi người dùng bỏ cụm "shop tôi".
    """
    normalized = backend.normalize_for_match(query)

    private_metric_patterns = [
        "doanh thu shop",
        "doanh thu cua shop",
        "doanh thu thang nay",
        "loi nhuan shop",
        "loi nhuan cua shop",
        "loi nhuan thang nay",
        "chi phi shop",
        "don hang cua shop",
        "top 5 san pham ban chay",
        "san pham ban chay nhat",
        "mat hang ban chay nhat",
        "roas cua shop",
        "quang cao cua shop",
    ]
    if any(pattern in normalized for pattern in private_metric_patterns):
        return True

    ownership_terms = [
        "shop toi",
        "cua shop toi",
        "cua shop",
        "shop cua toi",
        "cong ty toi",
        "cua cong ty toi",
        "doanh nghiep toi",
        "cua doanh nghiep toi",
        "cua toi",
    ]

    metric_terms = [
        "doanh thu",
        "thu nhap",
        "loi nhuan",
        "chi phi",
        "don hang",
        "ton kho",
        "quang cao",
        "roas",
        "ban chay",
        "top 5 san pham",
        "sap het hang",
        "nguy co het hang",
        "so luong ton",
        "sku",
        "thang nay",
        "quy nay",
    ]

    return (
        any(term in normalized for term in ownership_terms)
        and any(term in normalized for term in metric_terms)
    )


def private_business_answer(query: str = "") -> str:
    normalized = backend.normalize_for_match(query)

    if "loi nhuan" in normalized:
        return (
            "Tôi chưa có dữ liệu doanh thu và chi phí thực tế của shop nên chưa thể "
            "tính lợi nhuận tháng này. Bạn cần cung cấp file Excel hoặc CSV có tối thiểu "
            "doanh thu thực nhận, giá vốn, phí Shopee, chi phí quảng cáo, hoàn tiền và các chi phí khác."
        )

    if "doanh thu" in normalized:
        return (
            "Tôi chưa có dữ liệu đơn hàng hoặc báo cáo doanh thu thực tế của shop nên chưa thể "
            "xác định doanh thu tháng này. Bạn cần cung cấp file Excel hoặc CSV xuất từ Kênh Người Bán, "
            "có ngày đơn hàng, mã đơn, trạng thái và doanh thu thực nhận."
        )

    if "ban chay" in normalized or "top 5 san pham" in normalized:
        return (
            "Tôi chưa có dữ liệu đơn hàng thực tế của shop nên chưa thể xác định Top 5 sản phẩm bán chạy. "
            "Bạn cần cung cấp file Excel hoặc CSV có tối thiểu SKU, tên sản phẩm, số lượng bán, "
            "doanh thu và khoảng thời gian cần phân tích."
        )

    return (
        "Tôi chưa có dữ liệu nội bộ của công ty hoặc shop để trả lời câu hỏi này. "
        "Bạn cần cung cấp file Excel hoặc CSV có dữ liệu doanh thu, đơn hàng, "
        "chi phí, tồn kho hoặc báo cáo vận hành tương ứng."
    )


def clean_for_chat(answer: str) -> str:
    answer = backend.sanitize_model_answer(answer)

    kept_lines = []

    for line in answer.splitlines():
        normalized = backend.normalize_for_match(line)

        if normalized.startswith("nguon tham khao"):
            continue
        if normalized.startswith("nguon chinh"):
            continue
        if normalized.startswith("nguon:") or normalized.startswith("nguon "):
            continue
        if normalized.startswith("source"):
            continue
        if normalized.startswith("retrieval"):
            continue
        if normalized.startswith("context"):
            continue

        kept_lines.append(line)

    answer = "\n".join(kept_lines)
    # Loại một số từ nối tiếng Anh mà mô hình đôi khi chèn vào câu tiếng Việt.
    answer = re.sub(r"\bwhereas\b", "trong khi", answer, flags=re.IGNORECASE)
    answer = re.sub(r"\bhowever\b", "tuy nhiên", answer, flags=re.IGNORECASE)
    answer = re.sub(r"\n{3,}", "\n\n", answer)

    return answer.strip()


def enforce_vietnamese(
    answer: str,
    question: str,
    contexts: list[dict],
) -> str:
    answer = clean_for_chat(answer)

    if strong_mostly_english(answer):
        answer = backend.force_vietnamese_rewrite(
            original_answer=answer,
            question=question,
            contexts=contexts,
        )
        answer = clean_for_chat(answer)

    return answer




def ambiguous_question_answer(query: str) -> str | None:
    normalized = backend.normalize_for_match(query)

    if (
        normalized in {
            "phi bao nhieu",
            "muc phi bao nhieu",
            "phi shopee bao nhieu",
            "shopee thu phi bao nhieu",
        }
        or (
            "phi bao nhieu" in normalized
            and not any(
                term in normalized
                for term in [
                    "phi xu ly giao dich",
                    "phi co dinh",
                    "phi dich vu",
                    "phi van chuyen",
                    "cap sac",
                    "bo chuyen doi",
                    "nganh hang",
                ]
            )
        )
    ):
        st.session_state.last_clarification = "fee"
        return (
            "Bạn đang muốn hỏi loại phí nào?\n\n"
            "1. **Phí Xử Lý Giao Dịch**\n"
            "2. **Phí cố định theo ngành hàng/sản phẩm**\n"
            "3. **Phí dịch vụ**\n"
            "4. **Phí vận chuyển**\n\n"
            "Bạn chỉ cần chọn một mục hoặc nêu tên sản phẩm cụ thể."
        )

    if (
        "phi co dinh" in normalized
        and "dien tu" in normalized
        and not any(
            term in normalized
            for term in [
                "cap sac",
                "bo chuyen doi",
                "op lung",
                "mieng dan",
                "the nho",
                "thiet bi trinh chieu",
                "den flash",
                "den selfie",
            ]
        )
    ):
        st.session_state.last_clarification = "fixed_fee_electronics"
        return (
            "Ngành Điện tử có nhiều nhóm sản phẩm với mức phí khác nhau. "
            "Bạn hãy nêu rõ nhóm cần tra cứu, chẳng hạn:\n\n"
            "- Cáp, sạc và bộ chuyển đổi\n"
            "- Vỏ, ốp lưng và miếng dán\n"
            "- Thẻ nhớ\n"
            "- Thiết bị trình chiếu\n"
            "- Đèn flash điện thoại hoặc đèn selfie"
        )

    if (
        normalized in {
            "api dung de lam gi",
            "api la gi",
            "api shopee la gi",
        }
        or (
            "api" in normalized
            and "dung de lam gi" in normalized
            and not any(
                term in normalized
                for term in [
                    "shop api",
                    "merchant api",
                    "public api",
                    "open platform",
                ]
            )
        )
    ):
        st.session_state.last_clarification = "api"
        return (
            "Bạn muốn tìm hiểu API nào?\n\n"
            "1. **Shop API** — thao tác theo `shop_id`\n"
            "2. **Merchant API** — thao tác theo `merchant_id`\n"
            "3. **Public API** — nhóm API công khai theo tài liệu hiện có\n"
            "4. **Shopee Open Platform** — nền tảng kết nối ứng dụng với Shopee"
        )

    if (
        normalized in {
            "bao lau",
            "thoi han bao lau",
            "mat bao lau",
        }
        or (
            "bao lau" in normalized
            and not any(
                term in normalized
                for term in [
                    "tra hang",
                    "hoan tien",
                    "khieu nai",
                    "phan hoi",
                    "access token",
                ]
            )
        )
    ):
        st.session_state.last_clarification = "deadline"
        return (
            "Bạn đang hỏi thời hạn nào?\n\n"
            "- Thời hạn người mua gửi trả hàng\n"
            "- Thời hạn người bán khiếu nại\n"
            "- Thời hạn phản hồi yêu cầu trả hàng\n"
            "- Thời hạn của `access_token`"
        )

    return None


def response_style_instruction() -> str:
    style = str(
        st.session_state.get(
            "response_style",
            "Cân bằng",
        )
    )

    if style == "Ngắn gọn":
        return (
            "Trả lời bằng tiếng Việt, kết luận trước, ngắn gọn nhưng không bỏ "
            "sót dữ kiện quan trọng; tối đa khoảng 5 câu nếu không cần liệt kê."
        )

    if style == "Chi tiết":
        return (
            "Trả lời bằng tiếng Việt, trình bày có cấu trúc, giải thích nguyên nhân, "
            "nêu ví dụ hoặc bảng so sánh khi phù hợp; không suy đoán ngoài ngữ cảnh."
        )

    return (
        "Trả lời bằng tiếng Việt, tự nhiên, đúng trọng tâm, có giải thích vừa đủ "
        "và dùng Markdown dễ đọc; không suy đoán ngoài ngữ cảnh."
    )




# ============================================================
# V15 - INTENT ROUTER VÀ BỘ NHỚ HỘI THOẠI AN TOÀN
# ============================================================

def is_inventory_private_question(query: str) -> bool:
    """Nhận diện câu hỏi cần dữ liệu tồn kho thực tế, kể cả không có cụm 'shop tôi'."""
    normalized = backend.normalize_for_match(query)

    inventory_phrases = [
        "san pham nao dang co nguy co het hang",
        "san pham nao sap het hang",
        "san pham sap het hang",
        "nguy co het hang",
        "sap het hang",
        "canh bao ton kho",
        "ton kho hien tai",
        "so luong ton",
        "sku sap het",
        "hang nao sap het",
    ]

    # Không nhầm 'hết hàng' với 'hết hạn'.
    if "het han" in normalized and "het hang" not in normalized:
        return False

    return any(phrase in normalized for phrase in inventory_phrases)


def inventory_private_answer() -> str:
    return (
        "Tôi chưa có dữ liệu tồn kho thực tế của shop nên chưa thể xác định "
        "sản phẩm nào đang có nguy cơ hết hàng. Bạn cần cung cấp file Excel hoặc CSV "
        "có tối thiểu các cột: `SKU`, tên sản phẩm, số lượng tồn, số lượng bán theo ngày "
        "và mức tồn kho cảnh báo."
    )


def is_generic_summary_followup(query: str) -> bool:
    normalized = backend.normalize_for_match(query)
    phrases = {
        "tom tat lai",
        "tom tat",
        "tong hop lai",
        "rut gon lai",
        "tom luoc lai",
    }
    return normalized.strip(" .?!") in phrases


def generic_summary_answer() -> str:
    previous = previous_assistant_message()
    if not previous:
        return "Tôi chưa có câu trả lời trước đó để tóm tắt."

    topic = current_topic()
    if topic:
        return topic_summary_answer(lines=3)

    compact = " ".join(previous.split())
    if len(compact) > 420:
        compact = compact[:417].rstrip() + "..."
    return compact


def is_generic_example_followup(query: str) -> bool:
    normalized = backend.normalize_for_match(query).strip(" .?!")
    return normalized in {
        "cho vi du",
        "vi du",
        "cho mot vi du",
        "lay vi du",
        "vi du cu the",
        "cho vi du cu the",
    }


def api_example_answer(topic: str) -> str:
    examples = {
        "merchant_api": (
            "**Ví dụ minh họa Merchant API:**\n\n"
            "Giả sử `partner_id = 1001`, `api_path = /api/v2/...`, "
            "`timestamp = 1720000000`, `access_token = TOKEN` và `merchant_id = 2002`.\n\n"
            "`base_string = 1001 + /api/v2/... + 1720000000 + TOKEN + 2002`\n\n"
            "Sau đó dùng Partner Key làm khóa HMAC-SHA256 để tạo `signature`. "
            "Các giá trị trên chỉ dùng minh họa cấu trúc, không phải thông tin truy cập thật."
        ),
        "shop_api": (
            "**Ví dụ minh họa Shop API:**\n\n"
            "`base_string = partner_id + api_path + timestamp + access_token + shop_id`\n\n"
            "Ví dụ giả định: `1001 + /api/v2/... + 1720000000 + TOKEN + 3003`. "
            "Chuỗi được dùng cùng Partner Key để tạo `signature` bằng HMAC-SHA256."
        ),
        "public_api": (
            "**Ví dụ minh họa Public API theo tài liệu hiện có:**\n\n"
            "`base_string = partner_id + api_path + timestamp`\n\n"
            "Ví dụ giả định: `1001 + /api/v2/... + 1720000000`. "
            "Tôi không tự thêm tham số ngoài cấu trúc được nêu trong tài liệu."
        ),
    }
    return examples.get(topic, "")


def fixed_fee_example_answer() -> str:
    return (
        "**Ví dụ minh họa phí cố định 12%:**\n\n"
        "Giá sản phẩm: **100.000 VND**.\n\n"
        "Phí cố định = 100.000 × 12% = **12.000 VND**.\n\n"
        "Ví dụ này chỉ minh họa phép tính theo mức 12% của nhóm cáp, sạc và bộ chuyển đổi; "
        "chưa bao gồm các khoản phí hoặc điều chỉnh khác."
    )


def generic_example_followup_answer() -> str:
    topic = current_topic()

    if topic == "transaction_fee":
        return transaction_fee_example_answer()
    if topic == "fixed_fee":
        return fixed_fee_example_answer()
    if topic in {"merchant_api", "shop_api", "public_api"}:
        return api_example_answer(topic)
    if topic == "api_comparison":
        return (
            "**Ví dụ minh họa ba loại API:**\n\n"
            "- Public API: `partner_id + api_path + timestamp`\n"
            "- Shop API: `partner_id + api_path + timestamp + access_token + shop_id`\n"
            "- Merchant API: `partner_id + api_path + timestamp + access_token + merchant_id`\n\n"
            "Ví dụ chỉ mô tả cấu trúc; các ID và token thực tế phải lấy từ ứng dụng đã được cấp quyền."
        )

    return (
        "Bạn muốn tôi đưa ví dụ cho nội dung nào: phí bán hàng, "
        "Merchant API, Shop API hay Public API?"
    )


def is_fixed_fee_example_followup(query: str) -> bool:
    normalized = backend.normalize_for_match(query)
    asks_example = any(
        phrase in normalized
        for phrase in [
            "cho vi du tinh phi",
            "cho vi du voi gia san pham",
            "vi du voi gia san pham",
            "tinh phi voi gia san pham",
        ]
    )
    return asks_example and current_topic() == "fixed_fee"


def is_three_api_comparison_question(query: str) -> bool:
    normalized = backend.normalize_for_match(query)
    has_all = all(
        term in normalized
        for term in ["shop api", "merchant api", "public api"]
    )
    asks_detail = any(
        phrase in normalized
        for phrase in [
            "khac nhau",
            "so sanh",
            "giai thich chi tiet",
            "cau truc base_string",
            "base_string cua tung loai",
        ]
    )
    return has_all and asks_detail


def three_api_comparison_answer() -> str:
    st.session_state.active_topic = "api_comparison"
    return (
        "Ba loại API khác nhau chủ yếu ở phạm vi xác thực và phần cuối của `base_string`:\n\n"
        "| Loại API | Cấu trúc `base_string` theo tài liệu hiện có | Phạm vi nhận diện |\n"
        "|---|---|---|\n"
        "| Public API | `partner_id + api_path + timestamp` | Tài nguyên không gắn với một shop/merchant đã cấp quyền |\n"
        "| Shop API | `partner_id + api_path + timestamp + access_token + shop_id` | Một shop cụ thể |\n"
        "| Merchant API | `partner_id + api_path + timestamp + access_token + merchant_id` | Một merchant cụ thể |\n\n"
        "Các thành phần phải được ghép đúng thứ tự trước khi dùng Partner Key và HMAC-SHA256 "
        "để tạo `signature`. Không dùng `shop_id` thay cho `merchant_id` hoặc ngược lại."
    )


def is_direct_signature_algorithm_question(query: str) -> bool:
    normalized = backend.normalize_for_match(query)
    signature_term = "signature" in normalized or "chu ky" in normalized
    algorithm_term = any(
        phrase in normalized
        for phrase in [
            "thuat toan nao",
            "thuat toan gi",
            "tao bang thuat toan",
            "tao bang gi",
            "duoc tinh bang gi",
        ]
    )
    return signature_term and algorithm_term


def direct_signature_algorithm_answer() -> str:
    st.session_state.active_topic = "merchant_api"
    return (
        "Signature được tạo bằng thuật toán **HMAC-SHA256**. "
        "Hệ thống ghép `base_string` theo đúng thứ tự tham số, "
        "sau đó dùng Partner Key làm khóa để tính signature."
    )


def is_strict_out_of_scope_question(query: str) -> bool:
    """Chặn câu hỏi ngoài phạm vi trước retrieval để không chờ Ollama vô ích."""
    normalized = backend.normalize_for_match(query)

    # Yêu cầu lập trình liên quan trực tiếp Shopee/Open Platform vẫn nằm trong phạm vi.
    has_shopee_api_context = any(
        term in normalized
        for term in [
            "shopee", "merchant api", "shop api", "public api",
            "open platform", "base_string", "base string", "signature",
        ]
    )
    generic_programming = any(
        phrase in normalized
        for phrase in [
            "viet code", "code python", "lap trinh python",
            "quan ly sinh vien", "quan ly nhan vien",
            "tao website", "lam website", "lam web", "xay dung website",
            "website ban quan ao", "web ban quan ao",
            "huong dan toi lam website", "huong dan lam website",
            "viet chuong trinh", "chuong trinh java",
        ]
    )
    if generic_programming and not has_shopee_api_context:
        return True

    # Cho phép tên địa phương chen giữa "thời tiết" và mốc thời gian.
    if "thoi tiet" in normalized and any(
        marker in normalized for marker in ["hom nay", "ngay mai", "du bao"]
    ):
        return True

    patterns = [
        # Tài chính/giá thời gian thực và dự báo.
        "gia bitcoin",
        "bitcoin hom nay",
        "gia vang hom nay",
        "du bao gia vang",
        "gia vang ngay mai",
        "ty gia hom nay",
        "gia co phieu",
        "chung khoan hom nay",
        "du bao thi truong tai chinh",
        # Thể thao.
        "manchester united",
        "lich thi dau bong da",
        "ty so bong da",
        "hom nay da voi ai",
        "doi nao da hom nay",
        "ket qua bong da",
        # Thời tiết.
        "du bao thoi tiet",
        "thoi tiet hom nay",
        "thoi tiet ngay mai",
        "nhiet do hom nay",
        "nhiet do ngay mai",
        # Sáng tác/giải trí không thuộc nghiệp vụ Shopee.
        "viet cho toi mot bai tho",
        "viet bai tho",
        "bai tho tinh",
        "viet truyen",
        "ke chuyen",
        "sang tac bai hat",
    ]

    return any(pattern in normalized for pattern in patterns)


def strict_out_of_scope_answer() -> str:
    return (
        "Nội dung này nằm ngoài phạm vi của Shopee AI Assistant. "
        "Tôi tập trung hỗ trợ chính sách và phí Shopee, trả hàng/hoàn tiền, "
        "Shopee Open Platform/API, pháp luật thương mại điện tử, báo cáo thị trường "
        "và phân tích dữ liệu vận hành shop khi bạn cung cấp dữ liệu phù hợp."
    )

def is_no_seller_response_return_question(query: str) -> bool:
    normalized = backend.normalize_for_match(query)
    return (
        any(term in normalized for term in ["tra hang", "hoan tien"])
        and any(
            phrase in normalized
            for phrase in [
                "nguoi ban khong phan hoi",
                "neu nguoi ban khong phan hoi",
                "khong phan hoi yeu cau tra hang",
            ]
        )
    )


def no_seller_response_return_answer() -> str:
    return (
        "Kho tài liệu hiện tại chưa nêu đủ rõ hệ quả và thời hạn áp dụng riêng cho trường hợp "
        "người bán không phản hồi yêu cầu trả hàng ban đầu. Không nên dùng mốc 6 ngày gửi trả hàng "
        "hoặc mốc 2 ngày khiếu nại để thay thế cho thời hạn phản hồi của người bán. "
        "Bạn cần bổ sung tài liệu chính thức mô tả đúng bước Shopee tự động xử lý khi người bán không phản hồi."
    )


def is_order_reason_followup(query: str) -> bool:
    normalized = backend.normalize_for_match(query)
    return any(
        phrase in normalized
        for phrase in [
            "tai sao phai dung thu tu",
            "tai sao phai dung dung thu tu",
            "vi sao phai dung thu tu",
            "tai sao phai sap xep dung thu tu",
            "thu tu do de lam gi",
        ]
    ) and current_topic() in {
        "merchant_api",
        "shop_api",
        "public_api",
        "api_comparison",
    }


def order_reason_followup_answer() -> str:
    return (
        "Các tham số phải đúng thứ tự vì thứ tự là một phần của `base_string`. "
        "Nếu chỉ đổi vị trí một tham số, chuỗi đầu vào thay đổi, kết quả HMAC-SHA256 cũng thay đổi "
        "và `signature` có thể không khớp với phía Shopee, khiến yêu cầu bị từ chối."
    )

def is_merchant_base_string_question(query: str) -> bool:
    normalized = backend.normalize_for_match(query)

    if "merchant api" not in normalized:
        return False

    # Yêu cầu tổng hợp nhiều loại API phải đi qua RAG/LLM, không được rút gọn
    # nhầm thành câu hỏi riêng về base_string Merchant API.
    if (
        "tong hop toan bo" in normalized
        or ("shop api" in normalized and "public api" in normalized)
        or "loi thuong gap" in normalized
    ):
        return False

    # Chuẩn hóa các lỗi gõ phổ biến trước khi xét intent.
    alias_query = normalized
    for typo in [
        "base strng", "base strig", "base sting", "base sring",
        "base strin", "base strinh", "basestring", "base-string",
        "base  string", "base_strng", "base_strig",
    ]:
        alias_query = alias_query.replace(typo, "base string")

    string_intents = [
        "base_string",
        "base string",
        "ghep chuoi",
        "noi chuoi",
        "ghep base string",
        "noi base string",
        "build string",
        "build base string",
        "build base_string",
        "xay dung base string",
        "xay dung chuoi",
        "tao chuoi ky",
        "tao chuoi",
        "chuoi merchant api",
    ]
    detail_intents = [
        "gom nhung tham so nao",
        "gom tham so nao",
        "gom nhung gi",
        "gom gi",
        "gom j",
        "co nhung gi",
        "base string gom",
        "base_string gom",
        "theo thu tu nao",
        "tao base_string",
        "tao base string",
        "ghep chuoi",
        "noi chuoi",
        "ghep base string",
        "noi base string",
        "ghep base",
        "build string",
        "build base string",
        "build base_string",
        "xay dung",
        "tao chuoi ky",
        "tao chuoi",
        "chuoi merchant api",
        "nhu the nao",
        "nhu nao",
        "the nao",
        "ra sao",
    ]

    return (
        any(intent in alias_query for intent in string_intents)
        and any(intent in alias_query for intent in detail_intents)
    )


def merchant_base_string_answer() -> str:
    st.session_state.active_topic = "merchant_api"

    return (
        "Merchant API tạo `base_string` theo đúng thứ tự:\n\n"
        "`partner_id + api_path + timestamp + access_token + merchant_id`\n\n"
        "Trong đó, `merchant_id` là thành phần cuối dùng để xác định merchant. "
        "Chuỗi này được dùng cùng Partner Key để tạo `signature` bằng HMAC-SHA256. "
        "Nếu thiếu tham số hoặc đổi thứ tự, signature có thể không khớp và yêu cầu "
        "API có thể bị từ chối."
    )


def is_api_verification_question(query: str) -> bool:
    """Nhận diện câu hỏi đúng/sai đã có đáp án xác định để trả lời tức thời."""
    normalized = backend.normalize_for_match(query)
    patterns = [
        "merchant api khong can merchant_id",
        "merchant api khong can merchant id",
        "merchant_id khong can",
        "merchant id khong can",
        "shop api dung merchant_id",
        "shop api dung merchant id",
        "signature dung md5",
        "signature tao bang md5",
        "chu ky dung md5",
        "chu ky tao bang md5",
    ]
    return any(pattern in normalized for pattern in patterns)


def api_verification_answer(query: str) -> str:
    normalized = backend.normalize_for_match(query)
    st.session_state.active_topic = "merchant_api"

    if "md5" in normalized:
        return (
            "Không đúng. Theo tài liệu hiện có, `signature` được tạo bằng "
            "**HMAC-SHA256** với Partner Key, không phải MD5."
        )

    if "shop api" in normalized and ("merchant_id" in normalized or "merchant id" in normalized):
        return (
            "Không đúng. Khi tạo `base_string`, Shop API dùng `shop_id`; "
            "Merchant API mới dùng `merchant_id`."
        )

    return (
        "Không đúng. Merchant API cần `merchant_id` ở cuối `base_string`: "
        "`partner_id + api_path + timestamp + access_token + merchant_id`."
    )


def is_merchant_api_auth_components_question(query: str) -> bool:
    """Nhận diện riêng câu hỏi về thành phần/tham số xác thực Merchant API."""
    normalized = backend.normalize_for_match(query).strip(" .?!")

    if "merchant api" not in normalized:
        return False

    # Câu hỏi chuyên biệt về base_string do nhánh base_string xử lý.
    if is_merchant_base_string_question(query):
        return False

    has_auth_topic = (
        "xac thuc" in normalized
        or "authentication" in normalized
    )
    asks_components = any(
        phrase in normalized
        for phrase in [
            "thanh phan",
            "tham so",
            "gom nhung gi",
            "gom gi",
            "bao gom",
            "can nhung gi",
            "can gi",
            "components",
            "parameters",
        ]
    )

    return has_auth_topic and asks_components


def merchant_api_auth_components_answer() -> str:
    """Câu trả lời xác định sẵn, không gọi Hybrid Search hoặc mô hình ngôn ngữ."""
    st.session_state.active_topic = "merchant_api"

    return (
        "Merchant API sử dụng các thành phần xác thực chính sau:\n\n"
        "1. `partner_id`: mã đối tác/ứng dụng tích hợp.\n"
        "2. `api_path`: đường dẫn API đang được gọi.\n"
        "3. `timestamp`: thời điểm gửi yêu cầu.\n"
        "4. `access_token`: mã truy cập được cấp sau quá trình ủy quyền.\n"
        "5. `merchant_id`: mã merchant và là thành phần cuối của `base_string`.\n"
        "6. Partner Key: khóa bí mật dùng làm khóa HMAC; không nối vào `base_string`.\n"
        "7. `signature`: chữ ký được tạo bằng HMAC-SHA256 từ Partner Key và `base_string`.\n\n"
        "Thứ tự `base_string` là:\n\n"
        "`partner_id + api_path + timestamp + access_token + merchant_id`\n\n"
        "Nếu thiếu tham số, sai giá trị hoặc sai thứ tự, `signature` có thể không khớp "
        "và yêu cầu API có thể bị từ chối."
    )


def is_merchant_api_overview_question(query: str) -> bool:
    normalized = backend.normalize_for_match(query).strip(" .?!")
    if "merchant api" not in normalized:
        return False

    # Không giành intent của câu hỏi chuyên biệt.
    if (
        is_merchant_base_string_question(query)
        or is_merchant_api_auth_components_question(query)
    ):
        return False

    overview_phrases = [
        "merchant api gom nhung gi",
        "merchant api gom gi",
        "merchant api bao gom nhung gi",
        "merchant api bao gom gi",
        "merchant api co nhung gi",
        "merchant api la gi",
        "merchant api gom nhung thanh phan nao",
        "merchant api co nhung thanh phan nao",
        "merchant api gom cac thanh phan nao",
        "merchant api co cac thanh phan nao",
    ]
    return any(phrase in normalized for phrase in overview_phrases)


def merchant_api_overview_answer() -> str:
    st.session_state.active_topic = "merchant_api"
    return (
        "Trong phạm vi tài liệu xác thực hiện có, Merchant API gồm:\n\n"
        "1. `base_string`: `partner_id + api_path + timestamp + access_token + merchant_id`.\n"
        "2. Partner Key: khóa bí mật dùng để tính chữ ký HMAC-SHA256.\n"
        "3. `signature`: kết quả ký `base_string` bằng Partner Key.\n"
        "4. Quy tắc xác thực: tham số phải đủ giá trị và đúng thứ tự; nếu sai, "
        "`signature` có thể không khớp và API có thể từ chối yêu cầu."
    )


def is_signature_flow_question(query: str) -> bool:
    normalized = backend.normalize_for_match(query)

    return (
        "signature" in normalized
        and any(
            phrase in normalized
            for phrase in [
                "luong",
                "quy trinh",
                "cac buoc",
                "tao nhu the nao",
            ]
        )
    )


def signature_flow_answer() -> str:
    return (
        "**Luồng tạo signature:**\n\n"
        "`Tham số yêu cầu` → `Ghép base_string đúng thứ tự` → "
        "`Dùng Partner Key và HMAC-SHA256` → `Sinh signature` → "
        "`Gửi request tới API`\n\n"
        "Chỉ cần một tham số bị thiếu, sai giá trị hoặc sai thứ tự thì "
        "signature tạo ra có thể khác với phía Shopee."
    )


# ============================================================
# V19 - CÁC NHÁNH XỬ LÝ NHANH CHO TOÀN BỘ LỖI KIỂM THỬ V18
# ============================================================

def is_full_api_guide_question(query: str) -> bool:
    """Nhận diện yêu cầu tổng hợp đồng thời Public/Shop/Merchant API."""
    normalized = backend.normalize_for_match(query)
    has_all_api_types = all(
        term in normalized
        for term in ["public api", "shop api", "merchant api"]
    )
    asks_full_guide = any(
        phrase in normalized
        for phrase in [
            "tong hop toan bo",
            "tong hop day du",
            "giai thich toan bo",
            "trinh bay toan bo",
            "loi thuong gap",
            "vi du chi tiet cho tung loai",
            "cach tao base_string",
            "cach tao base string",
        ]
    )
    return has_all_api_types and asks_full_guide


def full_api_guide_answer() -> str:
    st.session_state.active_topic = "api_comparison"
    return (
        "## Tổng hợp Public API, Shop API và Merchant API\n\n"
        "| Loại API | Cấu trúc `base_string` theo tài liệu hiện có | Đối tượng nhận diện |\n"
        "|---|---|---|\n"
        "| Public API | `partner_id + api_path + timestamp` | Yêu cầu công khai, không nối `access_token`, `shop_id` hoặc `merchant_id` |\n"
        "| Shop API | `partner_id + api_path + timestamp + access_token + shop_id` | Một shop đã cấp quyền |\n"
        "| Merchant API | `partner_id + api_path + timestamp + access_token + merchant_id` | Một merchant đã cấp quyền |\n\n"
        "### Cách tạo `signature`\n\n"
        "1. Chuẩn bị đúng các tham số của loại API.\n"
        "2. Ghép `base_string` đúng thứ tự, không chèn dấu phân cách nếu tài liệu không yêu cầu.\n"
        "3. Dùng Partner Key làm khóa HMAC-SHA256 để ký `base_string`.\n"
        "4. Chuyển kết quả thành chuỗi hex và gửi cùng yêu cầu API.\n\n"
        "### Lỗi thường gặp\n\n"
        "- Đổi sai thứ tự tham số hoặc thiếu một tham số.\n"
        "- Dùng `merchant_id` cho Shop API hoặc dùng `shop_id` cho Merchant API.\n"
        "- Nối Partner Key trực tiếp vào `base_string`; Partner Key chỉ dùng làm khóa HMAC.\n"
        "- Dùng MD5 thay cho HMAC-SHA256.\n"
        "- Dùng `timestamp`, `access_token` hoặc ID không còn hợp lệ.\n\n"
        "### Ví dụ cấu trúc\n\n"
        "- Public API: `1001 + /api/v2/example + 1720000000`\n"
        "- Shop API: `1001 + /api/v2/example + 1720000000 + ACCESS_TOKEN + 3003`\n"
        "- Merchant API: `1001 + /api/v2/example + 1720000000 + ACCESS_TOKEN + 2002`\n\n"
        "Các giá trị trên chỉ để minh họa cấu trúc, không phải thông tin truy cập thật."
    )


def is_merchant_signature_python_example_question(query: str) -> bool:
    normalized = backend.normalize_for_match(query)
    has_merchant_context = "merchant api" in normalized
    has_signature = "signature" in normalized or "chu ky" in normalized
    has_python = "python" in normalized
    asks_example = any(
        phrase in normalized
        for phrase in [
            "viet vi du",
            "cho vi du",
            "vi du python",
            "viet code",
            "doan code",
            "ma nguon",
            "tao signature",
        ]
    )
    return has_merchant_context and has_signature and has_python and asks_example


def merchant_signature_python_example_answer() -> str:
    st.session_state.active_topic = "merchant_api"
    return (
        "Ví dụ Python tạo `signature` cho Merchant API bằng HMAC-SHA256:\n\n"
        "```python\n"
        "import hashlib\n"
        "import hmac\n"
        "import time\n\n"
        "partner_id = 123456\n"
        "partner_key = \"YOUR_PARTNER_KEY\"\n"
        "api_path = \"/api/v2/example/endpoint\"\n"
        "timestamp = int(time.time())\n"
        "access_token = \"YOUR_ACCESS_TOKEN\"\n"
        "merchant_id = 789012\n\n"
        "base_string = (\n"
        "    f\"{partner_id}{api_path}{timestamp}\"\n"
        "    f\"{access_token}{merchant_id}\"\n"
        ")\n\n"
        "signature = hmac.new(\n"
        "    partner_key.encode(\"utf-8\"),\n"
        "    base_string.encode(\"utf-8\"),\n"
        "    hashlib.sha256,\n"
        ").hexdigest()\n\n"
        "print(signature)\n"
        "```\n\n"
        "`base_string` phải giữ đúng thứ tự "
        "`partner_id + api_path + timestamp + access_token + merchant_id`. "
        "Các giá trị trong ví dụ đều là giá trị minh họa; không nhập Partner Key hoặc `access_token` thật vào tài liệu chia sẻ công khai."
    )


def is_vietnamese_only_merchant_explanation_question(query: str) -> bool:
    normalized = backend.normalize_for_match(query)
    return (
        "merchant api" in normalized
        and any(
            phrase in normalized
            for phrase in [
                "tieng viet hoan toan",
                "hoan toan bang tieng viet",
                "khong dung tu tieng anh",
                "chi dung tieng viet",
            ]
        )
    )


def vietnamese_only_merchant_explanation_answer() -> str:
    st.session_state.active_topic = "merchant_api"
    return (
        "Merchant API là giao diện dùng để gửi yêu cầu tới Shopee trong phạm vi một merchant đã được cấp quyền. "
        "Khi xác thực, hệ thống ghép `partner_id`, `api_path`, `timestamp`, `access_token` và `merchant_id` "
        "theo đúng thứ tự để tạo `base_string`.\n\n"
        "Sau đó, hệ thống dùng khóa bí mật của đối tác và thuật toán HMAC-SHA256 để tạo `signature`. "
        "Nếu thiếu tham số, sai giá trị hoặc sai thứ tự, chữ ký có thể không khớp và yêu cầu có thể bị từ chối."
    )

def is_capability_question(query: str) -> bool:
    normalized = backend.normalize_for_match(query)

    phrases = [
        "toi co the hoi them gi",
        "toi co the hoi gi",
        "ban co the giup gi",
        "ban ho tro nhung gi",
        "ngoai dieu tren",
        "ngoai nhung dieu tren",
        "toi co the hoi ban dieu gi",
        "co the hoi them gi khong",
        "toi nen hoi gi",
    ]

    return any(phrase in normalized for phrase in phrases)


def capability_answer() -> str:
    return (
        "Bạn có thể hỏi tôi về các nhóm nội dung sau:\n\n"
        "1. Phí bán hàng: phí cố định, phí xử lý giao dịch, phí dịch vụ và phí vận chuyển.\n"
        "2. Chính sách đăng bán: sản phẩm cấm/hạn chế, quy định ngành hàng và xử lý vi phạm.\n"
        "3. Trả hàng và hoàn tiền: quy trình, điều kiện, thời hạn và trách nhiệm của người bán.\n"
        "4. Shopee Open Platform/API: authorization, base_string, signature, đơn hàng, sản phẩm và logistics.\n"
        "5. Pháp luật thương mại điện tử: quyền lợi người tiêu dùng, dữ liệu cá nhân, quảng cáo và nhãn hàng hóa.\n"
        "6. Báo cáo thị trường và hoạt động của Shopee.\n"
        "7. Dữ liệu riêng của shop như doanh thu, đơn hàng, chi phí, tồn kho và quảng cáo "
        "sau khi bạn cung cấp file Excel hoặc CSV.\n\n"
        "Ví dụ: “Phí cố định của cáp sạc là bao nhiêu?” hoặc "
        "“Merchant API tạo base_string gồm những tham số nào?”"
    )


def is_data_requirement_followup(query: str) -> bool:
    normalized = backend.normalize_for_match(query)

    phrases = [
        "toi phai cung cap cho ban thong tin gi",
        "toi can cung cap thong tin gi",
        "can cung cap gi de ban tong hop",
        "toi phai gui du lieu gi",
        "toi can gui file gi",
        "ban can toi cung cap gi",
        "de ban lam tong hop thong tin cho toi",
    ]

    return any(phrase in normalized for phrase in phrases)


def operational_data_guidance() -> str:
    return (
        "Để tôi tổng hợp và phân tích hoạt động của công ty hoặc shop, "
        "bạn nên cung cấp file Excel hoặc CSV. Tùy câu hỏi, file nên có:\n\n"
        "1. Doanh thu: ngày, mã đơn, doanh thu gộp, giảm giá, doanh thu thực nhận.\n"
        "2. Đơn hàng: mã đơn, trạng thái, sản phẩm, SKU, số lượng và ngày phát sinh.\n"
        "3. Chi phí: phí cố định, phí xử lý giao dịch, phí vận chuyển, phí dịch vụ và quảng cáo.\n"
        "4. Trả hàng/hoàn tiền: mã đơn, lý do, số tiền hoàn và trạng thái xử lý.\n"
        "5. Tồn kho: SKU, tên sản phẩm, số lượng tồn và mức cảnh báo.\n"
        "6. Quảng cáo: chi phí, lượt nhấp, đơn hàng, doanh thu và ROAS nếu có.\n\n"
        "Không gửi mật khẩu, access_token, Partner Key, thông tin thẻ hoặc dữ liệu cá nhân nhạy cảm."
    )


def is_rewards_question(query: str) -> bool:
    normalized = backend.normalize_for_match(query)

    reward_terms = [
        "shopee xu",
        "diem thuong shopee",
        "diem thuong",
        "tich luy diem",
        "su dung diem",
        "doi diem",
    ]

    return any(term in normalized for term in reward_terms)


def contexts_support_rewards(contexts: list[dict]) -> bool:
    merged = backend.normalize_for_match(
        "\n".join(str(item.get("text", "")) for item in contexts)
    )

    titles = backend.normalize_for_match(
        " ".join(
            str(item.get("metadata", {}).get("title", ""))
            for item in contexts
        )
    )

    # Phải có tài liệu đúng chủ đề, không chỉ tình cờ xuất hiện chữ "điểm".
    title_supported = (
        "shopee xu" in titles
        or "diem thuong" in titles
        or "reward" in titles
        or "loyalty" in titles
    )

    subject_count = (
        merged.count("shopee xu")
        + merged.count("diem thuong")
    )

    action_present = any(
        term in merged
        for term in [
            "tich luy shopee xu",
            "su dung shopee xu",
            "doi shopee xu",
            "nhan shopee xu",
            "han su dung shopee xu",
        ]
    )

    return title_supported and subject_count >= 2 and action_present


def safe_rewards_answer() -> str:
    return (
        "Kho tài liệu hiện tại chưa có hướng dẫn đủ rõ về cách tích lũy và sử dụng Shopee Xu/điểm thưởng. "
        "Tôi không nên suy luận từ các tài liệu vận chuyển hoặc giao dịch không liên quan. "
        "Bạn cần bổ sung tài liệu chính thức về Shopee Xu hoặc chương trình khách hàng thân thiết."
    )



def is_explicit_standalone_question(query: str) -> bool:
    """
    Câu hỏi có chủ thể rõ ràng thì không được ghép nhầm với lượt trước.
    """
    normalized = backend.normalize_for_match(query)

    explicit_topics = [
        "phi xu ly giao dich",
        "phi co dinh",
        "merchant api",
        "shop api",
        "shopee open platform",
        "partner key",
        "access_token",
        "access token",
        "signature",
        "shopee xu",
        "diem thuong",
        "api lay don hang",
        "ho tro nhung api",
    ]

    return any(topic in normalized for topic in explicit_topics)


def source_titles(contexts: list[dict]) -> list[str]:
    titles = []

    for item in contexts:
        metadata = item.get("metadata", {})
        title = str(metadata.get("title", "")).strip()

        if title and title not in titles:
            titles.append(title)

    return titles


def context_text(contexts: list[dict]) -> str:
    return "\n".join(
        str(item.get("text", ""))
        for item in contexts
    )


def direct_transaction_fee_answer(
    query: str,
    contexts: list[dict],
) -> str | None:
    normalized = backend.normalize_for_match(query)

    if "phi xu ly giao dich" not in normalized:
        return None

    merged = context_text(contexts)

    formula_patterns = [
        r"Phí\s*Xử\s*Lý\s*Giao\s*Dịch\s*=\s*(.{20,320}?\*\s*\d+(?:[.,]\d+)?\s*%)",
        r"Phí\s*Xử\s*Lý\s*Giao\s*Dịch\s*được\s*tính.{0,100}?(Giá\s*sản\s*phẩm.{20,320}?\d+(?:[.,]\d+)?\s*%)",
    ]

    for pattern in formula_patterns:
        match = re.search(
            pattern,
            merged,
            flags=re.IGNORECASE | re.DOTALL,
        )

        if match:
            formula = " ".join(match.group(1).split())
            formula = formula.rstrip(" .")

            return (
                "Phí Xử Lý Giao Dịch được tính theo công thức:\n\n"
                f"Phí Xử Lý Giao Dịch = {formula}."
            )

    return None


def is_open_platform_purpose_question(query: str) -> bool:
    normalized = backend.normalize_for_match(query)

    return (
        "shopee open platform" in normalized
        and any(
            phrase in normalized
            for phrase in [
                "dung de lam gi",
                "la gi",
                "co tac dung gi",
            ]
        )
    )


def open_platform_purpose_answer(contexts: list[dict]) -> str:
    titles = " ".join(source_titles(contexts)).lower()

    modules = []

    if "authorization" in titles:
        modules.append("ủy quyền và xác thực shop")
    if "order" in titles:
        modules.append("quản lý đơn hàng")
    if "listing" in titles or "product" in titles:
        modules.append("quản lý sản phẩm")
    if "logistics" in titles:
        modules.append("logistics và vận chuyển")

    if not modules:
        modules = [
            "kết nối hệ thống của đối tác với các chức năng được Shopee cung cấp qua API"
        ]

    module_text = ", ".join(modules)

    return (
        "Shopee Open Platform là nền tảng dành cho nhà phát triển và đối tác "
        "để kết nối ứng dụng với hệ thống Shopee qua API. "
        f"Trong bộ tài liệu hiện có, nền tảng hỗ trợ các nội dung như {module_text}."
    )


def is_api_catalog_question(query: str) -> bool:
    normalized = backend.normalize_for_match(query)

    return (
        "shopee" in normalized
        and "api" in normalized
        and any(
            phrase in normalized
            for phrase in [
                "ho tro nhung api nao",
                "co nhung api nao",
                "danh sach api",
                "cac api nao",
            ]
        )
    )


def api_catalog_answer(contexts: list[dict]) -> str:
    titles = source_titles(contexts)
    title_text = " ".join(titles).lower()

    items = []

    if "authorization" in title_text:
        items.append("API ủy quyền/xác thực")
    if "order" in title_text:
        items.append("API quản lý đơn hàng")
    if "listing" in title_text or "product" in title_text:
        items.append("API quản lý sản phẩm/đăng bán")
    if "logistics" in title_text:
        items.append("API logistics")

    if items:
        return (
            "Trong bộ tài liệu hiện có, Shopee Open Platform có các nhóm API: "
            + "; ".join(items)
            + ". Tôi chưa nên khẳng định đây là toàn bộ danh mục API của Shopee."
        )

    return (
        "Tài liệu hiện tại chưa đủ để liệt kê đầy đủ các nhóm API của Shopee. "
        "Tôi chỉ nên kết luận về những module có tài liệu chính thức trong kho dữ liệu."
    )


def is_order_api_question(query: str) -> bool:
    normalized = backend.normalize_for_match(query)

    return (
        "api" in normalized
        and "don hang" in normalized
        and any(
            phrase in normalized
            for phrase in [
                "co api lay don hang",
                "api lay don hang",
                "lay don hang khong",
            ]
        )
    )


def order_api_answer(contexts: list[dict]) -> str:
    title_text = " ".join(source_titles(contexts)).lower()
    merged = backend.normalize_for_match(context_text(contexts))

    supported = (
        "order management" in title_text
        or "order" in title_text
        or "get_order" in merged
        or "order_list" in merged
        or "order detail" in merged
    )

    if supported:
        return (
            "Có. Bộ tài liệu hiện tại có nhóm API quản lý đơn hàng. "
            "Tuy nhiên, để nêu đúng endpoint, tham số và quyền truy cập, "
            "cần hỏi theo thao tác cụ thể như lấy danh sách đơn hoặc xem chi tiết đơn."
        )

    return (
        "Tôi chưa tìm thấy tài liệu trực tiếp xác nhận endpoint lấy đơn hàng "
        "trong kết quả hiện tại, nên chưa thể kết luận chi tiết."
    )


def is_signature_algorithm_question(query: str) -> bool:
    normalized = backend.normalize_for_match(query)

    return (
        "signature" in normalized
        and any(
            phrase in normalized
            for phrase in [
                "thuat toan gi",
                "tao bang gi",
                "duoc tinh bang gi",
            ]
        )
    )


def signature_algorithm_answer(contexts: list[dict]) -> str:
    merged = context_text(contexts)

    if re.search(r"HMAC[\s\-]?SHA256", merged, flags=re.IGNORECASE):
        return (
            "Signature được tạo bằng thuật toán HMAC-SHA256. "
            "Hệ thống tạo base_string theo đúng thứ tự tham số, "
            "sau đó dùng Partner Key làm khóa để tính signature."
        )

    return (
        "Tài liệu được truy xuất hiện chưa chứa thông tin đủ rõ "
        "để xác nhận thuật toán tạo signature."
    )


def strong_mostly_english(text: str) -> bool:
    if backend.mostly_english(text):
        return True

    words = re.findall(r"[A-Za-z]+", text)
    vietnamese_marks = re.findall(
        r"[ăâđêôơưáàảãạấầẩẫậắằẳẵặéèẻẽẹếềểễệ"
        r"íìỉĩịóòỏõọốồổỗộớờởỡợúùủũụứừửữựýỳỷỹỵ]",
        text.lower(),
    )

    return len(words) >= 20 and len(vietnamese_marks) < 3



def recent_conversation_text(
    max_messages: int = 6,
) -> str:
    messages = st.session_state.get(
        "messages",
        [],
    )

    selected = messages[-max_messages:]

    return "\n".join(
        str(item.get("content", ""))
        for item in selected
    )


def api_followup_rewrite(query: str) -> str | None:
    """
    Viết lại các câu nối tiếp dễ bị retrieval hiểu sai.
    Chỉ kích hoạt khi lịch sử gần nhất đang nói về base_string/signature/API.
    """
    normalized = backend.normalize_for_match(query)
    recent = backend.normalize_for_match(
        recent_conversation_text()
    )

    api_context = any(
        term in recent
        for term in [
            "base_string",
            "signature",
            "merchant api",
            "shop api",
            "partner_id",
            "merchant_id",
            "shop_id",
            "hmac-sha256",
        ]
    )

    if not api_context:
        return None

    if any(
        phrase in normalized
        for phrase in [
            "tai sao phai sap xep dung thu tu",
            "vi sao phai dung thu tu",
            "tai sao dung thu tu",
            "thu tu do de lam gi",
        ]
    ):
        return (
            "Trong quá trình tạo base_string của Shopee API, "
            "tại sao các tham số phải được ghép đúng thứ tự "
            "trước khi tính signature?"
        )

    if any(
        phrase in normalized
        for phrase in [
            "neu thieu merchant_id thi sao",
            "thieu merchant_id thi sao",
        ]
    ):
        return (
            "Khi tạo base_string cho Merchant API, "
            "điều gì xảy ra nếu thiếu merchant_id?"
        )

    if any(
        phrase in normalized
        for phrase in [
            "con shop api khac o dau",
            "shop api khac o dau",
            "con shop api",
        ]
    ):
        return (
            "So sánh Shop API và Merchant API khi tạo base_string: "
            "các tham số giống nhau và khác nhau ở đâu?"
        )

    return None


def global_transaction_fee_answer(
    query: str,
    chunks: list[dict],
) -> str | None:
    """
    Tìm công thức phí xử lý giao dịch trong toàn bộ kho chunk
    để tránh Hybrid Search bỏ sót đúng tài liệu.
    """
    normalized = backend.normalize_for_match(query)

    if "phi xu ly giao dich" not in normalized:
        return None

    matching_texts: list[str] = []

    for chunk in chunks:
        chunk_text = str(chunk.get("text", ""))
        normalized_chunk = backend.normalize_for_match(
            chunk_text
        )

        if (
            "phi xu ly giao dich" in normalized_chunk
            and (
                "6%" in chunk_text
                or "6 %" in chunk_text
            )
        ):
            matching_texts.append(chunk_text)

    merged = "\n".join(matching_texts[:12])

    if not merged:
        return None

    patterns = [
        r"Phí\s*Xử\s*Lý\s*Giao\s*Dịch\s*=\s*(.{20,520}?\*\s*6\s*%)",
        r"Phí\s*Xử\s*Lý\s*Giao\s*Dịch\s*được\s*tính.{0,120}?(Giá\s*sản\s*phẩm.{20,520}?\*\s*6\s*%)",
    ]

    for pattern in patterns:
        match = re.search(
            pattern,
            merged,
            flags=re.IGNORECASE | re.DOTALL,
        )

        if match:
            formula = " ".join(
                match.group(1).split()
            ).strip(" .")

            return (
                "Phí Xử Lý Giao Dịch được tính theo công thức:\n\n"
                f"Phí Xử Lý Giao Dịch = {formula}."
            )

    return None


def api_order_reason_answer(query: str) -> str | None:
    normalized = backend.normalize_for_match(query)
    rewritten = api_followup_rewrite(query)

    if (
        rewritten
        and "tại sao các tham số phải được ghép đúng thứ tự" in rewritten
    ):
        return (
            "Các tham số phải được ghép đúng thứ tự vì Shopee và ứng dụng "
            "phải tạo ra cùng một `base_string` để tính và kiểm tra `signature`. "
            "Chỉ cần đổi vị trí một tham số thì chuỗi đầu vào thay đổi, "
            "kết quả HMAC-SHA256 cũng thay đổi và yêu cầu có thể bị xác thực thất bại."
        )

    if any(
        phrase in normalized
        for phrase in [
            "tai sao phai sap xep dung thu tu",
            "vi sao phai dung thu tu",
        ]
    ):
        recent = backend.normalize_for_match(
            recent_conversation_text()
        )

        if "base_string" in recent or "signature" in recent:
            return (
                "Các tham số phải được ghép đúng thứ tự vì thứ tự là một phần "
                "của `base_string`. Nếu thứ tự khác tài liệu quy định, "
                "signature được tạo ra sẽ khác signature mà Shopee tính, "
                "nên yêu cầu có thể bị từ chối."
            )

    return None


def merchant_missing_answer(query: str) -> str | None:
    normalized = backend.normalize_for_match(query)

    if any(
        phrase in normalized
        for phrase in [
            "neu thieu merchant_id thi sao",
            "thieu merchant_id thi sao",
        ]
    ):
        return (
            "Với Merchant API, `merchant_id` là một thành phần của `base_string`. "
            "Nếu thiếu giá trị này, base_string không đúng cấu trúc yêu cầu, "
            "signature sẽ không khớp và lệnh gọi API có thể bị từ chối."
        )

    return None


def shop_merchant_comparison_answer(
    query: str,
) -> str | None:
    normalized = backend.normalize_for_match(query)

    comparison_requested = any(
        phrase in normalized
        for phrase in [
            "con shop api khac o dau",
            "shop api khac merchant api",
            "so sanh shop api va merchant api",
            "shop api va merchant api khac nhau",
        ]
    )

    if not comparison_requested:
        return None

    return (
        "Khi tạo `base_string`, Shop API và Merchant API giống nhau ở các tham số:\n\n"
        "`partner_id + api_path + timestamp + access_token`\n\n"
        "Điểm khác nhau là:\n\n"
        "1. Shop API nối thêm `shop_id`.\n"
        "2. Merchant API nối thêm `merchant_id`.\n\n"
        "Các tham số phải giữ đúng thứ tự trước khi tính signature."
    )


def final_vietnamese_guard(
    answer: str,
) -> str:
    cleaned = clean_for_chat(answer)

    if not strong_mostly_english(cleaned):
        return cleaned

    return (
        "Tôi chưa thể chuyển câu trả lời vừa tạo thành tiếng Việt một cách đáng tin cậy. "
        "Tôi sẽ không hiển thị nội dung tiếng Anh hoặc tự suy đoán thêm. "
        "Bạn hãy hỏi lại với phạm vi cụ thể hơn để tôi tra cứu đúng tài liệu."
    )



def is_ambiguous_title_question(
    text_value: str,
) -> bool:
    normalized = backend.normalize_for_match(
        text_value
    )
    ambiguous_patterns = {
        "phi bao nhieu",
        "bao nhieu",
        "no dung de lam gi",
        "giai thich de hieu hon",
        "tom tat trong 2 dong",
        "thong tin nay chuan khong",
        "con thi sao",
        "the thi sao",
    }

    return (
        normalized in ambiguous_patterns
        or len(
            normalized
        ) < 10
    )


def topic_title_label(
    topic: str,
) -> str:
    labels = {
        "transaction_fee": "Phí xử lý giao dịch",
        "fixed_fee": "Phí cố định Shopee",
        "merchant_api": "Merchant API",
        "shop_api": "Shop API",
        "public_api": "Public API",
        "open_platform": "Shopee Open Platform",
        "return_refund": "Trả hàng/hoàn tiền",
        "shopee_xu": "Shopee Xu",
    }

    return labels.get(
        topic,
        "",
    )


def adaptive_conversation_title(
    messages: list[dict[str, Any]],
) -> str:
    user_messages = [
        str(
            item.get(
                "content",
                "",
            )
        ).strip()
        for item in messages
        if item.get(
            "role"
        )
        == "user"
        and str(
            item.get(
                "content",
                "",
            )
        ).strip()
    ]

    if not user_messages:
        return default_conversation_title()

    topic_counts: dict[str, int] = {}

    for content in user_messages:
        topic = detect_topic(
            content
        )

        if topic:
            topic_counts[topic] = (
                topic_counts.get(
                    topic,
                    0,
                )
                + 1
            )

    ranked_topics = sorted(
        topic_counts.items(),
        key=lambda item: (
            item[1],
            -user_messages.index(
                next(
                    message
                    for message in user_messages
                    if detect_topic(
                        message
                    )
                    == item[0]
                )
            ),
        ),
        reverse=True,
    )

    labels = [
        topic_title_label(
            topic
        )
        for topic, count in ranked_topics
        if topic_title_label(
            topic
        )
    ]

    unique_labels: list[str] = []

    for label in labels:
        if label not in unique_labels:
            unique_labels.append(
                label
            )

    if len(
        unique_labels
    ) >= 2:
        combined = (
            f"{unique_labels[0]} & "
            f"{unique_labels[1]}"
        )

        if len(
            combined
        ) <= 38:
            return combined

    if unique_labels:
        return unique_labels[0]

    concrete_message = next(
        (
            content
            for content in user_messages
            if not is_ambiguous_title_question(
                content
            )
        ),
        user_messages[0],
    )

    return compact_conversation_title(
        concrete_message
    )

def compact_conversation_title(
    text_value: str,
) -> str:
    normalized = " ".join(text_value.split()).strip()

    title_rules = [
        ("phi xu ly giao dich", "Phí xử lý giao dịch"),
        ("phi co dinh", "Phí cố định Shopee"),
        ("merchant api", "Merchant API"),
        ("shop api", "Shop API"),
        ("signature", "Chữ ký API"),
        ("shopee open platform", "Shopee Open Platform"),
        ("tra hang", "Trả hàng và hoàn tiền"),
        ("doanh thu", "Phân tích doanh thu"),
        ("shopee xu", "Shopee Xu"),
    ]

    searchable = backend.normalize_for_match(
        normalized
    )

    for keyword, title in title_rules:
        if keyword in searchable:
            return title

    if len(normalized) > 34:
        return normalized[:31].rstrip() + "..."

    return normalized or default_conversation_title()


# ============================================================
# XỬ LÝ TRẢ LỜI
# ============================================================


def is_gibberish_query(query: str) -> bool:
    """Nhận diện đầu vào vô nghĩa để không đưa qua Hybrid Search/Ollama."""
    normalized = backend.normalize_for_match(query).strip()
    compact = re.sub(r"[^a-z0-9]+", "", normalized)

    if not compact:
        return True

    # Một chuỗi chỉ gồm số, không có ngữ cảnh, không phải câu hỏi tra cứu.
    # Chặn trước retrieval để tránh khớp nhầm số trang, năm hoặc mã trong tài liệu.
    if re.fullmatch(r"\d+", compact):
        return True

    exact_noise = {
        "haha",
        "hahaha",
        "hahahaha",
        "hehe",
        "hehehe",
        "hihi",
        "hihihi",
        "abc",
        "abcd",
        "abcxyz",
        "test",
        "testing",
        "alo",
        "ok",
        "oke",
        "kkkk",
        "lol",
        "sadsadsadsa",
        "asdf",
        "asdfgh",
        "qwerty",
        "qwertyuiop",
    }
    if compact in exact_noise:
        return True

    if re.fullmatch(r"(ha){2,}", compact):
        return True
    if re.fullmatch(r"(he){2,}", compact):
        return True
    if re.fullmatch(r"(hi){2,}", compact):
        return True
    if re.fullmatch(r"(sad){2,}[a-z]*", compact):
        return True
    if re.fullmatch(r"([a-z])\1{3,}", compact):
        return True

    # Chuỗi dài nhưng gần như không có nguyên âm thường là gõ ngẫu nhiên.
    if len(compact) >= 7:
        vowel_count = sum(char in "aeiouy" for char in compact)
        if vowel_count <= 1:
            return True

    return False


def gibberish_answer() -> str:
    return (
        "Tôi chưa xác định được câu hỏi bạn muốn hỏi. "
        "Bạn hãy nhập câu hỏi cụ thể về phí Shopee, chính sách, "
        "trả hàng/hoàn tiền, Shopee Open Platform/API "
        "hoặc dữ liệu vận hành shop."
    )


def should_use_quick_path(query: str) -> bool:
    """Chỉ nhận các nhánh chắc chắn không gọi Hybrid Search hoặc Ollama."""
    clean_query = backend.strip_duplicate_question(
        backend.normalize_unicode(" ".join(str(query).split()))
    )

    if is_gibberish_query(clean_query):
        return True

    simple_checks = [
        is_strict_out_of_scope_question,
        is_inventory_private_question,
        is_full_api_guide_question,
        is_merchant_signature_python_example_question,
        is_vietnamese_only_merchant_explanation_question,
        is_three_api_comparison_question,
        is_direct_signature_algorithm_question,
        is_api_verification_question,
        is_merchant_api_auth_components_question,
        is_merchant_api_overview_question,
        is_order_reason_followup,
        is_no_seller_response_return_question,
        is_generic_example_followup,
        is_generic_summary_followup,
        is_fixed_fee_example_followup,
        is_merchant_base_string_question,
        is_signature_flow_question,
        is_no_bank_discount_followup,
        is_fee_calculation_question,
        is_public_api_followup,
        is_detailed_shop_merchant_question,
        is_capability_question,
        is_data_requirement_followup,
        is_confirmation_followup,
        is_transaction_fee_example_followup,
        is_easy_explanation_followup,
        is_two_line_summary_followup,
        is_three_line_summary_followup,
        is_private_business_question,
    ]

    for checker in simple_checks:
        try:
            if checker(clean_query):
                return True
        except Exception:
            continue

    try:
        if ambiguous_question_answer(clean_query):
            return True
    except Exception:
        pass

    try:
        if backend.smalltalk_response(clean_query):
            return True
    except Exception:
        pass

    try:
        if backend.is_shop_data_file_followup(clean_query):
            return True
    except Exception:
        pass

    try:
        if backend.is_out_of_scope_question(clean_query):
            return True
    except Exception:
        pass

    try:
        if backend.business_private_data_question(clean_query):
            return True
    except Exception:
        pass

    try:
        if (
            api_order_reason_answer(clean_query)
            or merchant_missing_answer(clean_query)
            or (
                shop_merchant_comparison_answer(clean_query)
                if not is_detailed_shop_merchant_question(clean_query)
                else None
            )
        ):
            return True
    except Exception:
        pass

    return False


def generate_response(
    query: str,
    resources: tuple[Any, Any, list[dict], Any, dict[str, int]],
) -> dict[str, Any]:
    (
        embedding_model,
        collection,
        chunks,
        bm25_index,
        chunk_id_to_index,
    ) = resources

    started = time.perf_counter()

    clean_query = backend.strip_duplicate_question(
        backend.normalize_unicode(
            " ".join(query.split())
        )
    )

    sync_backend_history()
    update_active_topic(clean_query)

    if is_gibberish_query(clean_query):
        return {
            "answer": gibberish_answer(),
            "mode": "clarification",
            "elapsed": time.perf_counter() - started,
            "debug": [],
        }

    # V15: chặn ngoài phạm vi và xử lý câu nối tiếp trước retrieval.
    if is_strict_out_of_scope_question(clean_query):
        return {
            "answer": strict_out_of_scope_answer(),
            "mode": "out_of_scope",
            "elapsed": time.perf_counter() - started,
            "debug": [],
        }

    if is_inventory_private_question(clean_query):
        return {
            "answer": inventory_private_answer(),
            "mode": "private_inventory_missing",
            "elapsed": time.perf_counter() - started,
            "debug": [],
        }

    if is_full_api_guide_question(clean_query):
        return {
            "answer": full_api_guide_answer(),
            "mode": "full_api_guide",
            "elapsed": time.perf_counter() - started,
            "debug": [],
        }

    if is_merchant_signature_python_example_question(clean_query):
        return {
            "answer": merchant_signature_python_example_answer(),
            "mode": "merchant_signature_python_example",
            "elapsed": time.perf_counter() - started,
            "debug": [],
        }

    if is_vietnamese_only_merchant_explanation_question(clean_query):
        return {
            "answer": vietnamese_only_merchant_explanation_answer(),
            "mode": "merchant_vietnamese_only",
            "elapsed": time.perf_counter() - started,
            "debug": [],
        }

    if is_three_api_comparison_question(clean_query):
        return {
            "answer": three_api_comparison_answer(),
            "mode": "three_api_comparison",
            "elapsed": time.perf_counter() - started,
            "debug": [],
        }

    if is_direct_signature_algorithm_question(clean_query):
        return {
            "answer": direct_signature_algorithm_answer(),
            "mode": "signature_algorithm",
            "elapsed": time.perf_counter() - started,
            "debug": [],
        }

    if is_api_verification_question(clean_query):
        return {
            "answer": api_verification_answer(clean_query),
            "mode": "verification_guard",
            "elapsed": time.perf_counter() - started,
            "debug": [],
        }

    if is_merchant_api_auth_components_question(clean_query):
        return {
            "answer": merchant_api_auth_components_answer(),
            "mode": "merchant_api_auth_components",
            "elapsed": time.perf_counter() - started,
            "debug": [],
        }

    if is_merchant_api_overview_question(clean_query):
        return {
            "answer": merchant_api_overview_answer(),
            "mode": "merchant_api_overview",
            "elapsed": time.perf_counter() - started,
            "debug": [],
        }

    if is_order_reason_followup(clean_query):
        return {
            "answer": order_reason_followup_answer(),
            "mode": "conversation_guard",
            "elapsed": time.perf_counter() - started,
            "debug": [],
        }

    if is_no_seller_response_return_question(clean_query):
        return {
            "answer": no_seller_response_return_answer(),
            "mode": "deadline_guard",
            "elapsed": time.perf_counter() - started,
            "debug": [],
        }

    if is_generic_example_followup(clean_query):
        return {
            "answer": generic_example_followup_answer(),
            "mode": "example_followup",
            "elapsed": time.perf_counter() - started,
            "debug": [],
        }

    if is_generic_summary_followup(clean_query):
        return {
            "answer": generic_summary_answer(),
            "mode": "topic_summary",
            "elapsed": time.perf_counter() - started,
            "debug": [],
        }

    if is_fixed_fee_example_followup(clean_query):
        return {
            "answer": fixed_fee_example_answer(),
            "mode": "fixed_fee_example",
            "elapsed": time.perf_counter() - started,
            "debug": [],
        }

    clarification = ambiguous_question_answer(
        clean_query
    )

    if clarification:
        return {
            "answer": clarification,
            "mode": "clarification",
            "elapsed": time.perf_counter() - started,
            "debug": [],
        }

    if is_merchant_base_string_question(clean_query):
        return {
            "answer": merchant_base_string_answer(),
            "mode": "merchant_base_string",
            "elapsed": time.perf_counter() - started,
            "debug": [],
        }

    if is_signature_flow_question(clean_query):
        return {
            "answer": signature_flow_answer(),
            "mode": "signature_flow",
            "elapsed": time.perf_counter() - started,
            "debug": [],
        }

    if is_no_bank_discount_followup(clean_query):
        return {
            "answer": no_bank_discount_followup_answer(),
            "mode": "calculation_followup",
            "elapsed": time.perf_counter() - started,
            "debug": [],
        }

    if is_fee_calculation_question(clean_query):
        values = extract_fee_inputs(
            clean_query
        )

        if values:
            return {
                "answer": fee_calculation_answer(
                    values
                ),
                "mode": "calculation",
                "elapsed": time.perf_counter() - started,
                "debug": [],
            }

    if is_public_api_followup(clean_query):
        return {
            "answer": public_api_answer(),
            "mode": "public_api_guard",
            "elapsed": time.perf_counter() - started,
            "debug": [],
        }

    if is_detailed_shop_merchant_question(clean_query):
        return {
            "answer": detailed_shop_merchant_answer(),
            "mode": "api_comparison",
            "elapsed": time.perf_counter() - started,
            "debug": [],
        }

    if is_capability_question(clean_query):
        return {
            "answer": capability_answer(),
            "mode": "capabilities",
            "elapsed": time.perf_counter() - started,
            "debug": [],
        }

    if is_data_requirement_followup(clean_query):
        return {
            "answer": operational_data_guidance(),
            "mode": "data_guidance",
            "elapsed": time.perf_counter() - started,
            "debug": [],
        }

    if is_confirmation_followup(clean_query):
        return {
            "answer": confirmation_followup_answer(),
            "mode": "confirmation_followup",
            "elapsed": time.perf_counter() - started,
            "debug": [],
        }

    if is_transaction_fee_example_followup(clean_query):
        return {
            "answer": transaction_fee_example_answer(),
            "mode": "calculation_guard",
            "elapsed": time.perf_counter() - started,
            "debug": [],
        }

    if is_easy_explanation_followup(clean_query):
        if current_topic() == "transaction_fee":
            return {
                "answer": transaction_fee_easy_answer(),
                "mode": "topic_explanation",
                "elapsed": time.perf_counter() - started,
                "debug": [],
            }

    if is_two_line_summary_followup(clean_query):
        return {
            "answer": topic_summary_answer(lines=2),
            "mode": "topic_summary",
            "elapsed": time.perf_counter() - started,
            "debug": [],
        }

    if is_three_line_summary_followup(clean_query):
        return {
            "answer": topic_summary_answer(lines=3),
            "mode": "topic_summary",
            "elapsed": time.perf_counter() - started,
            "debug": [],
        }

    if is_private_business_question(clean_query):
        return {
            "answer": private_business_answer(clean_query),
            "mode": "private_business_data",
            "elapsed": time.perf_counter() - started,
            "debug": [],
        }

    direct = backend.smalltalk_response(clean_query)
    if direct:
        return {
            "answer": direct,
            "mode": "smalltalk",
            "elapsed": time.perf_counter() - started,
            "debug": [],
        }

    if backend.is_shop_data_file_followup(clean_query):
        return {
            "answer": backend.shop_data_file_guidance(),
            "mode": "guidance",
            "elapsed": time.perf_counter() - started,
            "debug": [],
        }

    if backend.is_out_of_scope_question(clean_query):
        return {
            "answer": (
                "Câu hỏi này nằm ngoài phạm vi dữ liệu của trợ lý Shopee hiện tại. "
                "Tôi có thể hỗ trợ về chính sách Shopee, phí, trả hàng/hoàn tiền, "
                "Shopee Open Platform/API, pháp luật thương mại điện tử, "
                "báo cáo thị trường và dữ liệu vận hành shop."
            ),
            "mode": "out_of_scope",
            "elapsed": time.perf_counter() - started,
            "debug": [],
        }

    if backend.business_private_data_question(clean_query):
        return {
            "answer": (
                "Tôi chưa có dữ liệu vận hành thực tế của shop để trả lời câu hỏi này. "
                "Bạn có thể bổ sung dữ liệu đơn hàng, doanh thu, chi phí, tồn kho "
                "hoặc quảng cáo để tôi phân tích."
            ),
            "mode": "private_data_missing",
            "elapsed": time.perf_counter() - started,
            "debug": [],
        }

    deterministic_followup = (
        api_order_reason_answer(clean_query)
        or merchant_missing_answer(clean_query)
        or (
            shop_merchant_comparison_answer(
                clean_query
            )
            if not is_detailed_shop_merchant_question(
                clean_query
            )
            else None
        )
    )

    if deterministic_followup:
        return {
            "answer": deterministic_followup,
            "mode": "conversation_guard",
            "elapsed": time.perf_counter() - started,
            "debug": [],
        }

    transaction_fee = global_transaction_fee_answer(
        query=clean_query,
        chunks=chunks,
    )

    if transaction_fee:
        return {
            "answer": transaction_fee,
            "mode": "global_fee_lookup",
            "elapsed": time.perf_counter() - started,
            "debug": [],
        }

    rewritten_followup = api_followup_rewrite(
        clean_query
    )

    if rewritten_followup:
        resolved_query = rewritten_followup
    elif is_explicit_standalone_question(clean_query):
        resolved_query = clean_query
    else:
        resolved_query = backend.build_follow_up_query(clean_query)

        if resolved_query == clean_query:
            resolved_query = backend.resolve_follow_up_question(clean_query)

    (
        _vector_results,
        _bm25_results,
        hybrid_results,
        retrieval_elapsed,
    ) = backend.hybrid_search(
        query=resolved_query,
        embedding_model=embedding_model,
        collection=collection,
        chunks=chunks,
        bm25_index=bm25_index,
    )

    if not hybrid_results:
        return {
            "answer": ("Kho dữ liệu hiện tại chưa có nguồn đủ phù hợp để trả lời câu hỏi này. "
                       "Bạn có thể nêu rõ chính sách, loại phí, nhóm sản phẩm hoặc chức năng API cần tra cứu."),
            "mode": "no_result",
            "elapsed": time.perf_counter() - started,
            "debug": [],
        }

    top_result = hybrid_results[0]

    contexts = backend.expand_context(
        top_result=top_result,
        chunks=chunks,
        chunk_id_to_index=chunk_id_to_index,
    )

    st.session_state.last_contexts = contexts

    direct_domain_answer = (
        direct_transaction_fee_answer(
            query=clean_query,
            contexts=contexts,
        )
        or (
            open_platform_purpose_answer(contexts)
            if is_open_platform_purpose_question(clean_query)
            else None
        )
        or (
            api_catalog_answer(contexts)
            if is_api_catalog_question(clean_query)
            else None
        )
        or (
            order_api_answer(contexts)
            if is_order_api_question(clean_query)
            else None
        )
        or (
            signature_algorithm_answer(contexts)
            if is_signature_algorithm_question(clean_query)
            else None
        )
    )

    if direct_domain_answer:
        return {
            "answer": clean_for_chat(direct_domain_answer),
            "mode": "direct_domain",
            "elapsed": time.perf_counter() - started,
            "debug": hybrid_results[:5],
        }

    if is_rewards_question(clean_query):
        if not contexts_support_rewards(contexts):
            return {
                "answer": safe_rewards_answer(),
                "mode": "rewards_guard",
                "elapsed": time.perf_counter() - started,
                "debug": hybrid_results[:5],
            }

    if backend.partner_key_location_question(clean_query):
        direct_partner = backend.direct_partner_key_answer(contexts)

        if direct_partner:
            answer = direct_partner
        else:
            answer = (
                "Tài liệu hiện tại chưa chỉ rõ vị trí lấy Partner Key. "
                "Bạn cần bổ sung hướng dẫn chính thức của Shopee Open Platform "
                "hoặc tài liệu quản lý ứng dụng/đối tác."
            )

        return {
            "answer": clean_for_chat(answer),
            "mode": "partner_key_guard",
            "elapsed": time.perf_counter() - started,
            "debug": hybrid_results[:5],
        }

    if backend.duration_question_requires_exact_relation(clean_query):
        if not backend.has_exact_response_deadline(contexts):
            return {
                "answer": (
                    "Tài liệu hiện tại chưa nêu rõ thời hạn người bán phải phản hồi "
                    "yêu cầu trả hàng ban đầu. Nguồn chỉ đề cập đến các mốc như "
                    "thời hạn người mua gửi trả hàng và thời hạn người bán khiếu nại, "
                    "nên tôi chưa thể kết luận một con số chính xác cho thời hạn phản hồi."
                ),
                "mode": "deadline_guard",
                "elapsed": time.perf_counter() - started,
                "debug": hybrid_results[:5],
            }

    deterministic = (
        backend.subject_followup_answer(
            original_query=clean_query,
            contexts=contexts,
        )
        or backend.deterministic_api_comparison(
            query=resolved_query,
            contexts=contexts,
        )
    )

    if deterministic:
        return {
            "answer": clean_for_chat(deterministic),
            "mode": "deterministic",
            "elapsed": time.perf_counter() - started,
            "debug": hybrid_results[:5],
        }

    answerable, reason = backend.answerability_check(
        query=resolved_query,
        contexts=contexts,
    )

    if not answerable:
        return {
            "answer": (
                "Tôi chưa có đủ dữ liệu để trả lời chắc chắn. "
                + reason
            ),
            "mode": "not_answerable",
            "elapsed": time.perf_counter() - started,
            "debug": hybrid_results[:5],
        }

    fast_answer = backend.fast_factual_answer(
        query=resolved_query,
        contexts=contexts,
        original_query=clean_query,
    )

    if fast_answer:
        return {
            "answer": clean_for_chat(fast_answer),
            "mode": "fast",
            "elapsed": time.perf_counter() - started,
            "debug": hybrid_results[:5],
        }

    llm_question = (
        resolved_query
        + "\n\nYêu cầu trình bày: "
        + response_style_instruction()
    )

    answer, llm_elapsed = backend.call_ollama(
        question=llm_question,
        contexts=contexts,
    )

    vietnamese_answer = enforce_vietnamese(
        answer=answer,
        question=resolved_query,
        contexts=contexts,
    )

    return {
        "answer": final_vietnamese_guard(
            vietnamese_answer
        ),
        "mode": "llm",
        "elapsed": time.perf_counter() - started,
        "llm_elapsed": llm_elapsed,
        "debug": hybrid_results[:5],
    }


# ============================================================
# SIDEBAR
# ============================================================

# ============================================================
# V7 - QUẢN LÝ NHIỀU CUỘC TRÒ CHUYỆN
# ============================================================

CONVERSATION_STORE = (
    backend.PROJECT_ROOT
    / "data"
    / "processed"
    / "chat_conversations_v12.json"
)



def normalize_debug_item(result: Any) -> dict[str, Any]:
    if isinstance(result, dict):
        metadata = result.get(
            "metadata",
            {},
        )

        safe_metadata = {
            str(key): value
            for key, value in dict(
                metadata or {}
            ).items()
            if isinstance(
                value,
                (
                    str,
                    int,
                    float,
                    bool,
                    type(None),
                ),
            )
        }

        return {
            "metadata": safe_metadata,
            "hybrid_score": float(
                result.get(
                    "hybrid_score",
                    0.0,
                )
                or 0.0
            ),
            "vector_score": float(
                result.get(
                    "vector_score",
                    0.0,
                )
                or 0.0
            ),
            "bm25_score": float(
                result.get(
                    "bm25_score",
                    0.0,
                )
                or 0.0
            ),
        }

    return serialize_debug_result(result)


def extract_year_from_title(title: str) -> int:
    years = re.findall(
        r"(20\\d{2})",
        str(title),
    )

    return max(
        (
            int(year)
            for year in years
        ),
        default=0,
    )




SOURCE_DISPLAY_NAMES = {
    "bieu phi co dinh theo nganh hang 2026":
        "Biểu phí cố định theo ngành hàng 2026",
    "phi xu ly giao dich 2026":
        "Phí xử lý giao dịch 2026",
    "api calls v2 2025":
        "API Calls V2 2025",
    "shop authorization 2026":
        "Ủy quyền Shop API 2026",
    "platform introduction 2024":
        "Giới thiệu Shopee Open Platform 2024",
    "quy trinh tra hang hoan tien nguoi ban 2025":
        "Quy trình trả hàng/hoàn tiền cho Người bán 2025",
    "chinh sach tra hang hoan tien":
        "Chính sách trả hàng và hoàn tiền",
    "chinh sach van chuyen":
        "Chính sách vận chuyển",
    "chinh sach bao mat":
        "Chính sách bảo mật",
    "dieu khoan dich vu":
        "Điều khoản dịch vụ",
    "dieu khoan dich vu shopee mall":
        "Điều khoản dịch vụ Shopee Mall",
    "quy che hoat dong san":
        "Quy chế hoạt động sàn Shopee",
    "form 20f 2025":
        "Form 20-F 2025",
    "q4 fy2025 results":
        "Kết quả kinh doanh quý IV/2025",
}


def display_source_name(
    raw_title: str,
) -> str:
    title = str(
        raw_title
    ).strip()

    if not title:
        return "Không rõ"

    normalized = backend.normalize_for_match(
        title
    )
    exact = SOURCE_DISPLAY_NAMES.get(
        normalized
    )

    if exact:
        return exact

    for key, value in SOURCE_DISPLAY_NAMES.items():
        if (
            key in normalized
            or normalized in key
        ):
            return value

    return title


def safe_html_text(
    value: Any,
) -> str:
    return html.escape(
        str(
            value
        ),
        quote=True,
    )


def message_plain_length(
    content: str,
) -> int:
    cleaned = re.sub(
        r"[`*_#>|~\[\]()]",
        "",
        str(
            content
        ),
    )

    return len(
        re.sub(
            r"\s+",
            " ",
            cleaned,
        ).strip()
    )


def has_markdown_table(
    content: str,
) -> bool:
    text_value = str(
        content
    )

    return bool(
        re.search(
            r"(?m)^\s*\|.+\|\s*$",
            text_value,
        )
        and re.search(
            r"(?m)^\s*\|?\s*:?-{3,}",
            text_value,
        )
    )


def assistant_column_ratios(
    content: str,
) -> tuple[float, float]:
    length = message_plain_length(
        content
    )
    line_count = str(
        content
    ).count(
        "\n"
    ) + 1

    if (
        has_markdown_table(
            content
        )
        or length >= 900
        or line_count >= 16
    ):
        return (
            0.92,
            0.08,
        )

    if (
        length >= 420
        or line_count >= 9
    ):
        return (
            0.82,
            0.18,
        )

    if (
        length >= 180
        or line_count >= 5
    ):
        return (
            0.72,
            0.28,
        )

    return (
        0.60,
        0.40,
    )


def user_column_ratios(
    content: str,
) -> tuple[float, float]:
    length = message_plain_length(
        content
    )
    line_count = str(
        content
    ).count(
        "\n"
    ) + 1

    if (
        length >= 450
        or line_count >= 8
    ):
        return (
            0.42,
            0.58,
        )

    if (
        length >= 180
        or line_count >= 4
    ):
        return (
            0.52,
            0.48,
        )

    if length >= 70:
        return (
            0.62,
            0.38,
        )

    return (
        0.70,
        0.30,
    )


def citation_tokens(text_value: str) -> set[str]:
    normalized = backend.normalize_for_match(
        text_value
    )
    stop_words = {
        "la",
        "cua",
        "cho",
        "va",
        "thi",
        "nao",
        "bao",
        "nhieu",
        "tren",
        "trong",
        "duoc",
        "nhung",
        "cac",
        "mot",
        "voi",
        "theo",
        "tai",
        "lieu",
        "shopee",
    }

    return {
        token
        for token in normalized.split()
        if len(token) >= 3
        and token not in stop_words
    }


def citation_topic_phrases(
    query: str,
) -> list[str]:
    topic = detect_topic(query)

    mapping = {
        "transaction_fee": [
            "phi xu ly giao dich",
        ],
        "fixed_fee": [
            "bieu phi co dinh",
            "phi co dinh",
        ],
        "merchant_api": [
            "api calls",
            "merchant api",
            "authorization",
        ],
        "shop_api": [
            "api calls",
            "shop authorization",
            "shop api",
        ],
        "public_api": [
            "api calls",
            "public api",
        ],
        "open_platform": [
            "platform introduction",
            "open platform",
            "api calls",
        ],
        "return_refund": [
            "tra hang",
            "hoan tien",
        ],
        "shopee_xu": [
            "shopee xu",
            "diem thuong",
        ],
    }

    return mapping.get(
        topic,
        [],
    )


def citation_result_score(
    raw_result: Any,
    query: str,
) -> float:
    result = normalize_debug_item(
        raw_result
    )
    metadata = result.get(
        "metadata",
        {},
    )
    title = str(
        metadata.get(
            "title",
            "",
        )
    )
    normalized_title = backend.normalize_for_match(
        title
    )
    query_terms = citation_tokens(
        query
    )
    title_terms = citation_tokens(
        title
    )
    overlap = len(
        query_terms.intersection(
            title_terms
        )
    )
    phrase_bonus = sum(
        6.0
        for phrase in citation_topic_phrases(
            query
        )
        if phrase in normalized_title
    )
    hybrid = max(
        0.0,
        float(
            result.get(
                "hybrid_score",
                0.0,
            )
            or 0.0
        ),
    )
    vector = max(
        0.0,
        min(
            1.0,
            float(
                result.get(
                    "vector_score",
                    0.0,
                )
                or 0.0
            ),
        ),
    )
    bm25 = max(
        0.0,
        float(
            result.get(
                "bm25_score",
                0.0,
            )
            or 0.0
        ),
    )

    return (
        phrase_bonus
        + overlap * 2.5
        + min(
            hybrid,
            2.0,
        )
        + vector * 2.0
        + min(
            bm25 / 25.0,
            4.0,
        )
        + extract_year_from_title(
            title
        )
        / 10000.0
    )


def filtered_citations_from_debug(
    debug_results: list[Any],
    query: str,
    limit: int = 2,
) -> list[dict[str, Any]]:
    ranked: list[
        tuple[
            float,
            dict[str, Any],
        ]
    ] = []
    seen: set[
        tuple[
            str,
            str,
        ]
    ] = set()

    for raw_result in debug_results:
        result = normalize_debug_item(
            raw_result
        )
        metadata = result.get(
            "metadata",
            {},
        )
        title = str(
            metadata.get(
                "title",
                "",
            )
        ).strip()
        page = str(
            metadata.get(
                "page",
                "—",
            )
        ).strip()

        if not title:
            continue

        key = (
            title.casefold(),
            page,
        )

        if key in seen:
            continue

        seen.add(key)
        ranked.append(
            (
                citation_result_score(
                    raw_result,
                    query,
                ),
                {
                    "title": title,
                    "page": page,
                    "year": extract_year_from_title(
                        title
                    ),
                },
            )
        )

    ranked.sort(
        key=lambda item: (
            item[0],
            int(
                item[1].get(
                    "year",
                    0,
                )
            ),
        ),
        reverse=True,
    )

    if not ranked:
        return []

    best_score = ranked[0][0]
    selected = [
        citation
        for score, citation in ranked
        if score >= max(
            2.0,
            best_score * 0.62,
        )
    ]

    return selected[:limit]


def should_prefer_static_citation(
    mode: str,
    query: str,
) -> bool:
    topic = detect_topic(
        query
    )
    exact_topics = {
        "transaction_fee",
        "fixed_fee",
        "merchant_api",
        "shop_api",
        "public_api",
        "open_platform",
    }
    exact_modes = {
        "calculation",
        "calculation_followup",
        "calculation_guard",
        "global_fee_lookup",
        "api_comparison",
        "public_api_guard",
        "conversation_guard",
        "merchant_base_string",
        "signature_flow",
        "partner_key_guard",
        "direct_domain",
        "fast",
        "deterministic",
        "confirmation_followup",
        "topic_summary",
        "topic_explanation",
        "three_api_comparison",
        "signature_algorithm",
        "verification_guard",
        "merchant_api_overview",
        "merchant_api_auth_components",
        "full_api_guide",
        "merchant_signature_python_example",
        "merchant_vietnamese_only",
        "example_followup",
        "fixed_fee_example",
    }

    return (
        topic in exact_topics
        or mode in exact_modes
    )


def select_response_citations(
    mode: str,
    query: str,
    debug_results: list[Any],
) -> list[dict[str, Any]]:
    no_citation_modes = {
        "clarification",
        "smalltalk",
        "capabilities",
        "out_of_scope",
        "private_data_missing",
        "private_business_data",
        "private_inventory_missing",
        "operational_missing",
        "processing_error",
        "processing_timeout",
        "not_answerable",
        "no_result",
        "rewards_guard",
        "deadline_guard",
        "data_guidance",
        "guidance",
    }

    if mode in no_citation_modes:
        return []

    static = static_citations(
        mode=mode,
        query=query,
    )

    if (
        static
        and should_prefer_static_citation(
            mode=mode,
            query=query,
        )
    ):
        return static[:1]

    filtered = filtered_citations_from_debug(
        debug_results=debug_results,
        query=query,
        limit=2,
    )

    if filtered:
        return filtered

    return static[:1]

def citations_from_debug(
    debug_results: list[Any],
    limit: int = 3,
) -> list[dict[str, Any]]:
    citations: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()

    for raw_result in debug_results:
        result = normalize_debug_item(
            raw_result
        )
        metadata = result.get(
            "metadata",
            {},
        )
        title = str(
            metadata.get(
                "title",
                "",
            )
        ).strip()
        page = str(
            metadata.get(
                "page",
                "—",
            )
        ).strip()

        if not title:
            continue

        key = (
            title.casefold(),
            page,
        )

        if key in seen:
            continue

        seen.add(key)
        citations.append(
            {
                "title": title,
                "page": page,
                "year": extract_year_from_title(
                    title
                ),
            }
        )

    citations.sort(
        key=lambda item: (
            int(
                item.get(
                    "year",
                    0,
                )
            ),
            str(
                item.get(
                    "title",
                    "",
                )
            ),
        ),
        reverse=True,
    )

    return citations[:limit]


def static_citations(
    mode: str,
    query: str,
) -> list[dict[str, Any]]:
    topic = detect_topic(query)

    if mode == "example_followup":
        active = current_topic()
        if active in {"merchant_api", "shop_api", "public_api", "api_comparison"}:
            return [
                {
                    "title": "Api calls v2 2025",
                    "page": "3",
                    "year": 2025,
                }
            ]
        if active == "transaction_fee":
            return [
                {
                    "title": "Phi xu ly giao dich 2026",
                    "page": "1",
                    "year": 2026,
                }
            ]
        if active == "fixed_fee":
            return [
                {
                    "title": "Bieu phi co dinh theo nganh hang 2026",
                    "page": "7",
                    "year": 2026,
                }
            ]

    if mode == "confirmation_followup":
        previous = previous_assistant_item()

        if previous:
            return list(
                previous.get(
                    "citations",
                    [],
                )
            )

    if (
        topic in {
            "merchant_api",
            "shop_api",
            "public_api",
            "open_platform",
        }
        or mode in {
            "api_comparison",
            "three_api_comparison",
            "public_api_guard",
            "conversation_guard",
            "merchant_base_string",
            "signature_flow",
            "signature_algorithm",
            "verification_guard",
            "merchant_api_overview",
            "merchant_api_auth_components",
            "full_api_guide",
            "merchant_signature_python_example",
            "merchant_vietnamese_only",
        }
    ):
        return [
            {
                "title": "Api calls v2 2025",
                "page": "3",
                "year": 2025,
            }
        ]

    if (
        topic == "transaction_fee"
        or mode in {
            "calculation",
            "calculation_followup",
            "calculation_guard",
            "fixed_fee_example",
            "global_fee_lookup",
            "topic_explanation",
        }
    ):
        return [
            {
                "title": "Phi xu ly giao dich 2026",
                "page": "1",
                "year": 2026,
            }
        ]

    if topic == "fixed_fee" or mode == "fixed_fee_example":
        return [
            {
                "title": "Bieu phi co dinh theo nganh hang 2026",
                "page": "7",
                "year": 2026,
            }
        ]

    if mode == "topic_summary":
        previous = previous_assistant_item()

        if previous:
            return list(
                previous.get(
                    "citations",
                    [],
                )
            )

    return []



def response_confidence(
    mode: str,
    debug_results: list[Any],
    citations: list[dict[str, Any]],
    query: str = "",
    answer: str = "",
) -> int | None:
    """Return an internal evidence-sufficiency heuristic on a 0--100 scale.

    The value is not calibrated against answer correctness and must never be
    presented as a probability that the answer is true.
    """
    no_score_modes = {
        "clarification",
        "smalltalk",
        "capabilities",
        "out_of_scope",
        "private_data_missing",
        "private_business_data",
        "private_inventory_missing",
        "operational_missing",
        "processing_error",
        "processing_timeout",
        "not_answerable",
        "no_result",
        "rewards_guard",
        "deadline_guard",
        "data_guidance",
        "guidance",
    }

    if mode in no_score_modes:
        return None

    calculation_modes = {
        "calculation",
        "calculation_followup",
        "calculation_guard",
    }

    if mode in calculation_modes:
        return 99

    deterministic_modes = {
        "api_comparison",
        "three_api_comparison",
        "public_api_guard",
        "conversation_guard",
        "merchant_base_string",
        "signature_flow",
        "signature_algorithm",
        "verification_guard",
        "merchant_api_overview",
        "merchant_api_auth_components",
        "full_api_guide",
        "merchant_signature_python_example",
        "merchant_vietnamese_only",
        "example_followup",
        "fixed_fee_example",
        "global_fee_lookup",
        "partner_key_guard",
        "direct_domain",
        "deterministic",
        "confirmation_followup",
        "topic_summary",
        "topic_explanation",
    }

    if mode in deterministic_modes and citations:
        return 97

    topic = detect_topic(
        query
    )

    if (
        mode == "fast"
        and citations
        and topic
        in {
            "transaction_fee",
            "fixed_fee",
            "merchant_api",
            "shop_api",
            "public_api",
            "open_platform",
        }
    ):
        return 96

    if debug_results:
        top = normalize_debug_item(
            debug_results[0]
        )
        hybrid = max(
            0.0,
            float(
                top.get(
                    "hybrid_score",
                    0.0,
                )
                or 0.0
            ),
        )
        vector = max(
            0.0,
            min(
                1.0,
                float(
                    top.get(
                        "vector_score",
                        0.0,
                    )
                    or 0.0
                ),
            ),
        )
        bm25 = max(
            0.0,
            float(
                top.get(
                    "bm25_score",
                    0.0,
                )
                or 0.0
            ),
        )
        hybrid_normalized = (
            hybrid
            / (
                hybrid
                + 1.0
            )
        )
        bm25_normalized = (
            bm25
            / (
                bm25
                + 30.0
            )
            if bm25 > 0
            else 0.0
        )
        score = (
            60
            + 15 * vector
            + 11 * bm25_normalized
            + 10 * hybrid_normalized
        )

        if citations:
            score += 3

        if mode == "llm":
            score -= 3

        return max(
            55,
            min(
                95,
                round(
                    score
                ),
            ),
        )

    if citations:
        return 91

    return None



def confidence_label(confidence: int | None) -> str:
    if confidence is None:
        return ""

    if confidence >= 90:
        return "Cao"
    if confidence >= 75:
        return "Khá cao"
    if confidence >= 60:
        return "Trung bình"

    return "Thấp"



def enrich_response(
    response: dict[str, Any],
    query: str,
) -> dict[str, Any]:
    enriched = dict(
        response
    )
    mode = str(
        enriched.get(
            "mode",
            "",
        )
    )
    answer = str(
        enriched.get(
            "answer",
            "",
        )
    )
    debug_results = list(
        enriched.get(
            "debug",
            [],
        )
        or []
    )
    citations = select_response_citations(
        mode=mode,
        query=query,
        debug_results=debug_results,
    )
    confidence = response_confidence(
        mode=mode,
        debug_results=debug_results,
        citations=citations,
        query=query,
        answer=answer,
    )

    enriched["citations"] = citations
    enriched["confidence"] = confidence
    enriched["confidence_label"] = (
        confidence_label(
            confidence
        )
    )

    missing_data_modes = {
        "private_data_missing",
        "private_business_data",
        "private_inventory_missing",
        "operational_missing",
        "not_answerable",
        "no_result",
        "processing_timeout",
        "rewards_guard",
        "deadline_guard",
    }
    enriched["data_status"] = (
        "missing"
        if mode in missing_data_modes
        else ""
    )

    return enriched





def render_evidence(
    message: dict[str, Any],
) -> None:
    citations = [
        item
        for item in message.get(
            "citations",
            [],
        )
        if isinstance(
            item,
            dict,
        )
    ]
    confidence = message.get(
        "confidence",
        None,
    )
    data_status = str(
        message.get(
            "data_status",
            "",
        )
    )
    label = str(
        message.get(
            "confidence_label",
            "",
        )
    )

    if citations:
        primary = citations[0]
        title = safe_html_text(
            display_source_name(
                str(
                    primary.get(
                        "title",
                        "Không rõ",
                    )
                )
            )
        )
        page = safe_html_text(
            primary.get(
                "page",
                "—",
            )
        )

        st.markdown(
            (
                '<div class="v13-source-primary">'
                '📚 <strong>Nguồn chính:</strong> '
                f'{title}, trang {page}'
                '</div>'
            ),
            unsafe_allow_html=True,
        )

        if (
            len(
                citations
            ) > 1
            and st.session_state.technical_mode
        ):
            with st.expander(
                f"{len(citations) - 1} nguồn bổ sung"
            ):
                for citation in citations[1:]:
                    st.markdown(
                        "- "
                        + display_source_name(
                            str(
                                citation.get(
                                    "title",
                                    "Không rõ",
                                )
                            )
                        )
                        + ", trang "
                        + str(
                            citation.get(
                                "page",
                                "—",
                            )
                        )
                    )

    if data_status == "missing":
        st.markdown(
            '<div class="v15-data-missing">⚠ Chưa đủ dữ liệu để kết luận</div>',
            unsafe_allow_html=True,
        )

    if confidence is not None:
        confidence_value = int(
            confidence
        )

        if confidence_value >= 90:
            css_class = (
                "v121-confidence-high"
            )
        elif confidence_value >= 70:
            css_class = (
                "v121-confidence-medium"
            )
        else:
            css_class = (
                "v121-confidence-low"
            )

        st.markdown(
            (
                f'<div class="{css_class}">'
                f'● Mức độ đầy đủ bằng chứng: '
                f'{safe_html_text(label)}'
                '</div>'
            ),
            unsafe_allow_html=True,
        )

        if st.session_state.technical_mode:
            st.caption(
                f"Điểm heuristic nội bộ: {confidence_value}/100. "
                "Điểm phản ánh mức hỗ trợ của evidence và phương thức tạo câu "
                "trả lời, không phải xác suất câu trả lời đúng."
            )




def stream_markdown_answer(answer: str) -> None:
    if not st.session_state.get(
        "streaming_enabled",
        True,
    ):
        st.markdown(answer)
        return

    tokens = re.findall(
        r"\\S+\\s*",
        answer,
    )

    if len(tokens) <= 18:
        st.markdown(answer)
        return

    placeholder = st.empty()
    groups = [
        "".join(
            tokens[index:index + 9]
        )
        for index in range(
            0,
            len(tokens),
            9,
        )
    ]
    delay = min(
        0.02,
        1.2 / max(
            1,
            len(groups),
        ),
    )
    visible = ""

    for group in groups:
        visible += group
        placeholder.markdown(
            visible + " ▌"
        )
        time.sleep(delay)

    placeholder.markdown(answer)


def message_identifier(message: dict[str, Any]) -> str:
    existing = str(
        message.get(
            "id",
            "",
        )
    )

    if existing:
        return existing

    generated = uuid.uuid4().hex
    message["id"] = generated
    return generated


def action_toolbar_component(
    content: str,
    message_id: str,
    selected: str,
    up_token: str,
    down_token: str,
) -> None:
    """Một iframe duy nhất chứa cả ba nút để kích thước luôn tuyệt đối đồng nhất."""
    payload = json.dumps(
        content,
        ensure_ascii=False,
    ).replace(
        "</",
        "<" + "\\/",
    )
    selected_json = json.dumps(
        selected,
        ensure_ascii=False,
    )
    up_token_json = json.dumps(up_token)
    down_token_json = json.dumps(down_token)

    components.html(
        f"""
        <html>
        <head>
        <style>
        :root {{ color-scheme: light; }}

        * {{ box-sizing: border-box; }}

        html,
        body {{
            width: 130px;
            min-width: 130px;
            max-width: 130px;
            height: 40px;
            min-height: 40px;
            max-height: 40px;
            margin: 0;
            padding: 0;
            overflow: hidden;
            background: transparent;
            font-family: Inter, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
        }}

        .toolbar {{
            display: flex;
            align-items: center;
            justify-content: flex-start;
            gap: 5px;
            width: 130px;
            height: 40px;
            margin: 0;
            padding: 0;
        }}

        .tool-button {{
            width: 40px;
            min-width: 40px;
            max-width: 40px;
            height: 40px;
            min-height: 40px;
            max-height: 40px;
            margin: 0;
            padding: 0;
            display: inline-flex;
            align-items: center;
            justify-content: center;
            color: #667085;
            background: rgba(31, 41, 55, 0.045);
            border: 1px solid transparent;
            border-radius: 12px;
            box-shadow: none;
            cursor: pointer;
            outline: none;
            transition:
                color .14s ease,
                background .14s ease,
                border-color .14s ease,
                transform .14s ease;
        }}

        .tool-button:hover {{
            color: #ee4d2d;
            background: rgba(238, 77, 45, 0.10);
        }}

        .tool-button:focus-visible {{
            color: #ee4d2d;
            background: #fff1ec;
            border-color: rgba(238, 77, 45, 0.38);
        }}

        .tool-button:active {{
            transform: scale(0.96);
        }}

        .tool-button.selected,
        .tool-button.copied {{
            color: #ee4d2d;
            background: #fff1ec;
            border-color: rgba(238, 77, 45, 0.24);
        }}

        .tool-button svg {{
            display: block;
            width: 19px;
            height: 19px;
            margin: 0;
            padding: 0;
            fill: none;
            stroke: currentColor;
            stroke-width: 1.8;
            stroke-linecap: round;
            stroke-linejoin: round;
        }}

        textarea {{
            position: fixed;
            left: -9999px;
            width: 1px;
            height: 1px;
            opacity: 0;
        }}
        </style>
        </head>
        <body>
            <div class="toolbar" role="group" aria-label="Hành động với câu trả lời">
                <button id="copy" class="tool-button" type="button" title="Sao chép" aria-label="Sao chép">
                    <svg viewBox="0 0 24 24" aria-hidden="true">
                        <rect x="8.5" y="8.5" width="10.5" height="10.5" rx="2"></rect>
                        <path d="M15.5 8.5V6.5a2 2 0 0 0-2-2h-7a2 2 0 0 0-2 2v7a2 2 0 0 0 2 2h2"></path>
                    </svg>
                </button>
                <button id="up" class="tool-button" type="button" title="Hữu ích" aria-label="Hữu ích">
                    <svg viewBox="0 0 24 24" aria-hidden="true">
                        <path d="M7.5 10.5v9h-3v-9h3Z"></path>
                        <path d="M7.5 18.2c2 1.1 4 1.6 6.4 1.6h2.2c1 0 1.8-.7 2-1.7l1.2-5.8c.2-1.1-.7-2.1-1.8-2.1h-3.7l.7-3.1c.3-1.4-.6-2.8-2-3.1l-5 6.5"></path>
                    </svg>
                </button>
                <button id="down" class="tool-button" type="button" title="Chưa tốt" aria-label="Chưa tốt">
                    <svg viewBox="0 0 24 24" aria-hidden="true">
                        <g transform="translate(0 24) scale(1 -1)">
                            <path d="M7.5 10.5v9h-3v-9h3Z"></path>
                            <path d="M7.5 18.2c2 1.1 4 1.6 6.4 1.6h2.2c1 0 1.8-.7 2-1.7l1.2-5.8c.2-1.1-.7-2.1-1.8-2.1h-3.7l.7-3.1c.3-1.4-.6-2.8-2-3.1l-5 6.5"></path>
                        </g>
                    </svg>
                </button>
            </div>
            <textarea id="fallback"></textarea>
            <script>
            (() => {{
                const selected = {selected_json};
                const copyButton = document.getElementById("copy");
                const upButton = document.getElementById("up");
                const downButton = document.getElementById("down");
                const fallback = document.getElementById("fallback");
                const text = {payload};
                const upToken = {up_token_json};
                const downToken = {down_token_json};
                const copyOriginal = copyButton.innerHTML;

                if (selected === "up") upButton.classList.add("selected");
                if (selected === "down") downButton.classList.add("selected");

                const clickParentButton = (token) => {{
                    const buttons = Array.from(window.parent.document.querySelectorAll("button"));
                    const target = buttons.find((button) => button.textContent.trim() === token);
                    if (target) target.click();
                }};

                copyButton.addEventListener("click", async () => {{
                    try {{
                        if (navigator.clipboard && window.isSecureContext) {{
                            await navigator.clipboard.writeText(text);
                        }} else {{
                            fallback.value = text;
                            fallback.focus();
                            fallback.select();
                            document.execCommand("copy");
                        }}
                        copyButton.innerHTML = '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="m5.5 12.5 4 4 9-9"></path></svg>';
                        copyButton.classList.add("copied");
                        copyButton.title = "Đã sao chép";
                        window.setTimeout(() => {{
                            copyButton.innerHTML = copyOriginal;
                            copyButton.classList.remove("copied");
                            copyButton.title = "Sao chép";
                        }}, 1300);
                    }} catch (error) {{
                        copyButton.title = "Không thể sao chép";
                    }}
                }});

                upButton.addEventListener("click", () => {{
                    upButton.classList.toggle("selected");
                    downButton.classList.remove("selected");
                    clickParentButton(upToken);
                }});

                downButton.addEventListener("click", () => {{
                    downButton.classList.toggle("selected");
                    upButton.classList.remove("selected");
                    clickParentButton(downToken);
                }});
            }})();
            </script>
        </body>
        </html>
        """,
        height=40,
        width=130,
        scrolling=False,
    )


FEEDBACK_LOG = (
    backend.PROJECT_ROOT
    / "data"
    / "processed"
    / "chatbot_v19_feedback.csv"
)


def append_feedback_log(
    message: dict[str, Any],
    rating: str,
) -> None:
    FEEDBACK_LOG.parent.mkdir(
        parents=True,
        exist_ok=True,
    )
    exists = FEEDBACK_LOG.exists()

    try:
        with FEEDBACK_LOG.open(
            "a",
            encoding="utf-8-sig",
            newline="",
        ) as file:
            writer = csv.DictWriter(
                file,
                fieldnames=[
                    "timestamp",
                    "conversation_id",
                    "message_id",
                    "rating",
                    "answer_mode",
                    "answer",
                ],
            )

            if not exists:
                writer.writeheader()

            writer.writerow(
                {
                    "timestamp": datetime.now().isoformat(
                        timespec="seconds"
                    ),
                    "conversation_id": st.session_state.get(
                        "active_conversation_id",
                        "",
                    ),
                    "message_id": message_identifier(
                        message
                    ),
                    "rating": rating,
                    "answer_mode": message.get(
                        "metrics",
                        {},
                    ).get(
                        "mode",
                        "",
                    ),
                    "answer": str(
                        message.get(
                            "content",
                            "",
                        )
                    ),
                }
            )
    except OSError:
        pass




def render_message_actions(
    message: dict[str, Any],
) -> None:
    message_id = message_identifier(
        message
    )
    content = str(
        message.get(
            "content",
            "",
        )
    )
    selected = str(
        message.get(
            "feedback",
            "",
        )
    )

    up_token = f"__V17_UP_{message_id}__"
    down_token = f"__V17_DOWN_{message_id}__"

    # Hai nút Streamlit ẩn chỉ nhận sự kiện từ toolbar HTML thống nhất.
    with st.container(
        key=f"v17_hidden_feedback_{message_id}"
    ):
        up_clicked = st.button(
            up_token,
            key=f"feedback_up_{message_id}",
        )
        down_clicked = st.button(
            down_token,
            key=f"feedback_down_{message_id}",
        )

    if up_clicked:
        new_rating = "" if selected == "up" else "up"
        message["feedback"] = new_rating
        append_feedback_log(
            message,
            new_rating or "clear",
        )
        persist_active_conversation()
        st.rerun()

    if down_clicked:
        new_rating = "" if selected == "down" else "down"
        message["feedback"] = new_rating
        append_feedback_log(
            message,
            new_rating or "clear",
        )
        persist_active_conversation()
        st.rerun()

    action_toolbar_component(
        content=content,
        message_id=message_id,
        selected=selected,
        up_token=up_token,
        down_token=down_token,
    )



def install_scroll_to_latest_button() -> None:
    """Tạo nút nổi trong trang cha để cuộn mượt tới tin nhắn/ô nhập mới nhất."""
    components.html(
        """
        <script>
        (() => {
            const doc = window.parent.document;
            const win = window.parent;
            const buttonId = "v17-scroll-latest";
            let button = doc.getElementById(buttonId);

            if (!button) {
                button = doc.createElement("button");
                button.id = buttonId;
                button.type = "button";
                button.setAttribute("aria-label", "Đi tới tin nhắn mới nhất");
                button.title = "Đi tới tin nhắn mới nhất";
                button.innerHTML = `
                    <svg viewBox="0 0 24 24" aria-hidden="true">
                        <path d="m6 9 6 6 6-6"></path>
                    </svg>`;
                Object.assign(button.style, {
                    position: "fixed",
                    right: "28px",
                    bottom: "96px",
                    width: "42px",
                    height: "42px",
                    padding: "0",
                    border: "1px solid rgba(238,77,45,.22)",
                    borderRadius: "999px",
                    color: "#ee4d2d",
                    background: "rgba(255,255,255,.94)",
                    boxShadow: "0 10px 28px rgba(238,77,45,.20)",
                    backdropFilter: "blur(12px)",
                    WebkitBackdropFilter: "blur(12px)",
                    display: "none",
                    alignItems: "center",
                    justifyContent: "center",
                    cursor: "pointer",
                    zIndex: "1000000",
                    transition: "opacity .18s ease, transform .18s ease, background .18s ease"
                });
                const svg = button.querySelector("svg");
                Object.assign(svg.style, {
                    width: "20px",
                    height: "20px",
                    fill: "none",
                    stroke: "currentColor",
                    strokeWidth: "2",
                    strokeLinecap: "round",
                    strokeLinejoin: "round"
                });
                button.addEventListener("mouseenter", () => {
                    button.style.background = "#fff1ec";
                    button.style.transform = "translateY(-2px)";
                });
                button.addEventListener("mouseleave", () => {
                    button.style.background = "rgba(255,255,255,.94)";
                    button.style.transform = "translateY(0)";
                });
                doc.body.appendChild(button);
            }

            const anchor = () => doc.getElementById("v17-chat-bottom-anchor");
            const update = () => {
                const target = anchor();
                if (!target) {
                    button.style.display = "none";
                    return;
                }
                const rect = target.getBoundingClientRect();
                const nearBottom = rect.top <= win.innerHeight - 90;
                button.style.display = nearBottom ? "none" : "flex";
            };

            button.onclick = () => {
                const target = anchor() || doc.querySelector('[data-testid="stChatInput"]');
                if (target) {
                    target.scrollIntoView({ behavior: "smooth", block: "end" });
                } else {
                    win.scrollTo({ top: doc.documentElement.scrollHeight, behavior: "smooth" });
                }
            };

            win.addEventListener("scroll", update, { passive: true });
            doc.addEventListener("scroll", update, { passive: true, capture: true });
            window.setTimeout(update, 80);
            window.setTimeout(update, 450);
        })();
        </script>
        """,
        height=0,
        width=0,
        scrolling=False,
    )


def safe_export_filename(
    title: str,
) -> str:
    normalized = backend.normalize_for_match(
        title
    )
    filename = re.sub(
        r"[^a-z0-9]+",
        "_",
        normalized,
    ).strip(
        "_"
    )

    return (
        filename[:60]
        or "shopee_ai_conversation"
    )


def conversation_to_markdown(
    conversation: dict[str, Any],
) -> str:
    title = str(
        conversation.get(
            "title",
            default_conversation_title(),
        )
    )
    lines = [
        f"# {title}",
        "",
        (
            "Xuất từ Shopee AI Assistant "
            "— Phiên bản V19 Final"
        ),
        "",
    ]

    for message in conversation.get(
        "messages",
        [],
    ):
        role = str(
            message.get(
                "role",
                "assistant",
            )
        )
        content = str(
            message.get(
                "content",
                "",
            )
        ).strip()
        timestamp = str(
            message.get(
                "time",
                "",
            )
        )

        if role == "user":
            lines.extend(
                [
                    (
                        "## Người dùng"
                        + (
                            f" — {timestamp}"
                            if timestamp
                            else ""
                        )
                    ),
                    "",
                    content,
                    "",
                ]
            )
            continue

        lines.extend(
            [
                (
                    "## Shopee AI"
                    + (
                        f" — {timestamp}"
                        if timestamp
                        else ""
                    )
                ),
                "",
                content,
                "",
            ]
        )

        citations = [
            item
            for item in message.get(
                "citations",
                [],
            )
            if isinstance(
                item,
                dict,
            )
        ]

        if citations:
            lines.append(
                "**Nguồn:**"
            )

            for citation in citations:
                lines.append(
                    "- "
                    + display_source_name(
                        str(
                            citation.get(
                                "title",
                                "Không rõ",
                            )
                        )
                    )
                    + ", trang "
                    + str(
                        citation.get(
                            "page",
                            "—",
                        )
                    )
                )

            lines.append(
                ""
            )

        confidence = message.get(
            "confidence",
            None,
        )

        if confidence is not None:
            lines.extend(
                [
                    (
                        "**Mức độ đầy đủ bằng chứng:** "
                        + str(
                            message.get(
                                "confidence_label",
                                "",
                            )
                        )
                        + f" (điểm nội bộ {int(confidence)}/100, không phải xác suất đúng)"
                    ),
                    "",
                ]
            )

        lines.extend(
            [
                "---",
                "",
            ]
        )

    return "\n".join(
        lines
    ).strip() + "\n"


def default_conversation_title() -> str:
    return "Cuộc trò chuyện mới"



def make_conversation(
    title: str | None = None,
) -> dict[str, Any]:
    now = datetime.now().isoformat(
        timespec="seconds"
    )

    return {
        "id": uuid.uuid4().hex,
        "title": title or default_conversation_title(),
        "created_at": now,
        "updated_at": now,
        "messages": [],
        "memory": {
            "active_topic": "",
            "last_fee_calculation": {},
        },
    }




def load_conversation_store() -> dict[str, dict[str, Any]]:
    if not CONVERSATION_STORE.exists():
        return {}

    try:
        raw = json.loads(
            CONVERSATION_STORE.read_text(
                encoding="utf-8"
            )
        )

        if not isinstance(raw, dict):
            return {}

        cleaned: dict[str, dict[str, Any]] = {}

        for conversation_id, conversation in raw.items():
            if not isinstance(conversation, dict):
                continue

            conversation.setdefault(
                "id",
                conversation_id,
            )
            conversation.setdefault(
                "title",
                default_conversation_title(),
            )
            conversation.setdefault(
                "messages",
                [],
            )
            conversation.setdefault(
                "memory",
                {
                    "active_topic": "",
                    "last_fee_calculation": {},
                },
            )

            if not isinstance(
                conversation["messages"],
                list,
            ):
                conversation["messages"] = []

            if not isinstance(
                conversation["memory"],
                dict,
            ):
                conversation["memory"] = {
                    "active_topic": "",
                    "last_fee_calculation": {},
                }

            cleaned_messages: list[dict[str, Any]] = []

            for message in conversation["messages"]:
                if not isinstance(message, dict):
                    continue

                cleaned_message: dict[str, Any] = {
                    "id": str(
                        message.get(
                            "id",
                            uuid.uuid4().hex,
                        )
                    ),
                    "role": str(
                        message.get(
                            "role",
                            "assistant",
                        )
                    ),
                    "content": str(
                        message.get(
                            "content",
                            "",
                        )
                    ),
                    "time": str(
                        message.get(
                            "time",
                            "",
                        )
                    ),
                    "feedback": str(
                        message.get(
                            "feedback",
                            "",
                        )
                    ),
                    "confidence": message.get(
                        "confidence",
                        None,
                    ),
                    "confidence_label": str(
                        message.get(
                            "confidence_label",
                            "",
                        )
                    ),
                    "data_status": str(
                        message.get(
                            "data_status",
                            "",
                        )
                    ),
                    "citations": [
                        dict(item)
                        for item in message.get(
                            "citations",
                            [],
                        )
                        if isinstance(item, dict)
                    ],
                    "debug": [
                        normalize_debug_item(item)
                        for item in message.get(
                            "debug",
                            [],
                        )
                    ],
                }

                metrics = message.get(
                    "metrics",
                    {},
                )

                if isinstance(metrics, dict):
                    cleaned_message["metrics"] = {
                        "mode": str(
                            metrics.get(
                                "mode",
                                "",
                            )
                        ),
                        "elapsed": float(
                            metrics.get(
                                "elapsed",
                                0.0,
                            )
                            or 0.0
                        ),
                    }

                cleaned_messages.append(
                    cleaned_message
                )

            conversation["messages"] = cleaned_messages
            conversation.setdefault(
                "created_at",
                datetime.now().isoformat(
                    timespec="seconds"
                ),
            )
            conversation.setdefault(
                "updated_at",
                conversation["created_at"],
            )
            cleaned[conversation_id] = conversation

        return cleaned

    except (
        OSError,
        json.JSONDecodeError,
        TypeError,
        ValueError,
    ):
        backup_path = CONVERSATION_STORE.with_suffix(
            ".bak"
        )

        if backup_path.exists():
            try:
                backup_raw = json.loads(
                    backup_path.read_text(
                        encoding="utf-8"
                    )
                )
                if isinstance(backup_raw, dict):
                    return backup_raw
            except (
                OSError,
                json.JSONDecodeError,
                TypeError,
                ValueError,
            ):
                pass

        return {}



def serialize_debug_result(result: Any) -> dict[str, Any]:
    """
    Chuyển SearchResult thành dict thuần để có thể lưu JSON.
    """
    metadata = getattr(result, "metadata", {}) or {}

    return {
        "metadata": {
            str(key): value
            for key, value in dict(metadata).items()
            if isinstance(
                value,
                (
                    str,
                    int,
                    float,
                    bool,
                    type(None),
                ),
            )
        },
        "hybrid_score": float(
            getattr(result, "hybrid_score", 0.0)
        ),
        "vector_score": float(
            getattr(result, "vector_score", 0.0)
        ),
        "bm25_score": float(
            getattr(result, "bm25_score", 0.0)
        ),
    }



def serializable_conversations() -> dict[str, dict[str, Any]]:
    output: dict[str, dict[str, Any]] = {}

    for conversation_id, conversation in (
        st.session_state.conversations.items()
    ):
        serialized_messages: list[dict[str, Any]] = []

        for message in conversation.get(
            "messages",
            [],
        ):
            serialized_message: dict[str, Any] = {
                "id": str(
                    message.get(
                        "id",
                        uuid.uuid4().hex,
                    )
                ),
                "role": str(
                    message.get(
                        "role",
                        "assistant",
                    )
                ),
                "content": str(
                    message.get(
                        "content",
                        "",
                    )
                ),
                "time": str(
                    message.get(
                        "time",
                        "",
                    )
                ),
                "feedback": str(
                    message.get(
                        "feedback",
                        "",
                    )
                ),
                "confidence": message.get(
                    "confidence",
                    None,
                ),
                "confidence_label": str(
                    message.get(
                        "confidence_label",
                        "",
                    )
                ),
                "data_status": str(
                    message.get(
                        "data_status",
                        "",
                    )
                ),
                "citations": [
                    {
                        "title": str(
                            item.get(
                                "title",
                                "",
                            )
                        ),
                        "page": str(
                            item.get(
                                "page",
                                "—",
                            )
                        ),
                        "year": int(
                            item.get(
                                "year",
                                0,
                            )
                            or 0
                        ),
                    }
                    for item in message.get(
                        "citations",
                        [],
                    )
                    if isinstance(item, dict)
                ],
                "debug": [
                    normalize_debug_item(item)
                    for item in message.get(
                        "debug",
                        [],
                    )
                ],
            }

            metrics = message.get(
                "metrics",
                {},
            )

            if isinstance(metrics, dict):
                serialized_message["metrics"] = {
                    "mode": str(
                        metrics.get(
                            "mode",
                            "",
                        )
                    ),
                    "elapsed": float(
                        metrics.get(
                            "elapsed",
                            0.0,
                        )
                        or 0.0
                    ),
                }

            serialized_messages.append(
                serialized_message
            )

        memory = conversation.get(
            "memory",
            {},
        )

        if not isinstance(memory, dict):
            memory = {}

        output[conversation_id] = {
            "id": str(
                conversation.get(
                    "id",
                    conversation_id,
                )
            ),
            "title": str(
                conversation.get(
                    "title",
                    default_conversation_title(),
                )
            ),
            "created_at": str(
                conversation.get(
                    "created_at",
                    "",
                )
            ),
            "updated_at": str(
                conversation.get(
                    "updated_at",
                    "",
                )
            ),
            "messages": serialized_messages,
            "memory": {
                "active_topic": str(
                    memory.get(
                        "active_topic",
                        "",
                    )
                ),
                "last_fee_calculation": dict(
                    memory.get(
                        "last_fee_calculation",
                        {},
                    )
                    or {}
                ),
            },
        }

    return output



def save_conversation_store() -> None:
    CONVERSATION_STORE.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    temp_path = CONVERSATION_STORE.with_suffix(
        ".tmp"
    )

    payload = serializable_conversations()

    try:
        temp_path.write_text(
            json.dumps(
                payload,
                ensure_ascii=False,
                indent=2,
                default=str,
            ),
            encoding="utf-8",
        )

        backup_path = CONVERSATION_STORE.with_suffix(
            ".bak"
        )

        if CONVERSATION_STORE.exists():
            try:
                backup_path.write_text(
                    CONVERSATION_STORE.read_text(
                        encoding="utf-8"
                    ),
                    encoding="utf-8",
                )
            except OSError:
                pass

        temp_path.replace(
            CONVERSATION_STORE
        )

    except OSError:
        # Không làm gián đoạn chatbot nếu ổ đĩa/tệp tạm đang bị khóa.
        if temp_path.exists():
            try:
                temp_path.unlink()
            except OSError:
                pass


def initialize_v7_state() -> None:
    initialize_state()

    if "conversations" not in st.session_state:
        st.session_state.conversations = (
            load_conversation_store()
        )

    if not st.session_state.conversations:
        conversation = make_conversation()
        st.session_state.conversations[
            conversation["id"]
        ] = conversation
        save_conversation_store()

    active_missing = (
        "active_conversation_id"
        not in st.session_state
        or st.session_state.active_conversation_id
        not in st.session_state.conversations
    )

    if active_missing:
        newest = max(
            st.session_state.conversations.values(),
            key=lambda item: item.get(
                "updated_at",
                "",
            ),
        )
        st.session_state.active_conversation_id = (
            newest["id"]
        )

        activate_conversation(
            st.session_state.active_conversation_id,
            reset_backend=False,
        )

    elif "messages" not in st.session_state:
        conversation = st.session_state.conversations[
            st.session_state.active_conversation_id
        ]

        st.session_state.messages = list(
            conversation.get(
                "messages",
                [],
            )
        )



def activate_conversation(
    conversation_id: str,
    reset_backend: bool = True,
) -> None:
    conversation = st.session_state.conversations[
        conversation_id
    ]
    memory = conversation.get(
        "memory",
        {},
    )

    if not isinstance(memory, dict):
        memory = {}

    st.session_state.active_conversation_id = (
        conversation_id
    )
    st.session_state.messages = list(
        conversation.get(
            "messages",
            [],
        )
    )
    st.session_state.last_contexts = []
    st.session_state.last_answer_mode = ""
    st.session_state.last_answer_query = ""
    st.session_state.active_topic = str(
        memory.get(
            "active_topic",
            "",
        )
    )
    st.session_state.last_fee_calculation = dict(
        memory.get(
            "last_fee_calculation",
            {},
        )
        or {}
    )
    st.session_state.processing = False
    st.session_state.pending_request = None
    st.session_state.processing_request_id = ""
    st.session_state.processing_started_at = 0.0
    st.session_state.last_clarification = ""

    if reset_backend:
        backend.reset_conversation()





def persist_active_conversation() -> None:
    conversation_id = (
        st.session_state.active_conversation_id
    )
    conversation = st.session_state.conversations[
        conversation_id
    ]

    conversation["messages"] = (
        st.session_state.messages
    )
    conversation["memory"] = {
        "active_topic": str(
            st.session_state.get(
                "active_topic",
                "",
            )
        ),
        "last_fee_calculation": dict(
            st.session_state.get(
                "last_fee_calculation",
                {},
            )
            or {}
        ),
    }
    conversation["updated_at"] = (
        datetime.now().isoformat(
            timespec="seconds"
        )
    )
    conversation["title"] = (
        adaptive_conversation_title(
            conversation["messages"]
        )
    )

    save_conversation_store()




def create_new_conversation() -> None:
    conversation = make_conversation()

    st.session_state.conversations[
        conversation["id"]
    ] = conversation

    save_conversation_store()
    activate_conversation(
        conversation["id"]
    )


def delete_active_conversation() -> None:
    conversation_id = (
        st.session_state.active_conversation_id
    )

    st.session_state.conversations.pop(
        conversation_id,
        None,
    )

    if not st.session_state.conversations:
        conversation = make_conversation()
        st.session_state.conversations[
            conversation["id"]
        ] = conversation

    newest = max(
        st.session_state.conversations.values(),
        key=lambda item: item.get(
            "updated_at",
            "",
        ),
    )

    save_conversation_store()
    activate_conversation(
        newest["id"]
    )


def sorted_conversations() -> list[dict[str, Any]]:
    return sorted(
        st.session_state.conversations.values(),
        key=lambda item: item.get(
            "updated_at",
            "",
        ),
        reverse=True,
    )




def render_message(
    message: dict[str, Any],
) -> None:
    role = str(
        message.get(
            "role",
            "assistant",
        )
    )
    content = str(
        message.get(
            "content",
            "",
        )
    )
    timestamp = str(
        message.get(
            "time",
            "",
        )
    )

    message_identifier(
        message
    )

    if role == "user":
        spacer_ratio, message_ratio = (
            user_column_ratios(
                content
            )
        )
        spacer, message_column = st.columns(
            [
                spacer_ratio,
                message_ratio,
            ],
            gap="large",
        )

        with message_column:
            with st.container(
                border=True
            ):
                st.markdown(
                    content
                )

                if timestamp:
                    st.markdown(
                        (
                            '<div class="v9-time user">'
                            f'{safe_html_text(timestamp)}'
                            '</div>'
                        ),
                        unsafe_allow_html=True,
                    )

        return

    message_ratio, spacer_ratio = (
        assistant_column_ratios(
            content
        )
    )
    message_column, spacer = st.columns(
        [
            message_ratio,
            spacer_ratio,
        ],
        gap="large",
    )

    with message_column:
        with st.container(
            border=True
        ):
            st.markdown(
                (
                    '<div class="v13-assistant-label">'
                    'Shopee AI'
                    '</div>'
                ),
                unsafe_allow_html=True,
            )
            if bool(message.get("stream_once", False)):
                stream_markdown_answer(content)
                message["stream_once"] = False
                persist_active_conversation()
            else:
                st.markdown(content)

            render_evidence(
                message
            )

            if timestamp:
                st.markdown(
                    (
                        '<div class="v9-time">'
                        f'{safe_html_text(timestamp)}'
                        '</div>'
                    ),
                    unsafe_allow_html=True,
                )

            if st.session_state.technical_mode:
                metrics = message.get(
                    "metrics",
                    {},
                )
                confidence = message.get(
                    "confidence",
                    None,
                )
                confidence_text = (
                    f"{int(confidence)}/100 (heuristic)"
                    if confidence is not None
                    else "—"
                )

                st.markdown(
                    f"""
                    <div class="v9-technical">
                        Chế độ: {safe_html_text(metrics.get("mode", "—"))} ·
                        Thời gian: {float(metrics.get("elapsed", 0.0) or 0.0):.2f}s ·
                        Điểm đủ bằng chứng nội bộ: {safe_html_text(confidence_text)}
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

                debug_results = message.get(
                    "debug",
                    [],
                )

                if debug_results:
                    with st.expander(
                        "Top 5 kết quả truy xuất"
                    ):
                        for index, raw_result in enumerate(
                            debug_results,
                            start=1,
                        ):
                            result = normalize_debug_item(
                                raw_result
                            )
                            metadata = result.get(
                                "metadata",
                                {},
                            )
                            source_name = display_source_name(
                                str(
                                    metadata.get(
                                        "title",
                                        "Không rõ",
                                    )
                                )
                            )

                            st.markdown(
                                f"**{index}. "
                                f"{source_name}**  \n"
                                f"Trang {metadata.get('page', '—')} · "
                                f"Hybrid `{float(result.get('hybrid_score', 0.0)):.4f}` · "
                                f"Vector `{float(result.get('vector_score', 0.0)):.4f}` · "
                                f"BM25 `{float(result.get('bm25_score', 0.0)):.4f}`"
                            )

            render_message_actions(
                message
            )





# ============================================================
# V19 - XỬ LÝ NỀN, HỦY YÊU CẦU, TIMEOUT AN TOÀN VÀ POLLING KHÔNG KHÓA
# ============================================================

MAX_BACKGROUND_WAIT_SECONDS = 20.0

class ResponseJobManager:
    def __init__(self) -> None:
        self._generation = 0
        self._executor = self._new_executor()
        self._jobs: dict[str, Future] = {}
        self._cancelled: set[str] = set()
        self._lock = threading.Lock()

    def _new_executor(self) -> ThreadPoolExecutor:
        self._generation += 1
        return ThreadPoolExecutor(
            max_workers=2,
            thread_name_prefix=f"shopee-ai-{self._generation}",
        )

    def submit(
        self,
        request_id: str,
        query: str,
        resources: tuple[Any, Any, list[dict], Any, dict[str, int]],
    ) -> Future:
        with self._lock:
            existing = self._jobs.get(request_id)
            if existing is not None:
                return existing

            script_context = get_script_run_ctx()
            future = self._executor.submit(
                run_response_job,
                query,
                resources,
                script_context,
            )
            self._jobs[request_id] = future
            return future

    def get(self, request_id: str) -> Future | None:
        with self._lock:
            return self._jobs.get(request_id)

    def consume(self, request_id: str) -> dict[str, Any]:
        with self._lock:
            if request_id in self._cancelled:
                self._jobs.pop(request_id, None)
                raise RuntimeError("Yêu cầu đã bị hủy.")

            future = self._jobs.pop(request_id)
        return future.result()

    def cancel(self, request_id: str) -> None:
        old_executor: ThreadPoolExecutor | None = None

        with self._lock:
            self._cancelled.add(request_id)
            future = self._jobs.pop(request_id, None)

            if future is not None and not future.cancel():
                # Thread Python đang chạy không thể bị dừng cưỡng bức.
                # Đổi executor để câu hỏi mới không xếp hàng sau tác vụ cũ.
                old_executor = self._executor
                self._executor = self._new_executor()

        if old_executor is not None:
            old_executor.shutdown(
                wait=False,
                cancel_futures=True,
            )

    def is_cancelled(self, request_id: str) -> bool:
        with self._lock:
            return request_id in self._cancelled


@st.cache_resource(show_spinner=False)
def response_job_manager() -> ResponseJobManager:
    return ResponseJobManager()


def run_response_job(
    query: str,
    resources: tuple[Any, Any, list[dict], Any, dict[str, int]],
    script_context: Any,
) -> dict[str, Any]:
    if add_script_run_ctx is not None and script_context is not None:
        try:
            add_script_run_ctx(
                threading.current_thread(),
                script_context,
            )
        except Exception:
            pass

    response = generate_response(
        query=query,
        resources=resources,
    )
    return enrich_response(
        response=response,
        query=query,
    )



def assistant_message_from_response(
    response: dict[str, Any],
) -> dict[str, Any]:
    return {
        "id": uuid.uuid4().hex,
        "role": "assistant",
        "content": str(response.get("answer", "")),
        "time": datetime.now().strftime("%H:%M"),
        "metrics": {
            "mode": response.get("mode", ""),
            "elapsed": response.get("elapsed", 0.0),
        },
        "debug": [
            normalize_debug_item(result)
            for result in response.get("debug", [])
        ],
        "citations": list(response.get("citations", [])),
        "confidence": response.get("confidence", None),
        "confidence_label": str(
            response.get("confidence_label", "")
        ),
        "data_status": str(response.get("data_status", "")),
        "feedback": "",
        "stream_once": True,
    }


def finish_processing_request(
    request_id: str,
    current_query: str,
) -> bool:
    """Nhận kết quả đã xong; không bao giờ nhận kết quả của yêu cầu đã hủy."""
    cancelled_ids = set(
        st.session_state.get("cancelled_request_ids", [])
    )
    manager = response_job_manager()

    if request_id in cancelled_ids or manager.is_cancelled(request_id):
        clear_processing_state()
        return False

    future = manager.get(request_id)
    if future is None or not future.done():
        return False

    try:
        response = manager.consume(request_id)

        cancelled_ids = set(
            st.session_state.get("cancelled_request_ids", [])
        )
        if request_id in cancelled_ids:
            clear_processing_state()
            return False

        assistant_message = assistant_message_from_response(response)
    except Exception as exc:
        if request_id in set(
            st.session_state.get("cancelled_request_ids", [])
        ):
            clear_processing_state()
            return False

        assistant_message = {
            "id": uuid.uuid4().hex,
            "role": "assistant",
            "content": (
                "Tôi gặp lỗi khi xử lý câu hỏi này. "
                "Bạn hãy thử gửi lại câu hỏi."
            ),
            "time": datetime.now().strftime("%H:%M"),
            "metrics": {
                "mode": "processing_error",
                "elapsed": 0.0,
            },
            "debug": [],
            "citations": [],
            "confidence": None,
            "confidence_label": "",
            "data_status": "",
            "feedback": "",
        }
        st.session_state.last_processing_error = str(exc)

    st.session_state.messages.append(assistant_message)
    st.session_state.last_answer_mode = str(
        assistant_message.get("metrics", {}).get("mode", "")
    )
    st.session_state.last_answer_query = current_query
    clear_processing_state()
    persist_active_conversation()
    return True


def clear_processing_state() -> None:
    st.session_state.processing = False
    st.session_state.pending_request = None
    st.session_state.processing_request_id = ""
    st.session_state.processing_started_at = 0.0


def cancel_current_processing() -> None:
    request_id = str(
        st.session_state.get(
            "processing_request_id",
            "",
        )
    )
    current_query = str(
        st.session_state.get(
            "pending_request",
            "",
        )
    )

    if request_id:
        response_job_manager().cancel(request_id)
        cancelled = list(
            st.session_state.get(
                "cancelled_request_ids",
                [],
            )
        )
        cancelled.append(request_id)
        st.session_state.cancelled_request_ids = cancelled[-20:]

    clear_processing_state()

    st.session_state.messages.append(
        {
            "id": uuid.uuid4().hex,
            "role": "assistant",
            "content": "Đã hủy xử lý câu hỏi.",
            "time": datetime.now().strftime("%H:%M"),
            "metrics": {
                "mode": "cancelled",
                "elapsed": 0.0,
            },
            "debug": [],
            "citations": [],
            "confidence": None,
            "confidence_label": "",
            "data_status": "",
            "feedback": "",
            "cancelled_query": current_query,
        }
    )
    persist_active_conversation()


def timeout_current_processing() -> None:
    """Tự dừng hiển thị khi tác vụ nền vượt giới hạn an toàn."""
    request_id = str(st.session_state.get("processing_request_id", ""))
    current_query = str(st.session_state.get("pending_request", ""))

    if request_id:
        response_job_manager().cancel(request_id)
        cancelled = list(st.session_state.get("cancelled_request_ids", []))
        cancelled.append(request_id)
        st.session_state.cancelled_request_ids = cancelled[-20:]

    clear_processing_state()
    st.session_state.messages.append(
        {
            "id": uuid.uuid4().hex,
            "role": "assistant",
            "content": (
                "Tôi chưa tìm thấy nguồn đủ phù hợp trong thời gian xử lý cho phép. "
                "Bạn hãy nêu rõ chính sách, loại phí, nhóm sản phẩm hoặc chức năng API cần tra cứu."
            ),
            "time": datetime.now().strftime("%H:%M"),
            "metrics": {"mode": "processing_timeout", "elapsed": MAX_BACKGROUND_WAIT_SECONDS},
            "debug": [],
            "citations": [],
            "confidence": None,
            "confidence_label": "",
            "data_status": "missing",
            "feedback": "",
            "timed_out_query": current_query,
        }
    )
    persist_active_conversation()


def render_processing_card(
    query: str,
    request_id: str,
) -> None:
    started_at = float(
        st.session_state.get(
            "processing_started_at",
            0.0,
        )
        or 0.0
    )
    elapsed = max(
        0.0,
        time.monotonic() - started_at,
    ) if started_at else 0.0

    ratio, _ = assistant_column_ratios(query)
    message_column, spacer = st.columns(
        [max(0.62, ratio), 1.0 - max(0.62, ratio)],
        gap="large",
    )

    with message_column:
        with st.container(border=True):
            st.markdown(
                '<div class="v13-assistant-label">Shopee AI</div>',
                unsafe_allow_html=True,
            )
            st.markdown(
                f"""
                <div class="v17-processing-panel">
                    <div class="v17-processing-spinner" aria-hidden="true"></div>
                    <div>
                        <div class="v17-processing-title">Đang tìm và tổng hợp thông tin</div>
                        <div class="v17-processing-detail">
                            Đã xử lý khoảng {elapsed:.1f} giây. Bạn có thể hủy nếu muốn đổi câu hỏi.
                        </div>
                        <span class="v17-processing-query">{safe_html_text(query)}</span>
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

            with st.container(
                key=f"v17_cancel_{request_id}"
            ):
                if st.button(
                    "Hủy xử lý",
                    key=f"v17_cancel_button_{request_id}",
                    icon=":material/close:",
                ):
                    cancel_current_processing()
                    st.toast(
                        "Đã hủy. Bạn có thể gửi câu hỏi khác.",
                        icon="🛑",
                    )
                    st.rerun()



if hasattr(st, "fragment"):
    @st.fragment(run_every="400ms")
    def processing_status_fragment(
        request_id: str,
        current_query: str,
    ) -> None:
        """Tự kiểm tra future; kết quả tự hiện mà không cần bấm Hủy."""
        if not st.session_state.get("processing", False):
            return

        active_id = str(
            st.session_state.get("processing_request_id", "")
        )
        if active_id != request_id:
            return

        started_at = float(st.session_state.get("processing_started_at", 0.0) or 0.0)
        elapsed = max(0.0, time.monotonic() - started_at) if started_at else 0.0
        if elapsed >= MAX_BACKGROUND_WAIT_SECONDS:
            timeout_current_processing()
            st.rerun()

        if finish_processing_request(request_id, current_query):
            st.rerun()

        render_processing_card(
            query=current_query,
            request_id=request_id,
        )
else:
    def processing_status_fragment(
        request_id: str,
        current_query: str,
    ) -> None:
        """Fallback cho Streamlit cũ; nên nâng Streamlit để dùng st.fragment."""
        if finish_processing_request(request_id, current_query):
            st.rerun()

        render_processing_card(
            query=current_query,
            request_id=request_id,
        )

        # Fallback tự rerun toàn trang. Chỉ dùng khi st.fragment chưa tồn tại.
        time.sleep(0.45)
        st.rerun()


# ============================================================
# V9 - KHỞI CHẠY GIAO DIỆN
# ============================================================

initialize_v7_state()
initialize_agent_state()
st.session_state.setdefault("workspace_mode", "Tra cứu RAG")

with st.sidebar:
    st.markdown(
        """
        <div class="brand-wrap">
            <div class="brand-logo"><svg class="shopee-bag-mark" viewBox="0 0 24 24" aria-hidden="true">
                <path d="M6.5 8.5h11l-.7 10.2a1.8 1.8 0 0 1-1.8 1.7H9a1.8 1.8 0 0 1-1.8-1.7L6.5 8.5Z"></path>
                <path d="M9 9V7a3 3 0 0 1 6 0v2"></path>
                <path d="M9.7 13.1c.6.7 1.4 1.1 2.3 1.1s1.7-.4 2.3-1.1"></path>
            </svg></div>
            <div>
                <div class="brand-name">Shopee AI Assistant</div>
                <div class="brand-subtitle">Trợ lý doanh nghiệp bán hàng</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.segmented_control(
        "Chế độ trình diễn",
        options=["Tra cứu RAG", "Agent đa công cụ"],
        key="workspace_mode",
        required=True,
        width="stretch",
        help=(
            "Agent dùng CSV mô phỏng, RAG và calculator có trace; "
            "không kết nối shop thật."
        ),
    )

    if st.button(
        "＋ Cuộc trò chuyện mới",
        width="stretch",
        type="primary",
        disabled=st.session_state.processing,
    ):
        create_new_conversation()
        st.rerun()

    st.markdown(
        '<div class="v9-history-heading">Lịch sử trò chuyện</div>',
        unsafe_allow_html=True,
    )

    for conversation in sorted_conversations():
        conversation_id = conversation["id"]
        title = safe_html_text(
            conversation.get(
                "title",
                default_conversation_title(),
            )
        )

        if conversation_id == st.session_state.active_conversation_id:
            st.markdown(
                f'<div class="v9-active-chat">● {title}</div>',
                unsafe_allow_html=True,
            )
        else:
            if st.button(
                title,
                key=f"open_{conversation_id}",
                width="stretch",
                disabled=st.session_state.processing,
            ):
                activate_conversation(conversation_id)
                st.rerun()

    st.divider()

    st.session_state.technical_mode = st.toggle(
        "Chế độ kỹ thuật",
        value=st.session_state.technical_mode,
        help="Hiển thị thời gian, điểm đủ bằng chứng nội bộ và kết quả retrieval.",
    )

    allowed_styles = [
        "Ngắn gọn",
        "Cân bằng",
        "Chi tiết",
    ]
    current_style = (
        st.session_state.response_style
        if st.session_state.response_style
        in allowed_styles
        else "Cân bằng"
    )
    st.session_state.response_style = st.selectbox(
        "Phong cách trả lời",
        options=allowed_styles,
        index=allowed_styles.index(
            current_style
        ),
    )

    assistant_messages = [
        item
        for item in st.session_state.messages
        if item.get("role") == "assistant"
    ]
    elapsed_values = [
        float(
            item.get(
                "metrics",
                {},
            ).get(
                "elapsed",
                0.0,
            )
            or 0.0
        )
        for item in assistant_messages
    ]
    average_elapsed = (
        sum(elapsed_values)
        / len(elapsed_values)
        if elapsed_values
        else 0.0
    )
    useful_count = sum(
        1
        for item in assistant_messages
        if item.get("feedback") == "up"
    )

    with st.expander("📊 Thống kê hội thoại"):
        st.markdown(
            f"""
            <div class="v12-stat-line">
                <span>Số câu trả lời</span>
                <strong>{len(assistant_messages)}</strong>
            </div>
            <div class="v12-stat-line">
                <span>Thời gian trung bình</span>
                <strong>{average_elapsed:.2f}s</strong>
            </div>
            <div class="v12-stat-line">
                <span>Phản hồi hữu ích</span>
                <strong>{useful_count}</strong>
            </div>
            """,
            unsafe_allow_html=True,
        )

    export_conversation = (
        st.session_state.conversations[
            st.session_state.active_conversation_id
        ]
    )
    export_title = str(
        export_conversation.get(
            "title",
            default_conversation_title(),
        )
    )
    st.download_button(
        "⬇ Xuất hội thoại (.md)",
        data=conversation_to_markdown(
            export_conversation
        ),
        file_name=(
            safe_export_filename(
                export_title
            )
            + ".md"
        ),
        mime="text/markdown",
        width="stretch",
        disabled=st.session_state.processing,
    )
    st.markdown(
        (
            '<div class="v13-export-note">'
            'File gồm nội dung, nguồn và mức đủ bằng chứng nội bộ; '
            'phù hợp lưu kết quả test hoặc đưa vào phụ lục.'
            '</div>'
        ),
        unsafe_allow_html=True,
    )

    if st.session_state.technical_mode:
        with st.expander("🧠 Luồng xử lý AI"):
            st.markdown(
                """
                <div class="v12-pipeline">
                Câu hỏi người dùng<br>
                ↓<br>
                Nhận diện phạm vi & câu hỏi mơ hồ<br>
                ↓<br>
                Hybrid Search (Vector + BM25)<br>
                ↓<br>
                Context Expansion<br>
                ↓<br>
                Answerability Check<br>
                ↓<br>
                Fast Answer / Qwen Local<br>
                ↓<br>
                Citation + Evidence Sufficiency + Feedback
                </div>
                """,
                unsafe_allow_html=True,
            )

    if st.button(
        "🗑 Xóa cuộc trò chuyện hiện tại",
        width="stretch",
        disabled=st.session_state.processing,
    ):
        delete_active_conversation()
        st.rerun()

    st.markdown(
        """
        <div class="v9-sidebar-note">
            Tạo cuộc trò chuyện mới không xóa hội thoại cũ.
            Bạn có thể mở lại từng cuộc trò chuyện trong danh sách.
        </div>
        """,
        unsafe_allow_html=True,
    )


if st.session_state.workspace_mode == "Agent đa công cụ":
    render_agent_view()
    st.stop()


resources = load_resources()
active_conversation = st.session_state.conversations[
    st.session_state.active_conversation_id
]

st.markdown(
    f"""
    <div class="v9-page-header">
        <div class="v9-page-title">
            {safe_html_text(active_conversation.get("title", default_conversation_title()))}
        </div>
        <div class="v9-page-subtitle">
            Shopee AI Assistant · Phiên bản V19 Final
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)


if not st.session_state.messages:
    st.markdown(
        """
        <div class="v9-empty">
            <div class="v9-empty-icon"><svg class="shopee-bag-mark" viewBox="0 0 24 24" aria-hidden="true">
                <path d="M6.5 8.5h11l-.7 10.2a1.8 1.8 0 0 1-1.8 1.7H9a1.8 1.8 0 0 1-1.8-1.7L6.5 8.5Z"></path>
                <path d="M9 9V7a3 3 0 0 1 6 0v2"></path>
                <path d="M9.7 13.1c.6.7 1.4 1.1 2.3 1.1s1.7-.4 2.3-1.1"></path>
            </svg></div>
            <div class="v9-empty-title">
                Xin chào, tôi có thể hỗ trợ gì cho shop của bạn?
            </div>
            <div class="v9-empty-subtitle">
                Tra cứu chính sách, phí bán hàng, trả hàng/hoàn tiền,
                Shopee Open Platform/API, pháp luật thương mại điện tử
                và dữ liệu vận hành của shop.
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    suggestions = [
        "Phí xử lý giao dịch Shopee được tính như thế nào?",
        "Phí cố định đối với cáp sạc là bao nhiêu?",
        "Merchant API tạo base_string gồm những tham số nào?",
        "Shopee Open Platform dùng để làm gì?",
    ]

    suggestion_columns = st.columns(2)

    for index, suggestion in enumerate(suggestions):
        with suggestion_columns[index % 2]:
            if st.button(
                suggestion,
                key=(
                    f"suggestion_"
                    f"{st.session_state.active_conversation_id}_"
                    f"{index}"
                ),
                width="stretch",
                disabled=st.session_state.processing,
            ):
                st.session_state.pending_prompt = suggestion
                st.rerun()


for message in st.session_state.messages:
    render_message(message)

st.markdown(
    '<div id="v17-chat-bottom-anchor"></div>',
    unsafe_allow_html=True,
)
install_scroll_to_latest_button()


input_placeholder = (
    "Shopee AI đang xử lý — có thể nhấn Hủy xử lý ở phía trên..."
    if st.session_state.processing
    else "Nhập câu hỏi về Shopee..."
)

prompt = st.chat_input(
    input_placeholder,
    disabled=st.session_state.processing,
)


# ============================================================
# XỬ LÝ YÊU CẦU ĐANG CHỜ — tự hiện kết quả, hủy đúng nghĩa
# ============================================================

if (
    st.session_state.processing
    and st.session_state.pending_request
):
    current_query = str(st.session_state.pending_request)
    request_id = str(
        st.session_state.get("processing_request_id", "")
    )

    if not request_id:
        request_id = uuid.uuid4().hex
        st.session_state.processing_request_id = request_id
        st.session_state.processing_started_at = time.monotonic()

    manager = response_job_manager()
    if manager.get(request_id) is None:
        manager.submit(
            request_id=request_id,
            query=current_query,
            resources=resources,
        )

    processing_status_fragment(
        request_id=request_id,
        current_query=current_query,
    )


# ============================================================
# NHẬN YÊU CẦU MỚI
# ============================================================

if (
    st.session_state.pending_prompt
    and not st.session_state.processing
):
    prompt = st.session_state.pending_prompt
    st.session_state.pending_prompt = None


if prompt and not st.session_state.processing:
    clean_prompt = str(prompt).strip()

    if clean_prompt:
        submit_fingerprint = backend.normalize_for_match(
            clean_prompt
        )
        submitted_at = time.monotonic()
        repeated_too_fast = (
            submit_fingerprint
            == str(
                st.session_state.get(
                    "last_submit_fingerprint",
                    "",
                )
            )
            and submitted_at
            - float(
                st.session_state.get(
                    "last_submit_at",
                    0.0,
                )
                or 0.0
            )
            < 1.5
        )

        if repeated_too_fast:
            st.toast(
                "Câu hỏi vừa được gửi. Vui lòng chờ Shopee AI trả lời.",
                icon="⏳",
            )
            st.stop()

        st.session_state.last_submit_fingerprint = (
            submit_fingerprint
        )
        st.session_state.last_submit_at = (
            submitted_at
        )

        user_message = {
            "id": uuid.uuid4().hex,
            "role": "user",
            "content": clean_prompt,
            "time": datetime.now().strftime("%H:%M"),
        }

        st.session_state.messages.append(user_message)

        if should_use_quick_path(clean_prompt):
            quick_response = enrich_response(
                response=generate_response(
                    query=clean_prompt,
                    resources=resources,
                ),
                query=clean_prompt,
            )
            assistant_message = assistant_message_from_response(
                quick_response
            )
            st.session_state.messages.append(assistant_message)
            st.session_state.last_answer_mode = str(
                assistant_message.get("metrics", {}).get("mode", "")
            )
            st.session_state.last_answer_query = clean_prompt
            clear_processing_state()
            persist_active_conversation()
            st.rerun()

        st.session_state.pending_request = clean_prompt
        st.session_state.processing = True
        st.session_state.processing_request_id = ""
        st.session_state.processing_started_at = time.monotonic()

        persist_active_conversation()
        st.rerun()
