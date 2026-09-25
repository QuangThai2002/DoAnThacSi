from __future__ import annotations

from decimal import Decimal, InvalidOperation
from typing import Any, Mapping


def decimal_value(value: int | float | str | Decimal) -> Decimal:
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError) as exc:
        raise ValueError(f"Invalid number: {value!r}") from exc


def json_number(value: Decimal) -> int | float:
    if value == value.to_integral_value():
        return int(value)
    return float(value)


class CalculatorTool:
    """Deterministic calculations used by the agent trace."""

    def rank_costs(self, costs_vnd: Mapping[str, int | float | str]) -> dict[str, Any]:
        parsed = {name: decimal_value(value) for name, value in costs_vnd.items()}
        ranking = sorted(parsed.items(), key=lambda item: (-item[1], item[0]))
        total = sum(parsed.values(), Decimal("0"))
        return {
            "tool": "calculator.rank_costs",
            "cost_ranking": [
                {
                    "name": name,
                    "amount_vnd": json_number(amount),
                    "share_of_ranked_costs": (
                        round(float(amount / total), 4) if total else 0.0
                    ),
                }
                for name, amount in ranking
            ],
            "total_ranked_costs_vnd": json_number(total),
            "formula": "share_of_ranked_costs = cost / sum(costs)",
        }

    def percentage_of(self, part: int | float | str, whole: int | float | str) -> dict[str, Any]:
        part_decimal = decimal_value(part)
        whole_decimal = decimal_value(whole)
        if whole_decimal == 0:
            raise ValueError("Cannot divide by zero.")
        return {
            "tool": "calculator.percentage_of",
            "part": json_number(part_decimal),
            "whole": json_number(whole_decimal),
            "percentage": round(float(part_decimal / whole_decimal * Decimal("100")), 4),
            "formula": "percentage = part / whole * 100",
        }
