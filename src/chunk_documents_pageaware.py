from __future__ import annotations

from pathlib import Path
import csv
import json
import re
from datetime import datetime


PROJECT_ROOT = Path(__file__).resolve().parents[1]
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"

DOCUMENTS_PATH = PROCESSED_DIR / "documents.jsonl"
CHUNKS_PATH = PROCESSED_DIR / "chunks.jsonl"
CHUNKING_LOG_PATH = PROCESSED_DIR / "chunking_log.csv"

# Mỗi chunk chỉ thuộc một trang để trích dẫn không bị lệch.
MAX_CHARS = 2400
OVERLAP_CHARS = 250
MIN_CHARS = 80


def clean_text(text: str) -> str:
    if not text:
        return ""

    text = text.replace("\x00", " ")
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    lines = []
    previous_blank = False

    for raw_line in text.splitlines():
        line = re.sub(r"[ \t]+", " ", raw_line).strip()

        if not line:
            if not previous_blank:
                lines.append("")
            previous_blank = True
        else:
            lines.append(line)
            previous_blank = False

    return "\n".join(lines).strip()


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


def split_document_sections(text: str) -> list[dict]:
    """
    Hỗ trợ:
    ===== PAGE 1 =====
    ===== SHEET Sheet1 =====
    Nếu không có marker thì trả về một section chung.
    """
    text = text.replace("\r\n", "\n").replace("\r", "\n")

    pattern = re.compile(
        r"===== (PAGE|SHEET) ([^=\n]+) ====="
    )
    matches = list(pattern.finditer(text))

    if not matches:
        return [
            {
                "location_type": "document",
                "location": "",
                "text": clean_text(text),
            }
        ]

    sections = []

    if matches[0].start() > 0:
        before = clean_text(text[:matches[0].start()])
        if before:
            sections.append(
                {
                    "location_type": "document",
                    "location": "",
                    "text": before,
                }
            )

    for index, match in enumerate(matches):
        start = match.end()
        end = (
            matches[index + 1].start()
            if index + 1 < len(matches)
            else len(text)
        )

        section_text = clean_text(text[start:end])

        if section_text:
            sections.append(
                {
                    "location_type": match.group(1).lower(),
                    "location": match.group(2).strip(),
                    "text": section_text,
                }
            )

    return sections


def split_long_unit(text: str) -> list[str]:
    text = clean_text(text)

    if len(text) <= MAX_CHARS:
        return [text]

    # Ưu tiên cắt theo câu.
    sentences = re.split(
        r"(?<=[.!?;:])\s+",
        text,
    )

    units = []
    current = ""

    for sentence in sentences:
        sentence = clean_text(sentence)
        if not sentence:
            continue

        candidate = (
            sentence
            if not current
            else current + " " + sentence
        )

        if len(candidate) <= MAX_CHARS:
            current = candidate
            continue

        if current:
            units.append(current)
            current = ""

        if len(sentence) <= MAX_CHARS:
            current = sentence
            continue

        # Câu quá dài: cắt theo từ, không cắt giữa từ.
        words = sentence.split()
        word_chunk = ""

        for word in words:
            word_candidate = (
                word
                if not word_chunk
                else word_chunk + " " + word
            )

            if len(word_candidate) <= MAX_CHARS:
                word_chunk = word_candidate
            else:
                if word_chunk:
                    units.append(word_chunk)
                word_chunk = word

        if word_chunk:
            current = word_chunk

    if current:
        units.append(current)

    return units


def build_units(section_text: str) -> list[str]:
    paragraphs = [
        clean_text(paragraph)
        for paragraph in re.split(
            r"\n\s*\n",
            section_text,
        )
        if clean_text(paragraph)
    ]

    units = []
    for paragraph in paragraphs:
        units.extend(split_long_unit(paragraph))

    return units


def overlap_tail(text: str) -> str:
    if OVERLAP_CHARS <= 0:
        return ""

    tail = text[-OVERLAP_CHARS:]

    # Không bắt đầu giữa từ.
    first_space = tail.find(" ")
    if first_space >= 0:
        tail = tail[first_space + 1:]

    return clean_text(tail)


def chunk_one_section(section: dict) -> list[dict]:
    units = build_units(section["text"])
    chunks = []
    current = ""

    for unit in units:
        candidate = (
            unit
            if not current
            else current + "\n\n" + unit
        )

        if len(candidate) <= MAX_CHARS:
            current = candidate
            continue

        if len(current) >= MIN_CHARS:
            chunks.append(
                {
                    "text": clean_text(current),
                    "location_type": section["location_type"],
                    "location": section["location"],
                }
            )

        tail = overlap_tail(current)
        current = (
            unit
            if not tail
            else clean_text(tail + "\n\n" + unit)
        )

        # Bảo đảm overlap + unit không vượt ngưỡng.
        if len(current) > MAX_CHARS:
            pieces = split_long_unit(current)
            for piece in pieces[:-1]:
                if len(piece) >= MIN_CHARS:
                    chunks.append(
                        {
                            "text": piece,
                            "location_type": section["location_type"],
                            "location": section["location"],
                        }
                    )
            current = pieces[-1] if pieces else ""

    if len(current) >= MIN_CHARS:
        chunks.append(
            {
                "text": clean_text(current),
                "location_type": section["location_type"],
                "location": section["location"],
            }
        )

    return chunks


def make_page_aware_chunks(text: str) -> list[dict]:
    all_chunks = []

    for section in split_document_sections(text):
        all_chunks.extend(chunk_one_section(section))

    return all_chunks


def write_jsonl(records: list[dict], path: Path) -> None:
    with path.open("w", encoding="utf-8") as file:
        for record in records:
            file.write(
                json.dumps(record, ensure_ascii=False) + "\n"
            )


def write_csv(
    rows: list[dict],
    path: Path,
) -> None:
    fieldnames = [
        "document_id",
        "title",
        "source_group",
        "text_length",
        "chunk_count",
        "avg_chunk_length",
        "status",
        "created_at",
        "note",
    ]

    with path.open(
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
    if not DOCUMENTS_PATH.exists():
        print(f"Không tìm thấy: {DOCUMENTS_PATH}")
        print("Hãy chạy: python .\\src\\extract_documents.py")
        return

    documents = load_jsonl(DOCUMENTS_PATH)

    if not documents:
        print("documents.jsonl đang rỗng.")
        return

    all_chunks = []
    log_rows = []

    print(f"Số tài liệu đầu vào: {len(documents)}")
    print(
        "Mỗi chunk được giới hạn trong một trang/sheet "
        "để trích dẫn chính xác.\n"
    )

    used_chunk_ids = set()

    for document in documents:
        document_id = str(
            document.get("document_id", "")
        ).strip()
        title = str(document.get("title", "")).strip()
        text = clean_text(document.get("text", ""))
        source_group = str(
            document.get("source_group", "")
        ).strip()

        if not document_id:
            status = "missing_document_id"
            chunks = []
            note = "Tài liệu không có document_id."
        elif not text:
            status = "empty_text"
            chunks = []
            note = "Tài liệu không có text."
        elif not bool(document.get("use_for_retrieval", True)):
            status = "excluded_by_metadata"
            chunks = []
            note = "use_for_retrieval=false."
        else:
            chunks = make_page_aware_chunks(text)
            status = "success" if chunks else "no_chunks"
            note = (
                "Chunk không vượt qua ranh giới trang/sheet; "
                "overlap chỉ nằm trong cùng location."
            )

        for index, chunk in enumerate(chunks, start=1):
            chunk_id = f"{document_id}_CHUNK_{index:04d}"

            if chunk_id in used_chunk_ids:
                raise ValueError(
                    f"Trùng chunk_id: {chunk_id}"
                )
            used_chunk_ids.add(chunk_id)

            location_type = chunk["location_type"]
            location = chunk["location"]

            page = (
                location
                if location_type == "page"
                else ""
            )

            chunk_record = {
                "chunk_id": chunk_id,
                "document_id": document_id,
                "chunk_index": index,
                "title": title,
                "document_type": document.get(
                    "document_type",
                    "",
                ),
                "source_group": source_group,
                "source": document.get("source", ""),
                "source_owner": document.get(
                    "source_owner",
                    "",
                ),
                "source_url": document.get(
                    "source_url",
                    "",
                ),
                "organization": document.get(
                    "organization",
                    "",
                ),
                "published_year": document.get(
                    "published_year",
                    "",
                ),
                "effective_date": document.get(
                    "effective_date",
                    "",
                ),
                "language": document.get(
                    "language",
                    "",
                ),
                "file_path": document.get(
                    "file_path",
                    "",
                ),
                "detected_file_path": document.get(
                    "detected_file_path",
                    "",
                ),
                "sha256": document.get("sha256", ""),
                "data_authenticity": document.get(
                    "data_authenticity",
                    "",
                ),
                "verification_status": document.get(
                    "verification_status",
                    "",
                ),
                "location_type": location_type,
                "location": location,
                "page": page,
                "page_start": page,
                "page_end": page,
                "pages": page,
                "text": chunk["text"],
                "char_count": len(chunk["text"]),
            }

            all_chunks.append(chunk_record)

        average_length = (
            round(
                sum(
                    len(chunk["text"])
                    for chunk in chunks
                ) / len(chunks),
                2,
            )
            if chunks
            else 0
        )

        log_rows.append(
            {
                "document_id": document_id,
                "title": title,
                "source_group": source_group,
                "text_length": len(text),
                "chunk_count": len(chunks),
                "avg_chunk_length": average_length,
                "status": status,
                "created_at": datetime.now().strftime(
                    "%Y-%m-%d %H:%M:%S"
                ),
                "note": note,
            }
        )

        print(
            f"{document_id} | {status} | "
            f"{len(text)} ký tự | {len(chunks)} chunks"
        )

    write_jsonl(all_chunks, CHUNKS_PATH)
    write_csv(log_rows, CHUNKING_LOG_PATH)

    print("\n===== HOÀN THÀNH =====")
    print(f"Tổng tài liệu : {len(documents)}")
    print(f"Tổng chunks   : {len(all_chunks)}")
    print(f"Đã ghi        : {CHUNKS_PATH}")
    print(f"Đã ghi        : {CHUNKING_LOG_PATH}")
    print(
        "\nBước tiếp theo: "
        "python .\\src\\build_vector_db.py"
    )


if __name__ == "__main__":
    main()
