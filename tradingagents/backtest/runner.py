"""Shared orchestration for the backtest CLI command and script.

Both ``scripts/backtest.py`` (argparse) and ``tradingagents backtest`` (typer)
call :func:`run_and_report` so the two entry points don't duplicate
source-selection, cost-gating, printing, or artifact-writing.
"""

from __future__ import annotations

import datetime
from pathlib import Path

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from tradingagents.backtest.decisions import (
    decisions_from_auto_trader,
    decisions_from_live_generate,
    decisions_from_memory_log,
)
from tradingagents.backtest.engine import BacktestConfig, run_backtest
from tradingagents.backtest.result import BacktestResult
from tradingagents.default_config import DEFAULT_CONFIG
from tradingagents.discovery.sp500_universe import tickers_for_sectors
from tradingagents.execution.portfolio_router import RiskLimits

_LIVE_CAVEAT = (
    "Live-generate re-runs the full agent pipeline for every (ticker, date) — "
    "this costs real LLM spend and time, and social-sentiment data is NOT "
    "historical, so treat live-mode results as a plumbing check, not a clean "
    "historical study. Replay mode (memory/artifacts) has neither problem."
)


def _weekday_grid(start: str, end: str) -> list[datetime.date]:
    """Weekdays in [start, end] — the candidate grid for live-generate.

    Live-generate can't use the benchmark's real session index (that's only
    known after fetching prices), so weekdays are a good-enough grid; the engine
    later maps each resulting decision onto a real trading session anyway.
    """
    start_d = datetime.datetime.strptime(start, "%Y-%m-%d").date()
    end_d = datetime.datetime.strptime(end, "%Y-%m-%d").date()
    days, cur = [], start_d
    while cur <= end_d:
        if cur.weekday() < 5:
            days.append(cur)
        cur += datetime.timedelta(days=1)
    return days


def _resolve_universe(
    tickers: list[str] | None, sectors: list[str] | None, watchlist: str | None
) -> list[str]:
    """Resolve the ticker universe for live-generate from the given options."""
    result: list[str] = []
    if tickers:
        result.extend(t.upper() for t in tickers)
    if sectors:
        for group in tickers_for_sectors(sectors).values():
            result.extend(group)
    if watchlist:
        for raw in Path(watchlist).read_text(encoding="utf-8").splitlines():
            line = raw.split("#", 1)[0].strip()
            if line:
                result.append(line.upper())
    # Dedupe, preserve order.
    return list(dict.fromkeys(result))


def run_and_report(
    *,
    start_date: str,
    end_date: str,
    source: str = "memory",
    tickers: list[str] | None = None,
    sectors: list[str] | None = None,
    watchlist: str | None = None,
    initial_cash: float = 100_000.0,
    benchmark: str = "SPY",
    holding_period_exit: int | None = None,
    position_pct: float = 0.05,
    max_positions: int = 15,
    max_sector_pct: float = 0.35,
    risk_free_rate: float = 0.0,
    whole_shares: bool = False,
    confirm_live: bool = False,
    config: dict | None = None,
    console: Console | None = None,
) -> BacktestResult | None:
    """Run a backtest end to end and print + write the report.

    Returns the :class:`BacktestResult`, or ``None`` if a live-generate run was
    requested without ``confirm_live`` (a cost warning is printed instead).
    """
    console = console or Console()
    config = config or DEFAULT_CONFIG
    ticker_filter = {t.upper() for t in tickers} if tickers else None

    if source == "memory":
        decisions = decisions_from_memory_log(config, start_date, end_date, ticker_filter)
    elif source == "artifacts":
        decisions = decisions_from_auto_trader(config, start_date, end_date, ticker_filter)
    elif source == "live":
        universe = _resolve_universe(tickers, sectors, watchlist)
        grid = _weekday_grid(start_date, end_date)
        estimate = len(universe) * len(grid)
        if not confirm_live:
            console.print(
                Panel(
                    f"{_LIVE_CAVEAT}\n\n"
                    f"This run would make about [bold]{estimate}[/bold] full agent "
                    f"runs ({len(universe)} tickers x {len(grid)} weekdays).\n"
                    f"Re-run with --yes to proceed.",
                    title="Live-generate cost warning",
                    border_style="red",
                )
            )
            return None
        console.print(f"[yellow]{_LIVE_CAVEAT}[/yellow]")
        console.print(f"Live-generating ~{estimate} decisions; this will take a while...")
        decisions = decisions_from_live_generate(
            config, universe, grid,
            on_progress=lambda day, tkr: console.print(f"  {day} {tkr}...", style="dim"),
        )
    else:
        raise ValueError(f"Unknown source {source!r}; expected memory | artifacts | live")

    if not decisions:
        console.print(
            "[red]No decisions found for the given range/source.[/red] "
            "For replay modes, you need prior analyze/auto_trader runs in that window."
        )
        return None

    cfg = BacktestConfig(
        decisions=decisions,
        start_date=start_date,
        end_date=end_date,
        benchmark=benchmark,
        initial_cash=initial_cash,
        limits=RiskLimits(
            position_pct_per_trade=position_pct,
            max_open_positions=max_positions,
            max_sector_pct=max_sector_pct,
        ),
        max_holding_days=holding_period_exit,
        whole_shares=whole_shares,
        risk_free_rate=risk_free_rate,
        results_dir=config["results_dir"],
    )
    result = run_backtest(cfg)
    _print_report(console, result, source)
    json_path, equity_path = result.write(config["results_dir"])
    console.print(f"[dim]Report: {json_path}[/dim]")
    console.print(f"[dim]Equity curve: {equity_path}[/dim]")
    return result


def _print_report(console: Console, result: BacktestResult, source: str) -> None:
    m = result.metrics
    console.print(
        Panel(
            f"Source: [bold]{source}[/bold]   "
            f"Window: {result.config['start_date']} → {result.config['end_date']}   "
            f"Decisions: {result.config['num_decisions']}",
            title="Backtest",
            border_style="cyan",
        )
    )

    table = Table(title="Performance", show_header=False)
    table.add_column("Metric")
    table.add_column("Value", justify="right")

    def pct(x):
        return f"{x:+.2%}"

    ret_style = "green" if m["total_return"] >= 0 else "red"
    alpha_style = "green" if m["alpha"] >= 0 else "red"
    table.add_row("Total return", f"[{ret_style}]{pct(m['total_return'])}[/{ret_style}]")
    table.add_row(f"Benchmark ({result.config['benchmark']}) return", pct(m["benchmark_return"]))
    table.add_row("Alpha", f"[{alpha_style}]{pct(m['alpha'])}[/{alpha_style}]")
    table.add_row("CAGR", pct(m["cagr"]))
    table.add_row("Annualized volatility", pct(m["annualized_volatility"]))
    table.add_row("Sharpe", f"{m['sharpe']:.2f}")
    table.add_row("Sortino", f"{m['sortino']:.2f}")
    table.add_row("Max drawdown", f"[red]{pct(m['max_drawdown'])}[/red]")
    table.add_row("Win rate", f"{m['win_rate']:.0%}")
    table.add_row("Trades", str(m["num_trades"]))
    table.add_row("Avg holding (days)", f"{m['avg_holding_days']:.1f}")
    console.print(table)

    if result.config.get("missing_tickers"):
        console.print(
            f"[yellow]No price data for: {', '.join(result.config['missing_tickers'])} "
            f"(decisions on these were skipped).[/yellow]"
        )
    if result.skipped:
        console.print(f"[dim]{len(result.skipped)} decision(s) skipped (no price / out of range).[/dim]")
