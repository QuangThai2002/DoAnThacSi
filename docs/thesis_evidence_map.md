# Bản đồ bằng chứng cho luận văn

Tài liệu này liên kết các claim dự kiến trong luận văn với artefact kỹ thuật.
Nó giúp tránh mô tả tính năng hoặc số liệu không được kiểm chứng.

| Nội dung luận văn | Bằng chứng cần trích | Trạng thái hiện tại |
| --- | --- | --- |
| Pipeline ingest/chunk/index | `extract_documents.py`, `chunk_documents_pageaware.py`, `build_vector_db.py`, log trong `data/processed/` | Có baseline. |
| Hybrid retrieval | `hybrid_search_shopee_v2.py`, cấu hình weight, CSV evaluation | Có mã; số liệu chính thức chờ benchmark khóa. |
| So sánh BM25/Dense/Hybrid | `retrieval_eval.py`, Gold locked, manifest, CSV TEST | Chưa hoàn tất. |
| Scope/private-shop guard | `scope_eval.py`, kết quả scope evaluation | Có seed test; cần mở rộng benchmark verified. |
| Confidence | `response_confidence` và benchmark calibration/error analysis | Heuristic, không gọi là xác suất đúng. |
| Agent đa tool | `src/agent/`, `data/shop_mock/`, trace JSON, agent evaluation | Có deterministic baseline; cần annotation độc lập và end-to-end evaluation. |
| Demo UI | `src/shopee_chat_web_v19.py` | Có RAG demo; Agent chưa tích hợp UI. |
| Tái tạo | `requirements.txt`, README, reproducibility docs, Git manifest | Có baseline. |

## Khẳng định nên dùng

- “Hệ thống sử dụng hybrid retrieval kết hợp BM25 và dense retrieval.”
- “Agent baseline chọn tool theo planner xác định được, tạo trace và dùng dữ
  liệu cửa hàng mô phỏng.”
- “Kết quả thực nghiệm được đánh giá trên benchmark đã annotation và khóa.”
  Chỉ dùng câu này sau khi phase annotation/lock hoàn thành.

## Khẳng định chưa được dùng

- “Confidence 90% nghĩa là xác suất trả lời đúng 90%.”
- “Hệ thống kết nối trực tiếp Shopee Seller Centre.”
- “Agent dùng LLM planner.”
- “Hybrid tốt hơn mọi baseline.” Chỉ được nói sau TEST locked.
- Bất kỳ score nào từ `gold_benchmark_v1.jsonl` khi `gold_verified=false`.

## Artefact cần đính kèm hoặc lưu trữ

1. Git commit hash khi tạo kết quả final.
2. Locked benchmark và SHA-256 manifest.
3. CSV chi tiết + summary + manifest provenance của retrieval, scope và Agent.
4. Bảng error analysis có id câu hỏi, loại lỗi, nguyên nhân và hướng xử lý.
5. Ảnh/screen recording từ demo với nguồn và trace Agent.
