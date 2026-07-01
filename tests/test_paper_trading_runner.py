"""Integration-style test for the daily runner's orchestration logic.

Mocks out the multi-agent graph and the price lookup (both talk to the
network / an LLM) so this stays a fast, offline unit test of the wiring:
one ticker's decision executes as a trade, portfolio state persists, and
the summary files land where the dashboard expects them.
"""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest


@pytest.mark.unit
def test_run_daily_executes_a_buy_and_persists_state(tmp_path, monkeypatch):
    import paper_trading.config as config_module
    import paper_trading.runner as runner_module

    state_path = tmp_path / "state" / "portfolio.json"
    runs_dir = tmp_path / "runs"
    monkeypatch.setattr(runner_module, "PORTFOLIO_STATE_PATH", state_path)
    monkeypatch.setattr(runner_module, "RUNS_DIR", runs_dir)
    monkeypatch.setattr(
        runner_module,
        "PORTFOLIO_SETTINGS",
        {
            "starting_cash": 100_000.0,
            "buy_pct": 0.10,
            "overweight_pct": 0.05,
            "underweight_sell_pct": 0.50,
            "commission": 0.0,
        },
    )
    monkeypatch.setattr(config_module, "PORTFOLIO_STATE_PATH", state_path)
    monkeypatch.setattr(config_module, "RUNS_DIR", runs_dir)

    fake_graph = MagicMock()
    fake_graph.propagate.return_value = ({"final_trade_decision": "**Rating**: Buy"}, "Buy")
    fake_graph.save_reports.return_value = None

    with (
        patch.object(runner_module, "TradingAgentsGraph", return_value=fake_graph),
        patch.object(runner_module, "get_latest_price", return_value=100.0),
    ):
        summary = runner_module.run_daily("2026-07-01", tickers=["AAPL"])

    assert summary["decisions"][0]["ticker"] == "AAPL"
    assert summary["decisions"][0]["rating"] == "Buy"
    assert summary["decisions"][0]["trade"]["action"] == "BUY"
    assert summary["portfolio"]["nav"] == pytest.approx(100_000.0)

    assert state_path.exists()
    saved = json.loads(state_path.read_text(encoding="utf-8"))
    assert saved["positions"]["AAPL"]["shares"] == pytest.approx(100.0)

    summary_json = runs_dir / "2026-07-01" / "summary.json"
    summary_md = runs_dir / "2026-07-01" / "summary.md"
    assert summary_json.exists()
    assert summary_md.exists()
    assert "AAPL" in summary_md.read_text(encoding="utf-8")


@pytest.mark.unit
def test_run_daily_records_ticker_error_without_aborting_other_tickers(tmp_path, monkeypatch):
    import paper_trading.runner as runner_module

    state_path = tmp_path / "state" / "portfolio.json"
    runs_dir = tmp_path / "runs"
    monkeypatch.setattr(runner_module, "PORTFOLIO_STATE_PATH", state_path)
    monkeypatch.setattr(runner_module, "RUNS_DIR", runs_dir)
    monkeypatch.setattr(
        runner_module,
        "PORTFOLIO_SETTINGS",
        {
            "starting_cash": 100_000.0,
            "buy_pct": 0.10,
            "overweight_pct": 0.05,
            "underweight_sell_pct": 0.50,
            "commission": 0.0,
        },
    )

    good_graph = MagicMock()
    good_graph.propagate.return_value = ({"final_trade_decision": "**Rating**: Hold"}, "Hold")

    def _graph_factory(*args, **kwargs):
        return good_graph

    with (
        patch.object(runner_module, "TradingAgentsGraph", side_effect=_graph_factory),
        patch.object(
            runner_module, "get_latest_price", side_effect=RuntimeError("no data")
        ),
    ):
        summary = runner_module.run_daily("2026-07-01", tickers=["BADTICKER", "AAPL"])

    errored, ok = summary["decisions"]
    assert errored["ticker"] == "BADTICKER"
    assert errored["error"] == "no data"
    assert ok["ticker"] == "AAPL"
    assert ok["rating"] == "Hold"
