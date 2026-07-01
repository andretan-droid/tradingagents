"""End-to-end backtest engine tests with a stub price provider — no network/LLM.

Crucially these exercise the REAL route_portfolio_decision through the
SimulatedBroker, so the risk limits are proven to fire in-sim.
"""

from __future__ import annotations

import datetime

import pandas as pd
import pytest

from tradingagents.backtest.decisions import DecisionEvent
from tradingagents.backtest.engine import BacktestConfig, run_backtest
from tradingagents.backtest.prices import PriceProvider
from tradingagents.execution.portfolio_router import RiskLimits


def _biz_days(start, n):
    days, cur = [], datetime.date.fromisoformat(start)
    while len(days) < n:
        if cur.weekday() < 5:
            days.append(cur)
        cur += datetime.timedelta(days=1)
    return days


def _provider(price_map, benchmark="SPY"):
    return PriceProvider({t: pd.Series(v, index=list(v.index)) for t, v in price_map.items()},
                         benchmark=benchmark)


@pytest.fixture
def rising_prices():
    days = _biz_days("2026-01-05", 6)
    aapl = pd.Series([100, 102, 104, 106, 108, 110], index=days)
    msft = pd.Series([200, 201, 202, 203, 204, 205], index=days)
    spy = pd.Series([400, 400, 400, 400, 400, 400], index=days)
    return days, _provider({"AAPL": aapl, "MSFT": msft, "SPY": spy})


@pytest.mark.unit
def test_buy_then_sell_produces_one_closed_trade(rising_prices):
    days, prices = rising_prices
    decisions = [
        DecisionEvent(days[0], "AAPL", "Buy"),
        DecisionEvent(days[3], "AAPL", "Sell"),
    ]
    cfg = BacktestConfig(
        decisions=decisions, start_date=days[0].isoformat(), end_date=days[-1].isoformat(),
        benchmark="SPY", initial_cash=100_000.0,
        limits=RiskLimits(0.5, 15, 1.0), prices=prices,
    )
    result = run_backtest(cfg)

    assert len(result.closed_trades) == 1
    trade = result.closed_trades[0]
    assert trade.symbol == "AAPL"
    # 500 shares (50k / 100) sold at 106 -> pnl (106-100)*500 = 3000
    assert trade.pnl == pytest.approx(3_000.0)
    assert result.metrics["total_return"] == pytest.approx(0.03)


@pytest.mark.unit
def test_max_open_positions_limit_fires_in_sim(rising_prices):
    days, prices = rising_prices
    # Two buys same day, but cap = 1 open position -> only the first fills.
    decisions = [
        DecisionEvent(days[0], "AAPL", "Buy"),
        DecisionEvent(days[0], "MSFT", "Buy"),
    ]
    cfg = BacktestConfig(
        decisions=decisions, start_date=days[0].isoformat(), end_date=days[-1].isoformat(),
        benchmark="SPY", initial_cash=100_000.0,
        limits=RiskLimits(0.1, 1, 1.0), prices=prices,  # max_open_positions=1
    )
    result = run_backtest(cfg)
    # exactly one position was opened (then closed at eod) -> one closed trade
    assert result.metrics["num_trades"] == 1


@pytest.mark.unit
def test_max_holding_days_force_closes(rising_prices):
    days, prices = rising_prices
    decisions = [DecisionEvent(days[0], "AAPL", "Buy")]  # never sold explicitly
    cfg = BacktestConfig(
        decisions=decisions, start_date=days[0].isoformat(), end_date=days[-1].isoformat(),
        benchmark="SPY", initial_cash=100_000.0,
        limits=RiskLimits(0.5, 15, 1.0), max_holding_days=2, prices=prices,
    )
    result = run_backtest(cfg)

    assert len(result.closed_trades) == 1
    assert result.closed_trades[0].exit_reason == "max_hold"


@pytest.mark.unit
def test_explicit_sell_wins_over_max_hold_same_day(rising_prices):
    days, prices = rising_prices
    # Sell lands exactly when the max-hold sweep would also trigger; must not double-close.
    decisions = [
        DecisionEvent(days[0], "AAPL", "Buy"),
        DecisionEvent(days[2], "AAPL", "Sell"),
    ]
    cfg = BacktestConfig(
        decisions=decisions, start_date=days[0].isoformat(), end_date=days[-1].isoformat(),
        benchmark="SPY", initial_cash=100_000.0,
        limits=RiskLimits(0.5, 15, 1.0),
        max_holding_days=2,  # days[0] -> days[2] is 2 calendar-ish days
        prices=prices,
    )
    result = run_backtest(cfg)

    assert len(result.closed_trades) == 1
    assert result.closed_trades[0].exit_reason == "sell"


@pytest.mark.unit
def test_missing_price_ticker_is_skipped(rising_prices):
    days, prices = rising_prices
    decisions = [DecisionEvent(days[0], "NOPRICE", "Buy")]
    cfg = BacktestConfig(
        decisions=decisions, start_date=days[0].isoformat(), end_date=days[-1].isoformat(),
        benchmark="SPY", initial_cash=100_000.0, prices=prices,
    )
    result = run_backtest(cfg)

    assert result.metrics["num_trades"] == 0
    assert any(s["reason"] == "no_price" for s in result.skipped)


@pytest.mark.unit
def test_decision_on_weekend_rolls_to_next_session(rising_prices):
    days, prices = rising_prices
    saturday = datetime.date(2026, 1, 3)  # before the first session (Mon 1/5)
    decisions = [DecisionEvent(saturday, "AAPL", "Buy")]
    cfg = BacktestConfig(
        decisions=decisions, start_date=days[0].isoformat(), end_date=days[-1].isoformat(),
        benchmark="SPY", initial_cash=100_000.0,
        limits=RiskLimits(0.5, 15, 1.0), prices=prices,
    )
    result = run_backtest(cfg)
    # The Saturday buy executes on the first session and is closed at eod -> 1 trade.
    assert result.metrics["num_trades"] == 1
    assert result.closed_trades[0].entry_date == days[0].isoformat()


@pytest.mark.unit
def test_no_trading_days_raises(rising_prices):
    _, prices = rising_prices
    cfg = BacktestConfig(
        decisions=[], start_date="2030-01-01", end_date="2030-01-02",
        benchmark="SPY", prices=prices,
    )
    with pytest.raises(ValueError, match="trading sessions"):
        run_backtest(cfg)
