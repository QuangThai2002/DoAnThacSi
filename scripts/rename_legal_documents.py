from pathlib import Path
import shutil
import unicodedata
import re

PROJECT_ROOT = Path(r"C:\Users\Powder\Desktop\DoAnThacSi\master-thesis-rag-agent")
INCOMING = PROJECT_ROOT / "data" / "raw" / "incoming_legal"
LEGAL = PROJECT_ROOT / "data" / "raw" / "legal_ecommerce"
DRAFTS = INCOMING / "_excluded_drafts"
REVIEW = INCOMING / "_manual_review"

def norm(s):
    s = s.replace("Đ","D").replace("đ","d")
    s = unicodedata.normalize("NFD", s)
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    s = re.sub(r"[^a-zA-Z0-9]+", " ", s).lower()
    return re.sub(r"\s+", " ", s).strip()

RULES = [
    (["luat122 2025 qh15", "122 2025 qh15"], "law_ecom_001_luat_thuong_mai_dien_tu_2025"),
    (["248 2026 nd cp 30062026 signed", "248 ndcp signed"], "law_ecom_002_nghi_dinh_248_2026"),
    (["20 2023 qh15 513347", "vanbangoc luat20 2023 qh15"], "law_transaction_001_luat_giao_dich_dien_tu_2023"),
    (["vanbangoc luat bvqlntd 2023"], "law_consumer_001_luat_bao_ve_quyen_loi_nguoi_tieu_dung_2023"),
    (["vanbangoc n 55 2024 nd cp 16052024", "55 nd cp signed"], "law_consumer_002_nghi_dinh_55_2024"),
    (["91qh signed"], "law_data_001_luat_bao_ve_du_lieu_ca_nhan_2025"),
    (["1 vbhn bct 2026 55", "55 2026 vbhn bct"], "law_promotion_001_vbhn_55_2026_xuc_tien_thuong_mai"),
    (["342 ndcp signed"], "law_ads_002_nghi_dinh_342_2025_quang_cao"),
    (["37 1 signed"], "law_quality_002_nghi_dinh_37_2026_chat_luong_san_pham"),
    (["37 pl"], "law_quality_002a_nghi_dinh_37_2026_phu_luc"),
    (["111 signed"], "law_label_002_nghi_dinh_111_2021_sua_doi_nhan_hang_hoa"),
    (["1 vbhn bct 2025 44", "tvhienthitoanvan 1 vbhn bct 2025 44", "tvvanbangoc 1 vbhn bct 2025 44"], "law_quality_moit_001_vbhn_44_2025_quan_ly_chat_luong"),
]

DRAFT_KEYS = ["du thao", "trinh ky", "ndthuongmaidientu248 final", "ndquyenloinguoitieudung trinhky", "plquyenloinguoitieudung trinhky", "template"]
MANUAL_KEYS = ["tvvanbangoc 04 vbhn vpqh"]

def unique_path(folder, name):
    p = folder / name
    i = 1
    while p.exists():
        p = folder / f"{Path(name).stem}_{i}{Path(name).suffix}"
        i += 1
    return p

def main():
    for d in [INCOMING, LEGAL, DRAFTS, REVIEW]:
        d.mkdir(parents=True, exist_ok=True)

    files = [p for p in INCOMING.iterdir() if p.is_file()]

    for src in files:
        n = norm(src.stem)
        ext = src.suffix.lower()

        if any(norm(k) in n for k in DRAFT_KEYS):
            dst = unique_path(DRAFTS, src.name)
            shutil.move(str(src), str(dst))
            print(f"[LOAI DU THAO] {src.name}")
            continue

        if any(norm(k) in n for k in MANUAL_KEYS):
            dst = unique_path(REVIEW, src.name)
            shutil.move(str(src), str(dst))
            print(f"[CAN KIEM TRA TAY] {src.name}")
            continue

        matched = None
        for keys, new_stem in RULES:
            if any(norm(k) in n for k in keys):
                matched = new_stem
                break

        if not matched:
            dst = unique_path(REVIEW, src.name)
            shutil.move(str(src), str(dst))
            print(f"[CHUA NHAN DIEN] {src.name}")
            continue

        dst = LEGAL / f"{matched}{ext}"
        if dst.exists():
            dst = unique_path(REVIEW, src.name)
            shutil.move(str(src), str(dst))
            print(f"[CO THE TRUNG] {src.name}")
        else:
            shutil.move(str(src), str(dst))
            print(f"[DA DOI TEN] {src.name} -> {dst.name}")

    print("\nCAC NHOM CON THIEU CAN KIEM TRA:")
    missing = [
        "law_data_002_nghi_dinh_356_2025_bao_ve_du_lieu_ca_nhan.pdf",
        "law_ads_001_vbhn_luat_quang_cao.pdf",
        "law_quality_001_vbhn_luat_chat_luong_san_pham_hang_hoa.pdf",
        "law_label_001_nghi_dinh_43_2017_nhan_hang_hoa.pdf",
    ]
    for name in missing:
        print(f"- {name}")

if __name__ == "__main__":
    main()
