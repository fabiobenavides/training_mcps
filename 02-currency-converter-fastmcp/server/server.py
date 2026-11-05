"""FastMCP server: currency converter with fixed demo exchange rates."""

from __future__ import annotations

import logging

from fastmcp import FastMCP
from fastmcp.exceptions import ToolError

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

mcp = FastMCP("currency-converter-fastmcp")

# Units of each currency per 1 USD (demo rates, not live market data).
RATES_TO_USD: dict[str, float] = {
    "USD": 1.0,
    "EUR": 0.92,
    "MXN": 17.2,
    "COP": 4100.0,
}


def _normalize_code(code: str) -> str:
    return code.strip().upper()


def _convert(amount: float, from_currency: str, to_currency: str) -> dict:
    if amount < 0:
        raise ValueError("amount must be greater than or equal to 0")

    source = _normalize_code(from_currency)
    target = _normalize_code(to_currency)

    if source not in RATES_TO_USD:
        raise ValueError(
            f"Unsupported currency: {from_currency!r}. "
            f"Supported: {', '.join(sorted(RATES_TO_USD))}"
        )
    if target not in RATES_TO_USD:
        raise ValueError(
            f"Unsupported currency: {to_currency!r}. "
            f"Supported: {', '.join(sorted(RATES_TO_USD))}"
        )

    amount_in_usd = amount / RATES_TO_USD[source]
    result = amount_in_usd * RATES_TO_USD[target]
    rate = RATES_TO_USD[target] / RATES_TO_USD[source]

    return {
        "amount": amount,
        "from": source,
        "to": target,
        "rate": round(rate, 6),
        "result": round(result, 4),
    }


@mcp.tool()
def convert_currency(amount: float, from_currency: str, to_currency: str) -> dict:
    """Convert an amount between supported currencies using fixed demo rates.

    Supported currencies: USD, EUR, MXN, COP. Conversion goes through USD as a pivot.
    """
    logger.info("convert_currency amount=%s from=%s to=%s", amount, from_currency, to_currency)
    try:
        return _convert(amount, from_currency, to_currency)
    except ValueError as exc:
        raise ToolError(str(exc)) from exc


@mcp.tool()
def list_rates() -> dict:
    """List supported currencies and their fixed rates relative to 1 USD."""
    return {
        "base": "USD",
        "rates": dict(sorted(RATES_TO_USD.items())),
        "note": "Demo rates only; not live market data.",
    }


if __name__ == "__main__":
    mcp.run()
