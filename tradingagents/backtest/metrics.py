"""Pure performance-metric functions over an equity curve and a trade log.

No pandas/numpy dependency for the core math (keeps it trivially testable with
hand-computable fixtures). All functions degrade to 0.0 on empty / degenerate
input rather than raising, so a backtest that placed no trades still reports.
"""

from __future__ import annotations

from collections.abc import Sequence

_TRADING_DAYS_PER_YEAR = 252


def daily_returns_from_curve(equity_curve: Sequence[float]) -> list[float]:
    """Simple day-over-day returns; length is len(curve) - 1."""
    out = []
    for prev, cur in zip(equity_curve, equity_curve[1:], strict=False):
        out.append((cur - prev) / prev if prev else 0.0)
    return out


def total_return(equity_curve: Sequence[float]) -> float:
    if len(equity_curve) < 2 or not equity_curve[0]:
        return 0.0
    return (equity_curve[-1] - equity_curve[0]) / equity_curve[0]


def cagr(equity_curve: Sequence[float], n_trading_days: int) -> float:
    """Annualized compound growth rate. ``n_trading_days`` = number of sessions held."""
    if len(equity_curve) < 2 or not equity_curve[0] or n_trading_days <= 0:
        return 0.0
    growth = equity_curve[-1] / equity_curve[0]
    if growth <= 0:
        return -1.0
    years = n_trading_days / _TRADING_DAYS_PER_YEAR
    if years <= 0:
        return 0.0
    return growth ** (1 / years) - 1


def _mean(values: Sequence[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def _std(values: Sequence[float]) -> float:
    """Population standard deviation (matches a simple hand computation)."""
    if len(values) < 2:
        return 0.0
    mu = _mean(values)
    var = sum((v - mu) ** 2 for v in values) / len(values)
    return var**0.5


def annualized_volatility(daily_returns: Sequence[float]) -> float:
    return _std(daily_returns) * (_TRADING_DAYS_PER_YEAR**0.5)


def sharpe(daily_returns: Sequence[float], risk_free_rate: float = 0.0) -> float:
    """Annualized Sharpe ratio. ``risk_free_rate`` is an annual rate."""
    if len(daily_returns) < 2:
        return 0.0
    rf_daily = risk_free_rate / _TRADING_DAYS_PER_YEAR
    excess = [r - rf_daily for r in daily_returns]
    sd = _std(excess)
    if sd == 0:
        return 0.0
    return (_mean(excess) / sd) * (_TRADING_DAYS_PER_YEAR**0.5)


def sortino(daily_returns: Sequence[float], risk_free_rate: float = 0.0) -> float:
    """Annualized Sortino ratio (downside deviation in the denominator)."""
    if len(daily_returns) < 2:
        return 0.0
    rf_daily = risk_free_rate / _TRADING_DAYS_PER_YEAR
    excess = [r - rf_daily for r in daily_returns]
    downside = [min(0.0, e) for e in excess]
    dd = (sum(d**2 for d in downside) / len(excess)) ** 0.5
    if dd == 0:
        return 0.0
    return (_mean(excess) / dd) * (_TRADING_DAYS_PER_YEAR**0.5)


def max_drawdown(equity_curve: Sequence[float]) -> float:
    """Most negative peak-to-trough decline as a fraction (e.g. -0.25 = -25%)."""
    if len(equity_curve) < 2:
        return 0.0
    peak = equity_curve[0]
    worst = 0.0
    for value in equity_curve:
        if value > peak:
            peak = value
        if peak > 0:
            drawdown = (value - peak) / peak
            worst = min(worst, drawdown)
    return worst


def win_rate(closed_trades: Sequence) -> float:
    if not closed_trades:
        return 0.0
    winners = sum(1 for t in closed_trades if t.pnl > 0)
    return winners / len(closed_trades)


def avg_holding_days(closed_trades: Sequence) -> float:
    if not closed_trades:
        return 0.0
    return sum(t.holding_days for t in closed_trades) / len(closed_trades)


def compute_metrics(
    equity_curve: Sequence[float],
    closed_trades: Sequence,
    benchmark_curve: Sequence[float],
    risk_free_rate: float = 0.0,
) -> dict:
    """Bundle every metric plus final alpha vs the buy-and-hold benchmark."""
    n_days = max(len(equity_curve) - 1, 0)
    daily = daily_returns_from_curve(equity_curve)
    strat_total = total_return(equity_curve)
    bench_total = total_return(benchmark_curve)
    return {
        "total_return": strat_total,
        "benchmark_return": bench_total,
        "alpha": strat_total - bench_total,
        "cagr": cagr(equity_curve, n_days),
        "annualized_volatility": annualized_volatility(daily),
        "sharpe": sharpe(daily, risk_free_rate),
        "sortino": sortino(daily, risk_free_rate),
        "max_drawdown": max_drawdown(equity_curve),
        "win_rate": win_rate(closed_trades),
        "num_trades": len(closed_trades),
        "avg_holding_days": avg_holding_days(closed_trades),
    }
