"""Paper-money portfolio ledger.

Tracks cash, share positions, a trade history, and a NAV (net asset value)
history as plain JSON on disk, so it round-trips cleanly across process
runs (including across GitHub Actions jobs, which start from a clean
checkout every time). No real brokerage is involved anywhere here.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path


@dataclass
class Position:
    shares: float
    avg_cost: float


@dataclass
class Trade:
    date: str
    ticker: str
    rating: str
    action: str  # "BUY" or "SELL"
    shares: float
    price: float
    amount: float  # cash value of the trade, always positive
    cash_after: float


# Ratings that grow a position vs. ratings that shrink/exit one. "Hold" is
# intentionally absent from both -- it is a no-op.
_BUY_RATINGS = {"Buy", "Overweight"}
_SELL_RATINGS = {"Underweight", "Sell"}


@dataclass
class Portfolio:
    cash: float
    starting_cash: float
    positions: dict[str, Position] = field(default_factory=dict)
    trade_history: list[Trade] = field(default_factory=list)
    nav_history: list[dict] = field(default_factory=list)

    @classmethod
    def new(cls, starting_cash: float) -> Portfolio:
        return cls(cash=starting_cash, starting_cash=starting_cash)

    @classmethod
    def load_or_new(cls, path: str | Path, starting_cash: float) -> Portfolio:
        path = Path(path)
        if not path.exists():
            return cls.new(starting_cash)
        raw = json.loads(path.read_text(encoding="utf-8"))
        positions = {
            ticker: Position(**pos) for ticker, pos in raw.get("positions", {}).items()
        }
        trade_history = [Trade(**t) for t in raw.get("trade_history", [])]
        return cls(
            cash=raw["cash"],
            starting_cash=raw.get("starting_cash", starting_cash),
            positions=positions,
            trade_history=trade_history,
            nav_history=raw.get("nav_history", []),
        )

    def save(self, path: str | Path) -> None:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "cash": self.cash,
            "starting_cash": self.starting_cash,
            "positions": {
                ticker: asdict(pos) for ticker, pos in self.positions.items()
            },
            "trade_history": [asdict(t) for t in self.trade_history],
            "nav_history": self.nav_history,
        }
        path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    def positions_value(self, prices: dict[str, float]) -> float:
        return sum(
            pos.shares * prices[ticker]
            for ticker, pos in self.positions.items()
            if ticker in prices
        )

    def nav(self, prices: dict[str, float]) -> float:
        return self.cash + self.positions_value(prices)

    def apply_rating(
        self,
        ticker: str,
        rating: str,
        price: float,
        date: str,
        settings: dict,
        current_nav: float,
    ) -> Trade | None:
        """Execute the position-sizing policy for one ticker's rating.

        ``current_nav`` is the portfolio NAV *before* this trade, used as the
        base for Buy/Overweight sizing so allocations scale with portfolio
        growth rather than the original starting cash. Returns the executed
        ``Trade``, or ``None`` if the rating produced no trade (Hold, or a
        Sell/Underweight on a ticker with no position).
        """
        if price <= 0:
            raise ValueError(f"price must be positive, got {price!r} for {ticker}")

        commission = settings.get("commission", 0.0)
        position = self.positions.get(ticker)

        if rating in _BUY_RATINGS:
            pct = settings["buy_pct"] if rating == "Buy" else settings["overweight_pct"]
            budget = min(current_nav * pct, self.cash - commission)
            if budget <= 0:
                return None
            shares = round(budget / price, 4)
            if shares <= 0:
                return None
            cost = shares * price
            self.cash -= cost + commission
            if position is None:
                self.positions[ticker] = Position(shares=shares, avg_cost=price)
            else:
                total_shares = position.shares + shares
                position.avg_cost = (
                    position.avg_cost * position.shares + cost
                ) / total_shares
                position.shares = total_shares
            trade = Trade(
                date=date,
                ticker=ticker,
                rating=rating,
                action="BUY",
                shares=shares,
                price=price,
                amount=round(cost, 2),
                cash_after=round(self.cash, 2),
            )
            self.trade_history.append(trade)
            return trade

        if rating in _SELL_RATINGS:
            if position is None or position.shares <= 0:
                return None
            sell_fraction = 1.0 if rating == "Sell" else settings["underweight_sell_pct"]
            shares = round(position.shares * sell_fraction, 4)
            if shares <= 0:
                return None
            proceeds = shares * price
            self.cash += proceeds - commission
            position.shares = round(position.shares - shares, 4)
            if position.shares <= 0:
                del self.positions[ticker]
            trade = Trade(
                date=date,
                ticker=ticker,
                rating=rating,
                action="SELL",
                shares=shares,
                price=price,
                amount=round(proceeds, 2),
                cash_after=round(self.cash, 2),
            )
            self.trade_history.append(trade)
            return trade

        # Hold, or an unrecognized rating: no trade.
        return None

    def mark_to_market(self, prices: dict[str, float], date: str) -> dict:
        """Append (and return) today's NAV snapshot."""
        positions_value = self.positions_value(prices)
        snapshot = {
            "date": date,
            "cash": round(self.cash, 2),
            "positions_value": round(positions_value, 2),
            "nav": round(self.cash + positions_value, 2),
        }
        self.nav_history.append(snapshot)
        return snapshot
