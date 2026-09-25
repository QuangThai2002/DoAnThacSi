from __future__ import annotations

from pathlib import Path
import csv
import hashlib
import json
import re
import unicodedata
import zipfile
from collections import Counter
from datetime import datetime
from html import unescape
from xml.etree import ElementTree as ET

import fitz  # PyMuPDF
import pandas as pd


# ============================================================
# CẤU HÌNH
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = PROJECT_ROOT / "data" / "raw"
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"

DOCUMENTS_PATH = PROCESSED_DIR / "documents.jsonl"
EXTRACTION_LOG_PATH = PROCESSED_DIR / "extraction_log.csv"
GENERATED_METADATA_PATH = PROCESSED_DIR / "metadata_generated.csv"

# Chỉ quét các nhóm dữ liệu phục vụ đề tài Shopee.
ALLOWED_SOURCE_GROUPS = {
    "shopee_policy",
    "shopee_api",
    "legal_ecommerce",
    "sea_shopee_reports",
    "ecommerce_market_reports",
    "electronics_market",
    "customer_review_dataset",
    "shop_actual",
    "news_trends",
    "research_papers",
}

# Không bao giờ đưa các khu vực tạm/kiểm tra vào RAG.
EXCLUDED_DIR_NAMES = {
    "incoming_legal",
    "incoming_shopee",
    "_duplicates",
    "_excluded_drafts",
    "_manual_review",
    "_legacy",
    "__pycache__",
}

SUPPORTED_EXTENSIONS = {
    ".pdf",
    ".xlsx",
    ".xls",
    ".csv",
    ".txt",
    ".md",
    ".json",
    ".jsonl",
    ".html",
    ".htm",
    ".doc",
    ".docx",
}

MIN_PDF_TOTAL_TEXT = 500
MIN_PDF_AVG_TEXT_PER_PAGE = 50


# ============================================================
# HÀM TIỆN ÍCH
# ============================================================

def clean_text(text: str) -> str:
    if not text:
        return ""

    text = text.replace("\x00", " ").replace("\r\n", "\n").replace("\r", "\n")
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


def normalize_for_compare(text: str) -> str:
    text = text.replace("Đ", "D").replace("đ", "d")
    text = unicodedata.normalize("NFD", text)
    text = "".join(
        char for char in text
        if unicodedata.category(char) != "Mn"
    )
    text = text.lower()
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file:
        for block in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def is_excluded(path: Path) -> bool:
    relative_parts = path.relative_to(RAW_DIR).parts

    if not relative_parts:
        return True

    source_group = relative_parts[0]
    if source_group not in ALLOWED_SOURCE_GROUPS:
        return True

    return any(part in EXCLUDED_DIR_NAMES for part in relative_parts)


def infer_document_id(path: Path) -> str:
    """
    Tạo document_id từ tên file chuẩn:
    shp_pol_001_... -> SHP_POL_001
    law_quality_002a_... -> LAW_QUALITY_002A
    market_vn_001_... -> MARKET_VN_001
    """
    parts = path.stem.split("_")

    if (
        len(parts) >= 3
        and re.fullmatch(r"[a-zA-Z]+", parts[0])
        and re.fullmatch(r"[a-zA-Z]+", parts[1])
        and re.fullmatch(r"\d{3}[a-zA-Z]?", parts[2])
    ):
        return "_".join(parts[:3]).upper()

    # Fallback ổn định, không phụ thuộc fuzzy matching.
    short_hash = sha256(path)[:10].upper()
    source_group = path.relative_to(RAW_DIR).parts[0].upper()
    return f"{source_group}_{short_hash}"


def infer_title(path: Path) -> str:
    parts = path.stem.split("_")

    if (
        len(parts) >= 4
        and re.fullmatch(r"\d{3}[a-zA-Z]?", parts[2])
    ):
        title_parts = parts[3:]
    else:
        title_parts = parts

    title = " ".join(title_parts)
    title = re.sub(r"\s+", " ", title).strip()
    return title[:1].upper() + title[1:] if title else path.stem


def infer_year(path: Path) -> str:
    years = re.findall(r"(?<!\d)(20\d{2})(?!\d)", path.stem)
    return years[-1] if years else ""


def infer_language(source_group: str) -> str:
    if source_group in {"sea_shopee_reports", "shopee_api"}:
        return "en"
    return "vi"


def remove_repeated_pdf_lines(page_texts: list[str]) -> list[str]:
    """
    Loại header/footer/menu lặp lại trên nhiều trang.
    Không xóa các dòng quá dài để tránh mất nội dung điều khoản.
    """
    if len(page_texts) < 3:
        return page_texts

    page_line_sets = []
    for page_text in page_texts:
        normalized_lines = set()
        for line in page_text.splitlines():
            normalized = normalize_for_compare(line)

            if not normalized:
                continue
            if re.fullmatch(r"\d{1,4}", normalized):
                continue
            if 3 <= len(normalized) <= 120:
                normalized_lines.add(normalized)

        page_line_sets.append(normalized_lines)

    counter = Counter()
    for line_set in page_line_sets:
        counter.update(line_set)

    threshold = max(3, int(len(page_texts) * 0.60))
    repeated_lines = {
        line for line, count in counter.items()
        if count >= threshold
    }

    cleaned_pages = []
    for page_text in page_texts:
        kept_lines = []

        for line in page_text.splitlines():
            normalized = normalize_for_compare(line)

            if normalized in repeated_lines:
                continue

            kept_lines.append(line)

        cleaned_pages.append(clean_text("\n".join(kept_lines)))

    return cleaned_pages


# ============================================================
# TRÍCH XUẤT THEO ĐỊNH DẠNG
# ============================================================

def extract_pdf_text(path: Path) -> tuple[str, int, dict]:
    if path.read_bytes()[:5] != b"%PDF-":
        raise ValueError(
            "File có đuôi .pdf nhưng không phải PDF thật. "
            "Hãy đổi về đúng định dạng hoặc thay bằng PDF hợp lệ."
        )

    page_texts = []

    with fitz.open(path) as document:
        page_count = len(document)

        for page in document:
            page_text = clean_text(page.get_text("text"))
            page_texts.append(page_text)

    page_texts = remove_repeated_pdf_lines(page_texts)

    text_parts = []
    nonempty_pages = 0

    for page_number, page_text in enumerate(page_texts, start=1):
        if not page_text:
            continue

        nonempty_pages += 1
        text_parts.append(
            f"===== PAGE {page_number} =====\n{page_text}"
        )

    full_text = clean_text("\n\n".join(text_parts))
    average_text = (
        len(full_text) / page_count
        if page_count
        else 0
    )

    quality = {
        "nonempty_pages": nonempty_pages,
        "average_text_per_page": round(average_text, 2),
    }

    return full_text, page_count, quality


def extract_excel_text(path: Path) -> tuple[str, int, dict]:
    sheets = pd.read_excel(path, sheet_name=None, dtype=str)
    text_parts = []

    for sheet_name, dataframe in sheets.items():
        dataframe = dataframe.fillna("")
        rows = []

        for _, row in dataframe.iterrows():
            values = [
                str(value).strip()
                for value in row.tolist()
                if str(value).strip()
            ]
            if values:
                rows.append(" | ".join(values))

        if rows:
            text_parts.append(
                f"===== SHEET {sheet_name} =====\n"
                + "\n".join(rows)
            )

    return (
        clean_text("\n\n".join(text_parts)),
        len(sheets),
        {"nonempty_sheets": len(text_parts)},
    )


def extract_text_file(path: Path) -> tuple[str, int, dict]:
    encodings = ["utf-8-sig", "utf-8", "cp1258", "latin-1"]

    for encoding in encodings:
        try:
            text = path.read_text(encoding=encoding)
            return clean_text(text), 1, {"encoding": encoding}
        except UnicodeDecodeError:
            continue

    text = path.read_text(encoding="utf-8", errors="ignore")
    return clean_text(text), 1, {"encoding": "utf-8-errors-ignore"}


def html_to_text(html: str) -> str:
    html = re.sub(
        r"(?is)<(script|style).*?>.*?</\1>",
        " ",
        html,
    )
    html = re.sub(r"(?i)<br\s*/?>", "\n", html)
    html = re.sub(r"(?i)</p\s*>", "\n\n", html)
    html = re.sub(r"(?i)</div\s*>", "\n", html)
    html = re.sub(r"(?i)</h[1-6]\s*>", "\n\n", html)
    html = re.sub(r"(?s)<[^>]+>", " ", html)
    return clean_text(unescape(html))


def extract_html_or_doc_text(path: Path) -> tuple[str, int, dict]:
    raw = path.read_bytes()
    head = raw[:1000].lower()

    # Nhiều file .doc tải từ website thực chất là HTML.
    if b"<html" in head or b"<!doctype html" in head:
        for encoding in ["utf-8-sig", "utf-8", "cp1258", "latin-1"]:
            try:
                html = raw.decode(encoding)
                return (
                    html_to_text(html),
                    1,
                    {
                        "detected_format": "html",
                        "encoding": encoding,
                    },
                )
            except UnicodeDecodeError:
                continue

    raise ValueError(
        "File .doc nhị phân chưa được hỗ trợ. "
        "Hãy mở bằng Word và Save As PDF hoặc DOCX."
    )


def extract_docx_text(path: Path) -> tuple[str, int, dict]:
    namespace = {
        "w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
    }

    with zipfile.ZipFile(path) as archive:
        xml = archive.read("word/document.xml")

    root = ET.fromstring(xml)
    paragraphs = []

    for paragraph in root.findall(".//w:p", namespace):
        texts = [
            node.text or ""
            for node in paragraph.findall(".//w:t", namespace)
        ]
        text = clean_text("".join(texts))
        if text:
            paragraphs.append(text)

    return (
        clean_text("\n\n".join(paragraphs)),
        1,
        {"detected_format": "docx"},
    )


def extract_file(path: Path) -> tuple[str, int, dict]:
    extension = path.suffix.lower()

    if extension == ".pdf":
        return extract_pdf_text(path)

    if extension in {".xlsx", ".xls"}:
        return extract_excel_text(path)

    if extension in {
        ".csv",
        ".txt",
        ".md",
        ".json",
        ".jsonl",
    }:
        return extract_text_file(path)

    if extension in {".html", ".htm", ".doc"}:
        return extract_html_or_doc_text(path)

    if extension == ".docx":
        return extract_docx_text(path)

    raise ValueError(f"Chưa hỗ trợ định dạng: {extension}")


# ============================================================
# GHI KẾT QUẢ
# ============================================================

def write_jsonl(records: list[dict], path: Path) -> None:
    with path.open("w", encoding="utf-8") as file:
        for record in records:
            file.write(
                json.dumps(record, ensure_ascii=False) + "\n"
            )


def write_csv(
    rows: list[dict],
    path: Path,
    fieldnames: list[str],
) -> None:
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


# ============================================================
# CHƯƠNG TRÌNH CHÍNH
# ============================================================

def main() -> None:
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

    if not RAW_DIR.exists():
        print(f"Không tìm thấy thư mục: {RAW_DIR}")
        return

    raw_files = [
        path
        for path in RAW_DIR.rglob("*")
        if path.is_file()
        and path.suffix.lower() in SUPPORTED_EXTENSIONS
        and not is_excluded(path)
    ]

    raw_files.sort(
        key=lambda path: path.relative_to(RAW_DIR).as_posix().lower()
    )

    print(f"Tìm thấy {len(raw_files)} file hợp lệ trong data/raw.")
    print("Không sử dụng fuzzy matching.")
    print("Đang trích xuất trực tiếp theo đường dẫn thật...\n")

    documents = []
    log_rows = []
    metadata_rows = []
    used_ids = set()

    for path in raw_files:
        relative_path = path.relative_to(PROJECT_ROOT).as_posix()
        source_group = path.relative_to(RAW_DIR).parts[0]
        document_id = infer_document_id(path)

        if document_id in used_ids:
            document_id = (
                f"{document_id}_{sha256(path)[:6].upper()}"
            )
        used_ids.add(document_id)

        title = infer_title(path)
        status = "failed"
        note = ""
        extracted_text = ""
        page_or_sheet_count = 0
        quality = {}

        try:
            (
                extracted_text,
                page_or_sheet_count,
                quality,
            ) = extract_file(path)

            if path.suffix.lower() == ".pdf":
                average_text = float(
                    quality.get("average_text_per_page", 0)
                )

                if (
                    len(extracted_text) < MIN_PDF_TOTAL_TEXT
                    or average_text < MIN_PDF_AVG_TEXT_PER_PAGE
                ):
                    status = "needs_text_layer"
                    note = (
                        "PDF có quá ít lớp văn bản. "
                        "Không đưa vào documents.jsonl; "
                        "hãy tìm bản HTML/DOCX/PDF có text hoặc OCR kiểm chứng."
                    )
                else:
                    status = "success"
                    note = "Trích xuất PDF thành công."
            elif len(extracted_text) < 100:
                status = "warning_low_text"
                note = "Nội dung quá ngắn; chưa đưa vào RAG."
            else:
                status = "success"
                note = "Trích xuất thành công."

        except Exception as error:
            status = "error"
            note = str(error)

        include_in_documents = status == "success"

        if include_in_documents:
            document_record = {
                "document_id": document_id,
                "title": title,
                "document_type": path.suffix.lower().lstrip("."),
                "source_group": source_group,
                "source": "",
                "source_owner": "",
                "source_url": "",
                "organization": "",
                "published_year": infer_year(path),
                "effective_date": "",
                "language": infer_language(source_group),
                "file_path": relative_path,
                "detected_file_path": relative_path,
                "sha256": sha256(path),
                "data_authenticity": "pending_metadata_verification",
                "verification_status": "text_verified_metadata_pending",
                "use_for_retrieval": True,
                "page_or_sheet_count": page_or_sheet_count,
                "text_length": len(extracted_text),
                "extracted_at": datetime.now().strftime(
                    "%Y-%m-%d %H:%M:%S"
                ),
                "text": extracted_text,
            }
            documents.append(document_record)

        log_rows.append(
            {
                "document_id": document_id,
                "title": title,
                "source_group": source_group,
                "file_path": relative_path,
                "file_type": path.suffix.lower(),
                "status": status,
                "included_in_documents": include_in_documents,
                "text_length": len(extracted_text),
                "page_or_sheet_count": page_or_sheet_count,
                "sha256": sha256(path),
                "extracted_at": datetime.now().strftime(
                    "%Y-%m-%d %H:%M:%S"
                ),
                "note": note,
            }
        )

        metadata_rows.append(
            {
                "document_id": document_id,
                "title": title,
                "source_group": source_group,
                "file_path": relative_path,
                "source_owner": "",
                "source_url": "",
                "published_date": "",
                "effective_date": "",
                "language": infer_language(source_group),
                "sha256": sha256(path),
                "text_extractable": include_in_documents,
                "verification_status": (
                    "text_verified_metadata_pending"
                    if include_in_documents
                    else status
                ),
                "use_for_retrieval": include_in_documents,
                "note": note,
            }
        )

        print(
            f"{document_id} | {status} | "
            f"{len(extracted_text)} ký tự | {relative_path}"
        )

    write_jsonl(documents, DOCUMENTS_PATH)

    write_csv(
        log_rows,
        EXTRACTION_LOG_PATH,
        [
            "document_id",
            "title",
            "source_group",
            "file_path",
            "file_type",
            "status",
            "included_in_documents",
            "text_length",
            "page_or_sheet_count",
            "sha256",
            "extracted_at",
            "note",
        ],
    )

    write_csv(
        metadata_rows,
        GENERATED_METADATA_PATH,
        [
            "document_id",
            "title",
            "source_group",
            "file_path",
            "source_owner",
            "source_url",
            "published_date",
            "effective_date",
            "language",
            "sha256",
            "text_extractable",
            "verification_status",
            "use_for_retrieval",
            "note",
        ],
    )

    success_count = sum(
        row["status"] == "success"
        for row in log_rows
    )
    needs_text_count = sum(
        row["status"] == "needs_text_layer"
        for row in log_rows
    )
    error_count = sum(
        row["status"] == "error"
        for row in log_rows
    )

    print("\n===== KẾT QUẢ =====")
    print(f"File hợp lệ đã quét       : {len(raw_files)}")
    print(f"Tài liệu đưa vào RAG      : {success_count}")
    print(f"PDF cần lớp text/OCR      : {needs_text_count}")
    print(f"File lỗi                  : {error_count}")
    print(f"Đã ghi                    : {DOCUMENTS_PATH}")
    print(f"Đã ghi                    : {EXTRACTION_LOG_PATH}")
    print(f"Metadata cần bổ sung URL  : {GENERATED_METADATA_PATH}")
    print(
        "\nChỉ khi documents.jsonl có dữ liệu mới chạy "
        "chunk_documents_pageaware.py."
    )


if __name__ == "__main__":
    main()
