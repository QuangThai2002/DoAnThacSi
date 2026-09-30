from __future__ import annotations

import csv
import io
import re
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any, Mapping


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
}
REQUIRED_UPLOAD_FILES = frozenset({"orders.csv", "products.csv", "inventory.csv"})
OPTIONAL_UPLOAD_FILES = frozenset({"ads.csv", "purchase_orders.csv", "returns.csv", "reviews.csv"})
MAX_UPLOADED_CSV_BYTES = 10 * 1024 * 1024


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
        """Build a per-session tool after validating the required CSV schema."""
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
            rows_by_name[name] = cls._parse_uploaded_csv(name, raw_content)
        return cls(uploaded_rows=rows_by_name)

    @classmethod
    def _parse_uploaded_csv(
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

        try:
            text = raw_content.decode("utf-8-sig")
        except UnicodeDecodeError as exc:
            raise ShopDataValidationError(
                f"{name} phải được lưu theo mã hóa UTF-8."
            ) from exc

        reader = csv.DictReader(io.StringIO(text))
        headers = [str(header).strip() for header in (reader.fieldnames or []) if header]
        missing_columns = sorted(REQUIRED_UPLOAD_COLUMNS[name] - set(headers))
        if missing_columns:
            raise ShopDataValidationError(
                f"{name} thiếu cột: " + ", ".join(missing_columns)
            )
        reader.fieldnames = headers

        rows = [
            {
                str(key).strip(): str(value or "").strip()
                for key, value in row.items()
                if key is not None
            }
            for row in reader
        ]
        if not rows:
            raise ShopDataValidationError(f"{name} chưa có dòng dữ liệu.")

        date_column = {
            "orders.csv": "order_date",
            "inventory.csv": "last_updated",
            "purchase_orders.csv": "order_date",
            "returns.csv": "request_date",
            "reviews.csv": "review_date",
        }.get(name)
        if date_column:
            for row in rows:
                try:
                    row[date_column] = normalize_date(row[date_column])
                except ValueError:
                    # Keep the original value so the existing validation below can
                    # report a consistent Vietnamese error with its row number.
                    pass

        if name == "ads.csv":
            for row in rows:
                try:
                    row["month"] = normalize_month(row["month"])
                except ValueError:
                    pass

        cls._validate_uploaded_rows(name, rows)
        return rows

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
