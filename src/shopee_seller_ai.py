"""Seller-facing Streamlit UI for the thesis RAG + Agent backend.

This is intentionally separate from shopee_chat_web_v19.py so the V19 baseline
and its research UI remain unchanged.
"""

from __future__ import annotations

from pathlib import Path
import sys
from typing import Any

import streamlit as st

SRC_DIR = Path(__file__).resolve().parent
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from agent.agent_runner import AgentRunner
from agent.planner import Planner
from agent.shop_data_tool import ShopDataTool, ShopDataValidationError


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
      [data-testid="stSidebar"] { background: #ffffff !important; border-right: 1px solid #f1e7e2; min-width: 272px; }
      [data-testid="stSidebar"] * { color: #333333 !important; }
      [data-testid="stAppViewContainer"] p,
      [data-testid="stAppViewContainer"] li,
      [data-testid="stAppViewContainer"] span { color: #4b4b4b !important; }
      [data-testid="stAppViewContainer"] h1,
      [data-testid="stAppViewContainer"] h2,
      [data-testid="stAppViewContainer"] h3 { color: #252525 !important; }
      .block-container { max-width: 1100px; padding-top: 2.5rem; padding-bottom: 7rem; }

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
    "quick": {
        "Các loại phí Shopee": "Shopee đang áp dụng những loại phí nào?",
        "Chính sách hoàn tiền": "Người mua có thể yêu cầu hoàn tiền trong trường hợp nào?",
        "Cách bắt đầu bán": "Người mới cần chuẩn bị gì để bắt đầu bán hàng trên Shopee?",
    },
    "shop": {
        "Doanh thu tháng này": "Doanh thu tháng này của shop thế nào?",
        "Hàng sắp hết": "Sản phẩm nào đang sắp hết hàng?",
        "Hiệu quả quảng cáo": "Quảng cáo tháng này có hiệu quả không?",
    },
}
REQUIRED_FILES = ("orders.csv", "products.csv", "inventory.csv")


def initialise_state() -> None:
    st.session_state.setdefault("seller_messages", [])
    st.session_state.setdefault("seller_uploaded_rows", None)
    st.session_state.setdefault("seller_uploaded_names", ())
    st.session_state.setdefault("seller_upload_message", None)
    st.session_state.setdefault("seller_upload_error", None)
    st.session_state.setdefault("seller_chat_mode", None)
    st.session_state.setdefault("seller_page", "Trò chuyện")


def active_runner() -> AgentRunner:
    uploaded_rows = st.session_state.get("seller_uploaded_rows")
    if uploaded_rows is None:
        return AgentRunner()
    return AgentRunner(shop_data_tool=ShopDataTool(uploaded_rows=uploaded_rows))


def is_uploaded() -> bool:
    return st.session_state.get("seller_uploaded_rows") is not None


def reset_conversation(*, keep_mode: bool = False) -> None:
    st.session_state.seller_messages = []
    st.session_state.pop("seller_suggestion", None)
    if not keep_mode:
        st.session_state.seller_chat_mode = None


def human_title(question: str) -> str:
    text = " ".join(question.split())
    return text[:44] + ("…" if len(text) > 44 else "")


def data_note(source: str | None) -> str | None:
    if source == "uploaded_csv":
        return "Dữ liệu sử dụng: báo cáo bạn tải lên trong phiên này."
    if source == "mock_shop_data":
        return "Dữ liệu sử dụng: dữ liệu mô phỏng phục vụ demo."
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
    return result


def render_data_upload() -> None:
    st.subheader("Dữ liệu shop")
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
            reset_conversation(keep_mode=True)
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
    st.session_state.seller_chat_mode = "shop"
    reset_conversation(keep_mode=True)
    st.session_state.seller_upload_message = "Đã thêm dữ liệu shop thành công."
    st.session_state.seller_page = "Trò chuyện"
    st.rerun()


def render_assistant() -> None:
    if st.session_state.get("seller_upload_message"):
        st.toast(st.session_state.seller_upload_message, icon=":material/check_circle:")
        st.session_state.seller_upload_message = None

    mode = st.session_state.seller_chat_mode
    if not mode and not st.session_state.seller_messages:
        st.markdown('<div class="seller-eyebrow">TRỢ LÝ CHO NGƯỜI BÁN SHOPEE</div>', unsafe_allow_html=True)
        st.title("Bạn cần hỗ trợ điều gì?")
        st.markdown('<div class="seller-subtitle">Chọn đúng nhu cầu để bắt đầu một cuộc trò chuyện.</div>', unsafe_allow_html=True)
        st.space("medium")
        quick_column, shop_column = st.columns(2, gap="medium")
        with quick_column:
            with st.container(border=True):
                st.markdown("#### :material/forum: Hỏi nhanh về Shopee")
                st.write("Dành cho người đang bán hoặc chuẩn bị mở shop, muốn hiểu chính sách và cách vận hành cơ bản.")
                st.caption("Ví dụ: phí Shopee, hoàn tiền, điều kiện bán hàng.")
                if st.button("Bắt đầu hỏi", key="start_quick_chat", type="primary", icon=":material/send:", width="stretch"):
                    st.session_state.seller_chat_mode = "quick"
                    st.rerun()
        with shop_column:
            with st.container(border=True):
                st.markdown("#### :material/analytics: Phân tích shop của tôi")
                st.write("Dành cho người bán đã có dữ liệu và muốn kiểm tra doanh thu, tồn kho, quảng cáo hoặc chi phí.")
                st.caption("Cần thêm dữ liệu đơn hàng, sản phẩm và tồn kho.")
                if st.button("Phân tích shop", key="start_shop_chat", icon=":material/analytics:", width="stretch"):
                    st.session_state.seller_chat_mode = "shop"
                    st.rerun()
        return

    mode = mode or "quick"
    mode_labels = {
        "quick": ("Hỏi nhanh về Shopee", "Hỏi bằng ngôn ngữ tự nhiên về chính sách hoặc cách bán hàng trên Shopee."),
        "shop": ("Phân tích shop của tôi", "Hỏi về số liệu vận hành dựa trên dữ liệu shop bạn thêm trong phiên này."),
    }
    label, description = mode_labels[mode]
    st.markdown('<div class="seller-eyebrow">TRỢ LÝ BÁN HÀNG AI</div>', unsafe_allow_html=True)
    with st.container(horizontal=True, horizontal_alignment="distribute"):
        st.title(label)
        if st.button("Đổi nhu cầu", key="change_chat_mode", icon=":material/swap_horiz:"):
            reset_conversation()
            st.rerun()
    st.caption(description)
    if mode == "shop" and not is_uploaded():
        st.info("Để AI phân tích đúng số liệu shop, hãy thêm dữ liệu trước khi đặt câu hỏi.", icon=":material/upload_file:")
        if st.button("Thêm dữ liệu shop", key="go_to_data", type="primary", icon=":material/upload_file:"):
            st.session_state.seller_page = "Dữ liệu shop"
            st.rerun()

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

    placeholder = "Hỏi về chính sách hoặc cách bán hàng trên Shopee..." if mode == "quick" else "Hỏi về doanh thu, tồn kho hoặc quảng cáo của shop..."
    typed_prompt = st.chat_input(placeholder, key="seller_chat_input", submit_mode="disable")
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


initialise_state()
with st.sidebar:
    st.markdown("### :material/storefront: Trợ lý AI")
    if st.button("Cuộc trò chuyện mới", icon=":material/add_comment:", width="stretch"):
        reset_conversation()
        st.rerun()
    st.caption("Cuộc trò chuyện gần đây")
    recent_questions = [message["content"] for message in st.session_state.seller_messages if message["role"] == "user"][-3:]
    for question in reversed(recent_questions):
        st.caption(":material/chat: " + human_title(question))
    page = st.radio(
        "Điều hướng",
        ["Trò chuyện", "Dữ liệu shop"],
        index=["Trò chuyện", "Dữ liệu shop"].index(st.session_state.get("seller_page", "Trò chuyện")),
        label_visibility="collapsed",
    )
    st.session_state.seller_page = page
    st.caption("Dữ liệu shop chỉ được dùng trong phiên hiện tại.")

if page == "Trò chuyện":
    render_assistant()
else:
    render_data_upload()
