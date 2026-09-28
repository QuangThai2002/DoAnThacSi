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
from typing import Mapping

from .shop_data_tool import (
    REQUIRED_UPLOAD_COLUMNS,
    ShopDataTool,
    ShopDataValidationError,
)


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_LIBRARY_PATH = PROJECT_ROOT / "data" / "local_store" / "shop_data_library.sqlite"
REQUIRED_FILES = ("orders.csv", "products.csv", "inventory.csv")


DEMO_PRODUCTS = (
    ("Máy lọc không khí mini", "Đồ điện tử gia dụng", 1150000, 1690000),
    ("Bàn phím cơ 87 phím", "Gear máy tính", 410000, 690000),
    ("Giỏ táo nhập khẩu 2kg", "Hoa quả tươi", 165000, 249000),
    ("Hộp bánh quy bơ", "Bánh kẹo", 68000, 125000),
    ("Pin sạc dự phòng 10000mAh", "Điện thoại & phụ kiện", 235000, 420000),
    ("Tai nghe Bluetooth Lite", "Âm thanh", 185000, 320000),
    ("Áo thun cotton basic", "Thời trang nam", 78000, 169000),
    ("Váy liền thân công sở", "Thời trang nữ", 185000, 359000),
    ("Giày sneaker hàng ngày", "Giày dép", 320000, 590000),
    ("Túi tote canvas", "Túi xách", 65000, 149000),
    ("Kem chống nắng SPF50", "Mỹ phẩm", 135000, 265000),
    ("Nước rửa tay 500ml", "Chăm sóc cá nhân", 52000, 115000),
    ("Bỉm em bé gói lớn", "Mẹ & bé", 210000, 345000),
    ("Thức ăn cho mèo 1.5kg", "Thú cưng", 145000, 255000),
    ("Sách kỹ năng bán hàng", "Sách", 88000, 159000),
    ("Bộ bút gel 12 màu", "Văn phòng phẩm", 42000, 105000),
    ("Thảm tập yoga 6mm", "Thể thao", 165000, 295000),
    ("Mũ bảo hiểm nửa đầu", "Xe máy", 190000, 330000),
    ("Kệ để đồ 4 tầng", "Nội thất", 320000, 560000),
    ("Hạt dinh dưỡng tổng hợp", "Thực phẩm khô", 145000, 245000),
)
DEMO_PERIODS = tuple(
    f"{year:04d}-{month:02d}"
    for year, month in ((2025, month) for month in range(10, 13))
) + tuple(f"2026-{month:02d}" for month in range(1, 10))


def build_demo_rows(seed: int = 20260928) -> dict[str, list[dict[str, str]]]:
    """Build reproducible simulated data: 20 products across 12 months.

    The seed makes the pseudo-random values repeatable for a defence demo and
    tests, while still looking like varied day-to-day shop activity.
    """
    rng = random.Random(seed)
    products: list[dict[str, str]] = []
    orders: list[dict[str, str]] = []
    inventory: list[dict[str, str]] = []
    ads: list[dict[str, str]] = []
    for index, (product_name, category, cost, list_price) in enumerate(DEMO_PRODUCTS, start=1):
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

    campaign_categories = ("Gear máy tính", "Hoa quả tươi", "Bánh kẹo")
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

    def seed_demo(self) -> dict[str, list[dict[str, str]]]:
        return self.save("demo", deepcopy(DEMO_ROWS))

    def clear(self, library_key: str) -> None:
        connection = self._connect()
        try:
            connection.execute(
                "DELETE FROM shop_data_library WHERE library_key = ?", (library_key,)
            )
            connection.commit()
        finally:
            connection.close()
