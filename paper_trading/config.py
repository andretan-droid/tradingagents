"""Configuration for the daily paper-trading pipeline.

This is intentionally separate from ``tradingagents/default_config.py``: it
configures the *paper portfolio and candidate list*, not the multi-agent
graph itself (which is still controlled by ``TRADINGAGENTS_*`` env vars /
``DEFAULT_CONFIG``, see the root ``.env.example``).

Env-var overrides follow the same convention as
``tradingagents/default_config.py``: unset means "use the default below".
"""

from __future__ import annotations

import os
from pathlib import Path

# Directory this file lives in, e.g. .../paper_trading
_PAPER_TRADING_DIR = Path(__file__).resolve().parent

# ---------------------------------------------------------------------------
# Candidate watchlist
# ---------------------------------------------------------------------------
# One multi-agent analysis run (all analysts + bull/bear debate + risk
# debate + portfolio manager) happens per ticker per day, so keep this list
# short deliberately -- it is the main lever on how long/expensive a daily
# run is. Edit freely to add/remove tickers; "market" is just a label shown
# in the dashboard and isn't used by the pipeline itself.
#
# Ticker format follows Yahoo Finance conventions (see README "Markets and
# tickers"): US tickers are bare (AAPL), Singapore Exchange tickers use the
# ".SI" suffix, Bursa Malaysia tickers use ".KL".
WATCHLIST: list[dict[str, str]] = [
    {"ticker": "AAPL", "market": "US", "note": "Apple"},
    {"ticker": "NVDA", "market": "US", "note": "Nvidia"},
    {"ticker": "MSFT", "market": "US", "note": "Microsoft"},
    {"ticker": "D05.SI", "market": "SG", "note": "DBS Group"},
    {"ticker": "O39.SI", "market": "SG", "note": "OCBC"},
    {"ticker": "1155.KL", "market": "MY", "note": "Maybank"},
    {"ticker": "5183.KL", "market": "MY", "note": "Petronas Chemicals"},
]


def _float_env(name: str, default: float) -> float:
    raw = os.environ.get(name)
    return default if raw is None or raw == "" else float(raw)


def _path_env(name: str, default: Path) -> Path:
    raw = os.environ.get(name)
    return default if raw is None or raw == "" else Path(raw)


# ---------------------------------------------------------------------------
# Paper portfolio settings
# ---------------------------------------------------------------------------
PORTFOLIO_SETTINGS = {
    # Starting cash for a brand-new portfolio (only used the first time the
    # runner is invoked; ignored once state/portfolio.json exists).
    "starting_cash": _float_env("PAPER_TRADING_STARTING_CASH", 100_000.0),
    # Position-sizing policy applied to the Portfolio Manager's 5-tier
    # rating. This is deliberately simple (no target-weight rebalancing,
    # no leverage, long-only, fractional shares allowed):
    #   Buy         -> spend buy_pct of current NAV opening/adding to the position
    #   Overweight  -> spend overweight_pct of current NAV adding to the position
    #   Hold        -> no trade
    #   Underweight -> sell underweight_sell_pct of the current share count
    #   Sell        -> liquidate the entire position
    "buy_pct": _float_env("PAPER_TRADING_BUY_PCT", 0.10),
    "overweight_pct": _float_env("PAPER_TRADING_OVERWEIGHT_PCT", 0.05),
    "underweight_sell_pct": _float_env("PAPER_TRADING_UNDERWEIGHT_SELL_PCT", 0.50),
    # Flat per-trade commission in the instrument's currency (0 = frictionless
    # paper fills). Kept as a knob since real brokers rarely charge exactly 0.
    "commission": _float_env("PAPER_TRADING_COMMISSION", 0.0),
}

# Where portfolio state (cash/positions/trade history/NAV history) and the
# redirected memory/reflection log are persisted. Both must live inside the
# repo (not the default ~/.tradingagents home) so a GitHub Actions run can
# commit them back and the next scheduled run picks up where this one left
# off -- the Actions runner itself is thrown away after each job.
STATE_DIR = _path_env("PAPER_TRADING_STATE_DIR", _PAPER_TRADING_DIR / "state")
PORTFOLIO_STATE_PATH = STATE_DIR / "portfolio.json"
MEMORY_LOG_PATH = STATE_DIR / "trading_memory.md"

# Where each day's per-ticker agent reports + the daily summary are written.
RUNS_DIR = _path_env("PAPER_TRADING_RUNS_DIR", _PAPER_TRADING_DIR / "runs")

# Analyst team run for every ticker: technical/market, sentiment ("social" is
# the wire key -- see tradingagents/graph/analyst_execution.py), macro news,
# and fundamentals. Bull/bear researchers, the risk-management desk, and the
# portfolio manager always run regardless of this list.
SELECTED_ANALYSTS = ("market", "social", "news", "fundamentals")
