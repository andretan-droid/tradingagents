"""Full automated pipeline: screen a sector universe for cheap candidates, run
the multi-agent analysis on each, route decisions through portfolio-aware
risk limits, and notify + log the results.

Unlike watchlist_scanner.py (fixed ticker list, fixed-notional orders), this
script:
- discovers candidates itself via tradingagents.discovery.screener instead of
  reading a file you maintain by hand
- sizes and limits orders with tradingagents.execution.portfolio_router
  instead of the graph's built-in fixed-notional execution (this script
  leaves ``broker_enabled`` off on the graph and submits orders itself)
- posts to Discord on every order placed and a run summary at the end
- writes a JSON artifact per run plus an equity-history CSV that the local
  dashboard (tradingagents/dashboard) reads

Meant to be triggered daily — see scripts/run_auto_trader.bat and the README
"Automated screener + portfolio trading" section.

Usage:
    python scripts/auto_trader.py
    python scripts/auto_trader.py --sectors Technology Energy --top-n 3
    python scripts/auto_trader.py --date 2026-07-01 --no-skip-weekends
"""

from __future__ import annotations

import argparse
import csv
import json
import logging
import time
from datetime import datetime
from pathlib import Path

from rich.console import Console
from rich.table import Table

from tradingagents.default_config import DEFAULT_CONFIG
from tradingagents.discovery.screener import screen_sectors
from tradingagents.discovery.sp500_universe import all_sectors
from tradingagents.execution.alpaca_broker import AlpacaBroker
from tradingagents.execution.portfolio_router import RiskLimits, route_portfolio_decision
from tradingagents.graph.trading_graph import TradingAgentsGraph
from tradingagents.notifications.discord import (
    format_run_summary,
    format_trade_message,
    send_discord_message,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("auto_trader")
console = Console()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--sectors", nargs="+", default=all_sectors(),
        help=f"Sectors to screen (default: all — {', '.join(all_sectors())})",
    )
    parser.add_argument(
        "--top-n", type=int, default=5,
        help="Cheapest candidates per sector to run through full analysis (default: 5)",
    )
    parser.add_argument("--date", default=None, help="Analysis date YYYY-MM-DD (default: today)")
    parser.add_argument(
        "--delay", type=float, default=30.0,
        help="Seconds between tickers, to stay under LLM rate limits (default: 30)",
    )
    parser.add_argument(
        "--no-skip-weekends", action="store_true",
        help="Run even on Saturday/Sunday (off by default to save cost)",
    )
    parser.add_argument(
        "--position-pct", type=float, default=0.05,
        help="Fraction of account equity to size each new position at (default: 0.05 = 5%%)",
    )
    parser.add_argument("--max-positions", type=int, default=15, help="Max open positions (default: 15)")
    parser.add_argument(
        "--max-sector-pct", type=float, default=0.35,
        help="Max fraction of equity in any one sector (default: 0.35 = 35%%)",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    trade_date = args.date or datetime.now().strftime("%Y-%m-%d")

    if not args.no_skip_weekends:
        weekday = datetime.strptime(trade_date, "%Y-%m-%d").weekday()
        if weekday >= 5:  # Saturday=5, Sunday=6
            console.print(
                f"[yellow]{trade_date} is a weekend; markets are closed. Skipping "
                f"(pass --no-skip-weekends to run anyway).[/yellow]"
            )
            return

    config = DEFAULT_CONFIG.copy()
    # This script routes orders itself via portfolio_router; don't also let
    # the graph's built-in fixed-notional execution fire on the same decision.
    config["broker_enabled"] = False

    console.print(f"Screening {args.sectors} for {trade_date} (this scans the sector universe, takes a while)...")
    candidates = screen_sectors(args.sectors, top_n_per_sector=args.top_n)
    if not candidates:
        console.print("[red]Screener returned no candidates (data fetch failures?). Aborting.[/red]")
        return
    console.print(f"Screener selected {len(candidates)} candidate(s):")
    for c in candidates:
        console.print(f"  {c.ticker} ({c.sector}) — P/E {c.pe_ratio}, P/B {c.price_to_book}")

    try:
        broker = AlpacaBroker()
    except Exception as e:
        console.print(f"[yellow]Could not connect to Alpaca ({e}); continuing in analysis-only mode.[/yellow]")
        broker = None

    limits = RiskLimits(
        position_pct_per_trade=args.position_pct,
        max_open_positions=args.max_positions,
        max_sector_pct=args.max_sector_pct,
    )

    ta = TradingAgentsGraph(debug=False, config=config)

    results = []
    for i, candidate in enumerate(candidates, start=1):
        ticker = candidate.ticker
        console.print(f"\n[{i}/{len(candidates)}] Analyzing {ticker} ({candidate.sector})...")
        try:
            _, decision = ta.propagate(ticker, trade_date)
            action = "HOLD"
            if broker is not None:
                order_result = route_portfolio_decision(broker, ticker, decision, limits=limits)
                if order_result is not None:
                    action = order_result.side.upper()
                    send_discord_message(format_trade_message(ticker, decision, order_result))
            console.print(f"  -> {ticker}: [bold]{decision}[/bold] ({action})")
            results.append({
                "ticker": ticker, "sector": candidate.sector, "rating": decision,
                "action": action, "pe_ratio": candidate.pe_ratio,
                "price_to_book": candidate.price_to_book, "error": "",
            })
        except Exception as e:
            logger.exception("Analysis failed for %s", ticker)
            results.append({
                "ticker": ticker, "sector": candidate.sector, "rating": "",
                "action": "", "pe_ratio": candidate.pe_ratio,
                "price_to_book": candidate.price_to_book, "error": str(e),
            })

        if i < len(candidates):
            time.sleep(args.delay)

    _print_summary(results)
    _write_run_artifact(config, trade_date, results)
    if broker is not None:
        _append_equity_snapshot(config, broker)
    send_discord_message(format_run_summary(results))


def _print_summary(results: list[dict]) -> None:
    table = Table(title="Auto-Trader Run Summary")
    for col in ("Ticker", "Sector", "Rating", "Action", "Error"):
        table.add_column(col)
    for r in results:
        style = "red" if r["error"] else None
        table.add_row(r["ticker"], r["sector"], r["rating"], r["action"], r["error"], style=style)
    console.print(table)

    ok = [r for r in results if not r["error"]]
    orders = [r for r in ok if r["action"] in ("BUY", "SELL")]
    console.print(f"\n{len(ok)}/{len(results)} analyzed successfully, {len(orders)} order(s) placed.")


def _write_run_artifact(config: dict, trade_date: str, results: list[dict]) -> None:
    out_dir = Path(config["results_dir"]) / "auto_trader"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{trade_date}.json"
    out_path.write_text(
        json.dumps({"date": trade_date, "results": results}, indent=2), encoding="utf-8"
    )
    console.print(f"[dim]Run artifact written to {out_path}[/dim]")


def _append_equity_snapshot(config: dict, broker: AlpacaBroker) -> None:
    """Append a timestamped equity/cash/buying-power row for the dashboard's equity chart.

    Alpaca's own portfolio-history endpoint isn't used here — this simple
    per-run snapshot is enough to chart trend over daily runs and avoids
    depending on that endpoint's exact response shape across alpaca-py versions.
    """
    out_path = Path(config["results_dir"]) / "equity_history.csv"
    is_new = not out_path.exists()
    try:
        account = broker.get_account()
    except Exception:
        logger.exception("Could not fetch account for equity snapshot.")
        return
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        if is_new:
            writer.writerow(["timestamp", "equity", "cash", "buying_power"])
        writer.writerow([
            datetime.now().isoformat(timespec="seconds"),
            account.equity, account.cash, account.buying_power,
        ])


if __name__ == "__main__":
    main()
