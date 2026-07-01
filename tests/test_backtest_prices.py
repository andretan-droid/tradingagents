"""Tests for the backtest PriceProvider (as-of lookup, trading calendar) — no network."""

from __future__ import annotations

import datetime

import pandas as pd
import pytest

from tradingagents.backtest.prices import PriceProvider


def _days(*iso):
    return [datetime.date.fromisoformat(d) for d in iso]


@pytest.fixture
def provider():
    # Mon 1/5, Tue 1/6, Thu 1/8 (Wed 1/7 intentionally missing = holiday gap)
    idx = _days("2026-01-05", "2026-01-06", "2026-01-08")
    return PriceProvider(
        {
            "AAPL": pd.Series([100.0, 102.0, 104.0], index=idx),
            "SPY": pd.Series([400.0, 401.0, 403.0], index=idx),
        },
        benchmark="SPY",
    )


@pytest.mark.unit
def test_asof_exact_day(provider):
    assert provider.asof("AAPL", datetime.date(2026, 1, 6)) == 102.0


@pytest.mark.unit
def test_asof_gap_day_uses_last_available(provider):
    # 1/7 has no bar → returns 1/6's close.
    assert provider.asof("AAPL", datetime.date(2026, 1, 7)) == 102.0


@pytest.mark.unit
def test_asof_before_first_bar_is_none(provider):
    assert provider.asof("AAPL", datetime.date(2026, 1, 1)) is None


@pytest.mark.unit
def test_asof_unknown_ticker_is_none(provider):
    assert provider.asof("ZZZZ", datetime.date(2026, 1, 6)) is None


@pytest.mark.unit
def test_trading_days_are_benchmark_sessions_in_range(provider):
    days = provider.trading_days("2026-01-05", "2026-01-08")
    assert days == _days("2026-01-05", "2026-01-06", "2026-01-08")


@pytest.mark.unit
def test_trading_days_respects_range_bounds(provider):
    assert provider.trading_days("2026-01-06", "2026-01-06") == _days("2026-01-06")


@pytest.mark.unit
def test_missing_ticker_recorded():
    idx = _days("2026-01-05")
    provider = PriceProvider(
        {"AAPL": pd.Series([100.0], index=idx), "DEAD": pd.Series(dtype="float64")},
        benchmark="AAPL",
    )
    assert provider.missing_tickers == ["DEAD"]
    assert provider.has("AAPL") is True
    assert provider.has("DEAD") is False
