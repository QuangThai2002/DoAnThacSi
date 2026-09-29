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

TOPICS.extend([
    ("Bắt đầu mở shop", "Người mới nên xác định ngành hàng, khách hàng mục tiêu, nguồn hàng, giá vốn và cách giao hàng trước khi chạy quảng cáo. Mục tiêu giai đoạn đầu là có dữ liệu thật để học, không phải mở thật nhiều sản phẩm cùng lúc."),
    ("Chọn ngành hàng", "Khi chọn ngành hàng, hãy so sánh nhu cầu, mức giá, biên lợi nhuận, độ dễ hỏng, vốn nhập tối thiểu và mức độ cạnh tranh. Không có ngành hàng nào chắc chắn sinh lời chỉ vì đang bán nhiều."),
    ("Khách hàng mục tiêu", "Mô tả khách hàng mục tiêu bằng nhu cầu, mức giá chấp nhận, tình huống sử dụng và lý do họ chọn sản phẩm. Mô tả này giúp viết nội dung, chọn ảnh và thiết kế combo rõ hơn."),
    ("Trang sản phẩm", "Một trang sản phẩm nên làm rõ sản phẩm là gì, biến thể nào, lợi ích chính, thông số quan trọng, hướng dẫn dùng, chính sách đổi trả và điều người mua nhận được. Không dùng mô tả gây hiểu lầm hoặc vượt quá khả năng của sản phẩm."),
    ("Ảnh sản phẩm", "Ảnh nên cho thấy sản phẩm thực tế, các góc nhìn cần thiết, kích thước hoặc thông số quan trọng và biến thể. Ảnh đẹp không thay thế việc mô tả đúng và kiểm soát chất lượng."),
    ("Biến thể sản phẩm", "Màu, kích cỡ hoặc phiên bản nên có SKU riêng và tồn kho riêng. Nếu gộp nhầm biến thể, số liệu bán và cảnh báo hết hàng sẽ không đáng tin."),
    ("Danh mục sản phẩm", "Chọn danh mục gần nhất với tính chất thực của hàng hóa để người mua dễ tìm và để kiểm tra các yêu cầu, hạn chế hoặc phí liên quan. Khi không chắc, cần đối chiếu hướng dẫn chính thức của Shopee."),
    ("Sản phẩm cấm hoặc hạn chế", "Eslabong có thể nhắc kiểm tra danh mục cấm/hạn chế từ tài liệu Shopee, nhưng không tự kết luận một mặt hàng được phép bán. Với hàng có điều kiện hoặc rủi ro cao, cần đối chiếu quy định hiện hành trước khi đăng."),
    ("Kiểm tra đơn hàng", "Nên kiểm tra trạng thái đơn, thời hạn xử lý, địa chỉ lấy hàng và ghi chú người mua mỗi ngày. Quy trình nội bộ cần phân công rõ ai đóng gói, ai bàn giao và ai lưu bằng chứng."),
    ("Đóng gói", "Đóng gói cần phù hợp tính dễ vỡ, rò rỉ, kích thước và giá trị của hàng. Chụp ảnh hoặc quay quy trình đóng gói chỉ là biện pháp quản trị rủi ro; việc sử dụng làm bằng chứng phải theo quy trình và chính sách đang áp dụng."),
    ("Hủy đơn", "Khi có yêu cầu hủy, hãy kiểm tra trạng thái đơn và lý do trước khi thao tác. Không nên hứa kết quả hủy hoặc hoàn tiền vì quyền xử lý phụ thuộc trạng thái giao dịch và chính sách nền tảng."),
    ("Trả hàng và khiếu nại", "Khi có yêu cầu trả hàng, cần lưu ảnh đóng gói, mô tả sản phẩm, lịch sử trao đổi và bằng chứng phù hợp. Theo dõi đúng thời hạn hiển thị trên Kênh Người Bán và đối chiếu chính sách trước khi khiếu nại."),
    ("Chăm sóc khách hàng", "Phản hồi rõ ràng về sản phẩm, đơn hàng và cách xử lý vấn đề giúp giảm hiểu nhầm. Không yêu cầu người mua chia sẻ dữ liệu nhạy cảm ngoài kênh cần thiết và không tạo cam kết không thể thực hiện."),
    ("Đánh giá sản phẩm", "Đừng chỉ nhìn điểm trung bình. Hãy nhóm đánh giá theo chất lượng, sai mô tả, đóng gói, giao hàng và hỗ trợ để chọn đúng vấn đề cần sửa."),
    ("Đối soát doanh thu", "Đối soát là so sánh đơn hoàn tất, hoàn tiền, phí, khuyến mãi, quảng cáo và số tiền nhận được theo cùng kỳ. Nếu thiếu một loại báo cáo, Eslabong phải nêu phần chưa tính thay vì gọi đó là lợi nhuận cuối cùng."),
    ("Dòng tiền", "Dòng tiền khác doanh thu: cần theo dõi tiền nhập hàng, tiền quảng cáo, phí, tiền hoàn và thời điểm nhận thanh toán. Shop có GMV tăng vẫn có thể thiếu tiền nhập hàng nếu chu kỳ thu tiền dài."),
    ("Ngân sách nhập hàng", "Ngân sách nhập hàng nên dựa trên tốc độ bán, tồn khả dụng, thời gian chờ nhập, giá vốn và tiền mặt còn lại. Không nên dùng toàn bộ tiền mặt để nhập một SKU khi chưa có tín hiệu nhu cầu đủ tốt."),
    ("Nhà cung cấp", "Trước khi đặt số lượng lớn, cần thử mẫu, xác nhận tiêu chuẩn hàng, giá, số lượng tối thiểu, thời gian giao, điều kiện đổi lỗi và chứng từ. Lưu thỏa thuận bằng văn bản hoặc kênh có thể truy vết."),
    ("Kiểm tra chất lượng", "Mỗi lô hàng nên có danh sách kiểm tra theo lỗi hay gặp, số lượng, nhãn, hạn dùng nếu có và ngoại quan. Phát hiện lỗi sớm giúp tránh chi phí hoàn hàng và đánh giá tiêu cực."),
    ("Ra mắt sản phẩm", "Ra mắt một sản phẩm mới nên bắt đầu bằng lượng hàng và ngân sách thử nghiệm có giới hạn. Theo dõi lượt xem, số đơn, phản hồi, tỷ lệ hoàn và biên lợi nhuận trước khi mở rộng."),
    ("Mở rộng danh mục", "Chỉ mở rộng khi shop có năng lực quản lý tồn kho, chất lượng, đóng gói và dòng tiền cho sản phẩm mới. Sản phẩm liên quan thường dễ tạo combo hơn sản phẩm không liên quan."),
    ("Kế hoạch người mới", "Trong 14 ngày đầu, người mới có thể tập trung hoàn thiện 5–10 SKU, kiểm tra trang sản phẩm, chốt quy trình đóng gói và theo dõi phản hồi đầu tiên. Đây là lộ trình thử nghiệm, không phải cam kết doanh số."),
    ("Kế hoạch shop đang bán", "Shop đang hoạt động nên ưu tiên xác định 3 SKU: bán tốt, có biên tốt và chậm bán. Sau đó thử một thay đổi nhỏ có thể đo được thay vì thay đổi giá, quảng cáo và nội dung cùng lúc."),
    ("Hợp đồng với nhà cung cấp", "Một hợp đồng hoặc xác nhận mua hàng nên nêu rõ chủ thể, hàng hóa/tiêu chuẩn, số lượng, giá và thuế nếu có, lịch giao, thanh toán, đổi trả hàng lỗi, chứng từ và cách xử lý tranh chấp. Đây là danh sách kiểm tra nghiệp vụ, không thay thế tư vấn pháp lý."),
    ("Hợp đồng điện tử", "Giao dịch điện tử cần được lưu lịch sử, thời điểm và thông tin xác nhận theo cách có thể kiểm tra. Giá trị pháp lý của từng giao dịch phụ thuộc điều kiện luật định và tình huống cụ thể; Eslabong chỉ giải thích nguồn, không phán quyết hiệu lực hợp đồng."),
    ("Bằng chứng giao dịch", "Lưu đơn đặt hàng, xác nhận, hóa đơn/chứng từ, nội dung trao đổi và dữ liệu giao nhận theo quy trình nhất quán. Không chỉnh sửa hoặc tạo bằng chứng sau sự kiện."),
    ("Quyền lợi người tiêu dùng", "Thông tin về hàng hóa, giá, điều kiện giao dịch và cách xử lý vấn đề cần rõ ràng, dễ hiểu. Với câu hỏi về nghĩa vụ cụ thể hoặc tranh chấp, Eslabong phải dẫn nguồn luật và khuyến nghị trao đổi chuyên gia pháp lý khi rủi ro cao."),
    ("Chất lượng hàng hóa", "Doanh nghiệp cần kiểm soát việc hàng hóa phù hợp tiêu chuẩn, quy chuẩn hoặc nội dung đã công bố theo loại hàng. Hàng có rủi ro hoặc yêu cầu chuyên ngành cần được kiểm tra với quy định chuyên ngành trước khi bán."),
    ("Dữ liệu khách hàng", "Chỉ thu thập dữ liệu cần thiết cho đơn hàng và hỗ trợ khách; nêu rõ mục đích sử dụng, bảo vệ dữ liệu và hạn chế chia sẻ không cần thiết. Không tải dữ liệu khách hàng lên bản demo công khai."),
    ("Thuế và hóa đơn", "Eslabong không thay thế kế toán hoặc cơ quan thuế. Câu hỏi về nghĩa vụ thuế, hóa đơn và tư cách kinh doanh cần được đối chiếu quy định hiện hành và chuyên gia phù hợp trước khi thực hiện."),
    ("Mức chắc chắn", "Eslabong chỉ dùng ngôn ngữ khẳng định khi có dữ liệu và nguồn phù hợp. Khi thiếu dữ liệu, hệ thống phải nói rõ giới hạn, nêu giả định và đề xuất thử nghiệm nhỏ thay vì hứa kết quả."),
    ("Kiểm tra nguồn", "Câu trả lời chính sách hoặc pháp luật cần có tài liệu và thời điểm áp dụng. Hướng dẫn Eslabong được nhận diện riêng, không được trình bày như văn bản chính thức của Shopee hoặc cơ quan nhà nước."),
    ("Xung đột dữ liệu", "Khi số liệu giữa các báo cáo không khớp, cần ưu tiên kiểm tra kỳ thời gian, trạng thái đơn, tiền tệ, đơn hoàn và cách tính. Eslabong không tự chọn một con số rồi khẳng định đó là đúng."),
    ("Quyết định theo dữ liệu", "Một quyết định tốt cần nêu mục tiêu, chỉ số theo dõi, thời gian thử, ngưỡng dừng và người chịu trách nhiệm. Điều này giúp phân biệt kết quả do thay đổi nào tạo ra."),
    ("Rủi ro kinh doanh", "Rủi ro thường gặp gồm tồn kho quá mức, thiếu tiền mặt, hàng lỗi, phụ thuộc một nhà cung cấp, chi quảng cáo vượt biên lợi nhuận và tranh chấp. Eslabong chỉ cảnh báo dựa trên dữ liệu có sẵn, không dự đoán chắc chắn rủi ro chưa có bằng chứng."),
    ("Cảnh báo tồn kho", "Cảnh báo tồn kho là tín hiệu cần kiểm tra, không phải lệnh nhập hàng. Trước khi nhập, hãy xem tốc độ bán, hàng đang về, mùa vụ, hàng lỗi và ngân sách tiền mặt."),
    ("Cảnh báo lỗ", "Ước tính lỗ cần có tối thiểu giá bán, giá vốn, phí và khuyến mãi; nếu thiếu bất kỳ phần nào, Eslabong chỉ được nói rằng chưa đủ dữ liệu để kết luận."),
    ("Bảo mật tài khoản", "Không chia sẻ mật khẩu, mã xác thực hoặc khóa API trong chat hay file demo. Khi sau này tích hợp Shopee, thông tin truy cập phải được lưu bằng cơ chế bí mật và cấp quyền tối thiểu."),
    ("Phạm vi Shopee", "Eslabong hiện phân tích CSV tải lên, bộ demo và tài liệu đã nạp; không có quyền tự đọc tài khoản Shopee. Kết nối Shopee thật chỉ được thực hiện khi người dùng cấp quyền hợp lệ qua cơ chế chính thức."),
])


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
