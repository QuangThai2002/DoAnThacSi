"""Persistent, local data shelves for the seller-facing demo.

The library deliberately stores only structured operational data on the
user's computer.  It does not claim a connection to Shopee Seller Centre.
"""

from __future__ import annotations

import csv
import io
import json
import random
import sqlite3
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, Mapping

from .shop_data_tool import (
    REQUIRED_UPLOAD_COLUMNS,
    ShopDataTool,
    ShopDataValidationError,
)


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_LIBRARY_PATH = PROJECT_ROOT / "data" / "local_store" / "shop_data_library.sqlite"
REQUIRED_FILES = ("orders.csv", "products.csv", "inventory.csv")


# ``id, product name, business category, cost, list price, search aliases``.
# These are representative and permitted demo ideas, not Shopee's immutable live
# category tree.  The live tree and restrictions can change at any time.
DEMO_PRODUCTS = (
    ("appliance", "Máy lọc không khí mini", "Đồ điện tử gia dụng", 1150000, 1690000, "gia dụng điện máy lọc không khí"),
    ("computer-gear", "Bàn phím cơ 87 phím", "Gear máy tính", 410000, 690000, "gaming gear bàn phím chuột pc"),
    ("fresh-fruit", "Giỏ táo nhập khẩu 2kg", "Hoa quả tươi", 165000, 249000, "trái cây hoa quả táo thực phẩm tươi"),
    ("snacks", "Hộp bánh quy bơ", "Bánh kẹo", 68000, 125000, "bánh kẹo snack quà tặng"),
    ("phone-accessories", "Pin sạc dự phòng 10000mAh", "Điện thoại & phụ kiện", 235000, 420000, "điện thoại ốp lưng cáp sạc phụ kiện"),
    ("audio", "Tai nghe Bluetooth Lite", "Âm thanh", 185000, 320000, "tai nghe loa âm thanh bluetooth"),
    ("camera", "Webcam Full HD", "Camera & thiết bị quay chụp", 310000, 540000, "camera webcam máy ảnh quay chụp"),
    ("computer", "Màn hình máy tính 24 inch", "Máy tính & laptop", 1950000, 2890000, "máy tính laptop màn hình pc"),
    ("mens-fashion", "Áo thun cotton basic", "Thời trang nam", 78000, 169000, "quần áo thời trang nam áo thun"),
    ("womens-fashion", "Váy liền thân công sở", "Thời trang nữ", 185000, 359000, "quần áo thời trang nữ váy"),
    ("womens-shoes", "Giày sneaker hàng ngày", "Giày dép nữ", 320000, 590000, "giày dép nữ sneaker sandal"),
    ("mens-shoes", "Giày da công sở", "Giày dép nam", 350000, 620000, "giày dép nam da thể thao"),
    ("bags", "Túi tote canvas", "Túi xách & ví", 65000, 149000, "túi xách ví balo canvas"),
    ("fashion-accessories", "Kính mát chống UV", "Phụ kiện thời trang", 72000, 159000, "mũ nón kính thắt lưng phụ kiện"),
    ("jewelry", "Vòng tay bạc tối giản", "Trang sức", 210000, 390000, "trang sức nhẫn vòng tay dây chuyền"),
    ("skincare", "Kem chống nắng SPF50", "Chăm sóc da", 135000, 265000, "mỹ phẩm skincare kem chống nắng"),
    ("makeup", "Son kem lì", "Trang điểm", 98000, 189000, "makeup son phấn trang điểm"),
    ("personal-care", "Bộ dầu gội phục hồi tóc", "Chăm sóc cá nhân", 125000, 230000, "chăm sóc cá nhân tóc cơ thể"),
    ("baby", "Bỉm em bé gói lớn", "Mẹ & bé", 210000, 345000, "mẹ bé bỉm sữa đồ chơi trẻ em"),
    ("pet", "Thức ăn cho mèo 1.5kg", "Thú cưng", 145000, 255000, "chó mèo thú cưng thức ăn phụ kiện"),
    ("books", "Sách kỹ năng bán hàng", "Sách", 88000, 159000, "sách truyện giáo trình"),
    ("stationery", "Bộ bút gel 12 màu", "Văn phòng phẩm", 42000, 105000, "văn phòng phẩm bút sổ giấy"),
    ("toys", "Bộ xếp hình 500 mảnh", "Đồ chơi", 160000, 299000, "đồ chơi lego xếp hình trẻ em"),
    ("hobbies", "Mô hình xe thể thao tỉ lệ 1:32", "Sở thích & sưu tầm", 185000, 340000, "mô hình sưu tầm hobby figure"),
    ("sports", "Thảm tập yoga 6mm", "Thể thao & dã ngoại", 165000, 295000, "thể thao yoga gym dã ngoại"),
    ("travel", "Vali kéo cabin 20 inch", "Du lịch & hành lý", 490000, 860000, "du lịch vali hành lý balo"),
    ("motorcycle", "Mũ bảo hiểm nửa đầu", "Xe máy", 190000, 330000, "xe máy mũ bảo hiểm phụ kiện"),
    ("automotive", "Camera hành trình ô tô", "Ô tô & phụ kiện", 720000, 1190000, "ô tô xe hơi camera hành trình phụ kiện"),
    ("furniture", "Kệ để đồ 4 tầng", "Nội thất", 320000, 560000, "nội thất kệ bàn ghế"),
    ("home-decor", "Đèn ngủ decor để bàn", "Trang trí nhà cửa", 95000, 185000, "trang trí decor nhà cửa đèn"),
    ("kitchen", "Nồi chiên không dầu 4L", "Đồ dùng nhà bếp", 820000, 1290000, "nhà bếp nồi chảo dụng cụ bếp"),
    ("bedding", "Bộ ga gối cotton", "Chăn ga gối nệm", 280000, 490000, "chăn ga gối nệm phòng ngủ"),
    ("cleaning", "Nước giặt sinh học 3L", "Giặt giũ & vệ sinh nhà cửa", 105000, 195000, "nước giặt vệ sinh tẩy rửa"),
    ("tools", "Bộ tua vít đa năng", "Dụng cụ & thiết bị tiện ích", 145000, 255000, "dụng cụ sửa chữa điện nước tua vít"),
    ("garden", "Bộ hạt giống rau ban công", "Cây cảnh & làm vườn", 35000, 89000, "cây cảnh làm vườn hạt giống"),
    ("fresh-food", "Khô gà lá chanh 500g", "Thực phẩm chế biến", 98000, 175000, "đồ ăn thực phẩm chế biến khô gà"),
    ("dry-food", "Hạt dinh dưỡng tổng hợp", "Thực phẩm khô", 145000, 245000, "ngũ cốc hạt thực phẩm khô"),
    ("coffee", "Cà phê rang xay 500g", "Cà phê & trà", 110000, 205000, "cà phê trà đồ uống"),
    ("household", "Bình giữ nhiệt 750ml", "Hàng gia dụng", 115000, 215000, "gia dụng bình nước đồ dùng nhà"),
    ("lighting", "Đèn bàn LED cảm ứng", "Đèn & thiết bị chiếu sáng", 250000, 430000, "đèn led chiếu sáng đèn bàn"),
    ("health-fitness", "Máy massage cầm tay", "Thiết bị chăm sóc sức khỏe", 390000, 690000, "massage sức khỏe thiết bị cá nhân"),
    ("watches", "Đồng hồ thể thao điện tử", "Đồng hồ", 280000, 510000, "đồng hồ đeo tay thể thao"),
    ("eyewear", "Kính chống ánh sáng xanh", "Kính mắt", 92000, 185000, "kính mắt cận chống ánh sáng xanh"),
    ("underwear", "Bộ đồ mặc nhà cotton", "Đồ lót & đồ mặc nhà", 135000, 249000, "đồ lót đồ ngủ mặc nhà"),
    ("musical", "Đàn ukulele cho người mới", "Nhạc cụ", 340000, 590000, "nhạc cụ đàn guitar ukulele"),
    ("sewing", "Máy may mini gia đình", "May mặc & thủ công", 470000, 790000, "may mặc thủ công máy may len"),
    ("gifts", "Hộp quà nến thơm", "Quà tặng", 125000, 235000, "quà tặng sinh nhật nến hoa"),
    ("office-equipment", "Máy in nhãn nhiệt", "Thiết bị văn phòng", 520000, 890000, "máy in nhãn văn phòng bán hàng"),
    ("storage", "Hộp đựng đồ trong suốt", "Lưu trữ & sắp xếp", 85000, 159000, "hộp đựng đồ lưu trữ sắp xếp"),
    ("seasonal", "Đèn lồng trang trí lễ hội", "Trang trí theo mùa", 68000, 135000, "lễ hội tết giáng sinh trang trí"),
)
DEMO_PERIODS = tuple(
    f"{year:04d}-{month:02d}"
    for year, month in ((2025, month) for month in range(10, 13))
) + tuple(f"2026-{month:02d}" for month in range(1, 10))


def demo_catalog() -> list[dict[str, object]]:
    """Return searchable demo product choices without exposing implementation tuples."""
    return [
        {
            "id": product_id,
            "product_name": product_name,
            "category": category,
            "cost_per_unit_vnd": cost,
            "list_price_vnd": list_price,
            "search_terms": search_terms,
        }
        for product_id, product_name, category, cost, list_price, search_terms in DEMO_PRODUCTS
    ]


def random_demo_product_ids(count: int = 5, seed: int = 20260928) -> list[str]:
    """Pick a reproducible random starter assortment from the full catalogue."""
    product_ids = [str(product["id"]) for product in demo_catalog()]
    return random.Random(seed + count).sample(product_ids, k=min(count, len(product_ids)))


def build_demo_rows(
    selected_product_ids: Iterable[str] | None = None,
    seed: int = 20260928,
) -> dict[str, list[dict[str, str]]]:
    """Build reproducible simulated data for selected products across 12 months.

    The seed makes the pseudo-random values repeatable for a defence demo and
    tests, while still looking like varied day-to-day shop activity.
    """
    rng = random.Random(seed)
    products: list[dict[str, str]] = []
    orders: list[dict[str, str]] = []
    inventory: list[dict[str, str]] = []
    ads: list[dict[str, str]] = []
    wanted_ids = set(selected_product_ids) if selected_product_ids is not None else None
    selected_products = [product for product in DEMO_PRODUCTS if wanted_ids is None or product[0] in wanted_ids]
    if not selected_products:
        raise ValueError("Chọn ít nhất một mặt hàng để tạo dữ liệu demo.")
    for index, (_, product_name, category, cost, list_price, _) in enumerate(selected_products, start=1):
        sku = f"DEMO-{index:03d}"
        products.append({
            "sku": sku, "product_name": product_name, "category": category,
            "cost_per_unit_vnd": str(cost), "list_price_vnd": str(list_price),
        })
        reorder_point = rng.randint(5, 16)
        available = reorder_point + rng.randint(-4, 24)
        reserved = rng.randint(0, min(5, max(available, 0)))
        inventory.append({
            "sku": sku, "on_hand": str(max(available + reserved, 0)), "reserved": str(reserved),
            "reorder_point": str(reorder_point), "last_updated": "2026-09-28",
        })

        for period_index, period in enumerate(DEMO_PERIODS, start=1):
            quantity = rng.randint(1, 5)
            sold_price = int(list_price * rng.uniform(0.88, 1.0))
            gmv = quantity * sold_price
            seller_discount = int(gmv * rng.choice((0, 0, 0.03, 0.05, 0.08)))
            status = "completed" if rng.random() > 0.08 else "cancelled"
            orders.append({
                "order_id": f"DEMO-{period.replace('-', '')}-{index:03d}",
                "order_date": f"{period}-{rng.randint(1, 27):02d}", "status": status, "sku": sku,
                "quantity": str(quantity), "gross_merchandise_value_vnd": str(gmv),
                "seller_discount_vnd": str(seller_discount), "platform_discount_vnd": str(int(gmv * 0.02)),
                "estimated_transaction_fee_vnd": str(int(gmv * 0.05)),
                "estimated_service_fee_vnd": str(int(gmv * 0.025)),
            })

    campaign_categories = list(dict.fromkeys(product[2] for product in selected_products))[:3]
    for period in DEMO_PERIODS:
        for campaign_index, category in enumerate(campaign_categories, start=1):
            spend = rng.randrange(80000, 260000, 5000)
            ads.append({
                "campaign_id": f"ADS-{period.replace('-', '')}-{campaign_index}", "month": period,
                "campaign_name": f"Quảng cáo {category}", "spend_vnd": str(spend),
                "attributed_revenue_vnd": str(int(spend * rng.uniform(2.2, 5.5))),
                "orders": str(rng.randint(4, 18)),
            })
    return {"orders.csv": orders, "products.csv": products, "inventory.csv": inventory, "ads.csv": ads}


DEMO_ROWS = build_demo_rows()


def empty_rows() -> dict[str, list[dict[str, str]]]:
    """Return typed table headers with no rows for a new shop."""
    return {name: [] for name in REQUIRED_UPLOAD_COLUMNS}


def _csv_bytes(name: str, rows: list[dict[str, str]]) -> bytes:
    buffer = io.StringIO(newline="")
    fieldnames = sorted(REQUIRED_UPLOAD_COLUMNS[name])
    writer = csv.DictWriter(buffer, fieldnames=fieldnames, extrasaction="ignore")
    writer.writeheader()
    writer.writerows(rows)
    return buffer.getvalue().encode("utf-8")


def clean_and_validate_rows(
    rows_by_name: Mapping[str, list[Mapping[str, object]]],
) -> dict[str, list[dict[str, str]]]:
    """Remove completely blank editor rows and validate with the CSV contract."""
    cleaned: dict[str, list[dict[str, str]]] = {}
    for name, rows in rows_by_name.items():
        if name not in REQUIRED_UPLOAD_COLUMNS:
            continue
        normalized_rows = [
            {column: str(row.get(column, "") or "").strip() for column in REQUIRED_UPLOAD_COLUMNS[name]}
            for row in rows
        ]
        normalized_rows = [row for row in normalized_rows if any(row.values())]
        if normalized_rows:
            cleaned[name] = normalized_rows

    missing = [name for name in REQUIRED_FILES if name not in cleaned]
    if missing:
        raise ShopDataValidationError("Thiếu bảng bắt buộc: " + ", ".join(missing))

    content = {name: _csv_bytes(name, rows) for name, rows in cleaned.items()}
    return ShopDataTool.from_uploaded_csvs(content).uploaded_rows or {}


class ShopDataLibrary:
    """Tiny SQLite repository for the two deliberate data spaces in the UI."""

    def __init__(self, path: Path = DEFAULT_LIBRARY_PATH) -> None:
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        connection = self._connect()
        try:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS shop_data_library (
                    library_key TEXT PRIMARY KEY,
                    payload_json TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )
            connection.commit()
        finally:
            connection.close()

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self.path)

    def load(self, library_key: str) -> dict[str, list[dict[str, str]]] | None:
        connection = self._connect()
        try:
            row = connection.execute(
                "SELECT payload_json FROM shop_data_library WHERE library_key = ?",
                (library_key,),
            ).fetchone()
        finally:
            connection.close()
        if row is None:
            return None
        raw = json.loads(row[0])
        return {
            str(name): [{str(key): str(value) for key, value in item.items()} for item in rows]
            for name, rows in raw.items()
        }

    def save(self, library_key: str, rows: Mapping[str, list[Mapping[str, object]]]) -> dict[str, list[dict[str, str]]]:
        validated = clean_and_validate_rows(rows)
        payload = json.dumps(validated, ensure_ascii=False)
        timestamp = datetime.now(timezone.utc).isoformat()
        connection = self._connect()
        try:
            connection.execute(
                """
                INSERT INTO shop_data_library(library_key, payload_json, updated_at)
                VALUES (?, ?, ?)
                ON CONFLICT(library_key) DO UPDATE SET
                    payload_json = excluded.payload_json,
                    updated_at = excluded.updated_at
                """,
                (library_key, payload, timestamp),
            )
            connection.commit()
        finally:
            connection.close()
        return validated

    def seed_demo(
        self, selected_product_ids: Iterable[str] | None = None
    ) -> dict[str, list[dict[str, str]]]:
        """Persist an explicit simulated assortment for the learner workspace."""
        rows = DEMO_ROWS if selected_product_ids is None else build_demo_rows(selected_product_ids)
        return self.save("demo", deepcopy(rows))

    def clear(self, library_key: str) -> None:
        connection = self._connect()
        try:
            connection.execute(
                "DELETE FROM shop_data_library WHERE library_key = ?", (library_key,)
            )
            connection.commit()
        finally:
            connection.close()
