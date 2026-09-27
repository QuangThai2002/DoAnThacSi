# Protocol kiểm duyệt benchmark Agent

`agent_benchmark_candidate_v1.jsonl` là bộ ứng viên 32 câu được chuyển đổi có
chủ đích từ seed regression. Nó có split cố định nhưng **không có nhãn gold
được xác thực**. Không trích bất kỳ score nào của bộ này vào luận văn trước khi
review độc lập hoàn tất.

## Mục tiêu nhãn

Mỗi mẫu mô tả hành vi Agent có thể quan sát, thay vì yêu cầu người đánh giá
chấm một câu trả lời tự do:

| Thành phần | Cách kiểm duyệt | Điều kiện khi `verified` |
| --- | --- | --- |
| Intent | Đọc câu hỏi, đối chiếu phạm vi Agent | Một intent rõ ràng |
| Tool route | Đối chiếu tool tối thiểu và thứ tự phụ thuộc | Danh sách tool theo thứ tự |
| Kỳ dữ liệu | Đọc kỳ được nêu trong câu hỏi | `YYYY-MM` hoặc để trống nếu không cần |
| Citation | Mở tài liệu/chính sách nguồn | Ít nhất một `document_id` và tick xác nhận nguồn cho task có `rag` |
| Kết quả mock/tính toán | Đối chiếu CSV mock + công thức | Một hoặc nhiều marker ổn định xuất hiện trong answer cho task `shop_data`/`calculator` |
| Refusal | Xác nhận câu hỏi ngoài phạm vi | Không gọi tool, câu trả lời nêu ngoài phạm vi |

Citation document ID không chứng minh mọi câu chữ trong câu trả lời đúng. Nó là
nhãn tối thiểu để đo được Agent có trả về nguồn phù hợp với task chính sách.
Answer marker phải là giá trị hoặc cụm rõ ràng, ổn định theo output; không dùng
một đoạn văn dài hay một nhận định chủ quan.

## Quy trình làm việc

1. Tạo lại candidate khi cần kiểm tra tính tái lập:

   ```powershell
   .\.venv\Scripts\python.exe src\evaluation\generate_agent_benchmark_candidate_v1.py
   ```

2. Mở workbench, ưu tiên review DEV trước. Agent có thể được chạy để hỗ trợ
   đối chiếu, nhưng output của nó không tự điền nhãn.

   ```powershell
   .\.venv\Scripts\streamlit.exe run src\agent_annotation_workbench.py
   ```

3. Với task có RAG, mở tài liệu nguồn trong kho dữ liệu và nhập một hoặc nhiều
   `document_id` tương ứng, rồi tick xác nhận đối chiếu nguồn. Với task mock,
   đối chiếu `data/shop_mock/*.csv`, công thức ở `CalculatorTool`, và nhập các
   marker có thể kiểm tra.

4. Lưu `verified`, `needs_rewrite`, hoặc `rejected`. Workbench chỉ ghi vào
   `data/processed/agent_benchmark_review/`; candidate ban đầu giữ nguyên và
   mọi lần lưu có journal SHA-256 trước/sau.

5. Chỉ review/điều chỉnh routing trên DEV. Sau khi đã khóa nội dung TEST,
   không đọc output test để sửa planner, keyword hoặc prompt.

## Chạy đánh giá chính thức

Sau khi **mọi bản ghi TEST được kiểm duyệt độc lập**, chạy trên bản reviewed:

```powershell
.\.venv\Scripts\python.exe src\evaluation\agent_eval.py `
  --dataset data\processed\agent_benchmark_review\agent_benchmark_candidate_v1_reviewed.jsonl `
  --split test `
  --require-verified `
  --output data\processed\agent_plan_official_test_results.csv `
  --summary data\processed\agent_plan_official_test_summary.csv

.\.venv\Scripts\python.exe src\evaluation\agent_end_to_end_eval.py `
  --dataset data\processed\agent_benchmark_review\agent_benchmark_candidate_v1_reviewed.jsonl `
  --split test `
  --require-verified `
  --output data\processed\agent_e2e_official_test_results.csv `
  --summary data\processed\agent_e2e_official_test_summary.csv
```

`--require-verified` không chỉ kiểm tra `gold_verified`; nó từ chối cả bản ghi
thiếu reviewer/note, citation document ID/xác nhận nguồn cho RAG, hoặc answer
marker cho task mock/tính toán. Manifest chỉ đánh dấu `official_test_candidate`
khi TEST đã được review, cờ guard được bật và Git working tree sạch.

## Báo cáo luận văn

Nêu rõ Agent là baseline planner rule-based, dữ liệu shop là mô phỏng và
citation là evidence retrieval, không phải kết nối Seller Centre. Báo cáo riêng
planning (intent/tool routing) và end-to-end (tool trace, citation document,
marker, disclaimer/refusal, period, latency). Khi chưa hoàn tất review, chỉ gọi
chúng là kiểm thử phát triển/regression — không phải kết quả thực nghiệm.
