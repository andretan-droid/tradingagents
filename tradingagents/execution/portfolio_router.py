"""Portfolio-aware paper order routing: position sizing and risk limits.

``order_router.route_decision`` (used by ``TradingAgentsGraph``'s built-in
execution hook) submits a fixed-dollar order per decision with no memory of
what's already held. This module is the richer alternative used by the
watchlist/screener automation pipeline (``scripts/auto_trader.py``): it
looks at the live Alpaca account before every order and applies three rules
(moderate risk profile by default):

- Buy only if not already holding the ticker, and only if under the open
  position cap and the sector exposure cap.
- Sell (fully close the position) only if a position is actually held.
- Position size is a fixed percentage of current account equity, not a
  fixed dollar amount, so sizing scales with how the paper account is doing.

Sector exposure is computed from ``tradingagents.discovery.sp500_universe``
so it only applies to tickers within the known sector universe; a ticker
outside that universe skips the sector-cap check (logged) but still respects
the position-count cap and the "don't buy what you already hold" rule.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

from tradingagents.discovery.sp500_universe import ticker_to_sector
from tradingagents.execution.order_router import rating_to_side

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class RiskLimits:
    """Moderate risk profile (the default): ~5% of equity per position, up to
    15 open positions, no more than ~35% of equity in one sector."""

    position_pct_per_trade: float = 0.05
    max_open_positions: int = 15
    max_sector_pct: float = 0.35


def _position_by_symbol(positions: list) -> dict[str, object]:
    return {p.symbol.upper(): p for p in positions}


def _sector_market_value(positions: list, sector: str) -> float:
    total = 0.0
    for p in positions:
        if ticker_to_sector(p.symbol) == sector:
            total += float(p.market_value)
    return total


def route_portfolio_decision(
    broker,
    ticker: str,
    rating: str,
    limits: RiskLimits | None = None,
):
    """Apply risk limits and submit a paper order for ``rating``, if any.

    Returns the broker's ``OrderResult``, or ``None`` if no order was placed
    (Hold rating, or a risk limit blocked it) — in which case the skip
    reason is logged.
    """
    limits = limits or RiskLimits()
    side = rating_to_side(rating)
    if side is None:
        logger.info("Rating %r for %s maps to no action; skipping.", rating, ticker)
        return None

    positions = broker.list_positions()
    by_symbol = _position_by_symbol(positions)
    already_held = ticker.upper() in by_symbol

    if side == "sell":
        if not already_held:
            logger.info("Sell signal for %s but no open position; skipping.", ticker)
            return None
        logger.info("Closing position in %s", ticker)
        return broker.close_position(ticker)

    # side == "buy"
    if already_held:
        logger.info("Buy signal for %s but already holding a position; skipping.", ticker)
        return None

    if len(positions) >= limits.max_open_positions:
        logger.info(
            "Buy signal for %s but at max open positions (%d); skipping.",
            ticker, limits.max_open_positions,
        )
        return None

    account = broker.get_account()
    equity = float(account.equity)
    order_notional = equity * limits.position_pct_per_trade

    sector = ticker_to_sector(ticker)
    if sector is not None:
        sector_value = _sector_market_value(positions, sector)
        sector_cap = equity * limits.max_sector_pct
        if sector_value + order_notional > sector_cap:
            logger.info(
                "Buy signal for %s (%s) would breach sector cap "
                "(current $%.2f + order $%.2f > cap $%.2f); skipping.",
                ticker, sector, sector_value, order_notional, sector_cap,
            )
            return None
    else:
        logger.info("Sector unknown for %s; skipping sector-cap check.", ticker)

    logger.info("Submitting buy for %s: $%.2f (%.1f%% of equity)",
                ticker, order_notional, limits.position_pct_per_trade * 100)
    return broker.submit_market_order(symbol=ticker, side="buy", notional=order_notional)
