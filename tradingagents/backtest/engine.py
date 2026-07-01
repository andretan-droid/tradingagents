"""The backtest event loop: replay decisions through a simulated portfolio.

This is the only module that imports the live ``route_portfolio_decision`` — the
whole design goal is that the same risk-sizing/limit code runs here against a
:class:`SimulatedBroker` as runs live against Alpaca.
"""

from __future__ import annotations

import datetime
import logging
from collections import defaultdict
from dataclasses import dataclass, field

from tradingagents.backtest.broker import SimClock, SimulatedBroker
from tradingagents.backtest.decisions import DecisionEvent
from tradingagents.backtest.metrics import compute_metrics
from tradingagents.backtest.prices import PriceProvider
from tradingagents.backtest.result import BacktestResult
from tradingagents.execution.order_router import rating_to_side
from tradingagents.execution.portfolio_router import RiskLimits, route_portfolio_decision

logger = logging.getLogger(__name__)


@dataclass
class BacktestConfig:
    """Everything ``run_backtest`` needs. ``decisions`` is a pre-fetched list so
    the (possibly expensive) decision source runs once, before the engine."""

    decisions: list[DecisionEvent]
    start_date: str
    end_date: str
    benchmark: str = "SPY"
    initial_cash: float = 100_000.0
    limits: RiskLimits = field(default_factory=RiskLimits)
    max_holding_days: int | None = None
    whole_shares: bool = False
    risk_free_rate: float = 0.0
    results_dir: str | None = None
    prices: PriceProvider | None = None  # injectable for tests; else fetched


def _next_session_on_or_after(day: datetime.date, sessions: list[datetime.date]) -> datetime.date | None:
    """Roll a decision date forward to the next trading session (no look-ahead)."""
    for session in sessions:
        if session >= day:
            return session
    return None


def run_backtest(cfg: BacktestConfig) -> BacktestResult:
    tickers = sorted({e.ticker for e in cfg.decisions})

    prices = cfg.prices or PriceProvider.fetch(
        tickers, cfg.start_date, cfg.end_date, benchmark=cfg.benchmark
    )
    days = prices.trading_days(cfg.start_date, cfg.end_date)
    if not days:
        raise ValueError(
            f"No benchmark ({cfg.benchmark}) trading sessions between "
            f"{cfg.start_date} and {cfg.end_date}; cannot run backtest."
        )

    # Bucket each decision onto the next session on/after its date.
    events_by_day: dict[datetime.date, list[DecisionEvent]] = defaultdict(list)
    skipped: list[dict] = []
    for e in cfg.decisions:
        session = _next_session_on_or_after(e.date, days)
        if session is None:
            skipped.append({"date": e.date.isoformat(), "ticker": e.ticker,
                            "rating": e.rating, "reason": "after_range"})
            continue
        events_by_day[session].append(e)

    clock = SimClock(days[0])
    broker = SimulatedBroker(prices, clock, cfg.initial_cash, cfg.whole_shares)

    b0 = prices.asof(cfg.benchmark, days[0])
    if not b0:
        raise ValueError(f"No benchmark price for {cfg.benchmark} on {days[0]}.")
    bench_shares = cfg.initial_cash / b0

    equity_curve, benchmark_curve, iso_dates = [], [], []

    for day in days:
        clock.date = day
        day_events = events_by_day.get(day, [])

        # 1. Optional N-day holding-period exit — but never double-close a ticker
        #    that has an explicit Sell queued for today.
        if cfg.max_holding_days is not None:
            sells_today = {
                e.ticker.upper() for e in day_events if rating_to_side(e.rating) == "sell"
            }
            for sym in broker.open_symbols():
                if sym.upper() in sells_today:
                    continue
                if broker.holding_calendar_days(sym, day) >= cfg.max_holding_days:
                    broker.force_close(sym, exit_reason="max_hold")

        # 2. Apply the day's decisions through the REAL router. Sort sells before
        #    buys so a sell frees cash / a position slot for a same-day buy.
        for e in sorted(day_events, key=lambda ev: rating_to_side(ev.rating) != "sell"):
            if prices.asof(e.ticker, day) is None:
                skipped.append({"date": day.isoformat(), "ticker": e.ticker,
                                "rating": e.rating, "reason": "no_price"})
                continue
            route_portfolio_decision(broker, e.ticker, e.rating, limits=cfg.limits)

        # 3. Mark-to-market.
        equity_curve.append(broker.equity())
        benchmark_curve.append(bench_shares * prices.asof(cfg.benchmark, day))
        iso_dates.append(day.isoformat())

    # Close everything still open at the final session so all trades are realized.
    clock.date = days[-1]
    for sym in broker.open_symbols():
        broker.force_close(sym, exit_reason="eod")

    metrics = compute_metrics(
        equity_curve, broker.closed_trades, benchmark_curve, cfg.risk_free_rate
    )

    return BacktestResult(
        config={
            "start_date": cfg.start_date,
            "end_date": cfg.end_date,
            "benchmark": cfg.benchmark,
            "initial_cash": cfg.initial_cash,
            "max_holding_days": cfg.max_holding_days,
            "whole_shares": cfg.whole_shares,
            "risk_free_rate": cfg.risk_free_rate,
            "limits": {
                "position_pct_per_trade": cfg.limits.position_pct_per_trade,
                "max_open_positions": cfg.limits.max_open_positions,
                "max_sector_pct": cfg.limits.max_sector_pct,
            },
            "num_decisions": len(cfg.decisions),
            "missing_tickers": prices.missing_tickers,
        },
        dates=iso_dates,
        equity_curve=equity_curve,
        benchmark_curve=benchmark_curve,
        closed_trades=broker.closed_trades,
        open_positions=[],
        skipped=skipped,
        metrics=metrics,
    )
