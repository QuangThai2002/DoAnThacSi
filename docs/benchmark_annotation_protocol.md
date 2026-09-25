# Protocol annotation Gold Benchmark

Mục tiêu của protocol là chuyển Gold Benchmark từ câu hỏi sinh tự động thành
ground truth có thể được bảo vệ. Không khóa TEST hoặc dùng số liệu cuối cùng
trước khi hoàn thành protocol này.

## Đơn vị annotation

Mỗi record phải được kiểm tra theo chuỗi:

```text
Question -> expected_documents -> expected_pages -> evidence -> reference_answer
```

Một mắt xích sai thì record chưa đạt, kể cả khi retrieval tình cờ trả về đúng
tài liệu.

## Quy trình cho từng record

1. Mở tài liệu gốc, đến đúng trang được ghi trong record.
2. Xác nhận `document_id`, trang và evidence có thực, đủ để trả lời.
3. Viết lại câu hỏi như cách người bán có thể hỏi. Không nêu tên file, trang,
   header, câu navigation hay cụm từ copy nguyên từ evidence.
4. Viết `reference_answer` ngắn, chính xác và chỉ chứa điều nguồn khẳng định.
5. Với câu nhiều tài liệu, ghi từng bằng chứng và chỉ rõ vai trò của mỗi nguồn.
6. Kiểm tra câu hỏi có cần dữ liệu shop riêng tư hay không. Nếu có, đặt
   `requires_private_shop_data=true` và không đưa vào retrieval answerable set.
7. Ghi một `verification_note` có ngày review và lý do sửa. Chỉ sau đó mới đặt
   `gold_verified=true`.

## Tiêu chí đạt

| Kiểm tra | Điều kiện đạt |
| --- | --- |
| Nguồn | Mọi document/page tồn tại trong tài liệu gốc và index. |
| Evidence | Đủ để suy ra reference answer, không là menu/header/OCR rác. |
| Câu hỏi | Tự nhiên, không làm lộ tên nguồn/trang, không chép sát evidence. |
| Nhãn | Category/query type/split đúng định nghĩa. |
| Phạm vi | `answerable` và `requires_private_shop_data` phản ánh đúng khả năng hệ thống. |
| Đáp án | Không thêm tri thức ngoài nguồn, không mơ hồ về thời điểm/điều kiện. |

## Split và chống leakage

- Rà và viết lại trên DEV trước.
- Khóa câu hỏi/nhãn của TEST trước khi tuning retrieval; không chỉnh thuật toán
  dựa trên các lỗi TEST.
- CHALLENGE giữ các paraphrase khó, typo/noisy hoặc bằng chứng yếu nhưng vẫn có
  annotation rõ; báo cáo riêng, không trộn lẫn với TEST chính.
- Nếu thay chunking, embedding model hay corpus, đánh giá lại document/page
  links. Không giả định label cũ luôn đúng.

## Kiểm tra bằng công cụ

```powershell
.\.venv\Scripts\python.exe src\evaluation\audit_gold_benchmark.py `
  --dataset src\evaluation\gold_benchmark_v1_reviewed.jsonl

.\.venv\Scripts\python.exe src\evaluation\lock_gold_benchmark.py `
  --dataset src\evaluation\gold_benchmark_v1_reviewed.jsonl `
  --output src\evaluation\gold_benchmark_v1_locked.jsonl `
  --manifest src\evaluation\gold_benchmark_v1_locked_manifest.json
```

Lệnh lock chỉ thành công khi toàn bộ record verified và audit không còn flag.
