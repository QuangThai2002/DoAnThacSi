from __future__ import annotations

from pathlib import Path
import argparse
import csv
import hashlib
import json
import re
import shutil
import subprocess
import unicodedata
from datetime import datetime


PROJECT_ROOT = Path(
    r"C:\Users\Powder\Desktop\DoAnThacSi\master-thesis-rag-agent"
)
RAW = PROJECT_ROOT / "data" / "raw"
PROCESSED = PROJECT_ROOT / "data" / "processed"


def normalize(value: str) -> str:
    value = value.replace("Đ", "D").replace("đ", "d")
    value = unicodedata.normalize("NFD", value)
    value = "".join(
        ch for ch in value
        if unicodedata.category(ch) != "Mn"
    )
    value = re.sub(r"[^a-zA-Z0-9]+", " ", value).lower()
    return re.sub(r"\s+", " ", value).strip()


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file:
        for block in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def ensure_unique(destination: Path) -> Path:
    if not destination.exists():
        return destination

    counter = 1
    while True:
        candidate = destination.with_name(
            f"{destination.stem}_{counter}{destination.suffix}"
        )
        if not candidate.exists():
            return candidate
        counter += 1


def move(source: Path, destination: Path, apply: bool) -> None:
    print(f"MOVE: {source} -> {destination}")
    if apply:
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(source), str(ensure_unique(destination)))


def rename(source: Path, destination: Path, apply: bool) -> None:
    print(f"RENAME: {source} -> {destination}")
    if apply:
        destination.parent.mkdir(parents=True, exist_ok=True)
        if destination.exists():
            if sha256(source) == sha256(destination):
                duplicate = (
                    RAW / "_duplicates" / source.name
                )
                duplicate.parent.mkdir(parents=True, exist_ok=True)
                shutil.move(str(source), str(ensure_unique(duplicate)))
                return
            raise FileExistsError(
                f"File đích đã tồn tại nhưng nội dung khác: {destination}"
            )
        source.rename(destination)


def archive_stale_processed(apply: bool) -> None:
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    archive_dir = PROCESSED / f"_legacy_before_shopee_{timestamp}"

    stale_names = [
        "documents.jsonl",
        "chunks.jsonl",
        "documents_backup_20260710_112055.jsonl",
        "extraction_log.csv",
        "chunking_log.csv",
        "embedding_log.csv",
        "simple_embedding_log.csv",
        "metadata.csv.xlsx",
    ]

    for name in stale_names:
        source = PROCESSED / name
        if source.exists():
            move(source, archive_dir / name, apply)


def fix_market_files(apply: bool) -> None:
    folder = RAW / "ecommerce_market_reports"
    duplicate_dir = folder / "_duplicates"

    mappings = {
        "BCTMDT2020-8-pdf.PDF":
            "market_vn_001_sach_trang_tmdt_2020.pdf",
        "Bao-cao-TMDT-2021-V6-pdf.PDF":
            "market_vn_002_sach_trang_tmdt_2021.pdf",
        "Báo cáo EBI 2025 Final - Vn.pdf":
            "market_vn_003_ebi_2025.pdf",
        "Báo cáo EBI 2026 v2.0.pdf":
            "market_vn_004_ebi_2026.pdf",
    }

    for old_name, new_name in mappings.items():
        source = folder / old_name
        if source.exists():
            rename(source, folder / new_name, apply)

    duplicate = folder / "Bao_cao_TMDT_2021_V6_5a297.pdf"
    if duplicate.exists():
        move(
            duplicate,
            duplicate_dir / "duplicate_sach_trang_tmdt_2021.pdf",
            apply,
        )


def fix_electronics_files(apply: bool) -> None:
    folder = RAW / "electronics_market"
    mappings = {
        "Điện tử - điểm sáng trong sản xuất công nghiệp của Việt Nam.pdf":
            "electronics_vn_001_diem_sang_san_xuat_cong_nghiep_2021.pdf",
        "Xuất nhập khẩu máy tính và linh kiện điện tử của Việt Nam vẫn phụ thuộc vào doanh nghiệp FDI.pdf":
            "electronics_vn_002_xnk_may_tinh_linh_kien_fdi_2022.pdf",
        "Tạo vị thế cho ngành công nghiệp điện tử.pdf":
            "electronics_vn_003_tao_vi_the_nganh_dien_tu_2023.pdf",
    }

    for old_name, new_name in mappings.items():
        source = folder / old_name
        if source.exists():
            rename(source, folder / new_name, apply)


def fix_api_files(apply: bool) -> None:
    folder = RAW / "shopee_api"
    duplicate_dir = folder / "_duplicates"

    mappings = {
        "Developer Guide - Shopee Open Platform listing management.pdf":
            "shp_api_001_platform_introduction_2024.pdf",
        "Developer Guide - Shopee Open Platform API calls.pdf":
            "shp_api_002_api_calls_v2_2025.pdf",
        "Developer Guide - Shopee Open Platform shop authorization.pdf":
            "shp_api_003_shop_authorization_2026.pdf",
        "Developer Guide - Shopee Open Platform order management.pdf":
            "shp_api_004_order_management_2025.pdf",
    }

    for old_name, new_name in mappings.items():
        source = folder / old_name
        if source.exists():
            rename(source, folder / new_name, apply)

    wrong_logistics = (
        folder / "Developer Guide - Shopee Open Platform logistics.pdf"
    )
    if wrong_logistics.exists():
        move(
            wrong_logistics,
            duplicate_dir
            / "duplicate_order_management_saved_as_logistics.pdf",
            apply,
        )


def fix_research_filename(apply: bool) -> None:
    source = (
        RAW / "research_papers"
        / "vecom_plan_001_ke_hoach_cong_tac_2024.pdf.pdf"
    )
    destination = (
        RAW / "research_papers"
        / "vecom_plan_001_ke_hoach_cong_tac_2024.pdf"
    )
    if source.exists():
        rename(source, destination, apply)


def fix_transaction_law(apply: bool) -> None:
    legal = RAW / "legal_ecommerce"
    manual = RAW / "incoming_legal" / "_manual_review"

    bad = legal / "law_transaction_001_luat_giao_dich_dien_tu_2023.pdf"
    good = manual / "VanBanGoc_luat20-2023-qh15..pdf"

    if bad.exists():
        destination = (
            manual
            / "law_transaction_001_source_word_wrong_pdf_extension.doc"
        )
        move(bad, destination, apply)

    if good.exists():
        destination = (
            legal
            / "law_transaction_001_luat_giao_dich_dien_tu_2023.pdf"
        )
        move(good, destination, apply)


def create_missing_folders(apply: bool) -> None:
    folders = [
        RAW / "customer_review_dataset",
        RAW / "shop_actual",
        RAW / "news_trends",
        RAW / "research_papers",
        PROJECT_ROOT / "data" / "evaluation",
    ]

    for folder in folders:
        print(f"MKDIR: {folder}")
        if apply:
            folder.mkdir(parents=True, exist_ok=True)


def write_manifest(apply: bool) -> None:
    output = PROCESSED / "raw_dataset_manifest.csv"
    rows = []

    for path in sorted(RAW.rglob("*")):
        if not path.is_file():
            continue

        relative = path.relative_to(PROJECT_ROOT).as_posix()
        rows.append(
            {
                "file_path": relative,
                "file_name": path.name,
                "source_group": (
                    path.relative_to(RAW).parts[0]
                    if path.relative_to(RAW).parts
                    else ""
                ),
                "extension": path.suffix.lower(),
                "size_bytes": path.stat().st_size,
                "sha256": sha256(path),
                "status": "needs_metadata_review",
                "use_for_retrieval": "",
                "note": "",
            }
        )

    print(f"WRITE: {output} ({len(rows)} rows)")
    if apply:
        PROCESSED.mkdir(parents=True, exist_ok=True)
        with output.open("w", newline="", encoding="utf-8-sig") as file:
            writer = csv.DictWriter(
                file,
                fieldnames=list(rows[0].keys()) if rows else [
                    "file_path",
                    "file_name",
                    "source_group",
                    "extension",
                    "size_bytes",
                    "sha256",
                    "status",
                    "use_for_retrieval",
                    "note",
                ],
            )
            writer.writeheader()
            writer.writerows(rows)


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Dọn và kiểm tra dataset Shopee. "
            "Mặc định chỉ in kế hoạch, không thay đổi file."
        )
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Thực hiện đổi tên, di chuyển và archive.",
    )
    args = parser.parse_args()

    print("MODE:", "APPLY" if args.apply else "DRY-RUN")
    print("Không có file nào bị xóa vĩnh viễn.")

    create_missing_folders(args.apply)
    fix_market_files(args.apply)
    fix_electronics_files(args.apply)
    fix_api_files(args.apply)
    fix_research_filename(args.apply)
    fix_transaction_law(args.apply)
    archive_stale_processed(args.apply)
    write_manifest(args.apply)

    print("\nHOÀN TẤT.")
    if not args.apply:
        print(
            "Đây chỉ là dry-run. Kiểm tra danh sách rồi chạy lại với --apply."
        )
    else:
        print(
            "Dữ liệu cũ đã được archive. "
            "Chưa chạy extraction/chunking/embedding."
        )


if __name__ == "__main__":
    main()
