"""Turkish price formatting shared by the agent, reports and exports."""

from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal


def format_try(value: float | Decimal) -> str:
    """Return ``₺1.234,90`` style text (dot thousands separator, comma decimals)."""
    amount = Decimal(str(value)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    sign = "-" if amount < 0 else ""
    int_part, dec_part = f"{abs(amount):.2f}".split(".")
    grouped = f"{int(int_part):,}".replace(",", ".")
    return f"{sign}₺{grouped},{dec_part}"
