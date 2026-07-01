"""Latest-price lookup for executing paper trades.

Reuses the same symbol normalization and rate-limit retry the rest of the
framework's Yahoo Finance vendor uses, so a ticker like ``D05.SI`` or
``1155.KL`` resolves exactly the same way here as it does inside the
Market Analyst's tools.
"""

from __future__ import annotations

import yfinance as yf

from tradingagents.dataflows.stockstats_utils import yf_retry
from tradingagents.dataflows.symbol_utils import NoMarketDataError, normalize_symbol


def get_latest_price(ticker: str) -> float:
    """Return the most recent close price for ``ticker``.

    Raises ``NoMarketDataError`` if Yahoo Finance has no recent data for the
    symbol (delisted, mistyped, or an unsupported exchange).
    """
    canonical = normalize_symbol(ticker)
    data = yf_retry(lambda: yf.Ticker(canonical).history(period="5d"))
    if data.empty:
        raise NoMarketDataError(ticker, canonical, "no rows in the last 5 days")
    return round(float(data["Close"].iloc[-1]), 4)
