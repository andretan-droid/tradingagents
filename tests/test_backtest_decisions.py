"""Tests for backtest decision sources (memory log / artifacts / live) — no network/LLM."""

from __future__ import annotations

import datetime
import json

import pytest

from tradingagents.backtest.decisions import (
    DecisionEvent,
    decisions_from_auto_trader,
    decisions_from_live_generate,
    decisions_from_memory_log,
)


@pytest.mark.unit
def test_decisions_from_memory_log(tmp_path):
    from tradingagents.agents.utils.memory import TradingMemoryLog

    log_path = tmp_path / "mem.md"
    config = {"memory_log_path": str(log_path)}
    log = TradingMemoryLog(config)
    log.store_decision("AAPL", "2026-01-05", "Rating: Buy\n\nFINAL TRANSACTION PROPOSAL: **BUY**")
    log.store_decision("MSFT", "2026-02-10", "Rating: Sell\n\nFINAL TRANSACTION PROPOSAL: **SELL**")

    events = decisions_from_memory_log(config, "2026-01-01", "2026-01-31")

    assert len(events) == 1
    assert events[0] == DecisionEvent(datetime.date(2026, 1, 5), "AAPL", "Buy")


@pytest.mark.unit
def test_decisions_from_memory_log_ticker_filter(tmp_path):
    from tradingagents.agents.utils.memory import TradingMemoryLog

    log_path = tmp_path / "mem.md"
    config = {"memory_log_path": str(log_path)}
    log = TradingMemoryLog(config)
    log.store_decision("AAPL", "2026-01-05", "Rating: Buy")
    log.store_decision("MSFT", "2026-01-06", "Rating: Buy")

    events = decisions_from_memory_log(config, "2026-01-01", "2026-01-31", tickers={"AAPL"})

    assert [e.ticker for e in events] == ["AAPL"]


@pytest.mark.unit
def test_decisions_from_auto_trader_json_and_csv(tmp_path):
    results_dir = tmp_path
    config = {"results_dir": str(results_dir)}

    at_dir = results_dir / "auto_trader"
    at_dir.mkdir()
    (at_dir / "2026-01-05.json").write_text(json.dumps({
        "date": "2026-01-05",
        "results": [
            {"ticker": "AAPL", "rating": "Buy", "error": ""},
            {"ticker": "BADCO", "rating": "", "error": "boom"},       # skipped: error
            {"ticker": "NORATE", "rating": "", "error": ""},           # skipped: empty rating
        ],
    }))

    ws_dir = results_dir / "watchlist_scans"
    ws_dir.mkdir()
    (ws_dir / "2026-01-06.csv").write_text(
        "ticker,rating,action,error\nMSFT,Sell,SELL,\nERRCO,Buy,BUY,network down\n"
    )

    events = decisions_from_auto_trader(config, "2026-01-01", "2026-01-31")

    got = {(e.date.isoformat(), e.ticker, e.rating) for e in events}
    assert got == {("2026-01-05", "AAPL", "Buy"), ("2026-01-06", "MSFT", "Sell")}


@pytest.mark.unit
def test_decisions_from_auto_trader_dedupes_same_date_ticker(tmp_path):
    config = {"results_dir": str(tmp_path)}
    at_dir = tmp_path / "auto_trader"
    at_dir.mkdir()
    (at_dir / "2026-01-05.json").write_text(json.dumps({
        "date": "2026-01-05",
        "results": [
            {"ticker": "AAPL", "rating": "Buy", "error": ""},
            {"ticker": "AAPL", "rating": "Sell", "error": ""},  # last wins
        ],
    }))

    events = decisions_from_auto_trader(config, "2026-01-01", "2026-01-31")

    assert len(events) == 1
    assert events[0].rating == "Sell"


@pytest.mark.unit
def test_decisions_from_live_generate_uses_injected_graph():
    class FakeGraph:
        def propagate(self, ticker, date, asset_type="stock"):
            return {}, "Buy" if ticker == "AAPL" else "Hold"

    grid = [datetime.date(2026, 1, 5), datetime.date(2026, 1, 6)]
    events = decisions_from_live_generate({}, ["AAPL", "MSFT"], grid, graph=FakeGraph())

    got = {(e.ticker, e.rating) for e in events}
    assert ("AAPL", "Buy") in got
    assert ("MSFT", "Hold") in got


@pytest.mark.unit
def test_decisions_from_live_generate_skips_failures():
    class ExplodingGraph:
        def propagate(self, ticker, date, asset_type="stock"):
            raise RuntimeError("rate limit")

    events = decisions_from_live_generate({}, ["AAPL"], [datetime.date(2026, 1, 5)],
                                          graph=ExplodingGraph())
    assert events == []
