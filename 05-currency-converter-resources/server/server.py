"""FastMCP server: currency converter with rates exposed as an MCP resource."""

from __future__ import annotations

import json
import logging
from functools import lru_cache
from pathlib import Path

from fastmcp import FastMCP
from fastmcp.exceptions import ToolError

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

mcp = FastMCP("currency-converter-resources")

RATES_FILE = (Path(__file__).resolve().parent / "data" / "rates.json").resolve()
RATES_URI = "currency://rates"


@lru_cache(maxsize=1)
def _load_rates_payload() -> dict:
    """Load rates from data/rates.json (backing store for the MCP resource)."""
    with RATES_FILE.open(encoding="utf-8") as handle:
        payload = json.load(handle)

    rates = payload.get("rates")
    if not isinstance(rates, dict) or not rates:
        raise ValueError(f"Invalid rates file (missing rates): {RATES_FILE}")

    normalized = {
        str(code).strip().upper(): float(value) for code, value in rates.items()
    }
    return {
        "base": str(payload.get("base", "USD")).strip().upper(),
        "note": payload.get("note", "Demo rates only; not live market data."),
        "rates": normalized,
    }


def _rates_to_usd() -> dict[str, float]:
    return _load_rates_payload()["rates"]


def _normalize_code(code: str) -> str:
    return code.strip().upper()


def _convert(amount: float, from_currency: str, to_currency: str) -> dict:
    if amount < 0:
        raise ValueError("amount must be greater than or equal to 0")

    rates = _rates_to_usd()
    source = _normalize_code(from_currency)
    target = _normalize_code(to_currency)

    if source not in rates:
        raise ValueError(
            f"Unsupported currency: {from_currency!r}. "
            f"Supported: {', '.join(sorted(rates))}"
        )
    if target not in rates:
        raise ValueError(
            f"Unsupported currency: {to_currency!r}. "
            f"Supported: {', '.join(sorted(rates))}"
        )

    amount_in_usd = amount / rates[source]
    result = amount_in_usd * rates[target]
    rate = rates[target] / rates[source]

    return {
        "amount": amount,
        "from": source,
        "to": target,
        "rate": round(rate, 6),
        "result": round(result, 4),
    }


@mcp.resource(RATES_URI, mime_type="application/json")
def exchange_rates() -> dict:
    """Fixed demo exchange rates (units of each currency per 1 USD).

    Backed by server/data/rates.json. Clients read this via resources/read.
    """
    return _load_rates_payload()


@mcp.tool()
def convert_currency(amount: float, from_currency: str, to_currency: str) -> dict:
    """Convert an amount between supported currencies using rates from currency://rates.

    Conversion goes through USD as a pivot. Supported codes come from the rates resource.
    """
    logger.info("convert_currency amount=%s from=%s to=%s", amount, from_currency, to_currency)
    try:
        return _convert(amount, from_currency, to_currency)
    except ValueError as exc:
        raise ToolError(str(exc)) from exc


@mcp.tool()
def list_rates() -> dict:
    """List supported currencies and their fixed rates relative to 1 USD.

    Same data as the currency://rates MCP resource, returned as a tool result.
    """
    payload = _load_rates_payload()
    return {
        "base": payload["base"],
        "rates": dict(sorted(payload["rates"].items())),
        "note": payload["note"],
        "resource": RATES_URI,
    }


if __name__ == "__main__":
    mcp.run()
