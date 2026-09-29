"""Build a small, traceable operating-knowledge pack for Eslabong RAG.

The pack is deliberately labelled as internal guidance, not Shopee policy.
It is idempotent so a rebuild never duplicates tracked chunks.
"""

from __future__ import annotations

import json
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"
CHUNKS_PATH = PROCESSED_DIR / "chunks.jsonl"
DOCUMENTS_PATH = PROCESSED_DIR / "documents.jsonl"
DOCUMENT_ID = "ESLABONG_GUIDE_001"
TITLE = "So tay van hanh Eslabong 2026"

TOPICS = [
    ("SKU", "SKU là mã định danh riêng cho một sản phẩm hoặc một biến thể. Ví dụ: AO-THUN-DEN-M. Dùng SKU để tránh nhầm màu, kích cỡ hoặc lô hàng khi theo dõi tồn kho và đơn bán."),
    ("GMV", "GMV là tổng giá trị hàng hóa bán ra trước khi trừ phí, khuyến mãi do người bán chịu, hoàn tiền và giá vốn. GMV hữu ích để theo dõi quy mô bán, nhưng không phải lợi nhuận."),
    ("Doanh thu thực nhận", "Doanh thu thực nhận là số tiền còn lại sau các khoản phí và giảm giá được ghi nhận trong báo cáo. Muốn biết lãi hay lỗ, cần trừ thêm giá vốn, đóng gói, vận hành và quảng cáo."),
    ("ROAS", "ROAS = doanh thu được quy gán cho quảng cáo / chi quảng cáo. Ví dụ chi 1.000.000 đ tạo 4.000.000 đ doanh thu quy gán thì ROAS là 4,0. ROAS cao chưa chắc có lãi nếu biên lợi nhuận thấp."),
    ("Giá trị đơn trung bình", "Giá trị đơn trung bình = tổng GMV / số đơn hoàn tất. Có thể tăng chỉ số này bằng combo hoặc mua kèm, nhưng cần thử trên một nhóm sản phẩm trước."),
    ("Tỷ lệ chuyển đổi", "Tỷ lệ chuyển đổi = số đơn hoặc lượt mua / số lượt xem phù hợp. Chỉ số giảm có thể liên quan đến giá, ảnh, mô tả, đánh giá hoặc tình trạng hết hàng; không nên kết luận từ một chỉ số duy nhất."),
    ("Giá vốn", "Giá vốn là chi phí trực tiếp để có một sản phẩm sẵn sàng bán: giá nhập và các chi phí trực tiếp liên quan nếu shop hạch toán. Cần nhập giá vốn riêng để hệ thống ước lượng lãi gộp."),
    ("Biên lợi nhuận gộp", "Biên lợi nhuận gộp = (giá bán thu được - giá vốn) / giá bán thu được. Đây là ước lượng trước các chi phí vận hành khác. Không nên giảm giá khi chưa kiểm tra biên còn đủ an toàn."),
    ("Điểm hòa vốn", "Số lượng hòa vốn = tổng chi phí cố định trong kỳ / lãi góp trên mỗi sản phẩm. Đây là ước tính kế hoạch; kết quả thực tế thay đổi theo hoàn hàng, phí và giá vốn."),
    ("Giá sàn", "Giá sàn là mức giá thấp nhất shop chấp nhận trong một thử nghiệm sau khi tính giá vốn, phí dự kiến, đóng gói và mức lợi nhuận tối thiểu. Giá sàn là quy tắc nội bộ của shop, không phải giá thị trường."),
    ("Tồn kho an toàn", "Tồn kho an toàn là lượng hàng dự phòng để giảm nguy cơ hết hàng khi nhu cầu hoặc thời gian nhập biến động. Nên đặt theo tốc độ bán gần đây và thời gian nhà cung cấp giao hàng."),
    ("Điểm đặt hàng lại", "Điểm đặt hàng lại có thể ước tính bằng nhu cầu bán trung bình mỗi ngày × số ngày chờ nhập + tồn kho an toàn. Khi tồn khả dụng chạm mốc này, shop nên xem xét đặt thêm hàng."),
    ("Số ngày đủ hàng", "Số ngày đủ hàng = tồn khả dụng / lượng bán trung bình mỗi ngày. Nếu lượng bán gần bằng 0, chỉ số này không đáng tin và sản phẩm cần được xem như hàng chậm bán thay vì nhập thêm."),
    ("Vòng quay tồn kho", "Vòng quay tồn kho phản ánh tốc độ bán và thay thế hàng trong một kỳ. So sánh theo cùng ngành hàng và cùng kỳ; sản phẩm giá cao thường có nhịp quay khác sản phẩm tiêu dùng nhanh."),
    ("Tỷ lệ bán hết", "Tỷ lệ bán hết = số lượng đã bán / (số lượng đã bán + tồn cuối kỳ). Dùng để so sánh sức tiêu thụ giữa các sản phẩm, không dùng một mình để quyết định nhập hàng."),
    ("Hàng chậm bán", "Hàng chậm bán là sản phẩm có số ngày không phát sinh bán hoặc tốc độ bán thấp so với tồn. Trước khi giảm giá mạnh, hãy kiểm tra lại ảnh, mô tả, giá, đánh giá, từ khóa và nhu cầu thực tế."),
    ("Thử khuyến mãi", "Nên thử ưu đãi nhỏ trên 1–2 SKU, trong thời gian xác định. So sánh số đơn, GMV, biên lợi nhuận và tỷ lệ hoàn với kỳ trước; không khẳng định giảm giá sẽ làm doanh thu tăng."),
    ("Đánh giá khách hàng", "Đánh giá tích cực và nội dung phản hồi giúp xác định điểm mạnh của sản phẩm. Đánh giá tiêu cực nên được nhóm theo nguyên nhân như sai mô tả, đóng gói, chất lượng hoặc giao hàng để ưu tiên xử lý."),
    ("Quảng cáo", "Chỉ nên tăng ngân sách từng bước khi sản phẩm còn hàng, trang sản phẩm đủ rõ và biên lợi nhuận có thể chịu được chi phí quảng cáo. Theo dõi ROAS cùng doanh thu thực nhận thay vì chỉ nhìn lượt nhấp."),
    ("Combo", "Combo hoặc mua kèm phù hợp khi các sản phẩm liên quan và vẫn giữ biên lợi nhuận. Hãy theo dõi giá trị đơn trung bình, lợi nhuận gộp và tồn kho của từng SKU trong combo."),
    ("So sánh giá", "So sánh giá cần đặt cùng sản phẩm hoặc mức chất lượng tương đương. Giá cao vẫn có thể bán tốt nhờ thương hiệu, đánh giá, bảo hành, giao nhanh hoặc nội dung sản phẩm tốt hơn; đây là giả thuyết cần kiểm tra."),
    ("Kế hoạch 30 ngày", "Một kế hoạch 30 ngày nên có mục tiêu nhỏ đo được, ví dụ xử lý ba SKU chậm bán hoặc thử một combo. Mỗi tuần ghi số đơn, GMV, chi phí, tồn kho và lý do thay đổi để không nhầm tương quan với nguyên nhân."),
    ("Dữ liệu CSV", "orders.csv mô tả đơn hàng, products.csv mô tả sản phẩm, inventory.csv mô tả tồn kho và ads.csv mô tả quảng cáo. Eslabong chỉ phân tích các dữ liệu được tải vào phiên hoặc bộ demo; không tự đọc tài khoản Shopee."),
    ("Giới hạn kết quả", "Phân tích của Eslabong là hỗ trợ ra quyết định, không bảo đảm doanh thu hay lợi nhuận. Khi thiếu giá vốn, tồn kho, thời gian giao hàng hoặc dữ liệu đủ dài, hệ thống phải hạ mức chắc chắn của gợi ý."),
]


def load_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def save_jsonl(path: Path, rows: list[dict]) -> None:
    path.write_text("\n".join(json.dumps(row, ensure_ascii=False) for row in rows) + "\n", encoding="utf-8")


def build() -> tuple[int, int]:
    documents = [row for row in load_jsonl(DOCUMENTS_PATH) if row.get("document_id") != DOCUMENT_ID]
    chunks = [row for row in load_jsonl(CHUNKS_PATH) if row.get("document_id") != DOCUMENT_ID]
    full_text = "\n\n".join(f"{name}\n{text}" for name, text in TOPICS)
    documents.append({
        "document_id": DOCUMENT_ID,
        "title": TITLE,
        "document_type": "markdown",
        "source_group": "seller_operations_guides",
        "source": "Tai lieu huong dan noi bo Eslabong",
        "source_owner": "Eslabong",
        "source_url": "",
        "organization": "Eslabong",
        "published_year": "2026",
        "effective_date": "",
        "language": "vi",
        "file_path": "docs/eslabong_knowledge_pack.md",
        "detected_file_path": "docs/eslabong_knowledge_pack.md",
        "sha256": "internal-guidance-v1",
        "data_authenticity": "internal_guidance",
        "verification_status": "not_a_shopee_policy",
        "use_for_retrieval": True,
        "page_or_sheet_count": 1,
        "text_length": len(full_text),
        "extracted_at": "2026-09-29",
        "text": full_text,
    })
    for index, (name, text) in enumerate(TOPICS, start=1):
        chunks.append({
            "chunk_id": f"{DOCUMENT_ID}_CHUNK_{index:04d}",
            "document_id": DOCUMENT_ID,
            "chunk_index": index,
            "title": TITLE,
            "document_type": "markdown",
            "source_group": "seller_operations_guides",
            "source": "Tai lieu huong dan noi bo Eslabong",
            "source_owner": "Eslabong",
            "source_url": "",
            "organization": "Eslabong",
            "published_year": "2026",
            "effective_date": "",
            "language": "vi",
            "file_path": "docs/eslabong_knowledge_pack.md",
            "detected_file_path": "docs/eslabong_knowledge_pack.md",
            "sha256": "internal-guidance-v1",
            "data_authenticity": "internal_guidance",
            "verification_status": "not_a_shopee_policy",
            "location_type": "section",
            "location": str(index),
            "page": "",
            "page_start": "",
            "page_end": "",
            "pages": "",
            "text": f"{name}\n{text}",
            "char_count": len(text) + len(name) + 1,
        })
    save_jsonl(DOCUMENTS_PATH, documents)
    save_jsonl(CHUNKS_PATH, chunks)
    return len(documents), len(chunks)


if __name__ == "__main__":
    document_count, chunk_count = build()
    print(f"documents={document_count} chunks={chunk_count}")
