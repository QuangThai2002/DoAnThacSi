# Danh mục 32 tình huống kiểm thử Agent

Tài liệu nội bộ để dùng khi hoàn thiện báo cáo/bảo vệ; không hiển thị trong giao diện người dùng. Bộ câu hỏi gốc nằm tại `src/evaluation/agent_benchmark_candidate_v1.jsonl`.

## Mục tiêu và tiêu chí

Mỗi tình huống kiểm tra đồng thời: (1) nhận diện intent, (2) chọn đúng và đủ tool theo đúng thứ tự, (3) nhận diện kỳ dữ liệu nếu câu hỏi nêu tháng, (4) trả về citation cho câu RAG, (5) có câu trả lời trực tiếp và giới hạn phù hợp. Tool gồm `rag` (nguồn chính sách/tài liệu), `shop_data` (CSV mock/file người dùng gắn) và `calculator` (phép tính minh bạch). Các câu ngoài phạm vi phải không gọi tool và từ chối rõ ràng.

Phân chia cố định: DEV 16 câu để phát triển, TEST 10 câu để đánh giá sau khi được duyệt độc lập, CHALLENGE 6 câu để kiểm tra độ bền. Hiện mọi record vẫn là candidate chưa xác nhận độc lập (`gold_verified=false`), nên chỉ dùng kết quả hiện tại như regression kỹ thuật.

## 32 tình huống

| ID | Split | Tình huống/câu hỏi | Kết quả cần kiểm tra |
| --- | --- | --- | --- |
| agent_001 | DEV | Phí cố định Shopee tính thế nào? | `policy_rag` → `rag`; nguồn phí cố định; nêu công thức, không dùng số liệu shop. |
| agent_002 | DEV | Merchant API dùng làm gì? | `policy_rag` → `rag`; nguồn Open API; nêu giới hạn merchant xuyên biên giới/cấp quyền. |
| agent_003 | DEV | Quy trình trả hàng/hoàn tiền cần lưu ý gì? | `policy_rag` → `rag`; nguồn trả hàng; không nhầm với dữ liệu hoàn của shop. |
| agent_004 | DEV | Luật giao dịch điện tử cần quan tâm thông tin nào? | `policy_rag` → `rag`; nguồn luật; trả lời thận trọng, không tư vấn pháp lý kết luận. |
| agent_005 | TEST | Chính sách phí xử lý giao dịch là gì? | `policy_rag` → `rag`; nguồn phí xử lý; công thức và điều kiện áp dụng. |
| agent_006 | DEV | Doanh thu shop tháng 8/2026 bao nhiêu? | `shop_analysis` → `shop_data`, `calculator`; kỳ `2026-08`; trả doanh thu/GMV trực tiếp. |
| agent_007 | DEV | GMV tháng 8 và chi phí lớn nhất? | `shop_analysis` → `shop_data`, `calculator`; kỳ `2026-08`; GMV và xếp hạng khoản chi. |
| agent_008 | DEV | Sản phẩm nào dưới ngưỡng tồn kho? | `shop_data` → `shop_data`; tồn khả dụng so với ngưỡng nhập thêm. |
| agent_009 | DEV | ROAS quảng cáo tháng 8 là bao nhiêu? | `shop_analysis` → `shop_data`, `calculator`; kỳ `2026-08`; chi tiêu, doanh thu quy gán, ROAS. |
| agent_010 | DEV | Chi phí quảng cáo tháng 8 ảnh hưởng nhiều nhất ở đâu? | `shop_analysis` → `shop_data`, `calculator`; kỳ `2026-08`; không suy diễn lợi nhuận ròng. |
| agent_011 | TEST | Tháng 7 có bao nhiêu đơn và doanh thu sau phí? | `shop_analysis` → `shop_data`, `calculator`; kỳ `2026-07`; chỉ tính đơn hoàn tất. |
| agent_012 | TEST | Lợi nhuận tháng 8 so với chiết khấu người bán? | `shop_analysis` → `shop_data`, `calculator`; kỳ `2026-08`; ghi rõ là lãi góp ước tính. |
| agent_013 | DEV | Tháng 8 cần đối chiếu khoản phí nào theo Shopee? | `multi_tool_policy_and_shop_retrieval` → `shop_data`, `rag`; kỳ `2026-08`; có cả số liệu và chính sách. |
| agent_014 | DEV | Doanh thu tháng 8 và kiểm tra phí cố định ở đâu? | `multi_tool_policy_and_shop_analysis` → `shop_data`, `rag`, `calculator`; kỳ `2026-08`. |
| agent_015 | DEV | Tồn kho thấp nào và cần lưu ý quy định đăng bán gì? | `multi_tool_policy_and_shop_retrieval` → `shop_data`, `rag`; không gộp lẫn tồn kho với chính sách. |
| agent_016 | DEV | Đơn hàng có chi phí bao nhiêu, cần đối chiếu khoản nào? | `multi_tool_policy_and_shop_analysis` → `shop_data`, `rag`, `calculator`; số liệu và phí nguồn. |
| agent_017 | DEV | Quảng cáo tháng 8 và nội dung phí liên quan? | `multi_tool_policy_and_shop_retrieval` → `shop_data`, `rag`; kỳ `2026-08`. |
| agent_018 | TEST | GMV tháng 8 và điều khoản hoàn tiền liên quan gì? | `multi_tool_policy_and_shop_retrieval` → `shop_data`, `rag`; kỳ `2026-08`; không suy diễn quan hệ nhân quả. |
| agent_019 | TEST | Doanh thu tháng 8 và quy định bảo mật dữ liệu? | `multi_tool_policy_and_shop_retrieval` → `shop_data`, `rag`; kỳ `2026-08`. |
| agent_020 | CHALLENGE | Doanh số tháng 8 và tài liệu Merchant API cần xem gì? | `multi_tool_policy_and_shop_retrieval` → `shop_data`, `rag`; kỳ `2026-08`. |
| agent_021 | DEV | Thời tiết Hà Nội ngày mai? | `out_of_scope`; không gọi tool; từ chối theo phạm vi. |
| agent_022 | DEV | Giá vàng hôm nay? | `out_of_scope`; không gọi tool; không bịa dữ liệu thời gian thực. |
| agent_023 | TEST | Đội bóng nào vô địch World Cup? | `out_of_scope`; không gọi tool. |
| agent_024 | TEST | Bị sốt nên uống thuốc gì? | `out_of_scope`; không gọi tool; không tư vấn y tế. |
| agent_025 | CHALLENGE | Phim nào đang hay nhất? | `out_of_scope`; không gọi tool. |
| agent_026 | TEST | Báo cáo số đơn hoàn tất tháng 8. | `shop_data` → `shop_data`; kỳ `2026-08`; chỉ đơn hoàn tất. |
| agent_027 | CHALLENGE | SKU nào cần nhập thêm? | `shop_data` → `shop_data`; cảnh báo tồn, không tự đặt lượng nhập. |
| agent_028 | CHALLENGE | Tỷ lệ chi phí giao dịch tháng 8? | `shop_analysis` → `shop_data`, `calculator`; kỳ `2026-08`; phí giao dịch / GMV. |
| agent_029 | TEST | Sản phẩm nào bị cấm đăng bán? | `policy_rag` → `rag`; nguồn quy định đăng bán; không kết luận từng mặt hàng chưa rõ. |
| agent_030 | CHALLENGE | Luật bảo vệ dữ liệu cá nhân yêu cầu gì? | `policy_rag` → `rag`; nêu nguyên tắc tối thiểu và giới hạn tư vấn pháp lý. |
| agent_031 | TEST | Doanh thu, chi phí quảng cáo và chính sách phí tháng 8? | `multi_tool_policy_and_shop_analysis` → `shop_data`, `rag`, `calculator`; kỳ `2026-08`; đủ ba phần. |
| agent_032 | CHALLENGE | Shopee Open Platform cung cấp API nào? | `policy_rag` → `rag`; nguồn Open Platform; phân nhóm API, không tự nhận kết nối thật. |

## Dữ liệu và nguồn kiểm tra

- Nhóm shop/calculate sử dụng `data/shop_mock/*.csv` hoặc dữ liệu do người dùng tải vào chat. Mốc demo hiện tại của kỳ `2026-08`: 6 đơn hoàn tất, GMV 3.980.000 VND, doanh thu sau phí ước tính 3.537.200 VND; ROAS 6,14 từ 360.000 VND chi quảng cáo và 2.210.000 VND doanh thu quy gán.
- Nhóm policy/RAG dùng corpus tại `data/processed/chunks.jsonl`. Bản đồ tài liệu tối thiểu có trong `docs/agent_ai_audit.md`.
- Nhóm out-of-scope không dùng web, không gọi tool, không trả lời nội dung thời sự/y tế/giải trí.

## Cách chạy lại

```powershell
$env:PYTHONPATH = 'src'
.\.venv\Scripts\python.exe -m unittest tests.test_agent tests.test_agent_streamlit_view
.\.venv\Scripts\python.exe src\evaluation\agent_eval.py
.\.venv\Scripts\python.exe src\evaluation\agent_end_to_end_eval.py
```

Hai lệnh evaluation cuối chỉ tạo kết quả development/regression khi dataset còn chưa được duyệt độc lập. Để có kết quả TEST chính thức, áp dụng quy trình trong `docs/agent_annotation_protocol.md`.
