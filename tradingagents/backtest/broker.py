"""A simulated broker that duck-types the AlpacaBroker interface.

The point of this class is reuse: ``route_portfolio_decision`` (the live
risk-sizing/limit logic) calls exactly four broker methods — ``get_account``,
``list_positions``, ``submit_market_order``, ``close_position`` — so a
simulator implementing those runs the *real* routing code unchanged against
historical prices. Cash/buying-power are internal only (the router never reads
them).
"""

from __future__ import annotations

import datetime
import math
from dataclasses import dataclass, field

from tradingagents.backtest.prices import PriceProvider
from tradingagents.backtest.result import ClosedTrade
from tradingagents.execution.alpaca_broker import OrderResult


@dataclass
class SimClock:
    """Shared mutable clock: the engine advances ``date`` each iteration and the
    broker marks positions at whatever the current date is."""

    date: datetime.date


@dataclass
class SimPosition:
    """Duck-types an Alpaca position. The router only reads ``symbol`` and
    ``market_value``; ``shares`` is extra for the engine/reporting."""

    symbol: str
    market_value: float
    shares: float


@dataclass
class SimAccount:
    """Duck-types an Alpaca account. The router only reads ``equity``."""

    equity: float


@dataclass
class _OpenLot:
    entry_date: datetime.date
    entry_price: float
    shares: float
    last_mark: float  # last known price, so a momentarily missing bar doesn't drop the mark


@dataclass
class SimulatedBroker:
    """In-memory paper broker over :class:`PriceProvider`, marked at ``clock.date``."""

    prices: PriceProvider
    clock: SimClock
    initial_cash: float = 100_000.0
    whole_shares: bool = False

    cash: float = field(init=False)
    _lots: dict[str, _OpenLot] = field(init=False, default_factory=dict)
    closed_trades: list[ClosedTrade] = field(init=False, default_factory=list)
    _order_seq: int = field(init=False, default=0)

    def __post_init__(self):
        self.cash = float(self.initial_cash)

    # ---- price/mark helpers ----------------------------------------------

    def _mark(self, symbol: str) -> float:
        """Current price for a held symbol, falling back to its last known mark."""
        price = self.prices.asof(symbol, self.clock.date)
        if price is None:
            return self._lots[symbol].last_mark
        self._lots[symbol].last_mark = price
        return price

    def _next_order_id(self) -> str:
        self._order_seq += 1
        return f"sim-{self._order_seq}"

    # ---- Alpaca-duck-typed surface (called by route_portfolio_decision) ---

    def get_account(self) -> SimAccount:
        equity = self.cash + sum(lot.shares * self._mark(sym) for sym, lot in self._lots.items())
        return SimAccount(equity=equity)

    def list_positions(self) -> list[SimPosition]:
        return [
            SimPosition(symbol=sym, market_value=lot.shares * self._mark(sym), shares=lot.shares)
            for sym, lot in self._lots.items()
        ]

    def submit_market_order(self, symbol: str, side: str, notional: float) -> OrderResult:
        symbol = symbol.upper()
        price = self.prices.asof(symbol, self.clock.date)
        if price is None or price <= 0:
            return OrderResult(self._next_order_id(), symbol, side, notional, "rejected")

        if side == "buy":
            shares = notional / price
            if self.whole_shares:
                shares = math.floor(shares)
            if shares <= 0:
                return OrderResult(self._next_order_id(), symbol, side, notional, "rejected")
            spent = shares * price
            self.cash -= spent
            if symbol in self._lots:
                # Average into the existing lot (keeps a single open lot per symbol).
                lot = self._lots[symbol]
                total_shares = lot.shares + shares
                lot.entry_price = (lot.entry_price * lot.shares + price * shares) / total_shares
                lot.shares = total_shares
                lot.last_mark = price
            else:
                self._lots[symbol] = _OpenLot(self.clock.date, price, shares, price)
            return OrderResult(self._next_order_id(), symbol, side, spent, "filled")

        if side == "sell":
            return self.close_position(symbol)

        raise ValueError(f"side must be 'buy' or 'sell', got {side!r}")

    def close_position(self, symbol: str) -> OrderResult:
        symbol = symbol.upper()
        lot = self._lots.get(symbol)
        if lot is None:
            return OrderResult(self._next_order_id(), symbol, "sell", 0.0, "rejected")
        price = self.prices.asof(symbol, self.clock.date)
        if price is None or price <= 0:
            price = lot.last_mark
        proceeds = lot.shares * price
        self.cash += proceeds
        self._record_close(symbol, lot, price, exit_reason="sell")
        del self._lots[symbol]
        return OrderResult(self._next_order_id(), symbol, "sell", proceeds, "filled")

    # ---- engine helpers (not part of the Alpaca surface) ------------------

    def force_close(self, symbol: str, exit_reason: str) -> None:
        """Close a position tagging a specific exit reason (max_hold / eod)."""
        lot = self._lots.get(symbol.upper())
        if lot is None:
            return
        symbol = symbol.upper()
        price = self.prices.asof(symbol, self.clock.date) or lot.last_mark
        self.cash += lot.shares * price
        self._record_close(symbol, lot, price, exit_reason=exit_reason)
        del self._lots[symbol]

    def _record_close(self, symbol, lot: _OpenLot, exit_price: float, exit_reason: str) -> None:
        pnl = (exit_price - lot.entry_price) * lot.shares
        return_pct = (exit_price - lot.entry_price) / lot.entry_price if lot.entry_price else 0.0
        self.closed_trades.append(
            ClosedTrade(
                symbol=symbol,
                entry_date=lot.entry_date.isoformat(),
                exit_date=self.clock.date.isoformat(),
                entry_price=lot.entry_price,
                exit_price=exit_price,
                shares=lot.shares,
                pnl=pnl,
                return_pct=return_pct,
                holding_days=(self.clock.date - lot.entry_date).days,
                exit_reason=exit_reason,
            )
        )

    def equity(self) -> float:
        return self.get_account().equity

    def open_symbols(self) -> list[str]:
        return list(self._lots.keys())

    def holding_calendar_days(self, symbol: str, today: datetime.date) -> int:
        lot = self._lots.get(symbol.upper())
        return (today - lot.entry_date).days if lot else 0
