# AI audit bộ benchmark Agent v1

Ngày audit: 2026-10-03. Phạm vi: toàn bộ 32 câu trong `src/evaluation/agent_benchmark_candidate_v1.jsonl`, chạy với dữ liệu mock hiện tại và corpus cục bộ.

## Kết quả kiểm tra kỹ thuật

| Hạng mục | Kết quả |
| --- | --- |
| Intent và thứ tự tool | 32/32 khớp nhãn candidate sau khi sửa route trả hàng/hoàn tiền |
| Kỳ dữ liệu | 32/32 khớp |
| Tool trace | 32/32 chạy không lỗi |
| Câu ngoài phạm vi | 5/5 từ chối, không gọi tool |
| Regression Agent | 70/70 test pass |

Các lỗi đã sửa trong audit này:

- Câu quy trình trả hàng/hoàn tiền chung bị nhầm thành truy vấn dữ liệu shop.
- Câu số liệu tài chính đôi khi trả bảng xếp hạng chi phí thay vì chỉ số được hỏi.
- Câu đa công cụ có thể chỉ hiện số liệu hoặc chỉ hiện chính sách; nay giữ cả hai phần.
- Bổ sung trả lời nguồn cho Merchant API, Open Platform API, danh mục cấm đăng bán và nguyên tắc dữ liệu cá nhân.
- Câu hỏi dữ liệu shop hiện luôn ghi rõ số liệu là dữ liệu vận hành mô phỏng.

## Đối chiếu nguồn cho các câu có RAG

| ID | Nguồn phù hợp tối thiểu |
| --- | --- |
| agent_001, agent_014 | `SHP_FEE_003` — phí cố định |
| agent_002, agent_020 | `SHP_API_002` — Merchant API và cấp quyền |
| agent_003, agent_018 | `SHP_RET_003` — quy trình trả hàng/hoàn tiền |
| agent_004 | `LAW_TRANSACTION_001` — giao dịch điện tử |
| agent_005, agent_013, agent_016, agent_017, agent_031 | `SHP_FEE_004` và/hoặc `SHP_FEE_003` — khoản phí |
| agent_015, agent_029 | `SHP_POL_007` — quy định đăng bán |
| agent_019, agent_030 | `SHP_POL_001` — bảo mật/dữ liệu |
| agent_032 | `SHP_API_001`, `SHP_API_002` — Open Platform và API calls |

## Đối chiếu dữ liệu mock

Các câu dữ liệu/tính toán dùng `data/shop_mock/*.csv`. Các mốc hiện hành dùng trong kiểm tra gồm: tháng 2026-08 có 6 đơn hoàn tất, GMV 3.980.000 VND, doanh thu sau phí ước tính 3.537.200 VND, chi quảng cáo 360.000 VND, doanh thu quy gán 2.210.000 VND và ROAS 6,14. Các câu tồn kho dùng tồn khả dụng so với ngưỡng nhập thêm, không tự xem tồn vật lý là dữ liệu thời gian thực.

## Giới hạn bằng chứng

Đây là audit kỹ thuật do AI thực hiện. Các record vẫn giữ `gold_verified=false`, `review_status=not_reviewed` và chưa có xác nhận nguồn của người kiểm duyệt. Vì vậy có thể báo cáo là **kiểm thử phát triển/regression đã chạy**, nhưng chưa được gọi là kết quả thực nghiệm Agent chính thức trong luận văn. Muốn khóa TEST chính thức vẫn phải review độc lập theo `docs/agent_annotation_protocol.md`.
