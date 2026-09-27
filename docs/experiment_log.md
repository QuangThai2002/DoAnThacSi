# Nhật ký thực nghiệm kỹ thuật

Tài liệu này ghi các run kiểm tra kỹ thuật có thể tái lập. Các run có dataset
chưa được annotation độc lập luôn được gắn **regression-only** và không được
dùng làm kết luận hiệu quả trong luận văn.

## RAG pilot DEV - 2026-09-26

- Dataset: `src/evaluation/gold_pilot_verified.jsonl`, lọc `--split dev`.
- Số mẫu: 4; tất cả đã có `gold_verified=true` và được kiểm tra PDF/trang ở
  pilot. Quy mô này chỉ đủ để smoke test pipeline và chọn giả thuyết, không đủ
  để công bố hay freeze cấu hình.
- Command:

```powershell
.\.venv\Scripts\python.exe src\evaluation\retrieval_eval.py `
  --dataset src\evaluation\gold_pilot_verified.jsonl `
  --split dev --require-verified --repetitions 3 `
  --output <results.csv> --summary <summary.csv>
```

| Variant | Hit@1 | Hit@5 | MRR@10 | Page Hit@5 | Median latency |
| --- | ---: | ---: | ---: | ---: | ---: |
| BM25 | 0.750 | 1.000 | 0.833 | 1.000 | 7.7 ms |
| Dense | 1.000 | 1.000 | 1.000 | 0.750 | 45.4 ms |
| Hybrid + heuristic | 1.000 | 1.000 | 1.000 | 1.000 | 114.4 ms |
| Hybrid không query bonus | 1.000 | 1.000 | 1.000 | 1.000 | 53.0 ms |

**Quyết định:** không thay đổi retrieval default. Hai variant hybrid bằng nhau
trên bốn mẫu, nên mọi kết luận về latency/chất lượng sẽ quá yếu. Khi DEV đã có
đủ annotation, dùng error analysis để chọn một thay đổi duy nhất; TEST và
CHALLENGE không được dùng để tune.

## Agent end-to-end regression - 2026-09-26

- Dataset: `src/evaluation/agent_eval_dataset.jsonl` (32 câu).
- Đặc tính: tất cả 32 nhãn đang `gold_verified=false`; đây là regression test
  cho deterministic baseline, không phải Agent experiment chính thức.
- Command:

```powershell
.\.venv\Scripts\python.exe src\evaluation\agent_end_to_end_eval.py
```

| Contract | Kết quả regression |
| --- | ---: |
| Intent accuracy | 1.000 |
| Plan tool exact match | 1.000 |
| Tool execution success | 1.000 |
| Citation contract | 1.000 |
| Mock-data disclaimer | 1.000 |
| Out-of-scope refusal | 1.000 |
| Period parsing | 1.000 |
| Trace without error | 1.000 |
| Median/P95 latency | 69.8 / 129.9 ms |

**Quyết định:** Agent baseline đạt contract kỹ thuật hiện tại. Trước khi đưa
vào chương thực nghiệm, phải tách/kiểm duyệt độc lập 30--50 câu và định nghĩa
chấm task success, calculation exact match, citation correctness và refusal.

## RAG Candidate v2 DEV routing regression - 2026-09-27

- Code revision: `908474f72879df378fd1059a21eec4b582780fa8` (working tree
  sạch khi chạy).
- Dataset: `src/evaluation/benchmark_candidate_v2.jsonl`, chỉ `--split dev`.
- Số mẫu: 17. Tất cả là candidate có evidence/source/page khớp cơ học, nhưng
  `gold_verified=false`; manifest gắn nhãn `development_or_regression_only`.
  Vì vậy bảng này chỉ dùng để chọn hướng sửa ở DEV, **không** là số liệu luận
  văn và không được suy ra hiệu quả trên TEST.
- Lặp: 3; variants: BM25, dense, hybrid không bonus và hybrid heuristic.

| Variant | Hit@1 | Hit@5 | MRR@10 | nDCG@5 | Page Hit@5 | Median / P95 latency |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| BM25 | 0.706 | 0.882 | 0.788 | 0.805 | 0.824 | 4.7 / 12.9 ms |
| Dense | 0.647 | 0.882 | 0.735 | 0.766 | 0.765 | 24.6 / 28.8 ms |
| Hybrid không query bonus | 0.706 | 0.824 | 0.776 | 0.768 | 0.765 | 31.0 / 36.8 ms |
| Hybrid + heuristic | 0.765 | 1.000 | 0.882 | 0.913 | 0.941 | 66.2 / 81.5 ms |

Sau vòng error analysis trước đó, chỉ câu DEV và heuristic có unit test được
chỉnh; 10 record TEST không đổi. Báo cáo lỗi của variant heuristic còn 3 lỗi
Top-1 và 1 lỗi trang, nhưng không còn lỗi thiếu tài liệu đúng trong Top-5.

**Quyết định:** không tiếp tục tăng bonus theo từng câu DEV. Giữ ablation này
như dấu vết chẩn đoán, ưu tiên kiểm duyệt 34 candidate trên PDF gốc và chỉ
freeze cấu hình/đánh giá TEST sau khi có nhãn độc lập.
