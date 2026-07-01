"""Tests for BacktestResult serialization and dashboard surfacing — no network."""

from __future__ import annotations

import json

import pytest

from tradingagents.backtest.result import BacktestResult, ClosedTrade
from tradingagents.dashboard.data import build_dashboard_data, latest_backtest_artifact


def _sample_result():
    return BacktestResult(
        config={"start_date": "2026-01-05", "end_date": "2026-01-16", "benchmark": "SPY"},
        dates=["2026-01-05", "2026-01-06"],
        equity_curve=[100_000.0, 105_000.0],
        benchmark_curve=[100_000.0, 101_000.0],
        closed_trades=[ClosedTrade("AAPL", "2026-01-05", "2026-01-06", 100.0, 110.0,
                                   500.0, 5_000.0, 0.10, 1, "sell")],
        open_positions=[],
        skipped=[],
        metrics={"total_return": 0.05, "alpha": 0.04},
        generated_at="20260105_120000",
    )


@pytest.mark.unit
def test_to_json_round_trips():
    result = _sample_result()
    payload = result.to_json()
    reloaded = json.loads(json.dumps(payload))  # must be JSON-serializable
    assert reloaded["metrics"]["total_return"] == 0.05
    assert reloaded["closed_trades"][0]["symbol"] == "AAPL"


@pytest.mark.unit
def test_write_produces_json_csv_and_latest(tmp_path):
    result = _sample_result()
    json_path, equity_path = result.write(str(tmp_path))

    assert json_path.exists()
    assert equity_path.exists()
    latest = tmp_path / "backtest" / "latest.json"
    assert latest.exists()
    assert json.loads(latest.read_text())["metrics"]["alpha"] == 0.04

    csv_text = equity_path.read_text()
    assert csv_text.splitlines()[0] == "date,equity,benchmark"
    assert "2026-01-05,100000.0,100000.0" in csv_text


@pytest.mark.unit
def test_latest_backtest_artifact_missing_returns_none(tmp_path):
    assert latest_backtest_artifact(str(tmp_path)) is None


@pytest.mark.unit
def test_build_dashboard_data_includes_latest_backtest(tmp_path):
    _sample_result().write(str(tmp_path))
    config = {"results_dir": str(tmp_path)}

    data = build_dashboard_data(config, broker=None)

    assert data["latest_backtest"] is not None
    assert data["latest_backtest"]["metrics"]["total_return"] == 0.05


@pytest.mark.unit
def test_build_dashboard_data_without_backtest(tmp_path):
    config = {"results_dir": str(tmp_path)}
    data = build_dashboard_data(config, broker=None)
    assert data["latest_backtest"] is None
