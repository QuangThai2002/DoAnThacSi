"""Build a clean, source-matched candidate benchmark for human annotation.

The output is a review aid, not a substitute for annotation. Every record is
deliberately unverified until a reviewer checks the original PDF and page.
"""

from __future__ import annotations

import json
import re
from collections import Counter
from pathlib import Path
from typing import Any

from audit_gold_benchmark import audit, read_jsonl, write_jsonl


PROJECT_ROOT = Path(__file__).resolve().parents[2]
CHUNKS_PATH = PROJECT_ROOT / "data" / "processed" / "chunks.jsonl"
OUTPUT_PATH = Path(__file__).with_name("benchmark_candidate_v2.jsonl")
SUMMARY_PATH = Path(__file__).with_name("benchmark_candidate_v2_summary.json")
FIELDS = (
    "id",
    "question",
    "category",
    "query_type",
    "split",
    "document_id",
    "page",
    "evidence",
    "reference_answer",
)


ROW_DATA = r'''
v2_api_capabilities_001	Shopee Open Platform hỗ trợ những nhóm nghiệp vụ nào cho người bán?	shopee_api	paraphrase	dev	SHP_API_001	1	Get access to a wide range of Open APIs with Shopee Open Platform, including those for orders, products, marketing and more.	Nền tảng cung cấp Open API cho đơn hàng, sản phẩm, marketing và các nhu cầu vận hành liên quan.
v2_api_optimization_002	Việc tích hợp Open Platform có thể hỗ trợ tối ưu vận hành cửa hàng ở những khía cạnh nào?	shopee_api	paraphrase	dev	SHP_API_001	1	integrate your systems with Shopee’s to discover untapped potential in the areas of operations optimization and data management.	Tài liệu nêu khả năng tích hợp hệ thống để tối ưu vận hành và quản lý dữ liệu.
v2_api_partner_environment_003	Partner ID bản test và bản live được dùng trong môi trường nào?	shopee_api	technical_api	dev	SHP_API_002	2	Test partner ID can only be used in the test environment, and Live partner ID can only be used in the production environment.	Partner ID test chỉ dùng ở test environment; Partner ID live chỉ dùng ở production environment.
v2_api_timestamp_004	Yêu cầu thời gian đối với một API request của Shopee là gì?	shopee_api	technical_api	dev	SHP_API_002	2	Each API request needs to be requested within 5 minutes of a timestamp.	Mỗi API request cần được gửi trong vòng 5 phút tính từ timestamp.
v2_api_authorization_005	Shop API và Merchant API được gọi sau điều kiện nào?	shopee_api	exact	dev	SHP_API_002	3	Shop and Merchant APIs can be called only after the shop has granted authorization.	Hai loại API chỉ được gọi sau khi shop cấp quyền ủy quyền.
v2_api_shop_signature_006	Khi tạo base string cho Shop API, những thành phần nào cần được ghép theo thứ tự?	shopee_api	technical_api	test	SHP_API_002	3	Shop API: partner_id, api path, timestamp, access_token, shop_id	Base string của Shop API gồm partner_id, api path, timestamp, access_token và shop_id theo thứ tự tài liệu nêu.
v2_api_merchant_signature_007	Base string của Merchant API khác Shop API ở định danh cuối cùng như thế nào?	shopee_api	technical_api	test	SHP_API_002	3	Merchant API: partner_id, api path, timestamp, access_token, merchant_id	Merchant API dùng merchant_id ở thành phần cuối, thay cho shop_id.
v2_api_merchant_scope_008	Những loại tài khoản bán hàng nào thực sự cần endpoint cấp merchant thay vì shop?	shopee_api	ambiguous_evidence_weak	challenge	SHP_API_002	3	Currently, only Shopee cross-border merchants need to use Merchant API. Local sellers do not need to use it.	Tài liệu nói Merchant API hiện chỉ cần cho người bán Shopee xuyên biên giới; người bán nội địa không cần dùng.
v2_fee_rename_001	Nhãn phí mới có hiệu lực từ ngày nào?	fee_seller_cost	exact	dev	SHP_FEE_004	1	Bắt đầu từ ngày 24/04/2026, Shopee cập nhật tên "Phí Thanh Toán" thành "Phí Xử Lý Giao Dịch"	Tên phí được cập nhật từ ngày 24/04/2026.
v2_fee_transaction_formula_002	Công thức tính Phí Xử Lý Giao Dịch của Shopee gồm các khoản nào và áp dụng tỷ lệ bao nhiêu?	fee_seller_cost	numerical_fee	dev	SHP_FEE_004	1	Phí Xử Lý Giao Dịch = ( Giá sản phẩm trước Shopee trợ giá + Phí vận chuyển Người mua trả - Khuyến mãi Người bán đã áp dụng - Khuyến mãi từ Ngân hàng ) *6%	Phí bằng tổng giá sản phẩm trước trợ giá và phí vận chuyển người mua trả, trừ hai khoản khuyến mãi nêu trong công thức, rồi nhân 6%.
v2_fee_check_003	Người bán có lựa chọn nào để xem được số tiền bị tính?	fee_seller_cost	exact	dev	SHP_FEE_004	1	Có 2 cách Người bán có thể kiểm tra Phí Xử Lý Giao Dịch cho từng đơn hàng của Shop	Tài liệu nêu hai cách kiểm tra phí trên đơn hàng.
v2_fee_headphones_004	Phí cố định của nhóm tai nghe nhét tai và chụp tai là bao nhiêu?	fee_seller_cost	numerical_fee	test	SHP_FEE_006	1	Thiết Bị Âm Thanh Tai nghe nhét tai & chụp tai 10.00%	Mức phí cố định là 10,00%.
v2_fee_audio_cable_005	Nhóm cáp âm thanh hoặc video và đầu chuyển chịu mức phí cố định nào?	fee_seller_cost	numerical_fee	test	SHP_FEE_006	1	Thiết Bị Âm Thanh Cáp âm thanh/ video & Đầu chuyển 10.00%	Mức phí cố định là 10,00%.
v2_fee_dslr_006	Máy ảnh cơ hoặc DSLR có mức phí cố định bao nhiêu?	fee_seller_cost	numerical_fee	challenge	SHP_FEE_006	2	Cameras & Flycam Máy ảnh Máy ảnh cơ/DSLRs 7.50%	Mức phí cố định là 7,50%.
v2_return_buyer_window_001	Người mua còn thời gian nào để khởi tạo một yêu cầu sau khi đơn hoàn tất?	logistics_return_refund	paraphrase	dev	SHP_RET_003	1	Người mua có thể nhấn yêu cầu Trả hàng/Hoàn tiền trong vòng 15 ngày kể từ khi đơn giao thành công.	Người mua có thể gửi yêu cầu trong vòng 15 ngày kể từ lúc đơn giao thành công.
v2_return_reason_correction_002	Nếu người mua chọn sai lý do trả hàng hoặc hoàn tiền, Shopee xử lý yêu cầu như thế nào?	logistics_return_refund	paraphrase	dev	SHP_RET_003	2	Trong trường hợp Người mua chọn sai lý do khi nhấn Trả hàng/Hoàn tiền, Shopee sẽ chủ động điều chỉnh lại	Shopee có thể chủ động điều chỉnh yêu cầu hoặc vấn đề khiếu nại để bảo đảm xử lý phù hợp và chính xác.
v2_return_immediate_refund_003	Người bán không đồng ý với quyết định hoàn tiền ngay thì phải khiếu nại trong bao lâu?	logistics_return_refund	exact	dev	SHP_RET_003	3	Trong vòng 2 ngày kể từ khi Shopee gửi thông báo Hoàn tiền Ngay cho Người mua mà không yêu cầu trả hàng	Người bán cần khiếu nại trong vòng 2 ngày kể từ thông báo.
v2_return_ship_back_004	Bên mua cần gửi lại bưu kiện trong mấy ngày khi phương án nhận hoàn được chọn?	logistics_return_refund	paraphrase	test	SHP_RET_003	4	Người mua sẽ phải gửi trả hàng lại về địa chỉ Người bán trong vòng 6 ngày.	Người mua phải gửi trả hàng về địa chỉ người bán trong vòng 6 ngày.
v2_return_appeal_button_005	Nút khiếu nại của người bán hiển thị trong bao lâu ở quy trình hàng hoàn?	logistics_return_refund	exact	test	SHP_RET_003	4	Thời gian hiển thị nút khiếu nại (Hạn khiếu nại) Trong vòng 2 ngày	Nút khiếu nại hiển thị trong vòng 2 ngày.
v2_return_not_received_fee_006	Nếu người mua khiếu nại với lý do chưa nhận được hàng, người bán có bị tính các loại phí nào?	logistics_return_refund	ambiguous_evidence_weak	challenge	SHP_RET_003	3	Người bán không bị tính phí dịch vụ, phí cố định, phí Xử Lý	Theo đoạn evidence, người bán không bị tính phí dịch vụ, phí cố định và phí xử lý trong trường hợp này.
v2_listing_scope_001	Chủ thể chịu trách nhiệm tuân thủ là ai?	policy_listing	exact	dev	SHP_POL_007	1	Quy định này áp dụng đối với tất cả Người Bán trên Sàn TMĐT Shopee	Quy định áp dụng cho tất cả người bán trên sàn thương mại điện tử Shopee.
v2_listing_documents_002	Khi Shopee yêu cầu chứng từ, người bán phải bảo đảm điều gì về chứng từ đã cung cấp?	policy_listing	paraphrase	dev	SHP_POL_007	1	tất cả các chứng từ mà Người Bán cung cấp cho Shopee đều được scan từ chứng từ gốc, không được làm giả, chỉnh sửa, tẩy xóa.	Chứng từ phải được scan từ bản gốc và không được làm giả, chỉnh sửa hay tẩy xóa.
v2_listing_prohibited_003	Khi tạo tin bán hàng, các nhóm nội dung không được đưa vào gồm những gì?	policy_listing	exact	test	SHP_POL_007	1	NGHIÊM CẤM đăng tải những sản phẩm có nội dung sau đây:	Tài liệu mở đầu danh sách các nội dung bị cấm; người đánh giá cần đối chiếu danh sách đầy đủ trong nguồn.
v2_listing_title_004	Tên sản phẩm đăng bán cần đáp ứng các yêu cầu cơ bản nào?	policy_listing	paraphrase	challenge	SHP_POL_007	2	Tên sản phẩm phải mô tả đúng hàng hóa, dịch vụ được đăng bán và phải là tiếng Việt có dấu, đủ ký tự, rõ nghĩa, không dùng các ký tự đặc biệt, không viết tắt.	Tên phải mô tả đúng hàng hóa/dịch vụ, bằng tiếng Việt có dấu, đủ ký tự, rõ nghĩa, không ký tự đặc biệt và không viết tắt.
v2_finance_export_001	Các bước cơ bản để xuất Báo Cáo Doanh Thu trên Kênh Người Bán là gì?	seller_finance	exact	dev	SHP_FIN_002	1	Bước 1: Tại mục Chi tiết, lựa chọn mục Đã thanh toán	Quy trình bắt đầu ở mục Chi tiết, chọn Đã thanh toán; sau đó chọn khung thời gian, Xuất và tải báo cáo gần nhất.
v2_finance_summary_002	Trang Tổng quát của Báo Cáo Doanh Thu thể hiện những thông tin gì?	seller_finance	paraphrase	dev	SHP_FIN_002	2	Báo Cáo Doanh Thu tải về sẽ gồm các trang sau:	Trang Summary thể hiện thông tin người bán, thời gian xuất báo cáo và tổng đơn đã thanh toán trong kỳ.
v2_finance_service_fee_003	Trang Chi tiết phí dịch vụ trong báo cáo dùng để theo dõi những đơn hàng nào?	seller_finance	exact	test	SHP_FIN_002	2	Trang Chi tiết phí dịch vụ (Service Fee Details): Hiển thị các đơn hàng có phát sinh phí dịch vụ.	Trang này hiển thị các đơn hàng phát sinh phí dịch vụ.
v2_finance_order_fields_004	Báo cáo doanh thu có thể cung cấp những thông tin đơn hàng nào ngoài mã đơn?	seller_finance	paraphrase	challenge	SHP_FIN_002	6	bao gồm Mã đơn hàng, Mã yêu cầu hoàn tiền, Mã s phẩm, Ngày đặt hàng, Ngày hoàn thành thanh t thanh toán và Loại đơn hàng.	Ngoài mã đơn, báo cáo có thể gồm mã yêu cầu hoàn tiền, mã sản phẩm, ngày đặt hàng, ngày hoàn thành thanh toán và loại đơn hàng.
v2_sea_orders_001	Shopee ghi nhận bao nhiêu đơn hàng gộp trong quý 4 năm 2025?	market_sea_reports	exact	dev	SEA_REP_003	1	Gross orders totaled 4.0 billion for the quarter, increasing by 30.5% year-on-year.	Shopee có 4,0 tỷ đơn hàng gộp trong quý, tăng 30,5% so với cùng kỳ.
v2_sea_gmv_002	GMV của Shopee trong quý 4 năm 2025 là bao nhiêu và thay đổi thế nào so với cùng kỳ?	market_sea_reports	exact	test	SEA_REP_003	1	GMV was US$36.7 billion for the quarter, increasing by 28.6% year-on-year.	GMV là 36,7 tỷ USD, tăng 28,6% so với cùng kỳ.
v2_sea_revenue_003	Doanh thu GAAP của Shopee trong quý 4 năm 2025 là bao nhiêu?	market_sea_reports	numerical_fee	challenge	SEA_REP_003	1	GAAP revenue was US$5.0 billion, up 35.8% year-on-year.	Doanh thu GAAP là 5,0 tỷ USD, tăng 35,8% so với cùng kỳ.
v2_privacy_examples_001	Các ví dụ nào minh họa loại thông tin nhận dạng một cá nhân?	privacy_dispute	paraphrase	dev	SHP_POL_001	1	Các ví dụ thường gặp về dữ liệu cá nhân có thể gồm có tên, số chứng minh nhân dân và thông tin liên hệ.	Ví dụ gồm tên, số chứng minh nhân dân và thông tin liên hệ.
v2_privacy_consent_002	Khi sử dụng dịch vụ hoặc tạo tài khoản, người dùng đồng ý với những hoạt động xử lý dữ liệu nào?	privacy_dispute	paraphrase	test	SHP_POL_001	1	bạn đã biết rõ và đồng ý toàn bộ cho phép chúng tôi thu thập, sử dụng, tiết lộ và/hoặc xử lý dữ liệu cá nhân của bạn như mô tả trong đây.	Người dùng xác nhận đồng ý việc thu thập, sử dụng, tiết lộ và/hoặc xử lý dữ liệu theo chính sách.
v2_privacy_sources_003	Ngoài thông tin do người dùng cung cấp, Shopee có thể thu thập dữ liệu từ những nguồn nào?	privacy_dispute	paraphrase	challenge	SHP_POL_001	2	Chúng tôi có thể thu thập thông tin của bạn từ bạn, các công ty liên kết, các bên thứ ba và từ các nguồn khác	Nguồn dữ liệu có thể gồm người dùng, công ty liên kết, bên thứ ba và các nguồn khác theo chính sách.
'''.strip()


def parse_specs() -> list[dict[str, str]]:
    records: list[dict[str, str]] = []
    for line_number, line in enumerate(ROW_DATA.splitlines(), start=1):
        values = line.split("\t")
        if len(values) != len(FIELDS):
            raise ValueError(
                f"Candidate specification row {line_number} has {len(values)} fields, expected {len(FIELDS)}."
            )
        records.append(dict(zip(FIELDS, values, strict=True)))
    return records


def normalize(text: str) -> str:
    text = text.replace("\ufeff", "").replace("\u200b", "").replace("\u00a0", " ")
    return re.sub(r"\s+", " ", text).strip().casefold()


def evidence_exists(specification: dict[str, str], chunks: list[dict[str, Any]]) -> None:
    page_chunks = [
        str(chunk.get("text", ""))
        for chunk in chunks
        if str(chunk.get("document_id", "")) == specification["document_id"]
        and str(chunk.get("page", "")) == specification["page"]
    ]
    needle = normalize(specification["evidence"])
    if not any(needle in normalize(text) for text in page_chunks):
        raise ValueError(
            "Evidence phrase was not found in expected source/page: "
            f"{specification['id']} -> {specification['document_id']} page {specification['page']}"
        )


def build_candidate(chunks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    specifications = parse_specs()
    identifiers = [item["id"] for item in specifications]
    if len(identifiers) != len(set(identifiers)):
        raise ValueError("Candidate benchmark specifications contain duplicate IDs.")

    records: list[dict[str, Any]] = []
    for item in specifications:
        evidence_exists(item, chunks)
        records.append(
            {
                "id": item["id"],
                "question": item["question"],
                "category": item["category"],
                "query_type": item["query_type"],
                "split": item["split"],
                "answerable": True,
                "requires_private_shop_data": False,
                "expected_documents": [item["document_id"]],
                "expected_pages": [item["page"]],
                "reference_answer": item["reference_answer"],
                "evidence": [
                    {
                        "document_id": item["document_id"],
                        "page": item["page"],
                        "support": item["evidence"],
                    }
                ],
                "gold_verified": False,
                "review_status": "not_reviewed",
                "candidate_origin": "ai_assisted_source_matching",
                "verification_note": (
                    "AI-assisted candidate matched to an extracted source/page. "
                    "A human reviewer must inspect the original PDF page, rewrite "
                    "when needed, and explicitly set gold_verified=true."
                ),
            }
        )
    return records


def main() -> None:
    chunks = read_jsonl(CHUNKS_PATH)
    records = build_candidate(chunks)
    write_jsonl(OUTPUT_PATH, records)
    queue, report = audit(records, chunks)
    non_verification_flags = sorted(
        {
            flag
            for item in queue
            for flag in item["quality_flags"]
            if flag != "gold_not_human_verified"
        }
    )
    if non_verification_flags:
        raise ValueError(
            "Candidate benchmark still has mechanical audit issues: "
            + ", ".join(non_verification_flags)
        )

    summary = {
        "record_count": len(records),
        "by_split": dict(sorted(Counter(item["split"] for item in records).items())),
        "by_category": dict(sorted(Counter(item["category"] for item in records).items())),
        "audit_non_verification_flags": non_verification_flags,
        "human_verification_required": True,
    }
    SUMMARY_PATH.write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"Wrote {len(records)} AI-assisted candidate records to {OUTPUT_PATH}")
    print(json.dumps(summary, ensure_ascii=False))


if __name__ == "__main__":
    main()
