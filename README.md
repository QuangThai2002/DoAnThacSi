# Shopee RAG Assistant — Baseline V19

Hệ thống trợ lý hỏi đáp tiếng Việt về chính sách, vận hành và API Shopee. Dự án kết hợp tìm kiếm từ khóa BM25, truy hồi ngữ nghĩa bằng embedding, ChromaDB và mô hình ngôn ngữ cục bộ qua Ollama. Giao diện người dùng được xây bằng Streamlit.

> **Trạng thái baseline:** RAG demo hoạt động và đã có khung đánh giá retrieval. Agent baseline có trace, tool routing và dữ liệu shop mô phỏng, nhưng chưa tích hợp vào UI hoặc hoàn tất đánh giá Agent độc lập. Gold Benchmark v1 vẫn cần kiểm chứng thủ công và thực nghiệm RAG chính thức chưa được khóa.

## Bản chạy chuẩn

| Vai trò | File chuẩn |
| --- | --- |
| Giao diện demo | `src/shopee_chat_web_v19.py` |
| Điều phối RAG + gọi LLM | `src/shopee_rag_complete_v4_0_1.py` |
| BM25, dense và hybrid retrieval | `src/hybrid_search_shopee_v2.py` |
| Trích xuất tài liệu | `src/extract_documents.py` |
| Chia đoạn có nhận biết trang | `src/chunk_documents_pageaware.py` |
| Xây ChromaDB | `src/build_vector_db.py` |
| Đánh giá retrieval | `src/evaluation/retrieval_eval.py` |
| Đánh giá phân luồng phạm vi | `src/evaluation/scope_eval.py` |

File `shopee_chat_web_v19.py` ở thư mục gốc chỉ là bản sao lịch sử. Không dùng file này để chạy demo, sửa lỗi hoặc lấy kết quả thực nghiệm.

## Kiến trúc hiện tại

```text
Tài liệu nguồn
  -> extract_documents.py -> documents.jsonl
  -> chunk_documents_pageaware.py -> chunks.jsonl
  -> build_vector_db.py -> ChromaDB (dense vectors)

Câu hỏi người dùng
  -> Streamlit V19 -> RAG backend
  -> scope/private-data guard + rewrite follow-up
  -> BM25 + dense retrieval -> hybrid heuristic
  -> context có giới hạn kích thước -> Ollama
  -> câu trả lời + nguồn + confidence level
```

Xem [kiến trúc chi tiết](docs/architecture.md) và [hướng dẫn tái tạo](docs/reproducibility.md).

## Cài đặt nhanh

Yêu cầu: Python 3.11+ được khuyến nghị, Git, và Ollama nếu muốn sinh câu trả lời từ LLM cục bộ.

```powershell
cd C:\Users\Powder\Desktop\DoAnThacSi\master-thesis-rag-agent
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

Tải model Ollama mặc định và chạy dịch vụ (chỉ cần cho phần generation):

```powershell
ollama pull qwen3:1.7b
ollama serve
```

Có thể thay đổi cấu hình mà không sửa mã nguồn:

```powershell
$env:OLLAMA_MODEL = "qwen3:1.7b"
$env:OLLAMA_URL = "http://localhost:11434/api/chat"
$env:EMBEDDING_MODEL = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
$env:CHROMA_COLLECTION_NAME = "shopee_rag_v1"
```

## Chạy hệ thống

```powershell
.\.venv\Scripts\streamlit.exe run src\shopee_chat_web_v19.py
```

Mở địa chỉ Streamlit hiện trên terminal, thường là `http://localhost:8501`.

## Xây lại chỉ mục từ dữ liệu nguồn

Không chạy các lệnh này nếu chỉ muốn dùng baseline sẵn có. Chúng tạo lại các artefact trong `data/processed/` và ChromaDB.

```powershell
.\.venv\Scripts\python.exe src\extract_documents.py
.\.venv\Scripts\python.exe src\chunk_documents_pageaware.py
.\.venv\Scripts\python.exe src\build_vector_db.py
```

Chi tiết đầu vào, đầu ra và kiểm tra sau mỗi bước nằm trong [hướng dẫn tái tạo](docs/reproducibility.md).

## Đánh giá

Chạy evaluation tách biệt hoàn toàn với các quick path, lịch sử hội thoại và UI:

```powershell
# Seed benchmark: chỉ dùng để smoke test khung đánh giá
.\.venv\Scripts\python.exe src\evaluation\retrieval_eval.py
.\.venv\Scripts\python.exe src\evaluation\scope_eval.py

# Gold Benchmark v1 Draft: chạy thử, không dùng làm số liệu luận văn cuối cùng
.\.venv\Scripts\python.exe src\evaluation\retrieval_eval.py `
  --dataset src\evaluation\gold_benchmark_v1.jsonl `
  --output data\processed\gold_v1_retrieval_eval_results.csv `
  --summary data\processed\gold_v1_retrieval_eval_summary.csv `
  --repetitions 3
```

Kết quả được ghi vào `data/processed/*_eval_results.csv` và `data/processed/*_eval_summary.csv`. Chỉ số chính gồm Hit@K, Recall@K, unique-document Recall@K, MRR@10, nDCG@5, Page Hit@5 và độ trễ.

**Lưu ý khoa học:** toàn bộ 120 câu của `gold_benchmark_v1.jsonl` hiện có `gold_verified=false`. Các câu được sinh từ chunk nên có thể thiên vị BM25; không được dùng các điểm số smoke test để kết luận hiệu quả của hệ thống trong luận văn.

`src/evaluation/gold_pilot_verified.jsonl` có 6 câu đã kiểm tra PDF/trang để minh họa quy trình annotation/lock. Bộ pilot quá nhỏ để báo cáo hiệu quả hệ thống.

Chạy health check không làm thay đổi các kết quả chính thức trong repository:

```powershell
.\scripts\verify_baseline.ps1
# Thêm retrieval smoke test (chậm hơn):
.\scripts\verify_baseline.ps1 -RunRetrieval
```

## Lộ trình đến bản bảo vệ

1. Kiểm chứng thủ công Gold Benchmark v1 theo PDF/trang, viết lại câu hỏi và khóa tập TEST.
2. Chạy thí nghiệm chính thức trên DEV / TEST / CHALLENGE, sau đó lập bảng lỗi.
3. Cải thiện retrieval dựa trên lỗi DEV, không tuning theo TEST.
4. Mở rộng và đánh giá Agent baseline: RAG Tool + Shop Data Tool (dữ liệu mô phỏng) + Calculator Tool + planner có log bước chạy.
5. Hoàn thiện luận văn, slide và kịch bản demo.

Lộ trình kỹ thuật cụ thể: [docs/roadmap.md](docs/roadmap.md).

Agent baseline và cách chạy demo: [docs/agent_baseline.md](docs/agent_baseline.md).

```powershell
.\.venv\Scripts\streamlit.exe run src\agent_demo.py --server.port 8502
```

## Dữ liệu và quyền riêng tư

- `data/raw/`, `data/vector_db/`, các bản sao hội thoại và file nén bị loại khỏi Git qua `.gitignore`.
- Không đưa khóa API, dữ liệu cửa hàng thật hoặc thông tin nhận diện người dùng vào repository hay báo cáo.
- Dữ liệu cửa hàng ở Agent phase sẽ là dữ liệu mô phỏng, có mô tả rõ giới hạn trong luận văn.

## Giới hạn baseline cần nêu trung thực

- `confidence` hiện là evidence-sufficiency / heuristic nội bộ, không phải xác suất câu trả lời đúng đã được calibration.
- Các quick path trong UI có thể tạo phản hồi định sẵn cho vài nhóm câu hỏi; chúng không được dùng trong evaluation retrieval.
- Agent hiện là baseline xác định được tool routing trên dữ liệu mock; chưa phải kết nối shop thật hoặc LLM planner, nên không được mô tả quá phạm vi này trong luận văn.
