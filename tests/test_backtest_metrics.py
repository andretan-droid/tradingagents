"""Tests for backtest metrics with hand-computable fixtures — pure, no deps."""

from __future__ import annotations

from dataclasses import dataclass

import pytest

from tradingagents.backtest import metrics


@dataclass
class _Trade:
    pnl: float
    holding_days: int


@pytest.mark.unit
def test_total_return():
    assert metrics.total_return([100, 110, 121]) == pytest.approx(0.21)


@pytest.mark.unit
def test_total_return_empty_or_single_point_is_zero():
    assert metrics.total_return([]) == 0.0
    assert metrics.total_return([100]) == 0.0


@pytest.mark.unit
def test_max_drawdown():
    # peak 120 -> trough 90 = -25%
    assert metrics.max_drawdown([100, 120, 90, 110]) == pytest.approx(-0.25)


@pytest.mark.unit
def test_max_drawdown_monotonic_up_is_zero():
    assert metrics.max_drawdown([100, 110, 120]) == 0.0


@pytest.mark.unit
def test_daily_returns_from_curve():
    assert metrics.daily_returns_from_curve([100, 110, 99]) == pytest.approx([0.1, -0.1])


@pytest.mark.unit
def test_sharpe_zero_volatility_is_zero():
    # constant returns -> zero std -> guarded to 0.0 (no div-by-zero)
    assert metrics.sharpe([0.01, 0.01, 0.01]) == 0.0


@pytest.mark.unit
def test_sharpe_positive_for_positive_mean_returns():
    s = metrics.sharpe([0.01, 0.02, -0.005, 0.015])
    assert s > 0


@pytest.mark.unit
def test_win_rate():
    trades = [_Trade(10, 1), _Trade(-5, 1), _Trade(20, 1), _Trade(-2, 1)]
    assert metrics.win_rate(trades) == 0.5


@pytest.mark.unit
def test_win_rate_no_trades_is_zero():
    assert metrics.win_rate([]) == 0.0


@pytest.mark.unit
def test_avg_holding_days():
    assert metrics.avg_holding_days([_Trade(1, 4), _Trade(1, 6)]) == 5.0


@pytest.mark.unit
def test_compute_metrics_alpha_is_strategy_minus_benchmark():
    m = metrics.compute_metrics(
        equity_curve=[100, 110],       # +10%
        closed_trades=[_Trade(10, 3)],
        benchmark_curve=[100, 104],    # +4%
    )
    assert m["total_return"] == pytest.approx(0.10)
    assert m["benchmark_return"] == pytest.approx(0.04)
    assert m["alpha"] == pytest.approx(0.06)
    assert m["num_trades"] == 1
