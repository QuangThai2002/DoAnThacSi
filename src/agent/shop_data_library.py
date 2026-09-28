"""Persistent, local data shelves for the seller-facing demo.

The library deliberately stores only structured operational data on the
user's computer.  It does not claim a connection to Shopee Seller Centre.
"""

from __future__ import annotations

import csv
import io
import json
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


# A compact, independent dataset that makes every chart and alert visible on
# first use.  It is not taken from a Seller Centre account.
DEMO_ROWS: dict[str, list[dict[str, str]]] = {
    "orders.csv": [
        {"order_id": "DEMO-001", "order_date": "2026-08-03", "status": "completed", "sku": "DEMO-001", "quantity": "2", "gross_merchandise_value_vnd": "600000", "seller_discount_vnd": "20000", "platform_discount_vnd": "0", "estimated_transaction_fee_vnd": "30000", "estimated_service_fee_vnd": "15000"},
        {"order_id": "DEMO-002", "order_date": "2026-08-12", "status": "completed", "sku": "DEMO-002", "quantity": "1", "gross_merchandise_value_vnd": "420000", "seller_discount_vnd": "0", "platform_discount_vnd": "0", "estimated_transaction_fee_vnd": "21000", "estimated_service_fee_vnd": "10500"},
        {"order_id": "DEMO-003", "order_date": "2026-08-19", "status": "completed", "sku": "DEMO-003", "quantity": "3", "gross_merchandise_value_vnd": "540000", "seller_discount_vnd": "25000", "platform_discount_vnd": "0", "estimated_transaction_fee_vnd": "27000", "estimated_service_fee_vnd": "13500"},
        {"order_id": "DEMO-004", "order_date": "2026-09-05", "status": "completed", "sku": "DEMO-001", "quantity": "1", "gross_merchandise_value_vnd": "300000", "seller_discount_vnd": "10000", "platform_discount_vnd": "0", "estimated_transaction_fee_vnd": "15000", "estimated_service_fee_vnd": "7500"},
    ],
    "products.csv": [
        {"sku": "DEMO-001", "product_name": "Tai nghe Bluetooth Lite", "category": "Âm thanh", "cost_per_unit_vnd": "185000", "list_price_vnd": "320000"},
        {"sku": "DEMO-002", "product_name": "Đèn bàn LED cảm ứng", "category": "Gia dụng", "cost_per_unit_vnd": "250000", "list_price_vnd": "430000"},
        {"sku": "DEMO-003", "product_name": "Chuột không dây Mini", "category": "Phụ kiện", "cost_per_unit_vnd": "95000", "list_price_vnd": "185000"},
    ],
    "inventory.csv": [
        {"sku": "DEMO-001", "on_hand": "5", "reserved": "2", "reorder_point": "4", "last_updated": "2026-09-10"},
        {"sku": "DEMO-002", "on_hand": "12", "reserved": "1", "reorder_point": "4", "last_updated": "2026-09-10"},
        {"sku": "DEMO-003", "on_hand": "4", "reserved": "1", "reorder_point": "5", "last_updated": "2026-09-10"},
    ],
    "ads.csv": [
        {"campaign_id": "ADS-001", "month": "2026-08", "campaign_name": "Tìm kiếm tai nghe", "spend_vnd": "80000", "attributed_revenue_vnd": "450000", "orders": "2"},
        {"campaign_id": "ADS-002", "month": "2026-08", "campaign_name": "Khám phá phụ kiện", "spend_vnd": "50000", "attributed_revenue_vnd": "220000", "orders": "1"},
    ],
}


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
