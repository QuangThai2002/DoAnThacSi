from pathlib import Path

import chromadb
from sentence_transformers import SentenceTransformer


# =========================
# 1. Cấu hình
# =========================

PROJECT_ROOT = Path(__file__).resolve().parents[1]

VECTOR_DB_DIR = PROJECT_ROOT / "data" / "vector_db" / "chroma"

COLLECTION_NAME = "enterprise_rag_v1"
MODEL_NAME = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"


# =========================
# 2. Hàm tìm kiếm
# =========================

def search(query: str, top_k: int = 5):
    model = SentenceTransformer(MODEL_NAME)

    client = chromadb.PersistentClient(path=str(VECTOR_DB_DIR))
    collection = client.get_collection(name=COLLECTION_NAME)

    query_embedding = model.encode(
        [query],
        normalize_embeddings=True
    ).tolist()

    results = collection.query(
        query_embeddings=query_embedding,
        n_results=top_k,
        include=["documents", "metadatas", "distances"]
    )

    documents = results["documents"][0]
    metadatas = results["metadatas"][0]
    distances = results["distances"][0]

    print("\n==============================")
    print(f"Câu hỏi: {query}")
    print("==============================\n")

    for i, (doc, meta, distance) in enumerate(zip(documents, metadatas, distances), start=1):
        print(f"--- Kết quả {i} ---")
        print(f"Điểm distance: {distance}")
        print(f"Tài liệu: {meta.get('title')}")
        print(f"Loại tài liệu: {meta.get('document_type')}")
        print(f"Tổ chức: {meta.get('organization')}")
        print(f"Năm: {meta.get('published_year')}")
        print(f"Chunk ID: {meta.get('document_id')}_chunk_{str(meta.get('chunk_index')).zfill(4)}")
        print("\nĐoạn nội dung:")
        print(doc[:1000])
        print("\n")


# =========================
# 3. Chạy thử
# =========================

if __name__ == "__main__":
    test_questions = [
        "FPT có chiến lược phát triển như thế nào?",
        "Doanh nghiệp có những rủi ro kinh doanh nào?",
        "Vinamilk có doanh thu năm 2024 là bao nhiêu?",
        "Quy định về bảo vệ dữ liệu cá nhân là gì?",
        "Người lao động được nghỉ phép năm bao nhiêu ngày?"
    ]

    for question in test_questions:
        search(question, top_k=3)