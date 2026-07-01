"""Backtesting: simulate the strategy over a historical date range and measure it.

Replays trading decisions (from the memory log / saved run artifacts, or
freshly generated via ``propagate()``) through a simulated portfolio that
reuses the live risk-sizing/limit logic in
``tradingagents.execution.portfolio_router``, then computes performance
metrics (return, alpha vs benchmark, Sharpe, max drawdown, win rate, ...).
"""

from tradingagents.backtest.engine import BacktestConfig, run_backtest
from tradingagents.backtest.result import BacktestResult, ClosedTrade

__all__ = ["BacktestConfig", "run_backtest", "BacktestResult", "ClosedTrade"]
