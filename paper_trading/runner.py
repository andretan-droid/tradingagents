"""Daily driver for the paper-trading pipeline.

For each ticker in the watchlist: run the full TradingAgents multi-agent
graph (analysts -> bull/bear researchers -> risk desk -> portfolio manager),
extract the resulting rating, execute it against the paper portfolio at the
latest available price, and save that ticker's reports. Then mark the whole
portfolio to market and persist state to disk.

Run directly:
    python -m paper_trading.runner
    python -m paper_trading.runner --date 2026-07-01 --tickers AAPL,NVDA
"""

from __future__ import annotations

import json
import logging
from dataclasses import asdict
from datetime import date as date_cls
from pathlib import Path

import typer

from paper_trading.config import (
    MEMORY_LOG_PATH,
    PORTFOLIO_SETTINGS,
    PORTFOLIO_STATE_PATH,
    RUNS_DIR,
    SELECTED_ANALYSTS,
    WATCHLIST,
)
from paper_trading.portfolio import Portfolio
from paper_trading.pricing import get_latest_price
from tradingagents.default_config import DEFAULT_CONFIG
from tradingagents.graph.trading_graph import TradingAgentsGraph

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

app = typer.Typer(add_completion=False)


def _build_graph_config() -> dict:
    config = DEFAULT_CONFIG.copy()
    # Redirect the decision-log/reflection memory into the repo (instead of
    # the default ~/.tradingagents home) so it survives across GitHub
    # Actions runs, each of which starts from a fresh checkout.
    config["memory_log_path"] = str(MEMORY_LOG_PATH)
    return config


def _process_ticker(ticker: str, run_date: str, portfolio: Portfolio, base_nav: float) -> dict:
    entry: dict = {"ticker": ticker, "rating": None, "trade": None, "error": None}
    try:
        graph = TradingAgentsGraph(
            selected_analysts=SELECTED_ANALYSTS,
            debug=False,
            config=_build_graph_config(),
        )
        final_state, rating = graph.propagate(ticker, run_date)
        graph.save_reports(final_state, ticker, save_path=RUNS_DIR / run_date / ticker)
        entry["rating"] = rating

        price = get_latest_price(ticker)
        entry["price"] = price
        trade = portfolio.apply_rating(
            ticker, rating, price, run_date, PORTFOLIO_SETTINGS, base_nav
        )
        if trade is not None:
            entry["trade"] = asdict(trade)
    except Exception as exc:  # noqa: BLE001 - one bad ticker must not kill the whole run
        logger.exception("Failed to process %s", ticker)
        entry["error"] = str(exc)
    return entry


def _write_summary(run_date: str, summary: dict) -> None:
    run_dir = RUNS_DIR / run_date
    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")

    lines = [f"# Paper trading summary -- {run_date}", ""]
    lines.append("| Ticker | Rating | Trade | Error |")
    lines.append("| --- | --- | --- | --- |")
    for entry in summary["decisions"]:
        trade = entry.get("trade")
        trade_str = (
            f"{trade['action']} {trade['shares']} @ {trade['price']}" if trade else "-"
        )
        lines.append(
            f"| {entry['ticker']} | {entry.get('rating') or '-'} | {trade_str} | "
            f"{entry.get('error') or '-'} |"
        )
    portfolio_snapshot = summary["portfolio"]
    lines += [
        "",
        "## Portfolio snapshot",
        f"- Cash: {portfolio_snapshot['cash']}",
        f"- Positions value: {portfolio_snapshot['positions_value']}",
        f"- NAV: {portfolio_snapshot['nav']}",
    ]
    (run_dir / "summary.md").write_text("\n".join(lines), encoding="utf-8")


def run_daily(run_date: str, tickers: list[str] | None = None) -> dict:
    """Run one paper-trading day for ``tickers`` (default: the watchlist).

    Returns the daily summary dict; also written to
    ``paper_trading/runs/<run_date>/summary.{json,md}`` and persists the
    updated portfolio state to ``paper_trading/state/portfolio.json``.
    """
    watchlist = tickers or [row["ticker"] for row in WATCHLIST]
    portfolio = Portfolio.load_or_new(
        PORTFOLIO_STATE_PATH, PORTFOLIO_SETTINGS["starting_cash"]
    )
    # Buy/Overweight sizing is a percentage of NAV as of the last close
    # (or the starting cash on day one), held fixed for the whole run so
    # sizing doesn't compound across tickers processed in the same batch.
    base_nav = (
        portfolio.nav_history[-1]["nav"]
        if portfolio.nav_history
        else portfolio.starting_cash
    )

    decisions = [
        _process_ticker(ticker, run_date, portfolio, base_nav) for ticker in watchlist
    ]

    prices: dict[str, float] = {}
    for ticker in list(portfolio.positions):
        try:
            prices[ticker] = get_latest_price(ticker)
        except Exception:
            logger.exception("Failed to price existing position %s", ticker)
    snapshot = portfolio.mark_to_market(prices, run_date)
    portfolio.save(PORTFOLIO_STATE_PATH)

    summary = {"date": run_date, "decisions": decisions, "portfolio": snapshot}
    _write_summary(run_date, summary)
    return summary


@app.command()
def main(
    date: str = typer.Option(
        None, "--date", help="Analysis date, YYYY-MM-DD (default: today)."
    ),
    tickers: str = typer.Option(
        None, "--tickers", help="Comma-separated ticker override (default: the watchlist)."
    ),
) -> None:
    run_date = date or date_cls.today().isoformat()
    ticker_list = [t.strip() for t in tickers.split(",")] if tickers else None
    summary = run_daily(run_date, ticker_list)
    typer.echo((Path(RUNS_DIR) / run_date / "summary.md").read_text(encoding="utf-8"))
    typer.echo(f"\nNAV: {summary['portfolio']['nav']}")


if __name__ == "__main__":
    app()
