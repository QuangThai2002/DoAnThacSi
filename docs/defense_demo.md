# Kịch bản demo bảo vệ (7–8 phút)

## Chuẩn bị trước khi vào phòng

```powershell
cd C:\Users\Powder\Desktop\DoAnThacSi\master-thesis-rag-agent
.\.venv\Scripts\python.exe src\defense_preflight.py --check-ollama
.\.venv\Scripts\python.exe -m unittest tests\test_agent.py
.\.venv\Scripts\python.exe src\evaluation\scope_eval.py
ollama serve
.\.venv\Scripts\streamlit.exe run src\shopee_chat_web_v19.py
# Terminal khác cho Agent UI độc lập (tùy chọn; Agent đã có trong app chuẩn):
.\.venv\Scripts\streamlit.exe run src\agent_demo.py --server.port 8502
```

Mở sẵn:

- Streamlit RAG/Agent ở `http://localhost:8501`; Agent demo riêng ở `http://localhost:8502` chỉ khi cần phương án dự phòng.
- `docs/architecture.md` để giải thích pipeline.
- Một terminal cho Agent CLI và CSV kết quả evaluation đã chạy trước.
- `data/processed/defense_preflight_report.md` để phân biệt rõ demo-ready với
  evidence-ready nếu hội đồng hỏi trạng thái thực nghiệm.
- [`docs/defense_qa.md`](defense_qa.md) để trả lời nhất quán về RAG, Agent,
  dữ liệu mock, confidence và giới hạn nghiên cứu.

## Demo 1 — RAG có nguồn (2 phút)

1. Hỏi một câu chính sách cụ thể, ví dụ: “Phí cố định được tính như thế nào?”
2. Chỉ vào câu trả lời, citation và trang nguồn.
3. Giải thích: câu trả lời chỉ tổng hợp evidence; không có evidence thì hệ thống
   phải nói không đủ dữ liệu.

## Demo 2 — Scope guard (1 phút)

1. Hỏi một câu cần dữ liệu shop thật hoặc ngoài phạm vi.
2. Chỉ ra hệ thống không bịa GMV/lợi nhuận khi chưa có dữ liệu.
3. Kết nối với scope evaluation, không diễn giải guard là “AI biết mọi thứ”.

## Demo 3 — Agent đa tool (3 phút)

```powershell
.\.venv\Scripts\python.exe src\agent\run_agent.py `
  "Tháng 8 năm 2026 shop tôi có doanh thu bao nhiêu và theo chính sách Shopee các khoản phí nào cần đối chiếu?" `
  --json
```

Trình bày theo đúng trace:

1. Planner chọn `shop_data`, `rag`, `calculator`.
2. `shop_data` lấy GMV/doanh thu từ CSV mô phỏng đã công bố.
3. `rag` trả tài liệu/trang chính sách để đối chiếu.
4. `calculator` xếp hạng chi phí theo công thức có thể kiểm tra.
5. Kết luận luôn có nhãn “dữ liệu mô phỏng”, không mô tả đây là dữ liệu Shopee thật.

## Kết quả thực nghiệm (1–2 phút)

Chỉ trình chiếu kết quả từ Gold Benchmark đã khóa. Bảng tối thiểu: BM25, Dense,
Hybrid không heuristic, Hybrid có heuristic; Hit@K, MRR@10, nDCG@5, Page Hit@5
và latency. Sau bảng, nêu 2–3 nhóm lỗi có ví dụ.

## Phương án dự phòng

- Nếu Ollama lỗi: dùng Agent CLI, trace JSON và kết quả CSV đã chuẩn bị; không
  giả vờ generation đang chạy.
- Nếu Streamlit lỗi: mở `docs/architecture.md`, chạy unit test/Agent CLI và
  giải thích artefact retrieval đã lưu.
- Nếu được hỏi score: chỉ mở CSV/manifest thuộc commit đã ghi nhận; không chạy
  tuning hoặc thay benchmark ngay trong buổi bảo vệ.
