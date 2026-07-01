"""Backtest the strategy over a historical date range.

Replays trading decisions through a simulated portfolio (reusing the live
risk-sizing/limit logic) and reports performance vs a buy-and-hold benchmark.

Default source is `memory` (decisions already saved to the memory log by prior
`analyze`/`auto_trader` runs) — free and look-ahead-clean. `artifacts` replays
saved auto_trader/watchlist JSON+CSV. `live` re-runs the agents over the range
(expensive; requires --yes; sentiment data isn't historical — see the warning).

Usage:
    python scripts/backtest.py --start-date 2026-01-01 --end-date 2026-03-31
    python scripts/backtest.py --start-date 2026-01-01 --end-date 2026-03-31 \
        --source artifacts --holding-period-exit 10
    python scripts/backtest.py --start-date 2026-01-01 --end-date 2026-02-01 \
        --source live --sectors Technology --yes
"""

from __future__ import annotations

import argparse

from tradingagents.backtest.runner import run_and_report


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--start-date", required=True, help="YYYY-MM-DD")
    parser.add_argument("--end-date", required=True, help="YYYY-MM-DD")
    parser.add_argument("--source", default="memory", choices=["memory", "artifacts", "live"],
                        help="Decision source (default: memory)")
    parser.add_argument("--tickers", nargs="+", default=None,
                        help="Filter (replay) or universe (live)")
    parser.add_argument("--sectors", nargs="+", default=None, help="Universe for --source live")
    parser.add_argument("--watchlist", default=None, help="Watchlist file for --source live")
    parser.add_argument("--initial-cash", type=float, default=100_000.0)
    parser.add_argument("--benchmark", default="SPY")
    parser.add_argument("--holding-period-exit", type=int, default=None,
                        help="Optional: auto-close positions after N days")
    parser.add_argument("--position-pct", type=float, default=0.05)
    parser.add_argument("--max-positions", type=int, default=15)
    parser.add_argument("--max-sector-pct", type=float, default=0.35)
    parser.add_argument("--risk-free-rate", type=float, default=0.0)
    parser.add_argument("--whole-shares", action="store_true")
    parser.add_argument("--yes", action="store_true", help="Confirm the cost of --source live")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    run_and_report(
        start_date=args.start_date,
        end_date=args.end_date,
        source=args.source,
        tickers=args.tickers,
        sectors=args.sectors,
        watchlist=args.watchlist,
        initial_cash=args.initial_cash,
        benchmark=args.benchmark,
        holding_period_exit=args.holding_period_exit,
        position_pct=args.position_pct,
        max_positions=args.max_positions,
        max_sector_pct=args.max_sector_pct,
        risk_free_rate=args.risk_free_rate,
        whole_shares=args.whole_shares,
        confirm_live=args.yes,
    )


if __name__ == "__main__":
    main()
