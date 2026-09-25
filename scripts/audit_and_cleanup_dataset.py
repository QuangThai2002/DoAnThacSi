from __future__ import annotations
from pathlib import Path
import csv, hashlib, re, shutil, unicodedata
from datetime import datetime

PROJECT_ROOT = Path(r"C:\Users\Powder\Desktop\DoAnThacSi\master-thesis-rag-agent")
RAW = PROJECT_ROOT / "data" / "raw"
PROCESSED = PROJECT_ROOT / "data" / "processed"
LEGAL = RAW / "legal_ecommerce"
SHOPEE = RAW / "shopee_policy"
SEA = RAW / "sea_shopee_reports"
IN_LEGAL = RAW / "incoming_legal"
DRAFTS = IN_LEGAL / "_excluded_drafts"
DUPLICATES = IN_LEGAL / "_duplicates"
REVIEW = IN_LEGAL / "_manual_review"
SHOPEE_REVIEW = RAW / "incoming_shopee" / "_manual_review"
LOG = PROCESSED / "dataset_cleanup_log.csv"
SUMMARY = PROCESSED / "dataset_audit_summary.txt"

REQUIRED_FOLDERS = [
    "shopee_policy", "shopee_api", "legal_ecommerce",
    "ecommerce_market_reports", "sea_shopee_reports",
    "electronics_market", "customer_review_dataset",
    "news_trends", "research_papers"
]

def norm(s: str) -> str:
    s = s.replace("Đ", "D").replace("đ", "d")
    s = unicodedata.normalize("NFD", s)
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    s = re.sub(r"[^a-zA-Z0-9]+", " ", s).lower()
    return re.sub(r"\s+", " ", s).strip()

def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()

def unique_path(folder: Path, name: str) -> Path:
    p = folder / name
    i = 1
    while p.exists():
        p = folder / f"{Path(name).stem}_{i}{Path(name).suffix}"
        i += 1
    return p

def ensure_dirs():
    created = []
    for name in REQUIRED_FOLDERS:
        p = RAW / name
        if not p.exists():
            p.mkdir(parents=True, exist_ok=True)
            created.append(name)
    for p in [PROCESSED, DRAFTS, DUPLICATES, REVIEW, SHOPEE_REVIEW]:
        p.mkdir(parents=True, exist_ok=True)
    return created

LEGAL_RULES = [
    (["luat122 2025 qh15"], "law_ecom_001_luat_thuong_mai_dien_tu_2025.pdf"),
    (["248 2026 nd cp 30062026 signed", "248 ndcp signed"], "law_ecom_002_nghi_dinh_248_2026.pdf"),
    (["20 2023 qh15 513347", "vanbangoc luat20 2023 qh15"], "law_transaction_001_luat_giao_dich_dien_tu_2023.pdf"),
    (["vanbangoc luat bvqlntd 2023"], "law_consumer_001_luat_bao_ve_quyen_loi_nguoi_tieu_dung_2023.pdf"),
    (["55 nd cp signed", "vanbangoc n 55 2024 nd cp 16052024"], "law_consumer_002_nghi_dinh_55_2024.pdf"),
    (["91qh signed"], "law_data_001_luat_bao_ve_du_lieu_ca_nhan_2025.pdf"),
    (["356 nd signed"], "law_data_002_nghi_dinh_356_2025_bao_ve_du_lieu_ca_nhan.pdf"),
    (["1 vbhn bct 2026 55", "55 2026 vbhn bct"], "law_promotion_001_vbhn_55_2026_xuc_tien_thuong_mai.pdf"),
    (["342 ndcp signed"], "law_ads_002_nghi_dinh_342_2025_quang_cao.pdf"),
    (["37 1 signed"], "law_quality_002_nghi_dinh_37_2026_chat_luong_san_pham.pdf"),
    (["37 pl"], "law_quality_002a_nghi_dinh_37_2026_phu_luc.pdf"),
    (["43 signed"], "law_label_001_nghi_dinh_43_2017_nhan_hang_hoa.pdf"),
    (["111 signed"], "law_label_002_nghi_dinh_111_2021_sua_doi_nhan_hang_hoa.pdf"),
    (["1 vbhn bct 2025 44", "44 vbhn bct", "tvhienthitoanvan 1 vbhn bct 2025 44", "tvvanbangoc 1 vbhn bct 2025 44"], "law_quality_moit_001_vbhn_44_2025_quan_ly_chat_luong.pdf"),
]
DRAFT_KEYS = ["du thao", "trinh ky", "ndthuongmaidientu248 final", "ndquyenloinguoitieudung trinhky", "plquyenloinguoitieudung trinhky", "template"]

STANDARD_LEGAL = {
    "law_ads_001_vbhn_luat_quang_cao.pdf",
    "law_quality_001_vbhn_luat_chat_luong_san_pham_hang_hoa.pdf",
    "law_data_002_nghi_dinh_356_2025_bao_ve_du_lieu_ca_nhan.pdf",
    "law_label_001_nghi_dinh_43_2017_nhan_hang_hoa.pdf",
}

def fix_double_ext(folder: Path, logs):
    if not folder.exists(): return
    for p in list(folder.rglob("*")):
        if p.is_file() and p.name.lower().endswith(".pdf.pdf"):
            dst = p.with_name(p.name[:-4])
            if dst.exists() and sha256(p) == sha256(dst):
                d = unique_path(DUPLICATES if folder == LEGAL else folder / "_duplicates", p.name)
                d.parent.mkdir(parents=True, exist_ok=True)
                shutil.move(str(p), str(d)); status = "duplicate_double_extension"; msg = "Trùng nội dung"
            elif not dst.exists():
                p.rename(dst); status = "fixed_double_extension"; msg = "Đã sửa .pdf.pdf thành .pdf"
            else:
                status = "double_extension_conflict"; msg = "Có xung đột nội dung"
            logs.append([datetime.now().isoformat(timespec="seconds"), folder.name, p.name, dst.name, status, msg])

def move_or_duplicate(src: Path, dst: Path):
    if not dst.exists():
        shutil.move(str(src), str(dst)); return "renamed", "Đổi tên thành công"
    if sha256(src) == sha256(dst):
        d = unique_path(DUPLICATES, src.name); shutil.move(str(src), str(d)); return "duplicate", f"Đã chuyển bản trùng vào {d}"
    d = unique_path(REVIEW, src.name); shutil.move(str(src), str(d)); return "conflict", f"Nội dung khác, chuyển vào {d}"

def process_legal(logs):
    for src in [p for p in LEGAL.iterdir() if p.is_file()]:
        if src.name.lower() in STANDARD_LEGAL or src.name.lower().startswith("law_"):
            continue
        n = norm(src.stem)
        if any(norm(k) in n for k in DRAFT_KEYS):
            dst = unique_path(DRAFTS, src.name); shutil.move(str(src), str(dst)); status, msg, new = "excluded_draft", "Loại khỏi RAG", dst.name
        elif "tvvanbangoc 04 vbhn vpqh" in n:
            dst = unique_path(REVIEW, src.name); shutil.move(str(src), str(dst)); status, msg, new = "manual_review", "Tên không đủ xác định", dst.name
        else:
            target = None
            for keys, name in LEGAL_RULES:
                if any(norm(k) in n for k in keys): target = name; break
            if target:
                status, msg = move_or_duplicate(src, LEGAL / target); new = target
            else:
                dst = unique_path(REVIEW, src.name); shutil.move(str(src), str(dst)); status, msg, new = "unrecognized", "Chưa nhận diện chắc chắn", dst.name
        logs.append([datetime.now().isoformat(timespec="seconds"), "legal_ecommerce", src.name, new, status, msg])

def process_shopee(logs):
    if not SHOPEE.exists(): return
    for src in [p for p in SHOPEE.iterdir() if p.is_file()]:
        n = norm(src.stem)
        if n.startswith("shp "): continue
        if n.startswith("vn ") or re.fullmatch(r"[a-z0-9]{15,}", n.replace(" ", "")):
            dst = unique_path(SHOPEE_REVIEW, src.name); shutil.move(str(src), str(dst))
            logs.append([datetime.now().isoformat(timespec="seconds"), "shopee_policy", src.name, dst.name, "manual_review", "Tên ngẫu nhiên, cần mở kiểm tra"])

def count_files(folder: Path):
    return sum(1 for p in folder.rglob("*") if p.is_file()) if folder.exists() else 0

def main():
    RAW.mkdir(parents=True, exist_ok=True)
    created = ensure_dirs(); logs = []
    for f in [LEGAL, SHOPEE, SEA]: fix_double_ext(f, logs)
    process_legal(logs); process_shopee(logs)
    with LOG.open("w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f); w.writerow(["timestamp","group","original_name","new_name","status","message"]); w.writerows(logs)
    required_legal = [
        "law_ecom_001_luat_thuong_mai_dien_tu_2025.pdf",
        "law_ecom_002_nghi_dinh_248_2026.pdf",
        "law_transaction_001_luat_giao_dich_dien_tu_2023.pdf",
        "law_consumer_001_luat_bao_ve_quyen_loi_nguoi_tieu_dung_2023.pdf",
        "law_consumer_002_nghi_dinh_55_2024.pdf",
        "law_data_001_luat_bao_ve_du_lieu_ca_nhan_2025.pdf",
        "law_data_002_nghi_dinh_356_2025_bao_ve_du_lieu_ca_nhan.pdf",
        "law_promotion_001_vbhn_55_2026_xuc_tien_thuong_mai.pdf",
        "law_ads_001_vbhn_luat_quang_cao.pdf",
        "law_ads_002_nghi_dinh_342_2025_quang_cao.pdf",
        "law_quality_001_vbhn_luat_chat_luong_san_pham_hang_hoa.pdf",
        "law_quality_002_nghi_dinh_37_2026_chat_luong_san_pham.pdf",
        "law_label_001_nghi_dinh_43_2017_nhan_hang_hoa.pdf",
        "law_label_002_nghi_dinh_111_2021_sua_doi_nhan_hang_hoa.pdf",
    ]
    lines = ["BAO CAO KIEM TRA DU LIEU", "="*60, f"Thoi gian: {datetime.now().isoformat(timespec='seconds')}", "", "SO LUONG FILE THEO NHOM"]
    for name in REQUIRED_FOLDERS: lines.append(f"- {name}: {count_files(RAW/name)} file")
    lines += ["", "THU MUC VUA TAO"] + ([f"- {x}" for x in created] if created else ["- Khong co"])
    lines += ["", "KIEM TRA BO LUAT COT LOI"]
    for name in required_legal: lines.append(f"[{'DA CO' if (LEGAL/name).exists() else 'CON THIEU'}] {name}")
    lines += ["", "NHAN XET", "- Shopee policy va Sea reports: du de bat dau MVP retrieval.", "- Con thieu: bao cao thi truong Viet Nam, review, Shopee API, du lieu shop thuc te.", "- Metadata va bo cau hoi danh gia chua hoan thien."]
    SUMMARY.write_text("\n".join(lines), encoding="utf-8-sig")
    print("HOAN TAT")
    print(f"Log: {LOG}")
    print(f"Bao cao: {SUMMARY}")

if __name__ == "__main__":
    main()
