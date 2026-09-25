# Tái tạo Baseline V19

## Phạm vi tái tạo

Hướng dẫn này tái tạo ba lớp độc lập:

1. Artefact dữ liệu và vector index.
2. Demo Streamlit với Ollama.
3. Evaluation retrieval/scope không cần Ollama.

Không commit `data/raw/`, ChromaDB hay các hội thoại thực tế. Muốn tái tạo hoàn toàn index, cần nhận dữ liệu nguồn hợp lệ qua kênh được phép.

## 1. Môi trường

```powershell
cd C:\Users\Powder\Desktop\DoAnThacSi\master-thesis-rag-agent
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

Kiểm tra import cơ bản:

```powershell
.\.venv\Scripts\python.exe -m py_compile `
  src\extract_documents.py `
  src\chunk_documents_pageaware.py `
  src\build_vector_db.py `
  src\hybrid_search_shopee_v2.py `
  src\shopee_rag_complete_v4_0_1.py `
  src\evaluation\retrieval_eval.py `
  src\evaluation\scope_eval.py
```

## 2. Cấu hình cố định của baseline

| Biến | Mặc định | Dùng bởi |
| --- | --- | --- |
| `EMBEDDING_MODEL` | `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2` | build index và retrieval |
| `CHROMA_COLLECTION_NAME` | `shopee_rag_v1` | build index và retrieval |
| `OLLAMA_MODEL` | `qwen3:1.7b` | generation |
| `OLLAMA_URL` | `http://localhost:11434/api/chat` | generation |

Không thay đổi model embedding, collection, chunking hoặc bộ dữ liệu giữa các biến thể retrieval trong cùng một bảng thực nghiệm.

## 3. Chuẩn bị dữ liệu và index

Đặt dữ liệu nguồn vào `data/raw/` theo cấu trúc giữ nguyên nguồn và quyền sử dụng. Sau đó chạy theo đúng thứ tự:

```powershell
.\.venv\Scripts\python.exe src\extract_documents.py
.\.venv\Scripts\python.exe src\chunk_documents_pageaware.py
.\.venv\Scripts\python.exe src\build_vector_db.py
```

| Bước | Đầu vào | Đầu ra cần kiểm tra |
| --- | --- | --- |
| Extract | `data/raw/` | `data/processed/documents.jsonl`, `extraction_log.csv` |
| Chunk | `documents.jsonl` | `chunks.jsonl`, `chunking_log.csv` |
| Embed | `chunks.jsonl` | `data/vector_db/chroma_shopee_v1/`, `embedding_log.csv` |

Sau khi build, xác nhận collection count bằng số chunk được embedding thành công trong `embedding_log.csv`. Nếu thay dữ liệu/chunk/model, phải build lại index và ghi nhận version vào báo cáo thực nghiệm.

## 4. Chạy demo

Cài và khởi động Ollama ở terminal khác:

```powershell
ollama pull qwen3:1.7b
ollama serve
```

Khởi động ứng dụng:

```powershell
.\.venv\Scripts\streamlit.exe run src\shopee_chat_web_v19.py
```

Manual smoke test tối thiểu:

1. Hỏi một câu chính sách có trong tài liệu và kiểm tra nguồn/trang hiển thị.
2. Hỏi một câu diễn đạt lại cùng ý, kiểm tra retrieval không lệch nguồn.
3. Hỏi câu cần dữ liệu vận hành cửa hàng, kiểm tra hệ thống không bịa số liệu.
4. Hỏi câu ngoài phạm vi, kiểm tra hệ thống từ chối/chuyển hướng phù hợp.
5. Tạo câu hỏi nối tiếp, kiểm tra ngữ cảnh hội thoại không đổi chủ đề sai.

Các smoke test UI không thay cho bảng retrieval evaluation.

## 5. Chạy evaluation

Seed benchmark để kiểm tra hồi quy khung evaluation:

```powershell
.\.venv\Scripts\python.exe src\evaluation\retrieval_eval.py
.\.venv\Scripts\python.exe src\evaluation\scope_eval.py
```

Gold benchmark draft, dùng ba lần lặp để đo latency ổn định hơn:

```powershell
.\.venv\Scripts\python.exe src\evaluation\retrieval_eval.py `
  --dataset src\evaluation\gold_benchmark_v1.jsonl `
  --output data\processed\gold_v1_retrieval_eval_results.csv `
  --summary data\processed\gold_v1_retrieval_eval_summary.csv `
  --repetitions 3
```

Trước khi báo cáo một kết quả là chính thức:

1. Kiểm chứng từng record với PDF/trang nguồn.
2. Gán `gold_verified=true` chỉ khi evidence, document và page đều đúng.
3. Khóa `TEST`; mọi tuning chỉ dùng `DEV`.
4. Chạy tất cả biến thể cùng index, máy, benchmark và số repetitions.
5. Lưu commit hash, cấu hình, kết quả CSV và phân tích lỗi.

Ví dụ lần chạy TEST chính thức sau khi benchmark đã được khóa:

```powershell
.\.venv\Scripts\python.exe src\evaluation\retrieval_eval.py `
  --dataset src\evaluation\gold_benchmark_v1_locked.jsonl `
  --split test `
  --require-verified `
  --output data\processed\official_test_results.csv `
  --summary data\processed\official_test_summary.csv `
  --repetitions 3
```

`--require-verified` phải báo lỗi nếu còn bất kỳ record nào có
`gold_verified=false`; đây là guard để tránh vô ý xuất số liệu draft vào luận
văn.

Khóa một benchmark chỉ sau khi audit không còn flag:

```powershell
.\.venv\Scripts\python.exe src\evaluation\lock_gold_benchmark.py `
  --dataset src\evaluation\gold_benchmark_v1_reviewed.jsonl `
  --output src\evaluation\gold_benchmark_v1_locked.jsonl `
  --manifest src\evaluation\gold_benchmark_v1_locked_manifest.json
```

Manifest lưu SHA-256 của dataset và `chunks.jsonl`. Ghi kèm manifest và Git
commit hash vào phụ lục thực nghiệm.

Để kiểm tra cơ chế lock trước khi có benchmark lớn, có thể chạy thử bộ pilot 6
record đã verified (chỉ là kiểm tra tooling, không phải thí nghiệm):

```powershell
.\.venv\Scripts\python.exe src\evaluation\lock_gold_benchmark.py `
  --dataset src\evaluation\gold_pilot_verified.jsonl `
  --output $env:TEMP\gold_pilot_locked.jsonl `
  --manifest $env:TEMP\gold_pilot_locked_manifest.json
```

## 6. Kết quả cần lưu cho mỗi lần chạy chính thức

- Git commit hash và `git status --short` rỗng.
- Thời điểm chạy, Python version, cấu hình model/index.
- Dataset version, số record mỗi split/category/query type.
- File `*_results.csv`, `*_summary.csv` và bảng phân tích lỗi.
- Lý do/điều kiện thay đổi nếu có reranking, chunking hoặc embedding model mới.

Những thông tin này giúp số liệu trong luận văn có thể tái tạo và truy vết.
