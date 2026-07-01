"""Unit tests for the paper-trading portfolio ledger and its sizing policy."""

from __future__ import annotations

import pytest

from paper_trading.portfolio import Portfolio

SETTINGS = {
    "buy_pct": 0.10,
    "overweight_pct": 0.05,
    "underweight_sell_pct": 0.50,
    "commission": 0.0,
}


@pytest.mark.unit
def test_buy_opens_a_new_position():
    portfolio = Portfolio.new(100_000.0)
    trade = portfolio.apply_rating("AAPL", "Buy", 200.0, "2026-07-01", SETTINGS, 100_000.0)

    assert trade.action == "BUY"
    assert trade.shares == pytest.approx(50.0)
    assert portfolio.positions["AAPL"].shares == pytest.approx(50.0)
    assert portfolio.positions["AAPL"].avg_cost == pytest.approx(200.0)
    assert portfolio.cash == pytest.approx(90_000.0)


@pytest.mark.unit
def test_overweight_adds_to_existing_position_and_updates_avg_cost():
    portfolio = Portfolio.new(100_000.0)
    portfolio.apply_rating("AAPL", "Buy", 200.0, "2026-07-01", SETTINGS, 100_000.0)
    nav = portfolio.nav({"AAPL": 220.0})

    trade = portfolio.apply_rating("AAPL", "Overweight", 220.0, "2026-07-02", SETTINGS, nav)

    assert trade.action == "BUY"
    position = portfolio.positions["AAPL"]
    assert position.shares == pytest.approx(72.9545, abs=1e-3)
    # avg cost should sit strictly between the two fill prices
    assert 200.0 < position.avg_cost < 220.0


@pytest.mark.unit
def test_hold_produces_no_trade():
    portfolio = Portfolio.new(100_000.0)
    trade = portfolio.apply_rating("AAPL", "Hold", 200.0, "2026-07-01", SETTINGS, 100_000.0)
    assert trade is None
    assert portfolio.cash == pytest.approx(100_000.0)
    assert portfolio.positions == {}


@pytest.mark.unit
def test_underweight_trims_half_the_position():
    portfolio = Portfolio.new(100_000.0)
    portfolio.apply_rating("AAPL", "Buy", 200.0, "2026-07-01", SETTINGS, 100_000.0)
    starting_shares = portfolio.positions["AAPL"].shares

    trade = portfolio.apply_rating(
        "AAPL", "Underweight", 210.0, "2026-07-02", SETTINGS, 100_000.0
    )

    assert trade.action == "SELL"
    assert trade.shares == pytest.approx(starting_shares * 0.5)
    assert portfolio.positions["AAPL"].shares == pytest.approx(starting_shares * 0.5)


@pytest.mark.unit
def test_sell_liquidates_the_entire_position():
    portfolio = Portfolio.new(100_000.0)
    portfolio.apply_rating("AAPL", "Buy", 200.0, "2026-07-01", SETTINGS, 100_000.0)

    trade = portfolio.apply_rating("AAPL", "Sell", 205.0, "2026-07-02", SETTINGS, 100_000.0)

    assert trade.action == "SELL"
    assert "AAPL" not in portfolio.positions


@pytest.mark.unit
@pytest.mark.parametrize("rating", ["Underweight", "Sell"])
def test_sell_side_rating_on_flat_position_is_a_no_op(rating):
    portfolio = Portfolio.new(100_000.0)
    trade = portfolio.apply_rating("AAPL", rating, 200.0, "2026-07-01", SETTINGS, 100_000.0)
    assert trade is None
    assert portfolio.cash == pytest.approx(100_000.0)


@pytest.mark.unit
def test_buy_is_capped_by_available_cash():
    portfolio = Portfolio.new(1_000.0)
    # buy_pct of a much larger "current_nav" than actual cash on hand must
    # still be capped by what's actually in the account.
    trade = portfolio.apply_rating("AAPL", "Buy", 50.0, "2026-07-01", SETTINGS, 1_000_000.0)
    assert trade.amount <= 1_000.0
    assert portfolio.cash >= 0.0


@pytest.mark.unit
def test_mark_to_market_snapshot():
    portfolio = Portfolio.new(100_000.0)
    portfolio.apply_rating("AAPL", "Buy", 200.0, "2026-07-01", SETTINGS, 100_000.0)

    snapshot = portfolio.mark_to_market({"AAPL": 210.0}, "2026-07-01")

    assert snapshot["cash"] == pytest.approx(90_000.0)
    assert snapshot["positions_value"] == pytest.approx(50.0 * 210.0)
    assert snapshot["nav"] == pytest.approx(90_000.0 + 50.0 * 210.0)
    assert portfolio.nav_history[-1] == snapshot


@pytest.mark.unit
def test_save_and_load_round_trip(tmp_path):
    portfolio = Portfolio.new(100_000.0)
    portfolio.apply_rating("AAPL", "Buy", 200.0, "2026-07-01", SETTINGS, 100_000.0)
    portfolio.mark_to_market({"AAPL": 205.0}, "2026-07-01")

    path = tmp_path / "portfolio.json"
    portfolio.save(path)
    reloaded = Portfolio.load_or_new(path, starting_cash=999.0)

    assert reloaded.cash == pytest.approx(portfolio.cash)
    assert reloaded.starting_cash == pytest.approx(100_000.0)
    assert reloaded.positions["AAPL"].shares == pytest.approx(50.0)
    assert len(reloaded.trade_history) == 1
    assert reloaded.nav_history == portfolio.nav_history


@pytest.mark.unit
def test_load_or_new_returns_fresh_portfolio_when_no_file(tmp_path):
    portfolio = Portfolio.load_or_new(tmp_path / "missing.json", starting_cash=5_000.0)
    assert portfolio.cash == pytest.approx(5_000.0)
    assert portfolio.positions == {}
    assert portfolio.trade_history == []


@pytest.mark.unit
def test_apply_rating_rejects_non_positive_price():
    portfolio = Portfolio.new(100_000.0)
    with pytest.raises(ValueError):
        portfolio.apply_rating("AAPL", "Buy", 0.0, "2026-07-01", SETTINGS, 100_000.0)
