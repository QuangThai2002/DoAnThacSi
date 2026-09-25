from __future__ import annotations

from pathlib import Path
import csv
import hashlib
import re
import shutil
import unicodedata
from datetime import datetime


PROJECT_ROOT = Path(
    r"C:\Users\Powder\Desktop\DoAnThacSi\master-thesis-rag-agent"
)

INCOMING_DIR = PROJECT_ROOT / "data" / "raw" / "incoming_shopee"
DESTINATION_DIR = PROJECT_ROOT / "data" / "raw" / "shopee_policy"
LOG_PATH = PROJECT_ROOT / "data" / "processed" / "file_rename_remaining_log.csv"


# Thứ tự rất quan trọng:
# Điều khoản Shopee Mall phải được kiểm tra trước Điều khoản dịch vụ thông thường.
MAPPINGS = [
    {
        "document_id": "SHP_FEE_005",
        "required": [
            "cap nhat ve phi",
            "nguoi ban khong thuoc shopee mall",
            "23 05 2026",
        ],
        "forbidden": [],
        "new_name": "shp_fee_005_cap_nhat_phi_non_mall_2026.pdf",
    },
    {
        "document_id": "SHP_POL_006",
        "required": ["dieu khoan dich vu", "shopee mall"],
        "forbidden": [],
        "new_name": "shp_pol_006_dieu_khoan_dich_vu_shopee_mall.pdf",
    },
    {
        "document_id": "SHP_DATA_001",
        "required": [
            "dieu khoan su dung",
            "tinh nang tong hop luot ban",
            "san thuong mai dien tu",
        ],
        "forbidden": [],
        "new_name": "shp_data_001_dieu_khoan_tong_hop_luot_ban.pdf",
    },
    {
        "document_id": "SHP_DATA_002",
        "required": [
            "quy dinh luu tru du lieu san pham",
            "kenh nguoi ban shopee",
        ],
        "forbidden": [],
        "new_name": "shp_data_002_quy_dinh_luu_tru_du_lieu_san_pham_2026.pdf",
    },
    {
        "document_id": "SHP_POL_007",
        "required": ["quy dinh ve dang ban san pham", "shopee"],
        "forbidden": [],
        "new_name": "shp_pol_007_quy_dinh_dang_ban_san_pham.pdf",
    },
    {
        "document_id": "SHP_IP_001",
        "required": [
            "quy trinh",
            "thu tuc phoi hop",
            "chu the quyen so huu tri tue",
        ],
        "forbidden": [],
        "new_name": "shp_ip_001_quy_trinh_phoi_hop_quyen_so_huu_tri_tue.pdf",
    },
    {
        "document_id": "SHP_POL_005",
        "required": ["dieu khoan dich vu", "shopee trung tam tro giup"],
        "forbidden": ["shopee mall"],
        "new_name": "shp_pol_005_dieu_khoan_dich_vu.pdf",
    },
]


def normalize_text(value: str) -> str:
    """Chuẩn hóa dấu tiếng Việt, ký tự lạ và khoảng trắng để so khớp tên file."""
    value = value.replace("Đ", "D").replace("đ", "d")
    value = unicodedata.normalize("NFD", value)
    value = "".join(
        character
        for character in value
        if unicodedata.category(character) != "Mn"
    )
    value = value.lower()
    value = re.sub(r"[^a-z0-9]+", " ", value)
    return re.sub(r"\s+", " ", value).strip()


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file:
        for block in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def matches(filename: str, mapping: dict) -> bool:
    normalized = normalize_text(Path(filename).stem)

    required_ok = all(
        normalize_text(keyword) in normalized
        for keyword in mapping["required"]
    )
    forbidden_ok = all(
        normalize_text(keyword) not in normalized
        for keyword in mapping["forbidden"]
    )

    return required_ok and forbidden_ok


def main() -> None:
    INCOMING_DIR.mkdir(parents=True, exist_ok=True)
    DESTINATION_DIR.mkdir(parents=True, exist_ok=True)
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)

    pdf_files = list(INCOMING_DIR.glob("*.pdf"))
    logs: list[dict] = []

    renamed_count = 0
    duplicate_count = 0
    missing_count = 0

    for mapping in MAPPINGS:
        candidates = [
            path for path in pdf_files
            if path.exists() and matches(path.name, mapping)
        ]

        destination = DESTINATION_DIR / mapping["new_name"]

        if len(candidates) == 0:
            status = "missing"
            source_name = ""
            message = "Không tìm thấy file phù hợp trong incoming_shopee"
            missing_count += 1

        elif len(candidates) > 1:
            status = "multiple_matches"
            source_name = " | ".join(path.name for path in candidates)
            message = "Có nhiều file cùng khớp; chưa tự động đổi để tránh nhầm"

        else:
            source = candidates[0]
            source_name = source.name

            if destination.exists():
                source_hash = file_sha256(source)
                destination_hash = file_sha256(destination)

                if source_hash == destination_hash:
                    status = "duplicate"
                    message = (
                        "File đích đã tồn tại và nội dung giống hệt. "
                        "Không xử lý để tránh đưa dữ liệu trùng vào RAG."
                    )
                    duplicate_count += 1
                else:
                    status = "conflict"
                    message = (
                        "File đích đã tồn tại nhưng nội dung khác. "
                        "Không ghi đè; cần kiểm tra thủ công."
                    )
            else:
                shutil.move(str(source), str(destination))
                status = "renamed"
                message = "Đổi tên và di chuyển thành công"
                renamed_count += 1

        logs.append(
            {
                "timestamp": datetime.now().isoformat(timespec="seconds"),
                "document_id": mapping["document_id"],
                "source_name": source_name,
                "new_name": mapping["new_name"],
                "destination": str(destination),
                "status": status,
                "message": message,
            }
        )

        print(
            f"[{status.upper()}] "
            f"{mapping['document_id']} -> {mapping['new_name']}"
        )
        if message:
            print(f"    {message}")

    # Kiểm tra file chính sách bảo mật đã đổi tên nhưng còn nằm trong incoming.
    privacy_source = INCOMING_DIR / "shp_pol_001_chinh_sach_bao_mat.pdf"
    privacy_destination = (
        DESTINATION_DIR / "shp_pol_001_chinh_sach_bao_mat.pdf"
    )

    if privacy_source.exists():
        if not privacy_destination.exists():
            shutil.move(str(privacy_source), str(privacy_destination))
            print(
                "[RENAMED] SHP_POL_001 -> "
                "shp_pol_001_chinh_sach_bao_mat.pdf"
            )
        elif file_sha256(privacy_source) == file_sha256(privacy_destination):
            print(
                "[DUPLICATE] shp_pol_001_chinh_sach_bao_mat.pdf "
                "đang bị trùng. Hãy xóa bản trong incoming_shopee "
                "sau khi kiểm tra."
            )
        else:
            print(
                "[CONFLICT] Có hai file chính sách bảo mật cùng tên "
                "nhưng nội dung khác. Chưa tự động xử lý."
            )

    with LOG_PATH.open("w", newline="", encoding="utf-8-sig") as file:
        writer = csv.DictWriter(
            file,
            fieldnames=[
                "timestamp",
                "document_id",
                "source_name",
                "new_name",
                "destination",
                "status",
                "message",
            ],
        )
        writer.writeheader()
        writer.writerows(logs)

    remaining_pdfs = list(INCOMING_DIR.glob("*.pdf"))

    print("\n===== KẾT QUẢ =====")
    print(f"Đổi tên thành công : {renamed_count}")
    print(f"File trùng          : {duplicate_count}")
    print(f"Không tìm thấy      : {missing_count}")
    print(f"Log                 : {LOG_PATH}")

    if remaining_pdfs:
        print("\nCác PDF còn lại trong incoming_shopee:")
        for path in remaining_pdfs:
            print(f"- {path.name}")
    else:
        print("\nKhông còn PDF nào chưa xử lý.")


if __name__ == "__main__":
    main()
