"""Streamlit dashboard for the paper-trading pipeline.

Read-only viewer over the state paper_trading/runner.py produces: portfolio
cash/positions/NAV history, each day's ratings and trades, and the full
multi-agent report for any ticker on any day.

Run with:
    streamlit run dashboard/app.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd
import streamlit as st

# Streamlit puts this file's own directory on sys.path, not the repo root --
# add the root explicitly so `paper_trading` and `tradingagents` resolve
# regardless of the working directory the dashboard is launched from.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from paper_trading.config import PORTFOLIO_STATE_PATH, RUNS_DIR, WATCHLIST  # noqa: E402
from paper_trading.portfolio import Portfolio  # noqa: E402

st.set_page_config(page_title="Paper Trading Agent", layout="wide")


@st.cache_data(ttl=60)
def _load_portfolio() -> Portfolio | None:
    if not Path(PORTFOLIO_STATE_PATH).exists():
        return None
    return Portfolio.load_or_new(PORTFOLIO_STATE_PATH, starting_cash=0.0)


@st.cache_data(ttl=60)
def _load_current_prices(tickers: tuple[str, ...]) -> dict[str, float]:
    from paper_trading.pricing import get_latest_price

    prices = {}
    for ticker in tickers:
        try:
            prices[ticker] = get_latest_price(ticker)
        except Exception:
            prices[ticker] = None
    return prices


def _available_run_dates() -> list[str]:
    if not Path(RUNS_DIR).exists():
        return []
    return sorted(
        (p.name for p in Path(RUNS_DIR).iterdir() if p.is_dir()), reverse=True
    )


st.title("Paper Trading Agent")
st.caption(
    "Simulated (paper-money) portfolio driven by the TradingAgents multi-agent "
    "pipeline. Nothing here touches a real brokerage account. Not investment advice."
)

portfolio = _load_portfolio()

if portfolio is None:
    st.info(
        "No portfolio state yet. Run `python -m paper_trading.runner` once to "
        "generate the first day's decisions and portfolio snapshot."
    )
    st.subheader("Watchlist")
    st.dataframe(pd.DataFrame(WATCHLIST), hide_index=True, use_container_width=True)
    st.stop()

# --- Portfolio overview -----------------------------------------------------
tickers = tuple(portfolio.positions.keys())
current_prices = _load_current_prices(tickers)

col1, col2, col3, col4 = st.columns(4)
latest_nav = portfolio.nav_history[-1]["nav"] if portfolio.nav_history else portfolio.cash
total_return = (
    (latest_nav / portfolio.starting_cash - 1.0) * 100 if portfolio.starting_cash else 0.0
)
col1.metric("Cash", f"${portfolio.cash:,.2f}")
col2.metric("Positions value", f"${portfolio.positions_value({k: v for k, v in current_prices.items() if v}):,.2f}")
col3.metric("Net asset value", f"${latest_nav:,.2f}")
col4.metric("Total return", f"{total_return:+.2f}%")

st.subheader("NAV history")
if portfolio.nav_history:
    nav_df = pd.DataFrame(portfolio.nav_history).set_index("date")
    st.line_chart(nav_df["nav"])
else:
    st.write("No NAV history yet.")

st.subheader("Positions")
if portfolio.positions:
    rows = []
    for ticker, pos in portfolio.positions.items():
        price = current_prices.get(ticker)
        market_value = pos.shares * price if price else None
        unrealized = (price - pos.avg_cost) * pos.shares if price else None
        rows.append(
            {
                "ticker": ticker,
                "shares": pos.shares,
                "avg_cost": pos.avg_cost,
                "current_price": price,
                "market_value": market_value,
                "unrealized_pnl": unrealized,
            }
        )
    st.dataframe(pd.DataFrame(rows), hide_index=True, use_container_width=True)
else:
    st.write("No open positions.")

st.subheader("Trade history")
if portfolio.trade_history:
    trades_df = pd.DataFrame([t.__dict__ for t in portfolio.trade_history])
    st.dataframe(trades_df.sort_values("date", ascending=False), hide_index=True, use_container_width=True)
else:
    st.write("No trades yet.")

# --- Daily decisions & agent reports ----------------------------------------
st.header("Daily decisions")
run_dates = _available_run_dates()
if not run_dates:
    st.write("No daily runs found yet.")
else:
    selected_date = st.selectbox("Run date", run_dates)
    summary_path = Path(RUNS_DIR) / selected_date / "summary.json"
    if summary_path.exists():
        summary = json.loads(summary_path.read_text(encoding="utf-8"))
        decisions_df = pd.DataFrame(summary["decisions"])
        st.dataframe(decisions_df, hide_index=True, use_container_width=True)

        ticker_options = [d["ticker"] for d in summary["decisions"] if not d.get("error")]
        if ticker_options:
            selected_ticker = st.selectbox("View full agent report for", ticker_options)
            report_path = Path(RUNS_DIR) / selected_date / selected_ticker / "complete_report.md"
            if report_path.exists():
                st.markdown(report_path.read_text(encoding="utf-8"))
            else:
                st.write("No saved report found for this ticker/date.")
    else:
        st.write("No summary found for this date.")
