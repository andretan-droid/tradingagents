"""Thin wrapper around Alpaca's paper-trading API (alpaca-py).

This module only ever talks to Alpaca's paper-trading endpoint
(``TradingClient(..., paper=True)``) — there is intentionally no live-trading
path here. alpaca-py is an optional dependency (the ``[alpaca]`` extra) so it
is imported lazily and only required when this module is actually used.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any

_TRADING_CLIENT_CLASS = None


class AlpacaNotConfigured(RuntimeError):
    """Raised when ALPACA_API_KEY / ALPACA_SECRET_KEY are missing."""


def _trading_client_class():
    """Lazily import alpaca-py and return the ``TradingClient`` class.

    Imported on demand so the optional dependency isn't required by the rest
    of the package; cached after the first call.
    """
    global _TRADING_CLIENT_CLASS
    if _TRADING_CLIENT_CLASS is not None:
        return _TRADING_CLIENT_CLASS

    try:
        from alpaca.trading.client import TradingClient
    except ImportError as exc:
        raise ImportError(
            "Alpaca paper-trading support requires the optional 'alpaca-py' "
            'dependency. Install it with: pip install "tradingagents[alpaca]"'
        ) from exc

    _TRADING_CLIENT_CLASS = TradingClient
    return _TRADING_CLIENT_CLASS


@dataclass
class OrderResult:
    """Result of a submitted paper order, normalized across alpaca-py versions."""

    order_id: str
    symbol: str
    side: str
    notional: float
    status: str


class AlpacaBroker:
    """Paper-trading-only client for Alpaca's Trading API.

    Credentials come from ``ALPACA_API_KEY`` / ``ALPACA_SECRET_KEY`` unless
    passed explicitly. Raises :class:`AlpacaNotConfigured` at construction
    time if neither is available, so a misconfigured run fails fast instead
    of silently skipping every order.
    """

    def __init__(self, api_key: str | None = None, secret_key: str | None = None):
        api_key = api_key or os.environ.get("ALPACA_API_KEY")
        secret_key = secret_key or os.environ.get("ALPACA_SECRET_KEY")
        if not api_key or not secret_key:
            raise AlpacaNotConfigured(
                "ALPACA_API_KEY and ALPACA_SECRET_KEY must be set to use the "
                "Alpaca paper-trading broker."
            )

        trading_client_cls = _trading_client_class()
        self._client = trading_client_cls(api_key, secret_key, paper=True)

    def submit_market_order(self, symbol: str, side: str, notional: float) -> OrderResult:
        """Submit a paper market order sized by notional (dollar) amount.

        ``side`` must be ``"buy"`` or ``"sell"``.
        """
        from alpaca.trading.enums import OrderSide, TimeInForce
        from alpaca.trading.requests import MarketOrderRequest

        if side not in ("buy", "sell"):
            raise ValueError(f"side must be 'buy' or 'sell', got {side!r}")

        request = MarketOrderRequest(
            symbol=symbol,
            notional=round(notional, 2),
            side=OrderSide.BUY if side == "buy" else OrderSide.SELL,
            time_in_force=TimeInForce.DAY,
        )
        order = self._client.submit_order(order_data=request)
        return OrderResult(
            order_id=str(order.id),
            symbol=order.symbol,
            side=str(order.side.value if hasattr(order.side, "value") else order.side),
            notional=notional,
            status=str(order.status.value if hasattr(order.status, "value") else order.status),
        )

    def close_position(self, symbol: str) -> OrderResult:
        """Fully liquidate an existing position with a market order."""
        order = self._client.close_position(symbol)
        return OrderResult(
            order_id=str(order.id),
            symbol=order.symbol,
            side=str(order.side.value if hasattr(order.side, "value") else order.side),
            notional=float(order.notional) if order.notional else 0.0,
            status=str(order.status.value if hasattr(order.status, "value") else order.status),
        )

    def get_account(self) -> Any:
        """Return the paper account (equity, cash, buying power, ...)."""
        return self._client.get_account()

    def list_positions(self) -> list:
        """Return all open positions in the paper account."""
        return self._client.get_all_positions()

    def list_recent_orders(self, limit: int = 20) -> list:
        """Return the most recent orders (any status), newest first."""
        from alpaca.trading.enums import QueryOrderStatus
        from alpaca.trading.requests import GetOrdersRequest

        request = GetOrdersRequest(status=QueryOrderStatus.ALL, limit=limit)
        return self._client.get_orders(filter=request)
