# Roadmap kỹ thuật đến bảo vệ

Mỗi phase dưới đây có điểm dừng rõ ràng. Không dùng TEST để chỉnh thuật toán; nếu baseline thay đổi, lưu commit và chạy lại benchmark đã khóa.

## Phase 1 — Khóa baseline và tái tạo

**Mục tiêu:** mọi người có thể biết chạy file nào, dùng cấu hình nào và tái tạo được kết quả baseline.

- Hoàn thành tài liệu kiến trúc, setup và giới hạn hệ thống.
- Giữ `src/shopee_chat_web_v19.py` là app chuẩn; không sửa bản sao root.
- Xác nhận `requirements.txt`, `.gitignore`, compile smoke test và Git baseline.

**Điều kiện hoàn thành:** working tree sạch, demo khởi động, evaluation chạy và tài liệu khớp mã nguồn.

**Tiến độ:** nền tảng kỹ thuật đã hoàn thành: dependency, Git baseline, health
check, tài liệu và canonical app đã được xác định. Cần chạy lại smoke test sau
mỗi thay đổi lớn.

## Phase 2 — Chuẩn hóa Gold Benchmark

**Mục tiêu:** tạo ground truth có thể bảo vệ trước hội đồng.

- Rà 120 record theo `document -> page -> evidence -> answer -> question`.
- Viết lại câu lexical, generic hoặc quá gần evidence; thêm paraphrase/noisy tự nhiên và multi-document thật.
- Kiểm tra cân bằng category/query type; bổ sung negative/private-shop-data.
- Gán `gold_verified=true` sau kiểm chứng; khóa split TEST.

**Đầu ra:** `gold_benchmark_v1_locked.jsonl`, audit table và biên bản quy tắc annotation.

**Tiến độ:** đã có protocol, audit/lock guard, pilot 6 câu đã đối chiếu PDF và
workbench render nguồn + lưu review trail. 120 câu draft vẫn chưa được xác thực
và là blocker chính trước thực nghiệm chính thức.

## Phase 3 — Thực nghiệm RAG chính thức

**Mục tiêu:** chứng minh retrieval bằng số liệu, không chỉ demo.

Biến thể tối thiểu:

1. BM25.
2. Dense retrieval.
3. Hybrid không query-specific bonus.
4. Hybrid với heuristic hiện hữu.

Đo Hit@K, Recall@K, unique-document Recall@K, MRR@10, nDCG@5, Page Hit@5, median/P95 latency, theo overall/category/query type và từng split.

**Điều kiện hoàn thành:** chỉ dùng DEV để tuning, chạy final một lần trên TEST, có error analysis cho ít nhất 20 thất bại đại diện.

## Phase 4 — Cải thiện retrieval có kiểm chứng

**Mục tiêu:** sửa các lỗi đã quan sát ở DEV và đo lại cùng benchmark.

Ưu tiên kỹ thuật:

1. Diversification/MMR để tránh nhiều chunk trùng một tài liệu.
2. Context builder đa tài liệu và phân bổ token theo bằng chứng.
3. Citation/evidence gating: không đủ nguồn thì hỏi lại hoặc từ chối có lý do.
4. Tách pure hybrid khỏi heuristic để báo cáo công bằng.
5. Thử reranker chỉ khi baseline và error analysis cho thấy có giá trị.

**Không làm:** đổi nhiều thứ cùng lúc hoặc báo cáo điểm sau khi tuning trên TEST.

**Tiến độ:** đã hoàn thành một vòng DEV có kiểm chứng: sửa wording DEV để
không lộ evidence, thêm heuristic có unit test, chạy ablation 4 variant và
error analysis. Candidate v2 vẫn chưa được human-verify nên kết quả chỉ là
development/regression; không tiếp tục tune theo 17 câu này.

## Phase 5 — Lớp AI Agent tối thiểu, có thể bảo vệ

**Mục tiêu:** chuyển từ RAG assistant sang hệ thống chọn và phối hợp tool.

```text
Question
  -> Planner
     -> RAG Tool (chính sách, có citation)
     -> Shop Data Tool (CSV mô phỏng)
     -> Calculator Tool (công thức kiểm chứng)
  -> Synthesizer (answer + trace + citations)
```

Đầu ra dự kiến:

- `data/shop_mock/orders.csv`, `products.csv`, `inventory.csv`, `ads.csv`.
- `src/agent/planner.py`, `rag_tool.py`, `shop_data_tool.py`, `calculator_tool.py`, `agent_runner.py`.
- Schema tool input/output có validation; trace JSON không chứa dữ liệu nhạy cảm.
- Câu demo kết hợp doanh thu/đơn hàng mô phỏng + chính sách + tính phí.

**Điều kiện hoàn thành:** agent tự chọn đúng tool, không tự bịa dữ liệu nội bộ, và trả được ít nhất một tác vụ đa bước có thể đối chiếu.

**Tiến độ:** đã triển khai Agent baseline, CLI, Streamlit demo, dữ liệu mock và
trace. Agent đã có chế độ trong app chuẩn; state Agent tách khỏi chat RAG.
Agent không được mô tả là kết nối Seller Centre hay LLM planner.

## Phase 6 — Đánh giá Agent

**Mục tiêu:** đo được lợi ích của Agent thay vì chỉ mô tả luồng.

- 30–50 câu gồm policy-only, shop-data-only, calculation-only, multi-tool, private-data và out-of-scope.
- Đo tool-selection accuracy, task success, calculation exact match, evidence/citation correctness, refusal correctness và latency.
- So sánh RAG-only với Agent ở nhóm multi-tool; định nghĩa rõ tiêu chí chấm.

**Tiến độ:** đã có planner evaluation, end-to-end contract evaluator, candidate
32 câu có split DEV 16 / TEST 10 / CHALLENGE 6, workbench kiểm duyệt và guard
cho citation document/answer marker. Candidate vẫn hoàn toàn unverified; cần
người review chạy protocol trước khi ghi score vào luận văn. Việc còn lại sau
review: chạy DEV để sửa lỗi, đóng băng TEST, so sánh RAG-only/Agent trên nhóm
multi-tool và chỉ chạy TEST một lần.

## Phase 7 — Luận văn, slide và demo

**Mục tiêu:** mọi khẳng định trong báo cáo có evidence kỹ thuật tương ứng.

- Viết chương phương pháp, dataset/annotation, thí nghiệm, kết quả, lỗi và giới hạn; không gọi heuristic score là calibrated probability.
- Lưu bảng số liệu, graph, commit hash và prompt/config phiên bản.
- Demo 3 luồng: RAG policy, scope/private-data safeguard, agent multi-tool.
- Có phương án dự phòng nếu Ollama hoặc mạng lỗi: index local, canned test data, lệnh khởi động và kết quả CSV đã lưu.
