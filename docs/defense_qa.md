# Hỏi–đáp bảo vệ đề tài

Các câu trả lời dưới đây bám vào artefact hiện có. Không thay số liệu trong dấu
ngoặc bằng score regression; chỉ điền score sau khi TEST benchmark đã review và
khóa.

## 1. Bài toán nghiên cứu là gì?

Hệ thống hỗ trợ tra cứu tri thức chính sách/vận hành/API Shopee bằng tiếng Việt,
với câu trả lời gắn nguồn. Phần mở rộng Agent xử lý các yêu cầu cần phối hợp
chính sách với số liệu vận hành cửa hàng mô phỏng và phép tính minh bạch. Mục
tiêu không phải khẳng định truy cập trực tiếp Shopee Seller Centre.

## 2. Vì sao không dùng LLM trả lời trực tiếp?

Chính sách thay đổi và câu trả lời không nguồn khó kiểm tra. RAG giới hạn ngữ
cảnh theo chunk truy hồi được, hiển thị document/page và cho phép báo thiếu bằng
chứng. Điều này giảm rủi ro bịa nội dung nhưng không loại bỏ hoàn toàn sai sót;
vì vậy citation vẫn phải được kiểm tra.

## 3. Corpus được chuẩn bị như thế nào?

Pipeline `extract_documents.py → chunk_documents_pageaware.py →
build_vector_db.py` bảo toàn `document_id`, vị trí/trang và text chunk. BM25
dùng text; dense retrieval dùng embedding; ChromaDB lưu vector. Khi corpus,
chunking hoặc embedding thay đổi, index và thực nghiệm phải chạy lại.

## 4. Hybrid retrieval kết hợp gì?

`hybrid_search_shopee_v2.py` kết hợp BM25 và dense retrieval. Các biến thể
evaluation tách BM25, dense, hybrid không query bonus và hybrid có heuristic
để tránh gộp một cải tiến rule-based vào baseline một cách mơ hồ.

## 5. Confidence có phải xác suất câu trả lời đúng không?

Không. `response_confidence`/`confidence_label` là evidence-sufficiency score
hoặc heuristic nội bộ, chưa được calibration trên tập nhãn độc lập. Trong luận
văn và khi bảo vệ phải gọi nó là mức đủ bằng chứng, không được phát biểu như
“đúng 90%”.

## 6. Agent khác RAG assistant ở đâu?

RAG assistant chủ yếu truy hồi tài liệu rồi sinh câu trả lời. Agent có planner
xác định được, quyết định route và ghi trace: `RAG Tool` cho chính sách,
`Shop Data Tool` cho CSV mô phỏng, `Calculator Tool` cho công thức. Câu hỏi đa
công cụ có thể gọi các tool theo thứ tự `shop_data → rag → calculator`.

## 7. Planner có phải LLM Agent không?

Chưa. `src/agent/planner.py` là planner rule-based có chủ đích, để tool routing
có thể kiểm thử và audit. Đây là baseline Agent xác định được; không nên mô tả
là LLM planner hoặc autonomous agent tổng quát.

## 8. Dữ liệu shop có phải dữ liệu thật của Shopee không?

Không. `data/shop_mock/*.csv` là dữ liệu mô phỏng, và answer/trace có nhãn rõ
ràng. Trường `estimated_*` chỉ dùng kiểm chứng phép tính, không phải bảng phí
Shopee hiện hành. Mức phí/chính sách chỉ được đối chiếu qua RAG citation.

## 9. Làm sao kiểm chứng kết quả Agent?

Planner evaluator đo intent/tool routing. End-to-end evaluator chạy Agent và
đo trace, citation contract, disclaimer dữ liệu mock, refusal ngoài phạm vi,
period và latency. Khi một sample được reviewer xác thực, task RAG phải có
expected citation document ID/xác nhận nguồn; task mock/tính toán phải có
answer marker kiểm tra được.

## 10. TEST có bị dùng để tuning không?

Quy trình quy định chỉ dùng DEV để sửa retrieval/planner. Candidate có split
DEV/TEST/CHALLENGE cố định; `--require-verified` chặn run chính thức nếu nhãn
thiếu. `lock_gold_benchmark.py` và `lock_agent_benchmark.py` tạo bản locked,
ghi hash dataset/corpus; Agent lock còn snapshot CSV mock.

## 11. Hiện có thể công bố score nào?

Chỉ công bố score từ manifest có `official_test_candidate`, với TEST verified,
locked và working tree sạch. Hiện các run đã lưu là development/regression-only;
chúng chứng minh code không vỡ chứ không phải kết luận hiệu quả khoa học.

## 12. Vì sao latency Agent có thể có P95 cao?

First-use của câu hỏi có RAG có thể phải nạp embedding model/index local. Cần
báo median/P95 và ghi rõ điều kiện warm/cold cache; không so sánh P95 cold-start
với retrieval warm-cache như hai phép đo tương đương.

## 13. Nếu Ollama hoặc Streamlit lỗi khi demo thì làm gì?

Không đổi benchmark hay chạy tuning tại chỗ. Dùng Agent CLI với `--json`, trace
đã có, evaluation CSV/manifest thuộc commit đã lưu và sơ đồ kiến trúc. Chạy
`src/defense_preflight.py --check-ollama` trước buổi bảo vệ để phát hiện lỗi
demo nhưng không lẫn nó với trạng thái evidence.

## 14. Giới hạn chính của đề tài là gì?

Corpus cần được cập nhật khi chính sách đổi; confidence chưa calibrated;
planner rule-based có độ bao phủ từ khóa hữu hạn; data shop là mô phỏng; và kết
quả retrieval/Agent chỉ được suy rộng trong phạm vi benchmark đã review. Đây là
các hướng phát triển tiếp theo, không phải chi tiết cần che giấu.

## 15. Hướng phát triển hợp lý sau luận văn?

Thứ tự đúng là: mở rộng annotation độc lập và benchmark; thử reranker/LLM
planner chỉ trên DEV; kết nối dữ liệu Seller Centre sau khi có quyền/API và cơ
chế bảo mật; sau đó đo lại task success, citation correctness, chi phí và độ
trễ trên nguồn dữ liệu/version được kiểm soát.

## Câu chốt khi kết thúc demo

> Hệ thống hiện chứng minh được retrieval có nguồn và Agent route/tool trace có
> thể kiểm tra. Những score nào chưa có benchmark TEST đã kiểm duyệt được giữ ở
> mức regression, không được trình bày như kết quả thực nghiệm cuối cùng.
