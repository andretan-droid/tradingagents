"""Tests for paper_trading config env-var overrides."""

from __future__ import annotations

import importlib

import pytest


@pytest.mark.unit
def test_starting_cash_env_override(monkeypatch):
    monkeypatch.setenv("PAPER_TRADING_STARTING_CASH", "50000")
    import paper_trading.config as config_module

    importlib.reload(config_module)
    try:
        assert config_module.PORTFOLIO_SETTINGS["starting_cash"] == 50_000.0
    finally:
        monkeypatch.delenv("PAPER_TRADING_STARTING_CASH", raising=False)
        importlib.reload(config_module)


@pytest.mark.unit
def test_default_watchlist_is_nonempty_and_well_formed():
    from paper_trading.config import WATCHLIST

    assert len(WATCHLIST) > 0
    for row in WATCHLIST:
        assert row["ticker"]
        assert row["market"]


@pytest.mark.unit
def test_state_and_runs_dirs_are_inside_the_paper_trading_package():
    from paper_trading.config import RUNS_DIR, STATE_DIR

    assert "paper_trading" in str(STATE_DIR)
    assert "paper_trading" in str(RUNS_DIR)
