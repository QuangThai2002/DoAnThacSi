from __future__ import annotations

from pathlib import Path
import csv
import json
import os
from datetime import datetime

import chromadb
from sentence_transformers import SentenceTransformer


PROJECT_ROOT = Path(__file__).resolve().parents[1]
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"

VECTOR_DB_DIR = (
    PROJECT_ROOT
    / "data"
    / "vector_db"
    / "chroma_shopee_v1"
)

CHUNKS_PATH = PROCESSED_DIR / "chunks.jsonl"
EMBEDDING_LOG_PATH = PROCESSED_DIR / "embedding_log.csv"

COLLECTION_NAME = os.getenv(
    "CHROMA_COLLECTION_NAME",
    "shopee_rag_v1",
)

MODEL_NAME = os.getenv(
    "EMBEDDING_MODEL",
    "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
)

BATCH_SIZE = 32


def load_jsonl(path: Path) -> list[dict]:
    records = []

    with path.open("r", encoding="utf-8") as file:
        for line_number, line in enumerate(file, start=1):
            line = line.strip()
            if not line:
                continue

            try:
                records.append(json.loads(line))
            except json.JSONDecodeError as error:
                raise ValueError(
                    f"Lỗi JSON tại dòng {line_number}: {error}"
                ) from error

    return records


def safe_metadata(chunk: dict) -> dict:
    fields = [
        "document_id",
        "chunk_index",
        "title",
        "document_type",
        "source_group",
        "source",
        "source_owner",
        "source_url",
        "organization",
        "published_year",
        "effective_date",
        "language",
        "file_path",
        "detected_file_path",
        "sha256",
        "data_authenticity",
        "verification_status",
        "location_type",
        "location",
        "page",
        "page_start",
        "page_end",
        "pages",
        "char_count",
    ]

    metadata = {}

    for field in fields:
        value = chunk.get(field, "")

        if value is None:
            value = ""

        if isinstance(value, (str, int, float, bool)):
            metadata[field] = value
        else:
            metadata[field] = str(value)

    return metadata


def write_log(rows: list[dict]) -> None:
    fieldnames = [
        "collection_name",
        "model_name",
        "vector_db_path",
        "total_chunks",
        "success_count",
        "failed_count",
        "collection_count",
        "created_at",
        "note",
    ]

    with EMBEDDING_LOG_PATH.open(
        "w",
        encoding="utf-8-sig",
        newline="",
    ) as file:
        writer = csv.DictWriter(
            file,
            fieldnames=fieldnames,
        )
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    if not CHUNKS_PATH.exists():
        print(f"Không tìm thấy: {CHUNKS_PATH}")
        print(
            "Hãy chạy: "
            "python .\\src\\chunk_documents_pageaware.py"
        )
        return

    chunks = load_jsonl(CHUNKS_PATH)

    if not chunks:
        print("chunks.jsonl đang rỗng.")
        return

    chunk_ids = [
        str(chunk.get("chunk_id", "")).strip()
        for chunk in chunks
    ]

    if any(not chunk_id for chunk_id in chunk_ids):
        raise ValueError(
            "Có chunk không có chunk_id."
        )

    if len(chunk_ids) != len(set(chunk_ids)):
        raise ValueError(
            "Phát hiện chunk_id bị trùng. "
            "Chưa tạo vector database."
        )

    VECTOR_DB_DIR.mkdir(parents=True, exist_ok=True)

    print(f"Tổng số chunks: {len(chunks)}")
    print(f"Embedding model: {MODEL_NAME}")
    print(f"Collection: {COLLECTION_NAME}")
    print(f"Vector DB: {VECTOR_DB_DIR}")
    print(
        "Lần chạy đầu có thể tải model từ Internet "
        "và mất vài phút.\n"
    )

    model = SentenceTransformer(MODEL_NAME)

    client = chromadb.PersistentClient(
        path=str(VECTOR_DB_DIR)
    )

    try:
        client.delete_collection(
            name=COLLECTION_NAME
        )
        print(
            f"Đã xóa collection cũ: {COLLECTION_NAME}"
        )
    except Exception:
        pass

    collection = client.create_collection(
        name=COLLECTION_NAME,
        metadata={
            "hnsw:space": "cosine",
            "embedding_model": MODEL_NAME,
            "project": "master_thesis_shopee_rag",
        },
    )

    success_count = 0
    failed_count = 0

    for start in range(0, len(chunks), BATCH_SIZE):
        batch = chunks[start:start + BATCH_SIZE]

        ids = []
        texts = []
        metadatas = []

        for chunk in batch:
            chunk_id = str(
                chunk.get("chunk_id", "")
            ).strip()
            text = str(
                chunk.get("text", "")
            ).strip()

            if not chunk_id or not text:
                failed_count += 1
                continue

            ids.append(chunk_id)
            texts.append(text)
            metadatas.append(safe_metadata(chunk))

        if not texts:
            continue

        try:
            embeddings = model.encode(
                texts,
                batch_size=16,
                show_progress_bar=False,
                normalize_embeddings=True,
            ).tolist()

            collection.add(
                ids=ids,
                embeddings=embeddings,
                documents=texts,
                metadatas=metadatas,
            )

            success_count += len(texts)

            print(
                f"Đã xử lý "
                f"{min(start + BATCH_SIZE, len(chunks))}"
                f"/{len(chunks)} chunks"
            )

        except Exception as error:
            failed_count += len(texts)
            print(
                f"Lỗi batch bắt đầu tại {start}: {error}"
            )

    collection_count = collection.count()

    note = (
        "Thành công."
        if (
            failed_count == 0
            and collection_count == success_count
        )
        else (
            "Cần kiểm tra: số bản ghi Chroma "
            "không khớp hoặc có batch thất bại."
        )
    )

    write_log(
        [
            {
                "collection_name": COLLECTION_NAME,
                "model_name": MODEL_NAME,
                "vector_db_path": str(VECTOR_DB_DIR),
                "total_chunks": len(chunks),
                "success_count": success_count,
                "failed_count": failed_count,
                "collection_count": collection_count,
                "created_at": datetime.now().strftime(
                    "%Y-%m-%d %H:%M:%S"
                ),
                "note": note,
            }
        ]
    )

    print("\n===== HOÀN THÀNH =====")
    print(f"Success          : {success_count}")
    print(f"Failed           : {failed_count}")
    print(f"Collection count : {collection_count}")
    print(f"Log              : {EMBEDDING_LOG_PATH}")

    if collection_count != success_count:
        raise RuntimeError(
            "Collection count không khớp success_count."
        )


if __name__ == "__main__":
    main()
