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
    clear_active_conversation()
    st.session_state.seller_conversations.append(
        {"id": chat_id, "mode": mode, "title": conversation_title([], mode), "messages": []}
    )


def open_conversation(chat_id: str) -> None:
    conversation = next(item for item in st.session_state.seller_conversations if item["id"] == chat_id)
    st.session_state.seller_active_chat_id = conversation["id"]
    st.session_state.seller_chat_mode = conversation["mode"]
    st.session_state.seller_messages = list(conversation["messages"])
    st.session_state.pop("seller_suggestion", None)


def show_chat_picker() -> None:
    st.session_state.seller_show_chat_picker = True


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
        with st.expander("Thêm dữ liệu bán hàng để phân tích doanh thu", icon=":material/upload_file:"):
            render_data_upload(inline=True)

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
render_assistant()
