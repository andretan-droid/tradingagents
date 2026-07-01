"""Tests for the dashboard's data-assembly layer (no Flask, no network)."""

from __future__ import annotations

import json
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from tradingagents.dashboard.data import (
    build_dashboard_data,
    equity_history,
    latest_run_artifact,
)


@pytest.mark.unit
def test_latest_run_artifact_returns_none_when_missing(tmp_path):
    assert latest_run_artifact(str(tmp_path)) is None


@pytest.mark.unit
def test_latest_run_artifact_returns_most_recent_by_filename(tmp_path):
    out_dir = tmp_path / "auto_trader"
    out_dir.mkdir()
    (out_dir / "2026-06-30.json").write_text(json.dumps({"date": "2026-06-30", "results": []}))
    (out_dir / "2026-07-01.json").write_text(json.dumps({"date": "2026-07-01", "results": []}))

    result = latest_run_artifact(str(tmp_path))

    assert result["date"] == "2026-07-01"


@pytest.mark.unit
def test_equity_history_returns_empty_when_missing(tmp_path):
    assert equity_history(str(tmp_path)) == []


@pytest.mark.unit
def test_equity_history_parses_csv_rows(tmp_path):
    path = tmp_path / "equity_history.csv"
    path.write_text("timestamp,equity,cash,buying_power\n2026-07-01T08:00:00,100000,50000,150000\n")

    rows = equity_history(str(tmp_path))

    assert rows == [{
        "timestamp": "2026-07-01T08:00:00", "equity": "100000",
        "cash": "50000", "buying_power": "150000",
    }]


@pytest.mark.unit
def test_build_dashboard_data_without_broker(tmp_path):
    config = {"results_dir": str(tmp_path)}

    data = build_dashboard_data(config, broker=None)

    assert data["account"] is None
    assert data["broker_error"] is not None
    assert data["equity_history"] == []
    assert data["latest_run"] is None


@pytest.mark.unit
def test_build_dashboard_data_with_broker(tmp_path):
    config = {"results_dir": str(tmp_path)}
    broker = MagicMock()
    broker.get_account.return_value = SimpleNamespace(equity=100000, cash=50000, buying_power=150000)
    broker.list_positions.return_value = [
        SimpleNamespace(symbol="AAPL", qty="10", avg_entry_price=150.0, market_value=1600.0, unrealized_pl=100.0)
    ]
    broker.list_recent_orders.return_value = [
        SimpleNamespace(submitted_at="2026-07-01T08:00:00", symbol="AAPL", side=SimpleNamespace(value="buy"),
                         notional=1500.0, status=SimpleNamespace(value="filled"))
    ]

    data = build_dashboard_data(config, broker=broker)

    assert data["broker_error"] is None
    assert data["account"] == {"equity": 100000.0, "cash": 50000.0, "buying_power": 150000.0}
    assert data["positions"][0]["symbol"] == "AAPL"
    assert data["orders"][0]["side"] == "buy"


@pytest.mark.unit
def test_build_dashboard_data_handles_broker_error(tmp_path):
    config = {"results_dir": str(tmp_path)}
    broker = MagicMock()
    broker.get_account.side_effect = Exception("connection refused")

    data = build_dashboard_data(config, broker=broker)

    assert data["broker_error"] == "connection refused"
