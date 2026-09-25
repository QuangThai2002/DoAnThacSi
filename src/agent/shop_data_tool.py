from __future__ import annotations

import csv
from datetime import date
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DATA_DIR = PROJECT_ROOT / "data" / "shop_mock"
COMPLETED_STATUS = "completed"


def as_decimal(value: str | int | float | Decimal) -> Decimal:
    try:
        return Decimal(str(value or "0"))
    except (InvalidOperation, ValueError) as exc:
        raise ValueError(f"Invalid monetary value: {value!r}") from exc


def as_number(value: Decimal) -> int | float:
    if value == value.to_integral_value():
        return int(value)
    return float(value)


class ShopDataTool:
    """Read-only analytics over intentionally disclosed mock shop data.

    Every result carries a `data_scope` marker. This prevents the demo from
    implying that the program has access to an actual Shopee seller account.
    """

    def __init__(self, data_dir: Path = DEFAULT_DATA_DIR) -> None:
        self.data_dir = data_dir

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
            "data_scope": "mock_shop_data",
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
            "data_scope": "mock_shop_data",
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
            "data_scope": "mock_shop_data",
            "period": period or "all_available_periods",
            "campaign_count": len(rows),
            "ad_spend_vnd": as_number(spend),
            "attributed_revenue_vnd": as_number(revenue),
            "attributed_order_count": orders,
            "roas": round(float(roas), 4),
            "formula": "ROAS = attributed_revenue / ad_spend",
        }

    def available_periods(self) -> list[str]:
        periods = {
            date.fromisoformat(row["order_date"]).strftime("%Y-%m")
            for row in self._read_csv("orders.csv")
        }
        return sorted(periods)

    def _read_csv(self, name: str) -> list[dict[str, str]]:
        path = self.data_dir / name
        if not path.exists():
            raise FileNotFoundError(f"Mock shop data file not found: {path}")
        with path.open("r", encoding="utf-8-sig", newline="") as file:
            return list(csv.DictReader(file))
