"""Decision sources for the backtester.

Every source yields a normalized ``list[DecisionEvent]`` so the engine is
agnostic to where decisions came from:

- ``decisions_from_memory_log`` / ``decisions_from_auto_trader`` — REPLAY
  decisions the system already made in real time. No LLM cost, no look-ahead
  bias (the ratings were produced on their date).
- ``decisions_from_live_generate`` — re-runs the full agent pipeline over a
  date grid. Expensive, and social-sentiment data isn't historical, so this is
  a plumbing/smoke path rather than a clean historical study (the CLI prints
  this caveat and gates it behind an explicit confirmation).
"""

from __future__ import annotations

import csv
import datetime
import json
import logging
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class DecisionEvent:
    date: datetime.date
    ticker: str
    rating: str  # canonical 5-tier string, passed straight to the router


def _parse_date(value: str) -> datetime.date | None:
    try:
        return datetime.datetime.strptime(value, "%Y-%m-%d").date()
    except (ValueError, TypeError):
        return None


def _in_range(day: datetime.date, start: str, end: str) -> bool:
    return _parse_date(start) <= day <= _parse_date(end)


def _dedupe_and_sort(events: list[DecisionEvent]) -> list[DecisionEvent]:
    """Keep one event per (date, ticker) (last wins), sorted by (date, ticker)."""
    by_key: dict[tuple[datetime.date, str], DecisionEvent] = {}
    for e in events:
        by_key[(e.date, e.ticker.upper())] = e
    return sorted(by_key.values(), key=lambda e: (e.date, e.ticker))


def decisions_from_memory_log(
    config: dict, start: str, end: str, tickers: set[str] | None = None
) -> list[DecisionEvent]:
    """Replay decisions from the append-only memory log.

    Pending entries are included: their rating was still made in real time; only
    the realized-return fields are missing, which the sim recomputes itself.
    """
    from tradingagents.agents.utils.memory import TradingMemoryLog

    tickers_upper = {t.upper() for t in tickers} if tickers else None
    events = []
    for entry in TradingMemoryLog(config).load_entries():
        day = _parse_date(entry.get("date", ""))
        rating = entry.get("rating")
        ticker = entry.get("ticker")
        if not day or not rating or not ticker:
            continue
        if not _in_range(day, start, end):
            continue
        if tickers_upper and ticker.upper() not in tickers_upper:
            continue
        events.append(DecisionEvent(day, ticker.upper(), rating))
    return _dedupe_and_sort(events)


def decisions_from_auto_trader(
    config: dict, start: str, end: str, tickers: set[str] | None = None
) -> list[DecisionEvent]:
    """Replay decisions from saved auto_trader JSON and watchlist-scan CSV artifacts."""
    tickers_upper = {t.upper() for t in tickers} if tickers else None
    results_dir = Path(config["results_dir"])
    events: list[DecisionEvent] = []

    def _keep(day, ticker, rating, error) -> bool:
        if not day or not rating or error:
            return False
        if not _in_range(day, start, end):
            return False
        return not (tickers_upper and ticker.upper() not in tickers_upper)

    # auto_trader/<date>.json — the date lives inside the file.
    for path in sorted((results_dir / "auto_trader").glob("*.json")):
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            logger.warning("Backtest: could not read auto_trader artifact %s", path)
            continue
        day = _parse_date(payload.get("date", ""))
        for row in payload.get("results", []):
            if _keep(day, row.get("ticker", ""), row.get("rating"), row.get("error")):
                events.append(DecisionEvent(day, row["ticker"].upper(), row["rating"]))

    # watchlist_scans/<date>.csv — the date is the filename stem.
    for path in sorted((results_dir / "watchlist_scans").glob("*.csv")):
        day = _parse_date(path.stem)
        try:
            with open(path, newline="", encoding="utf-8") as f:
                rows = list(csv.DictReader(f))
        except OSError:
            logger.warning("Backtest: could not read watchlist artifact %s", path)
            continue
        for row in rows:
            if _keep(day, row.get("ticker", ""), row.get("rating"), row.get("error")):
                events.append(DecisionEvent(day, row["ticker"].upper(), row["rating"]))

    return _dedupe_and_sort(events)


def decisions_from_live_generate(
    config: dict,
    tickers: list[str],
    date_grid: list[datetime.date],
    *,
    asset_type: str = "stock",
    graph=None,
    on_progress=None,
) -> list[DecisionEvent]:
    """Generate decisions by re-running the agent pipeline for each (date, ticker).

    EXPENSIVE: one full multi-agent run per pair. ``graph`` may be injected (a
    ``TradingAgentsGraph`` or a test double exposing ``propagate``); otherwise
    one is constructed from ``config``. A failed run is logged and skipped so
    one bad pair doesn't abort the whole grid.
    """
    if graph is None:
        from tradingagents.graph.trading_graph import TradingAgentsGraph

        graph = TradingAgentsGraph(config=config)

    events = []
    for day in date_grid:
        for ticker in tickers:
            if on_progress is not None:
                on_progress(day, ticker)
            try:
                _, decision = graph.propagate(ticker, day.isoformat(), asset_type=asset_type)
                events.append(DecisionEvent(day, ticker.upper(), decision))
            except Exception:
                logger.exception("Backtest live-generate failed for %s on %s", ticker, day)
    return _dedupe_and_sort(events)
