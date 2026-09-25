from __future__ import annotations

from pathlib import Path
import csv
import re
import shutil
import unicodedata
from datetime import datetime

PROJECT_ROOT = Path(r"C:\Users\Powder\Desktop\DoAnThacSi\master-thesis-rag-agent")
INCOMING_DIR = PROJECT_ROOT / "data" / "raw" / "incoming_shopee"
LOG_PATH = PROJECT_ROOT / "data" / "processed" / "file_rename_log.csv"

MAPPINGS = [
    ("SEA_REP_001", "2026-04-17 - Form 20-F.pdf", "sea_rep_001_form_20f_2025.pdf", "data/raw/sea_shopee_reports"),
    ("SEA_REP_002", "2026.03.03 Sea Fourth Quarter and Full Year 2025 Results Deck.pdf", "sea_rep_002_q4_fy2025_results_deck.pdf", "data/raw/sea_shopee_reports"),
    ("SEA_REP_003", "2026.03.03 Sea Fourth Quarter and Full Year 2025 Results.pdf", "sea_rep_003_q4_fy2025_results.pdf", "data/raw/sea_shopee_reports"),
    ("SHP_ADS_001", "af5e358d400848e89b0052adb1288bcf_Quảng cáo Shopee - Nâng cao 2025.pdf", "shp_ads_001_quang_cao_nang_cao_2025.pdf", "data/raw/shopee_policy"),
    ("SHP_POL_001", "CHÍNH SÁCH BẢO MẬT _ Shopee Trung tâm trợ giúp.pdf", "shp_pol_001_chinh_sach_bao_mat.pdf", "data/raw/shopee_policy"),
    ("SHP_POL_002", "CHÍNH SÁCH CẤM_HẠN CHẾ SẢN PHẨM _ Shopee Trung tâm trợ giúp.pdf", "shp_pol_002_chinh_sach_cam_han_che_san_pham.pdf", "data/raw/shopee_policy"),
    ("SHP_RET_001", "Chính sách phí vận chuyển dành cho đơn Trả Hàng_Hoàn tiền và đơn giao không thành công _ Học Viện Shopee [Shopee].pdf", "shp_ret_001_phi_van_chuyen_tra_hang_hoan_tien_2025.pdf", "data/raw/shopee_policy"),
    ("SHP_RET_002", "CHÍNH SÁCH TRẢ HÀNG VÀ HOÀN TIỀN _ Shopee Trung tâm trợ giúp.pdf", "shp_ret_002_chinh_sach_tra_hang_hoan_tien.pdf", "data/raw/shopee_policy"),
    ("SHP_LOG_001", "CHÍNH SÁCH VẬN CHUYỂN SHOPEE _ Shopee Trung tâm trợ giúp.pdf", "shp_log_001_chinh_sach_van_chuyen.pdf", "data/raw/shopee_policy"),
    ("SHP_MKT_001", "Các Ngành hàng bị hạn chế tham gia chương trình khuyến mãi của Shopee _ Học Viện Shopee [Shopee].pdf", "shp_mkt_001_nganh_hang_han_che_khuyen_mai_2026.pdf", "data/raw/shopee_policy"),
    ("SHP_MKT_002", "Giới thiệu về Kênh Marketing Shopee _ Học viện Shopee [Shopee].pdf", "shp_mkt_002_gioi_thieu_kenh_marketing_2025.pdf", "data/raw/shopee_policy"),
    ("SHP_FIN_001", "Hướng dẫn cách xem thông tin tại mục Doanh thu trên Kênh Người Bán và Ứng dụng Shopee _ Học viện Shopee [Shopee].pdf", "shp_fin_001_huong_dan_xem_doanh_thu_2025.pdf", "data/raw/shopee_policy"),
    ("SHP_FIN_002", "Hướng dẫn xuất Báo Cáo Doanh Thu và giải thích các thông tin trong báo cáo _ Học viện Shopee [Shopee].pdf", "shp_fin_002_huong_dan_xuat_bao_cao_doanh_thu_2026.pdf", "data/raw/shopee_policy"),
    ("SHP_FEE_001", "Một số phí bán hàng trên Shopee Người bán cần nắm rõ _ Học viện Shopee [Shopee].pdf", "shp_fee_001_tong_quan_phi_ban_hang_2026.pdf", "data/raw/shopee_policy"),
    ("SHP_FEE_002", "Phí Cố Định dành cho Người bán không thuộc Shopee Mall là gì_ _ Học Viện Shopee [Shopee].pdf", "shp_fee_002_phi_co_dinh_non_mall_2026.pdf", "data/raw/shopee_policy"),
    ("SHP_FEE_003", "Phí Cố Định dành cho Người bán thuộc Shopee Mall là gì_ _ Học Viện Shopee [Shopee].pdf", "shp_fee_003_phi_co_dinh_mall_2026.pdf", "data/raw/shopee_policy"),
    ("SHP_FEE_004", "Phí Xử Lý Giao Dịch trên Shopee là gì_ _ Học viện Shopee - Shopee Uni Vietnam.pdf", "shp_fee_004_phi_xu_ly_giao_dich_2026.pdf", "data/raw/shopee_policy"),
    ("SHP_POL_003", "QUY CHẾ HOẠT ĐỘNG SÀN THƯƠNG MẠI ĐIỆN TỬ SHOPEE.VN _ Shopee Trung tâm trợ giúp.pdf", "shp_pol_003_quy_che_hoat_dong_san.pdf", "data/raw/shopee_policy"),
    ("SHP_POL_004", "QUY TRÌNH GIẢI QUYẾT TRANH CHẤP_ XỬ LÝ KHIẾU NẠI _ Shopee Trung tâm trợ giúp.pdf", "shp_pol_004_quy_trinh_giai_quyet_tranh_chap_khieu_nai.pdf", "data/raw/shopee_policy"),
    ("SHP_RET_003", "Quy trình Trả hàng_Hoàn tiền trên Shopee dành cho Người bán _ Học viện Shopee - Shopee Uni Vietnam.pdf", "shp_ret_003_quy_trinh_tra_hang_hoan_tien_nguoi_ban_2025.pdf", "data/raw/shopee_policy"),
]


def normalize_text(value: str) -> str:
    value = value.replace("Đ", "D").replace("đ", "d")
    value = unicodedata.normalize("NFD", value)
    value = "".join(ch for ch in value if unicodedata.category(ch) != "Mn")
    value = value.lower()
    value = re.sub(r"[^a-z0-9]+", " ", value)
    return re.sub(r"\s+", " ", value).strip()


def find_source_file(original_name: str) -> Path | None:
    exact = INCOMING_DIR / original_name
    if exact.exists():
        return exact

    target_norm = normalize_text(Path(original_name).stem)
    ranked = []
    for pdf in INCOMING_DIR.glob("*.pdf"):
        current_norm = normalize_text(pdf.stem)
        if current_norm == target_norm:
            return pdf
        target_words = set(target_norm.split())
        current_words = set(current_norm.split())
        overlap = len(target_words & current_words) / max(len(target_words), 1)
        if overlap >= 0.82:
            ranked.append((overlap, pdf))

    ranked.sort(key=lambda x: x[0], reverse=True)
    if ranked and (len(ranked) == 1 or ranked[0][0] > ranked[1][0]):
        return ranked[0][1]
    return None


def main() -> None:
    INCOMING_DIR.mkdir(parents=True, exist_ok=True)
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)

    logs = []
    success = skipped = missing = 0

    for document_id, original_name, new_name, destination_rel in MAPPINGS:
        source = find_source_file(original_name)
        destination_dir = PROJECT_ROOT / destination_rel
        destination_dir.mkdir(parents=True, exist_ok=True)
        destination = destination_dir / new_name

        if source is None:
            status = "missing"
            message = "Không tìm thấy file nguồn trong incoming_shopee"
            missing += 1
        elif destination.exists():
            status = "skipped"
            message = "File đích đã tồn tại, không ghi đè"
            skipped += 1
        else:
            shutil.move(str(source), str(destination))
            status = "renamed"
            message = "Đổi tên và di chuyển thành công"
            success += 1

        logs.append({
            "timestamp": datetime.now().isoformat(timespec="seconds"),
            "document_id": document_id,
            "original_name": original_name,
            "new_name": new_name,
            "destination": str(destination),
            "status": status,
            "message": message,
        })
        print(f"[{status.upper()}] {document_id} -> {new_name}")

    with LOG_PATH.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=logs[0].keys())
        writer.writeheader()
        writer.writerows(logs)

    print("\n===== KẾT QUẢ =====")
    print(f"Thành công : {success}")
    print(f"Bỏ qua    : {skipped}")
    print(f"Thiếu file: {missing}")
    print(f"Log       : {LOG_PATH}")

    remaining = list(INCOMING_DIR.glob("*.pdf"))
    if remaining:
        print("\nCác PDF còn lại chưa được nhận diện:")
        for pdf in remaining:
            print(f"- {pdf.name}")
    else:
        print("\nKhông còn PDF chưa xử lý trong incoming_shopee.")


if __name__ == "__main__":
    main()
