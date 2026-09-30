from __future__ import annotations

import csv
import io
import re
import unicodedata
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any, Mapping

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DATA_DIR = PROJECT_ROOT / "data" / "shop_mock"
COMPLETED_STATUS = "completed"

REQUIRED_UPLOAD_COLUMNS = {
    "orders.csv": {
        "order_id",
        "order_date",
        "status",
        "sku",
        "quantity",
        "gross_merchandise_value_vnd",
        "seller_discount_vnd",
        "platform_discount_vnd",
        "estimated_transaction_fee_vnd",
        "estimated_service_fee_vnd",
    },
    "products.csv": {
        "sku",
        "product_name",
        "category",
        "cost_per_unit_vnd",
        "list_price_vnd",
    },
    "inventory.csv": {
        "sku",
        "on_hand",
        "reserved",
        "reorder_point",
        "last_updated",
    },
    "ads.csv": {
        "campaign_id",
        "month",
        "campaign_name",
        "spend_vnd",
        "attributed_revenue_vnd",
        "orders",
    },
    "purchase_orders.csv": {
        "purchase_order_id",
        "order_date",
        "supplier_name",
        "sku",
        "quantity",
        "unit_cost_vnd",
        "expected_arrival_date",
        "status",
    },
    "returns.csv": {
        "return_id",
        "order_id",
        "request_date",
        "sku",
        "quantity",
        "reason",
        "status",
        "refund_amount_vnd",
    },
    "reviews.csv": {
        "review_id",
        "review_date",
        "sku",
        "rating",
        "sentiment",
        "issue_type",
        "comment",
    },
    "operating_costs.csv": {
        "cost_id",
        "month",
        "cost_category",
        "amount_vnd",
        "note",
    },
    "inventory_movements.csv": {
        "movement_id",
        "movement_date",
        "sku",
        "movement_type",
        "quantity",
        "reference",
        "note",
    },
    "quality_checks.csv": {
        "check_id",
        "check_date",
        "purchase_order_id",
        "sku",
        "inspected_quantity",
        "defective_quantity",
        "defect_type",
        "status",
    },
    "cash_flow.csv": {
        "cash_flow_id",
        "date",
        "direction",
        "category",
        "amount_vnd",
        "reference",
        "note",
    },
    "supplier_performance.csv": {
        "supplier_id",
        "supplier_name",
        "month",
        "on_time_delivery_rate_percent",
        "defect_rate_percent",
        "average_lead_time_days",
        "order_count",
    },
    "customer_segments.csv": {
        "month",
        "segment_name",
        "customer_count",
        "order_count",
        "repeat_order_count",
        "gmv_vnd",
    },
    "product_funnel.csv": {
        "month",
        "sku",
        "views",
        "add_to_cart_count",
        "order_count",
    },
}
REQUIRED_UPLOAD_FILES = frozenset({"orders.csv", "products.csv", "inventory.csv"})
OPTIONAL_UPLOAD_FILES = frozenset({
    "ads.csv", "purchase_orders.csv", "returns.csv", "reviews.csv",
    "operating_costs.csv", "inventory_movements.csv", "quality_checks.csv",
    "cash_flow.csv", "supplier_performance.csv", "customer_segments.csv", "product_funnel.csv",
})
MAX_UPLOADED_CSV_BYTES = 10 * 1024 * 1024


# Người dùng không cần biết tên trường kỹ thuật. Các tiêu đề tiếng Việt dưới
# đây có thể viết có dấu hoặc không dấu; khi nạp, chúng được đổi về schema nội
# bộ để toàn bộ phép tính vẫn dùng chung một chuẩn.
VIETNAMESE_COLUMN_ALIASES: dict[str, dict[str, tuple[str, ...]]] = {
    "orders.csv": {
        "order_id": ("ma_don", "ma_don_hang"),
        "order_date": ("ngay_dat", "ngay_dat_hang", "ngay_tao_don"),
        "status": ("trang_thai",), "sku": ("ma_sku", "ma_san_pham"),
        "quantity": ("so_luong",),
        "gross_merchandise_value_vnd": ("gmv", "gmv_vnd", "gia_tri_hang_hoa", "gia_tri_hang_hoa_vnd"),
        "seller_discount_vnd": ("giam_gia_nguoi_ban", "giam_gia_nguoi_ban_vnd"),
        "platform_discount_vnd": ("tro_gia_san", "tro_gia_san_vnd", "giam_gia_san", "giam_gia_san_vnd"),
        "estimated_transaction_fee_vnd": ("phi_giao_dich_uoc_tinh", "phi_giao_dich_uoc_tinh_vnd"),
        "estimated_service_fee_vnd": ("phi_dich_vu_uoc_tinh", "phi_dich_vu_uoc_tinh_vnd"),
    },
    "products.csv": {
        "sku": ("ma_sku", "ma_san_pham"), "product_name": ("ten_san_pham",),
        "category": ("nganh_hang", "danh_muc"),
        "cost_per_unit_vnd": ("gia_von_don_vi", "gia_von_don_vi_vnd"),
        "list_price_vnd": ("gia_niem_yet", "gia_niem_yet_vnd", "gia_ban"),
    },
    "inventory.csv": {
        "sku": ("ma_sku", "ma_san_pham"), "on_hand": ("ton_thuc_te", "ton_kho"),
        "reserved": ("da_giu_cho", "hang_da_giu"), "reorder_point": ("nguong_nhap_them", "muc_nhap_lai"),
        "last_updated": ("ngay_cap_nhat",),
    },
    "ads.csv": {
        "campaign_id": ("ma_chien_dich",), "month": ("thang",), "campaign_name": ("ten_chien_dich",),
        "spend_vnd": ("chi_quang_cao", "chi_quang_cao_vnd"),
        "attributed_revenue_vnd": ("doanh_thu_quy_gan", "doanh_thu_quy_gan_vnd"),
        "orders": ("so_don_tu_quang_cao", "so_don"),
    },
    "purchase_orders.csv": {
        "purchase_order_id": ("ma_don_nhap",), "order_date": ("ngay_dat_hang", "ngay_nhap"),
        "supplier_name": ("nha_cung_cap",), "sku": ("ma_sku", "ma_san_pham"), "quantity": ("so_luong",),
        "unit_cost_vnd": ("gia_nhap_don_vi", "gia_nhap_don_vi_vnd"),
        "expected_arrival_date": ("ngay_du_kien_ve",), "status": ("trang_thai",),
    },
    "returns.csv": {
        "return_id": ("ma_hoan_hang",), "order_id": ("ma_don", "ma_don_hang"),
        "request_date": ("ngay_yeu_cau_hoan",), "sku": ("ma_sku", "ma_san_pham"),
        "quantity": ("so_luong",), "reason": ("ly_do",), "status": ("trang_thai",),
        "refund_amount_vnd": ("tien_hoan", "tien_hoan_vnd"),
    },
    "reviews.csv": {
        "review_id": ("ma_danh_gia",), "review_date": ("ngay_danh_gia",),
        "sku": ("ma_sku", "ma_san_pham"), "rating": ("so_sao", "diem_danh_gia"),
        "sentiment": ("cam_xuc",), "issue_type": ("van_de",), "comment": ("nhan_xet", "binh_luan"),
    },
    "operating_costs.csv": {
        "cost_id": ("ma_chi_phi",), "month": ("thang",), "cost_category": ("nhom_chi_phi",),
        "amount_vnd": ("so_tien", "so_tien_vnd"), "note": ("ghi_chu",),
    },
    "inventory_movements.csv": {
        "movement_id": ("ma_bien_dong",), "movement_date": ("ngay_bien_dong",),
        "sku": ("ma_sku", "ma_san_pham"), "movement_type": ("loai_bien_dong",),
        "quantity": ("so_luong",), "reference": ("ma_tham_chieu",), "note": ("ghi_chu",),
    },
    "quality_checks.csv": {
        "check_id": ("ma_kiem_tra",), "check_date": ("ngay_kiem_tra",), "purchase_order_id": ("ma_don_nhap",),
        "sku": ("ma_sku", "ma_san_pham"), "inspected_quantity": ("so_luong_da_kiem",),
        "defective_quantity": ("so_luong_loi",), "defect_type": ("loai_loi",), "status": ("trang_thai",),
    },
    "cash_flow.csv": {
        "cash_flow_id": ("ma_dong_tien",), "date": ("ngay_ghi_nhan", "ngay"),
        "direction": ("thu_chi", "huong_thu_chi"), "category": ("nhom", "danh_muc"),
        "amount_vnd": ("so_tien", "so_tien_vnd"), "reference": ("ma_tham_chieu",), "note": ("ghi_chu",),
    },
    "supplier_performance.csv": {
        "supplier_id": ("ma_nha_cung_cap",), "supplier_name": ("ten_nha_cung_cap", "nha_cung_cap"), "month": ("thang",),
        "on_time_delivery_rate_percent": ("giao_dung_hen_phan_tram", "giao_dung_hen"),
        "defect_rate_percent": ("ty_le_loi_phan_tram", "ty_le_loi"),
        "average_lead_time_days": ("so_ngay_giao_trung_binh",), "order_count": ("so_don",),
    },
    "customer_segments.csv": {
        "month": ("thang",), "segment_name": ("nhom_khach",), "customer_count": ("so_khach",),
        "order_count": ("so_don",), "repeat_order_count": ("don_mua_lai",), "gmv_vnd": ("gmv", "gmv_vnd"),
    },
    "product_funnel.csv": {
        "month": ("thang",), "sku": ("ma_sku", "ma_san_pham"), "views": ("luot_xem",),
        "add_to_cart_count": ("luot_them_gio",), "order_count": ("so_don",),
    },
}


def normalize_header(value: object) -> str:
    """Make Vietnamese spreadsheet headers comparable without requiring accents."""
    text = unicodedata.normalize("NFD", str(value or ""))
    text = "".join(char for char in text if unicodedata.category(char) != "Mn")
    text = text.replace("đ", "d").replace("Đ", "D").lower().strip()
    return re.sub(r"[^a-z0-9]+", "_", text).strip("_")


class ShopDataValidationError(ValueError):
    """Raised when an uploaded operational CSV cannot be used safely."""


def as_decimal(value: str | int | float | Decimal) -> Decimal:
    try:
        return Decimal(str(value or "0"))
    except (InvalidOperation, ValueError) as exc:
        raise ValueError(f"Invalid monetary value: {value!r}") from exc


def as_number(value: Decimal) -> int | float:
    if value == value.to_integral_value():
        return int(value)
    return float(value)


def normalize_date(value: str) -> str:
    """Normalize common CSV-export date formats to ISO-8601.

    Excel exports frequently contain ``8/31/2026`` instead of ``2026-08-31``.
    Storing the normalized form also keeps month filtering deterministic.
    """
    cleaned = str(value or "").strip()
    try:
        return date.fromisoformat(cleaned).isoformat()
    except ValueError:
        pass

    for date_format in ("%m/%d/%Y", "%d/%m/%Y"):
        try:
            return datetime.strptime(cleaned, date_format).date().isoformat()
        except ValueError:
            continue
    raise ValueError(f"Invalid date: {value!r}")


def normalize_month(value: str) -> str:
    """Normalize common spreadsheet month values to ``YYYY-MM``."""
    cleaned = str(value or "").strip()
    if len(cleaned) == 7 and cleaned[4:5] == "-":
        year, month = cleaned.split("-", maxsplit=1)
        if year.isdigit() and month.isdigit() and 1 <= int(month) <= 12:
            return f"{int(year):04d}-{int(month):02d}"

    month_year = re.fullmatch(r"(\d{1,2})/(\d{4})", cleaned)
    if month_year:
        month, year = (int(part) for part in month_year.groups())
        if 1 <= month <= 12:
            return f"{year:04d}-{month:02d}"

    return normalize_date(cleaned)[:7]


class ShopDataTool:
    """Read-only analytics over mock data or session-scoped uploaded CSVs.

    Every result carries a `data_scope` marker. Uploaded files remain in the
    current Streamlit session; the tool never implies a Seller Centre link.
    """

    def __init__(
        self,
        data_dir: Path = DEFAULT_DATA_DIR,
        uploaded_rows: Mapping[str, list[dict[str, str]]] | None = None,
    ) -> None:
        self.data_dir = data_dir
        self._uploaded_rows = (
            {name: list(rows) for name, rows in uploaded_rows.items()}
            if uploaded_rows is not None
            else None
        )
        self.data_scope = (
            "uploaded_csv" if self._uploaded_rows is not None else "mock_shop_data"
        )

    @property
    def uploaded_rows(self) -> dict[str, list[dict[str, str]]] | None:
        """Return session-owned parsed rows for the Streamlit integration."""
        return self._uploaded_rows

    @classmethod
    def from_uploaded_csvs(cls, files: Mapping[str, bytes]) -> "ShopDataTool":
        """Backward-compatible name for structured CSV or Excel uploads."""
        return cls.from_uploaded_files(files)

    @classmethod
    def from_uploaded_files(cls, files: Mapping[str, bytes]) -> "ShopDataTool":
        """Build a per-session tool from CSV/XLSX files using Vietnamese-friendly headers."""
        normalized_files = {str(name): value for name, value in files.items()}
        missing_files = sorted(REQUIRED_UPLOAD_FILES - set(normalized_files))
        if missing_files:
            raise ShopDataValidationError(
                "Thiếu file bắt buộc: " + ", ".join(missing_files)
            )

        unexpected_files = sorted(set(normalized_files) - set(REQUIRED_UPLOAD_COLUMNS))
        if unexpected_files:
            raise ShopDataValidationError(
                "File không được hỗ trợ: " + ", ".join(unexpected_files)
            )

        rows_by_name: dict[str, list[dict[str, str]]] = {}
        for name, raw_content in normalized_files.items():
            rows_by_name[name] = cls._parse_uploaded_file(name, raw_content)
        return cls(uploaded_rows=rows_by_name)

    @classmethod
    def _parse_uploaded_file(
        cls,
        name: str,
        raw_content: bytes,
    ) -> list[dict[str, str]]:
        if not raw_content:
            raise ShopDataValidationError(f"{name} đang trống.")
        if len(raw_content) > MAX_UPLOADED_CSV_BYTES:
            raise ShopDataValidationError(
                f"{name} vượt quá giới hạn {MAX_UPLOADED_CSV_BYTES // (1024 * 1024)} MB."
            )

        if raw_content.startswith(b"PK\x03\x04"):
            rows, headers = cls._read_excel_rows(name, raw_content)
        else:
            rows, headers = cls._read_csv_rows(name, raw_content)

        header_mapping = cls._header_mapping(name, headers)
        missing_columns = sorted(REQUIRED_UPLOAD_COLUMNS[name] - set(header_mapping.values()))
        if missing_columns:
            raise ShopDataValidationError(
                f"{name} thiếu cột bắt buộc: " + ", ".join(missing_columns)
            )
        rows = [
            {
                header_mapping.get(str(key).strip(), str(key).strip()): value
                for key, value in row.items()
                if key is not None
            }
            for row in rows
        ]
        rows = [cls._normalize_uploaded_values(name, row) for row in rows]
        if not rows:
            raise ShopDataValidationError(f"{name} chưa có dòng dữ liệu.")

        date_column = {
            "orders.csv": "order_date",
            "inventory.csv": "last_updated",
            "purchase_orders.csv": "order_date",
            "returns.csv": "request_date",
            "reviews.csv": "review_date",
            "inventory_movements.csv": "movement_date",
            "quality_checks.csv": "check_date",
            "cash_flow.csv": "date",
        }.get(name)
        if date_column:
            for row in rows:
                try:
                    row[date_column] = normalize_date(row[date_column])
                except ValueError:
                    # Keep the original value so the existing validation below can
                    # report a consistent Vietnamese error with its row number.
                    pass

        if name in {"ads.csv", "operating_costs.csv", "supplier_performance.csv", "customer_segments.csv", "product_funnel.csv"}:
            for row in rows:
                try:
                    row["month"] = normalize_month(row["month"])
                except ValueError:
                    pass

        cls._validate_uploaded_rows(name, rows)
        return rows

    @staticmethod
    def _normalize_uploaded_values(name: str, row: dict[str, str]) -> dict[str, str]:
        """Accept common Vietnamese values while keeping analytics deterministic."""
        normalized_row = dict(row)
        if "status" in normalized_row:
            status = normalize_header(normalized_row["status"])
            status_aliases = {
                "hoan_tat": "completed", "hoan_thanh": "completed", "da_hoan_thanh": "completed",
                "completed": "completed", "huy": "cancelled", "da_huy": "cancelled",
                "cancelled": "cancelled", "canceled": "cancelled", "da_nhan": "received",
                "received": "received", "da_xac_nhan": "confirmed", "confirmed": "confirmed",
            }
            normalized_row["status"] = status_aliases.get(status, str(normalized_row["status"]).strip())
        if name == "cash_flow.csv" and "direction" in normalized_row:
            direction = normalize_header(normalized_row["direction"])
            normalized_row["direction"] = {"tien_thu": "thu", "thu": "thu", "tien_chi": "chi", "chi": "chi"}.get(
                direction, str(normalized_row["direction"]).strip()
            )
        if name == "inventory_movements.csv" and "movement_type" in normalized_row:
            movement = normalize_header(normalized_row["movement_type"])
            normalized_row["movement_type"] = {
                "nhap_kho": "Nhập kho", "ban_ra": "Bán ra", "hang_loi_huy": "Hàng lỗi/hủy",
            }.get(movement, str(normalized_row["movement_type"]).strip())
        return normalized_row

    @staticmethod
    def _read_csv_rows(name: str, raw_content: bytes) -> tuple[list[dict[str, str]], list[str]]:
        try:
            text = raw_content.decode("utf-8-sig")
        except UnicodeDecodeError as exc:
            raise ShopDataValidationError(
                f"{name} cần là CSV mã hóa UTF-8 hoặc tệp Excel .xlsx."
            ) from exc
        reader = csv.DictReader(io.StringIO(text))
        headers = [str(header).strip() for header in (reader.fieldnames or []) if header]
        reader.fieldnames = headers
        rows = [
            {
                str(key).strip(): str(value or "").strip()
                for key, value in row.items()
                if key is not None
            }
            for row in reader
        ]
        return rows, headers

    @staticmethod
    def _spreadsheet_value(value: object) -> str:
        if value is None or pd.isna(value):
            return ""
        if isinstance(value, (datetime, date, pd.Timestamp)):
            return value.date().isoformat() if isinstance(value, pd.Timestamp) else value.isoformat()
        if isinstance(value, float) and value.is_integer():
            return str(int(value))
        return str(value).strip()

    @classmethod
    def _read_excel_rows(cls, name: str, raw_content: bytes) -> tuple[list[dict[str, str]], list[str]]:
        try:
            frame = pd.read_excel(io.BytesIO(raw_content), dtype=object)
        except Exception as exc:
            raise ShopDataValidationError(
                f"{name} không đọc được tệp Excel. Hãy lưu lại dưới dạng .xlsx rồi thử lại."
            ) from exc
        headers = [str(column).strip() for column in frame.columns if str(column).strip()]
        if len(headers) != len(frame.columns):
            raise ShopDataValidationError(f"{name} có tên cột trống.")
        rows = [
            {
                str(column).strip(): cls._spreadsheet_value(value)
                for column, value in record.items()
            }
            for record in frame.to_dict("records")
        ]
        return rows, headers

    @staticmethod
    def _header_mapping(name: str, headers: list[str]) -> dict[str, str]:
        aliases = {
            normalize_header(alias): canonical
            for canonical, choices in VIETNAMESE_COLUMN_ALIASES.get(name, {}).items()
            for alias in (canonical, *choices)
        }
        mapping = {
            header: aliases.get(normalize_header(header), str(header).strip())
            for header in headers
        }
        canonical_headers = list(mapping.values())
        duplicates = sorted({header for header in canonical_headers if canonical_headers.count(header) > 1})
        if duplicates:
            raise ShopDataValidationError(
                f"{name} có cột bị trùng nghĩa: " + ", ".join(duplicates)
            )
        return mapping

    @staticmethod
    def _validate_uploaded_rows(name: str, rows: list[dict[str, str]]) -> None:
        required_columns = REQUIRED_UPLOAD_COLUMNS[name]
        for row_number, row in enumerate(rows, start=2):
            blank_columns = sorted(
                column for column in required_columns if not row.get(column, "").strip()
            )
            if blank_columns:
                raise ShopDataValidationError(
                    f"{name}, dòng {row_number} thiếu giá trị: "
                    + ", ".join(blank_columns)
                )

            try:
                if name == "orders.csv":
                    date.fromisoformat(row["order_date"])
                    if int(row["quantity"]) < 0:
                        raise ValueError("quantity must not be negative")
                    for column in (
                        "gross_merchandise_value_vnd",
                        "seller_discount_vnd",
                        "platform_discount_vnd",
                        "estimated_transaction_fee_vnd",
                        "estimated_service_fee_vnd",
                    ):
                        as_decimal(row[column])
                elif name == "inventory.csv":
                    if any(
                        int(row[column]) < 0
                        for column in ("on_hand", "reserved", "reorder_point")
                    ):
                        raise ValueError("inventory values must not be negative")
                    date.fromisoformat(row["last_updated"])
                elif name == "products.csv":
                    as_decimal(row["cost_per_unit_vnd"])
                    as_decimal(row["list_price_vnd"])
                elif name == "ads.csv":
                    date.fromisoformat(f"{row['month']}-01")
                    int(row["orders"])
                    as_decimal(row["spend_vnd"])
                    as_decimal(row["attributed_revenue_vnd"])
                elif name == "purchase_orders.csv":
                    date.fromisoformat(row["order_date"])
                    date.fromisoformat(row["expected_arrival_date"])
                    if int(row["quantity"]) < 0:
                        raise ValueError("quantity must not be negative")
                    as_decimal(row["unit_cost_vnd"])
                elif name == "returns.csv":
                    date.fromisoformat(row["request_date"])
                    if int(row["quantity"]) < 0:
                        raise ValueError("quantity must not be negative")
                    as_decimal(row["refund_amount_vnd"])
                elif name == "reviews.csv":
                    date.fromisoformat(row["review_date"])
                    if not 1 <= int(row["rating"]) <= 5:
                        raise ValueError("rating must be between 1 and 5")
                elif name == "operating_costs.csv":
                    date.fromisoformat(f"{row['month']}-01")
                    if as_decimal(row["amount_vnd"]) < 0:
                        raise ValueError("amount must not be negative")
                elif name == "inventory_movements.csv":
                    date.fromisoformat(row["movement_date"])
                    if int(row["quantity"]) < 0:
                        raise ValueError("quantity must not be negative")
                elif name == "quality_checks.csv":
                    date.fromisoformat(row["check_date"])
                    inspected = int(row["inspected_quantity"])
                    defective = int(row["defective_quantity"])
                    if inspected < 0 or defective < 0 or defective > inspected:
                        raise ValueError("invalid inspection quantities")
                elif name == "cash_flow.csv":
                    date.fromisoformat(row["date"])
                    if row["direction"].strip().lower() not in {"thu", "chi"}:
                        raise ValueError("direction must be thu or chi")
                    if as_decimal(row["amount_vnd"]) < 0:
                        raise ValueError("amount must not be negative")
                elif name == "supplier_performance.csv":
                    date.fromisoformat(f"{row['month']}-01")
                    if not 0 <= float(row["on_time_delivery_rate_percent"]) <= 100:
                        raise ValueError("on-time rate must be in range")
                    if not 0 <= float(row["defect_rate_percent"]) <= 100:
                        raise ValueError("defect rate must be in range")
                    if float(row["average_lead_time_days"]) < 0 or int(row["order_count"]) < 0:
                        raise ValueError("supplier values must not be negative")
                elif name == "customer_segments.csv":
                    date.fromisoformat(f"{row['month']}-01")
                    if any(int(row[column]) < 0 for column in ("customer_count", "order_count", "repeat_order_count")):
                        raise ValueError("customer values must not be negative")
                    as_decimal(row["gmv_vnd"])
                elif name == "product_funnel.csv":
                    date.fromisoformat(f"{row['month']}-01")
                    views = int(row["views"])
                    carts = int(row["add_to_cart_count"])
                    orders = int(row["order_count"])
                    if views < 0 or carts < 0 or orders < 0 or carts > views or orders > carts:
                        raise ValueError("invalid funnel values")
            except (InvalidOperation, ValueError) as exc:
                raise ShopDataValidationError(
                    f"{name}, dòng {row_number} có ngày hoặc số không hợp lệ."
                ) from exc

    def sales_summary(self, period: str | None = None) -> dict[str, Any]:
        orders = [
            order
            for order in self._read_csv("orders.csv")
            if order["status"].strip().lower() == COMPLETED_STATUS
            and (period is None or order["order_date"].startswith(period))
        ]
        amounts = {
            "gross_merchandise_value_vnd": Decimal("0"),
            "seller_discount_vnd": Decimal("0"),
            "platform_discount_vnd": Decimal("0"),
            "estimated_transaction_fee_vnd": Decimal("0"),
            "estimated_service_fee_vnd": Decimal("0"),
        }
        quantity = 0
        for order in orders:
            quantity += int(order["quantity"])
            for field in amounts:
                amounts[field] += as_decimal(order[field])

        estimated_platform_fees = (
            amounts["estimated_transaction_fee_vnd"]
            + amounts["estimated_service_fee_vnd"]
        )
        net_revenue = (
            amounts["gross_merchandise_value_vnd"]
            - amounts["seller_discount_vnd"]
            - estimated_platform_fees
        )
        return {
            "tool": "shop_data.sales_summary",
            "data_scope": self.data_scope,
            "period": period or "all_available_periods",
            "completed_order_count": len(orders),
            "completed_unit_count": quantity,
            **{field: as_number(value) for field, value in amounts.items()},
            "estimated_platform_fees_vnd": as_number(estimated_platform_fees),
            "net_revenue_after_estimated_fees_vnd": as_number(net_revenue),
            "formula": "GMV - seller_discount - estimated_transaction_fee - estimated_service_fee",
            "included_status": COMPLETED_STATUS,
        }

    def product_gmv_ranking(self, period: str | None = None) -> dict[str, Any]:
        """Rank completed-order GMV by product for a focused seller question."""
        products = {row["sku"]: row["product_name"] for row in self._read_csv("products.csv")}
        totals: dict[str, dict[str, Decimal | int]] = {}
        for order in self._read_csv("orders.csv"):
            if order["status"].strip().lower() != COMPLETED_STATUS:
                continue
            if period is not None and not order["order_date"].startswith(period):
                continue
            row = totals.setdefault(
                order["sku"], {"gmv": Decimal("0"), "quantity": 0, "order_count": 0}
            )
            row["gmv"] = Decimal(str(row["gmv"])) + as_decimal(order["gross_merchandise_value_vnd"])
            row["quantity"] = int(row["quantity"]) + int(order["quantity"])
            row["order_count"] = int(row["order_count"]) + 1
        ranked = [
            {
                "sku": sku,
                "product_name": products.get(sku, sku),
                "gmv_vnd": as_number(Decimal(str(values["gmv"]))),
                "completed_unit_count": int(values["quantity"]),
                "completed_order_count": int(values["order_count"]),
            }
            for sku, values in totals.items()
        ]
        ranked.sort(key=lambda item: (-float(item["gmv_vnd"]), item["product_name"]))
        return {
            "tool": "shop_data.product_gmv_ranking",
            "data_scope": self.data_scope,
            "period": period or "all_available_periods",
            "ranked_products": ranked,
            "top_product": ranked[0] if ranked else None,
            "limitation": "Xếp hạng chỉ dựa trên đơn hoàn tất trong dữ liệu đang gắn; GMV không phải lợi nhuận.",
        }

    def product_contribution_ranking(self, period: str | None = None) -> dict[str, Any]:
        """Rank products by recorded contribution, from lowest to highest.

        This distinguishes a product that earns little per unit from the shop's
        total contribution. It deliberately excludes costs that are not tied to
        a single order (for example staffing or warehouse rent).
        """
        products = {row["sku"]: row for row in self._read_csv("products.csv")}
        totals: dict[str, dict[str, Decimal | int]] = {}
        for order in self._read_csv("orders.csv"):
            if order["status"].strip().lower() != COMPLETED_STATUS:
                continue
            if period is not None and not order["order_date"].startswith(period):
                continue
            row = totals.setdefault(
                order["sku"],
                {"gmv": Decimal("0"), "seller_discount": Decimal("0"), "transaction_fee": Decimal("0"), "service_fee": Decimal("0"), "quantity": 0, "order_count": 0},
            )
            row["gmv"] = Decimal(str(row["gmv"])) + as_decimal(order["gross_merchandise_value_vnd"])
            row["seller_discount"] = Decimal(str(row["seller_discount"])) + as_decimal(order["seller_discount_vnd"])
            row["transaction_fee"] = Decimal(str(row["transaction_fee"])) + as_decimal(order["estimated_transaction_fee_vnd"])
            row["service_fee"] = Decimal(str(row["service_fee"])) + as_decimal(order["estimated_service_fee_vnd"])
            row["quantity"] = int(row["quantity"]) + int(order["quantity"])
            row["order_count"] = int(row["order_count"]) + 1

        ranked: list[dict[str, Any]] = []
        for sku, values in totals.items():
            product = products.get(sku, {})
            gmv = Decimal(str(values["gmv"]))
            units = int(values["quantity"])
            product_cost = as_decimal(product.get("cost_per_unit_vnd", "0")) * units
            contribution = (
                gmv - Decimal(str(values["seller_discount"]))
                - Decimal(str(values["transaction_fee"])) - Decimal(str(values["service_fee"]))
                - product_cost
            )
            ranked.append({
                "sku": sku,
                "product_name": product.get("product_name", sku),
                "completed_order_count": int(values["order_count"]),
                "completed_unit_count": units,
                "gmv_vnd": as_number(gmv),
                "estimated_contribution_vnd": as_number(contribution),
                "estimated_contribution_per_unit_vnd": as_number(contribution / units) if units else 0,
                "contribution_margin_percent": round(float(contribution / gmv * 100), 2) if gmv else None,
            })
        ranked.sort(key=lambda item: (float(item["estimated_contribution_vnd"]), item["product_name"]))
        return {
            "tool": "shop_data.product_contribution_ranking",
            "data_scope": self.data_scope,
            "period": period or "all_available_periods",
            "ranked_products": ranked,
            "lowest_product": ranked[0] if ranked else None,
            "limitation": "Lãi góp ước tính đã trừ giá vốn, giảm giá người bán và phí sàn đã ghi nhận; chưa trừ quảng cáo, đóng gói, nhân sự, kho bãi, thuế và chi phí chung.",
        }

    def sales_period_comparison(self, period: str | None = None) -> dict[str, Any]:
        """Compare one recorded month with the immediately preceding recorded month."""
        monthly: dict[str, dict[str, Decimal | int]] = {}
        for order in self._read_csv("orders.csv"):
            if order["status"].strip().lower() != COMPLETED_STATUS:
                continue
            month = order["order_date"][:7]
            totals = monthly.setdefault(
                month,
                {"gmv": Decimal("0"), "seller_discount": Decimal("0"), "transaction_fee": Decimal("0"), "service_fee": Decimal("0"), "orders": 0},
            )
            totals["gmv"] = Decimal(str(totals["gmv"])) + as_decimal(order["gross_merchandise_value_vnd"])
            totals["seller_discount"] = Decimal(str(totals["seller_discount"])) + as_decimal(order["seller_discount_vnd"])
            totals["transaction_fee"] = Decimal(str(totals["transaction_fee"])) + as_decimal(order["estimated_transaction_fee_vnd"])
            totals["service_fee"] = Decimal(str(totals["service_fee"])) + as_decimal(order["estimated_service_fee_vnd"])
            totals["orders"] = int(totals["orders"]) + 1
        months = sorted(monthly)
        current_month = period if period in monthly else (months[-1] if months else None)
        previous_month = None
        if current_month is not None:
            current_index = months.index(current_month)
            previous_month = months[current_index - 1] if current_index else None

        def summary(month: str | None) -> dict[str, Any] | None:
            if month is None:
                return None
            values = monthly[month]
            gmv = Decimal(str(values["gmv"]))
            net = gmv - Decimal(str(values["seller_discount"])) - Decimal(str(values["transaction_fee"])) - Decimal(str(values["service_fee"]))
            return {
                "period": month,
                "gmv_vnd": as_number(gmv),
                "net_revenue_after_estimated_fees_vnd": as_number(net),
                "completed_order_count": int(values["orders"]),
            }

        current = summary(current_month)
        previous = summary(previous_month)
        gmv_change = None
        if current is not None and previous is not None and previous["gmv_vnd"]:
            gmv_change = round(((current["gmv_vnd"] - previous["gmv_vnd"]) / previous["gmv_vnd"]) * 100, 2)
        return {
            "tool": "shop_data.sales_period_comparison",
            "data_scope": self.data_scope,
            "current": current,
            "previous": previous,
            "gmv_change_percent": gmv_change,
            "limitation": "So sánh chỉ dùng hai tháng có đơn hoàn tất liền kề trong dữ liệu đang gắn; không tự suy ra nguyên nhân tăng hoặc giảm.",
        }

    def inventory_alerts(self) -> dict[str, Any]:
        products = {row["sku"]: row for row in self._read_csv("products.csv")}
        alerts: list[dict[str, Any]] = []
        for row in self._read_csv("inventory.csv"):
            available = int(row["on_hand"]) - int(row["reserved"])
            reorder_point = int(row["reorder_point"])
            if available <= reorder_point:
                product = products.get(row["sku"], {})
                alerts.append(
                    {
                        "sku": row["sku"],
                        "product_name": product.get("product_name", row["sku"]),
                        "available_units": available,
                        "reorder_point": reorder_point,
                        "shortfall_units": reorder_point - available,
                        "last_updated": row["last_updated"],
                    }
                )
        alerts.sort(key=lambda item: (-int(item["shortfall_units"]), item["sku"]))
        return {
            "tool": "shop_data.inventory_alerts",
            "data_scope": self.data_scope,
            "alert_count": len(alerts),
            "alerts": alerts,
            "rule": "available_units = on_hand - reserved; alert when available_units <= reorder_point",
        }

    def advertising_summary(self, period: str | None = None) -> dict[str, Any]:
        rows = [
            row
            for row in self._read_csv("ads.csv")
            if period is None or row["month"] == period
        ]
        spend = sum((as_decimal(row["spend_vnd"]) for row in rows), Decimal("0"))
        revenue = sum(
            (as_decimal(row["attributed_revenue_vnd"]) for row in rows),
            Decimal("0"),
        )
        orders = sum((int(row["orders"]) for row in rows), 0)
        roas = revenue / spend if spend else Decimal("0")
        return {
            "tool": "shop_data.advertising_summary",
            "data_scope": self.data_scope,
            "period": period or "all_available_periods",
            "campaign_count": len(rows),
            "ad_spend_vnd": as_number(spend),
            "attributed_revenue_vnd": as_number(revenue),
            "attributed_order_count": orders,
            "roas": round(float(roas), 4),
            "formula": "ROAS = attributed_revenue / ad_spend",
        }

    def profitability_summary(self, period: str | None = None) -> dict[str, Any]:
        """Estimate contribution after product cost and recorded platform fees."""
        products = {row["sku"]: row for row in self._read_csv("products.csv")}
        orders = [
            row for row in self._read_csv("orders.csv")
            if row["status"].strip().lower() == COMPLETED_STATUS
            and (period is None or row["order_date"].startswith(period))
        ]
        sales = self.sales_summary(period)
        cost_of_goods = sum(
            (
                as_decimal(products.get(row["sku"], {}).get("cost_per_unit_vnd", "0"))
                * int(row["quantity"])
                for row in orders
            ),
            Decimal("0"),
        )
        contribution = as_decimal(sales["net_revenue_after_estimated_fees_vnd"]) - cost_of_goods
        return {
            "tool": "shop_data.profitability_summary",
            "data_scope": self.data_scope,
            "period": period or "all_available_periods",
            "completed_order_count": len(orders),
            "estimated_cost_of_goods_vnd": as_number(cost_of_goods),
            "estimated_contribution_vnd": as_number(contribution),
            "formula": "GMV - seller_discount - recorded_platform_fees - product_cost",
            "limitation": "Chưa gồm đóng gói, nhân sự, kho bãi, thuế, chi phí vận chuyển phát sinh và chi phí quảng cáo nếu không được hỏi riêng.",
        }

    def operating_cost_summary(self, period: str | None = None) -> dict[str, Any]:
        """Summarize recorded overhead; it is intentionally separate from GMV."""
        rows = [
            row for row in self._read_csv("operating_costs.csv")
            if period is None or row["month"] == period
        ]
        by_category: dict[str, Decimal] = {}
        for row in rows:
            category = row["cost_category"].strip() or "Chưa phân loại"
            by_category[category] = by_category.get(category, Decimal("0")) + as_decimal(row["amount_vnd"])
        total = sum(by_category.values(), Decimal("0"))
        return {
            "tool": "shop_data.operating_cost_summary",
            "data_scope": self.data_scope,
            "period": period or "all_available_periods",
            "record_count": len(rows),
            "total_operating_cost_vnd": as_number(total),
            "by_category": {
                category: as_number(amount)
                for category, amount in sorted(by_category.items(), key=lambda item: (-item[1], item[0]))
            },
            "limitation": "Chỉ gồm chi phí vận hành đã nhập; chưa tự suy ra thuế, chi phí chưa ghi nhận hoặc chi phí cá nhân.",
        }

    def inventory_movement_summary(self, period: str | None = None) -> dict[str, Any]:
        """Report recorded inbound, outbound and damage movements, not a stock audit."""
        rows = [
            row for row in self._read_csv("inventory_movements.csv")
            if period is None or row["movement_date"].startswith(period)
        ]
        totals: dict[str, int] = {}
        for row in rows:
            movement_type = row["movement_type"].strip().lower() or "chưa phân loại"
            totals[movement_type] = totals.get(movement_type, 0) + int(row["quantity"])
        return {
            "tool": "shop_data.inventory_movement_summary",
            "data_scope": self.data_scope,
            "period": period or "all_available_periods",
            "movement_count": len(rows),
            "inbound_unit_count": totals.get("nhập kho", 0),
            "outbound_unit_count": totals.get("bán ra", 0),
            "damaged_unit_count": totals.get("hàng lỗi/hủy", 0),
            "by_type": dict(sorted(totals.items(), key=lambda item: (-item[1], item[0]))),
            "limitation": "Đây là biến động đã ghi nhận, không thay thế kiểm kê thực tế tại kho.",
        }

    def quality_summary(self, period: str | None = None) -> dict[str, Any]:
        """Summarize quality checks to flag possible supplier or product issues."""
        rows = [
            row for row in self._read_csv("quality_checks.csv")
            if period is None or row["check_date"].startswith(period)
        ]
        inspected = sum(int(row["inspected_quantity"]) for row in rows)
        defective = sum(int(row["defective_quantity"]) for row in rows)
        defects: dict[str, int] = {}
        for row in rows:
            defect_type = row["defect_type"].strip() or "Không phát hiện lỗi"
            defects[defect_type] = defects.get(defect_type, 0) + int(row["defective_quantity"])
        return {
            "tool": "shop_data.quality_summary",
            "data_scope": self.data_scope,
            "period": period or "all_available_periods",
            "check_count": len(rows),
            "inspected_unit_count": inspected,
            "defective_unit_count": defective,
            "defect_rate_percent": round((defective / inspected) * 100, 2) if inspected else None,
            "defects": dict(sorted(defects.items(), key=lambda item: (-item[1], item[0]))),
            "limitation": "Tỷ lệ lỗi chỉ phản ánh những lô đã được kiểm tra và nhập vào bảng này.",
        }

    def cash_flow_summary(self, period: str | None = None) -> dict[str, Any]:
        """Summarize recorded money movements, without equating it to accounting profit."""
        rows = [
            row for row in self._read_csv("cash_flow.csv")
            if period is None or row["date"].startswith(period)
        ]
        inflow = sum((as_decimal(row["amount_vnd"]) for row in rows if row["direction"].lower() == "thu"), Decimal("0"))
        outflow = sum((as_decimal(row["amount_vnd"]) for row in rows if row["direction"].lower() == "chi"), Decimal("0"))
        categories: dict[str, Decimal] = {}
        for row in rows:
            if row["direction"].lower() != "chi":
                continue
            category = row["category"].strip() or "Chưa phân loại"
            categories[category] = categories.get(category, Decimal("0")) + as_decimal(row["amount_vnd"])
        return {
            "tool": "shop_data.cash_flow_summary",
            "data_scope": self.data_scope,
            "period": period or "all_available_periods",
            "inflow_vnd": as_number(inflow),
            "outflow_vnd": as_number(outflow),
            "net_cash_movement_vnd": as_number(inflow - outflow),
            "outflow_by_category": {
                category: as_number(amount)
                for category, amount in sorted(categories.items(), key=lambda item: (-item[1], item[0]))
            },
            "limitation": "Đây là dòng tiền đã ghi nhận, không thay thế sổ sách kế toán hoặc số dư tài khoản ngân hàng.",
        }

    def supplier_performance_summary(self, period: str | None = None) -> dict[str, Any]:
        rows = [
            row for row in self._read_csv("supplier_performance.csv")
            if period is None or row["month"] == period
        ]
        suppliers = [
            {
                "supplier_name": row["supplier_name"],
                "on_time_delivery_rate_percent": float(row["on_time_delivery_rate_percent"]),
                "defect_rate_percent": float(row["defect_rate_percent"]),
                "average_lead_time_days": float(row["average_lead_time_days"]),
                "order_count": int(row["order_count"]),
            }
            for row in rows
        ]
        suppliers.sort(key=lambda item: (-item["on_time_delivery_rate_percent"], item["defect_rate_percent"], item["average_lead_time_days"]))
        return {
            "tool": "shop_data.supplier_performance_summary",
            "data_scope": self.data_scope,
            "period": period or "all_available_periods",
            "supplier_count": len(suppliers),
            "best_supplier": suppliers[0] if suppliers else None,
            "slowest_supplier": max(suppliers, key=lambda item: item["average_lead_time_days"]) if suppliers else None,
            "suppliers": suppliers,
            "limitation": "So sánh chỉ dựa trên các đơn và lô đã ghi; không đủ để khẳng định nhà cung cấp nào luôn tốt hơn.",
        }

    def customer_retention_summary(self, period: str | None = None) -> dict[str, Any]:
        rows = [
            row for row in self._read_csv("customer_segments.csv")
            if period is None or row["month"] == period
        ]
        customers = sum(int(row["customer_count"]) for row in rows)
        orders = sum(int(row["order_count"]) for row in rows)
        repeat_orders = sum(int(row["repeat_order_count"]) for row in rows)
        returning_customers = sum(
            int(row["customer_count"])
            for row in rows
            if "quay lại" in row["segment_name"].strip().lower()
        )
        return {
            "tool": "shop_data.customer_retention_summary",
            "data_scope": self.data_scope,
            "period": period or "all_available_periods",
            "customer_count": customers,
            "returning_customer_count": returning_customers,
            "order_count": orders,
            "repeat_order_count": repeat_orders,
            "repeat_order_rate_percent": round((repeat_orders / orders) * 100, 2) if orders else None,
            "limitation": "Bảng chỉ dùng số liệu tổng hợp, không lưu thông tin nhận diện cá nhân của khách hàng.",
        }

    def product_funnel_summary(self, period: str | None = None) -> dict[str, Any]:
        rows = [
            row for row in self._read_csv("product_funnel.csv")
            if period is None or row["month"] == period
        ]
        products = {row["sku"]: row["product_name"] for row in self._read_csv("products.csv")}
        funnel_rows = []
        for row in rows:
            views, carts, orders = int(row["views"]), int(row["add_to_cart_count"]), int(row["order_count"])
            funnel_rows.append({
                "sku": row["sku"],
                "product_name": products.get(row["sku"], row["sku"]),
                "views": views,
                "add_to_cart_count": carts,
                "order_count": orders,
                "view_to_cart_rate_percent": round((carts / views) * 100, 2) if views else None,
                "cart_to_order_rate_percent": round((orders / carts) * 100, 2) if carts else None,
            })
        weak_rows = [item for item in funnel_rows if item["views"] >= 20]
        weak_product = min(weak_rows, key=lambda item: (item["cart_to_order_rate_percent"] or 0, item["views"])) if weak_rows else None
        return {
            "tool": "shop_data.product_funnel_summary",
            "data_scope": self.data_scope,
            "period": period or "all_available_periods",
            "product_count": len(funnel_rows),
            "total_views": sum(item["views"] for item in funnel_rows),
            "total_add_to_cart_count": sum(item["add_to_cart_count"] for item in funnel_rows),
            "total_order_count": sum(item["order_count"] for item in funnel_rows),
            "weak_product": weak_product,
            "limitation": "Phễu chỉ nêu điểm cần kiểm tra; không chứng minh một thay đổi về ảnh, giá hay mô tả sẽ chắc chắn tăng đơn.",
        }

    def returns_summary(self, period: str | None = None) -> dict[str, Any]:
        rows = [
            row for row in self._read_csv("returns.csv")
            if period is None or row["request_date"].startswith(period)
        ]
        reasons: dict[str, int] = {}
        for row in rows:
            reasons[row["reason"]] = reasons.get(row["reason"], 0) + int(row["quantity"])
        return {
            "tool": "shop_data.returns_summary",
            "data_scope": self.data_scope,
            "period": period or "all_available_periods",
            "return_request_count": len(rows),
            "returned_unit_count": sum(int(row["quantity"]) for row in rows),
            "recorded_refund_amount_vnd": as_number(sum((as_decimal(row["refund_amount_vnd"]) for row in rows), Decimal("0"))),
            "reasons": dict(sorted(reasons.items(), key=lambda item: (-item[1], item[0]))),
        }

    def review_summary(self, period: str | None = None) -> dict[str, Any]:
        rows = [
            row for row in self._read_csv("reviews.csv")
            if period is None or row["review_date"].startswith(period)
        ]
        rating_total = sum(int(row["rating"]) for row in rows)
        issues: dict[str, int] = {}
        for row in rows:
            issue = row["issue_type"].strip() or "Không nêu vấn đề"
            issues[issue] = issues.get(issue, 0) + 1
        return {
            "tool": "shop_data.review_summary",
            "data_scope": self.data_scope,
            "period": period or "all_available_periods",
            "review_count": len(rows),
            "average_rating": round(rating_total / len(rows), 2) if rows else None,
            "low_rating_count": sum(int(row["rating"]) <= 3 for row in rows),
            "issues": dict(sorted(issues.items(), key=lambda item: (-item[1], item[0]))),
        }

    def procurement_summary(self, period: str | None = None) -> dict[str, Any]:
        rows = [
            row for row in self._read_csv("purchase_orders.csv")
            if period is None or row["order_date"].startswith(period)
        ]
        open_rows = [row for row in rows if row["status"].strip().lower() not in {"received", "cancelled"}]
        return {
            "tool": "shop_data.procurement_summary",
            "data_scope": self.data_scope,
            "period": period or "all_available_periods",
            "purchase_order_count": len(rows),
            "open_purchase_order_count": len(open_rows),
            "open_unit_count": sum(int(row["quantity"]) for row in open_rows),
            "open_purchase_value_vnd": as_number(sum((as_decimal(row["unit_cost_vnd"]) * int(row["quantity"]) for row in open_rows), Decimal("0"))),
        }

    def available_periods(self) -> list[str]:
        periods = {
            date.fromisoformat(row["order_date"]).strftime("%Y-%m")
            for row in self._read_csv("orders.csv")
        }
        return sorted(periods)

    def _read_csv(self, name: str) -> list[dict[str, str]]:
        if self._uploaded_rows is not None:
            if name in OPTIONAL_UPLOAD_FILES and name not in self._uploaded_rows:
                return []
            try:
                return self._uploaded_rows[name]
            except KeyError as exc:
                raise FileNotFoundError(
                    f"Uploaded shop data file not found: {name}"
                ) from exc

        path = self.data_dir / name
        if not path.exists():
            if name in OPTIONAL_UPLOAD_FILES:
                return []
            raise FileNotFoundError(f"Mock shop data file not found: {path}")
        with path.open("r", encoding="utf-8-sig", newline="") as file:
            return list(csv.DictReader(file))
