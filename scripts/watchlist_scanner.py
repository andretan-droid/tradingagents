"""Run TradingAgents analysis (and optional paper-order execution) across a
watchlist of tickers in one pass, meant to be triggered on a schedule (e.g.
Windows Task Scheduler, cron) for unattended daily runs.

For each ticker in the watchlist file, this calls the same
``TradingAgentsGraph.propagate()`` used by ``tradingagents analyze``, so
paper-order submission (when ``TRADINGAGENTS_BROKER_ENABLED=true``), report
saving, and the memory log all work exactly as they do interactively. A
single ticker's failure (rate limit, bad ticker, network blip) is logged and
skipped rather than aborting the whole scan, since an unattended run has no
one watching to restart it.

Usage:
    python scripts/watchlist_scanner.py
    python scripts/watchlist_scanner.py --watchlist my_list.txt --delay 45
    python scripts/watchlist_scanner.py --date 2026-07-01 --no-skip-weekends

See watchlist.example.txt for the file format, and the README "Paper
Trading (Alpaca)" section for how to enable order execution.
"""

from __future__ import annotations

import argparse
import csv
import logging
import sys
import time
from datetime import datetime
from pathlib import Path

from rich.console import Console
from rich.table import Table

from tradingagents.default_config import DEFAULT_CONFIG
from tradingagents.execution.order_router import rating_to_side
from tradingagents.graph.trading_graph import TradingAgentsGraph

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("watchlist_scanner")
console = Console()

REPO_ROOT = Path(__file__).resolve().parent.parent


def load_watchlist(path: Path) -> list[str]:
    """Parse a watchlist file: one ticker per line, '#' starts a comment."""
    tickers = []
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.split("#", 1)[0].strip()
        if line:
            tickers.append(line.upper())
    return tickers


def resolve_watchlist_path(cli_value: str | None) -> Path:
    if cli_value:
        path = Path(cli_value)
        if not path.exists():
            console.print(f"[red]Watchlist file not found: {path}[/red]")
            sys.exit(1)
        return path

    default_path = REPO_ROOT / "watchlist.txt"
    if default_path.exists():
        return default_path

    example_path = REPO_ROOT / "watchlist.example.txt"
    console.print(
        f"[yellow]No watchlist.txt found — using {example_path.name} as a starting "
        f"point. Copy it to watchlist.txt and edit it to use your own list.[/yellow]"
    )
    return example_path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--watchlist", default=None, help="Path to watchlist file (default: watchlist.txt)"
    )
    parser.add_argument(
        "--date", default=None, help="Analysis date YYYY-MM-DD (default: today)"
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=30.0,
        help="Seconds to wait between tickers, to stay under LLM rate limits (default: 30)",
    )
    parser.add_argument(
        "--no-skip-weekends",
        action="store_true",
        help="Run even on Saturday/Sunday (markets are closed; off by default to save cost)",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    trade_date = args.date or datetime.now().strftime("%Y-%m-%d")

    if not args.no_skip_weekends:
        weekday = datetime.strptime(trade_date, "%Y-%m-%d").weekday()
        if weekday >= 5:  # Saturday=5, Sunday=6
            console.print(
                f"[yellow]{trade_date} is a weekend; markets are closed. Skipping scan "
                f"(pass --no-skip-weekends to run anyway).[/yellow]"
            )
            return

    watchlist_path = resolve_watchlist_path(args.watchlist)
    tickers = load_watchlist(watchlist_path)
    if not tickers:
        console.print(f"[red]No tickers found in {watchlist_path}[/red]")
        sys.exit(1)

    config = DEFAULT_CONFIG.copy()
    broker_note = (
        "[green]paper orders WILL be submitted[/green]"
        if config.get("broker_enabled")
        else "[dim]paper orders disabled (TRADINGAGENTS_BROKER_ENABLED not set)[/dim]"
    )
    console.print(
        f"Scanning {len(tickers)} ticker(s) for {trade_date} — {broker_note}\n"
        f"Watchlist: {watchlist_path}"
    )

    ta = TradingAgentsGraph(debug=False, config=config)

    results = []
    for i, ticker in enumerate(tickers, start=1):
        console.print(f"\n[{i}/{len(tickers)}] Analyzing {ticker}...")
        try:
            _, decision = ta.propagate(ticker, trade_date)
            side = rating_to_side(decision)
            action = {"buy": "BUY", "sell": "SELL", None: "no action"}[side]
            console.print(f"  -> {ticker}: [bold]{decision}[/bold] ({action})")
            results.append({"ticker": ticker, "rating": decision, "action": action, "error": ""})
        except Exception as e:
            logger.exception("Analysis failed for %s", ticker)
            results.append({"ticker": ticker, "rating": "", "action": "", "error": str(e)})

        if i < len(tickers):
            time.sleep(args.delay)

    _print_summary(results)
    _write_summary_csv(config, trade_date, results)


def _print_summary(results: list[dict]) -> None:
    table = Table(title="Watchlist Scan Summary")
    table.add_column("Ticker")
    table.add_column("Rating")
    table.add_column("Action")
    table.add_column("Error")
    for r in results:
        style = "red" if r["error"] else None
        table.add_row(r["ticker"], r["rating"], r["action"], r["error"], style=style)
    console.print(table)

    ok = [r for r in results if not r["error"]]
    failed = [r for r in results if r["error"]]
    orders = [r for r in ok if r["action"] in ("BUY", "SELL")]
    console.print(
        f"\n{len(ok)}/{len(results)} analyzed successfully, "
        f"{len(orders)} order(s) placed, {len(failed)} failed."
    )


def _write_summary_csv(config: dict, trade_date: str, results: list[dict]) -> None:
    out_dir = Path(config["results_dir"]) / "watchlist_scans"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{trade_date}.csv"
    with open(out_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["ticker", "rating", "action", "error"])
        writer.writeheader()
        writer.writerows(results)
    console.print(f"[dim]Summary written to {out_path}[/dim]")


if __name__ == "__main__":
    main()
