"""Translate a Portfolio Manager rating into a paper broker order.

Wired into ``TradingAgentsGraph`` behind the ``broker_enabled`` config flag
(default off), so existing users see no behavior change unless they opt in.
Pure rating->side mapping lives here, decoupled from the broker client, so it
can be unit-tested without alpaca-py installed.
"""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)

# Buy / Overweight both express "add exposure"; Sell / Underweight both
# express "reduce exposure". Hold and anything unrecognised is a no-op —
# the 5-tier scale is defined in tradingagents.agents.utils.rating.
_BUY_RATINGS = {"buy", "overweight"}
_SELL_RATINGS = {"sell", "underweight"}


def rating_to_side(rating: str) -> str | None:
    """Return ``"buy"``, ``"sell"``, or ``None`` (Hold / unrecognised) for a rating."""
    normalized = rating.strip().lower()
    if normalized in _BUY_RATINGS:
        return "buy"
    if normalized in _SELL_RATINGS:
        return "sell"
    return None


def route_decision(broker, symbol: str, rating: str, notional_usd: float):
    """Submit a paper order for ``rating`` if it maps to Buy or Sell.

    Returns the broker's ``OrderResult`` on submission, or ``None`` if the
    rating is Hold (or unrecognised) and no order was placed.
    """
    side = rating_to_side(rating)
    if side is None:
        logger.info("Rating %r for %s maps to no action; skipping paper order.", rating, symbol)
        return None

    logger.info(
        "Submitting %s paper order for %s ($%.2f notional)", side, symbol, notional_usd
    )
    return broker.submit_market_order(symbol=symbol, side=side, notional=notional_usd)
