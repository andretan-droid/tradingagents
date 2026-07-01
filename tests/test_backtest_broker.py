"""Tests for SimulatedBroker share math and mark-to-market — no network."""

from __future__ import annotations

import datetime

import pytest

from tradingagents.backtest.broker import SimClock, SimulatedBroker


class _StubPrices:
    """Minimal PriceProvider stand-in: fixed price table keyed by (ticker, date)."""

    def __init__(self, table):
        self.table = table  # {(TICKER, date): price}

    def asof(self, ticker, day):
        return self.table.get((ticker.upper(), day))


D0 = datetime.date(2026, 1, 5)
D1 = datetime.date(2026, 1, 6)
D5 = datetime.date(2026, 1, 12)


@pytest.mark.unit
def test_buy_converts_notional_to_shares_and_debits_cash():
    prices = _StubPrices({("AAPL", D0): 100.0})
    clock = SimClock(D0)
    broker = SimulatedBroker(prices, clock, initial_cash=100_000.0)

    order = broker.submit_market_order("AAPL", "buy", 10_000.0)

    assert order.status == "filled"
    assert broker.cash == 90_000.0
    pos = broker.list_positions()[0]
    assert pos.symbol == "AAPL"
    assert pos.shares == 100.0            # 10_000 / 100
    assert pos.market_value == 10_000.0
    assert broker.get_account().equity == 100_000.0  # cash 90k + 10k position


@pytest.mark.unit
def test_whole_shares_floors_and_refunds_remainder():
    prices = _StubPrices({("AAPL", D0): 300.0})
    clock = SimClock(D0)
    broker = SimulatedBroker(prices, clock, initial_cash=100_000.0, whole_shares=True)

    broker.submit_market_order("AAPL", "buy", 1_000.0)  # 1000/300 = 3.33 -> 3 shares

    pos = broker.list_positions()[0]
    assert pos.shares == 3.0
    assert broker.cash == 100_000.0 - 900.0  # only 3*300 spent, remainder refunded


@pytest.mark.unit
def test_mark_to_market_follows_clock():
    prices = _StubPrices({("AAPL", D0): 100.0, ("AAPL", D1): 150.0})
    clock = SimClock(D0)
    broker = SimulatedBroker(prices, clock, initial_cash=100_000.0)
    broker.submit_market_order("AAPL", "buy", 10_000.0)  # 100 shares

    clock.date = D1  # price jumps to 150
    assert broker.list_positions()[0].market_value == 15_000.0
    assert broker.get_account().equity == 90_000.0 + 15_000.0


@pytest.mark.unit
def test_close_position_credits_proceeds_and_records_trade():
    prices = _StubPrices({("AAPL", D0): 100.0, ("AAPL", D5): 120.0})
    clock = SimClock(D0)
    broker = SimulatedBroker(prices, clock, initial_cash=100_000.0)
    broker.submit_market_order("AAPL", "buy", 10_000.0)  # 100 shares @ 100

    clock.date = D5
    order = broker.close_position("AAPL")

    assert order.status == "filled"
    assert broker.cash == 90_000.0 + 12_000.0  # 100 shares * 120
    assert broker.open_symbols() == []
    trade = broker.closed_trades[0]
    assert trade.symbol == "AAPL"
    assert trade.entry_price == 100.0
    assert trade.exit_price == 120.0
    assert trade.pnl == 2_000.0
    assert trade.holding_days == 7  # D0 -> D5 calendar days
    assert trade.exit_reason == "sell"


@pytest.mark.unit
def test_order_rejected_when_no_price():
    prices = _StubPrices({})  # no price for AAPL on D0
    broker = SimulatedBroker(prices, SimClock(D0), initial_cash=100_000.0)

    order = broker.submit_market_order("AAPL", "buy", 10_000.0)

    assert order.status == "rejected"
    assert broker.cash == 100_000.0
    assert broker.open_symbols() == []


@pytest.mark.unit
def test_force_close_tags_exit_reason():
    prices = _StubPrices({("AAPL", D0): 100.0, ("AAPL", D5): 110.0})
    clock = SimClock(D0)
    broker = SimulatedBroker(prices, clock, initial_cash=100_000.0)
    broker.submit_market_order("AAPL", "buy", 10_000.0)

    clock.date = D5
    broker.force_close("AAPL", exit_reason="max_hold")

    assert broker.closed_trades[0].exit_reason == "max_hold"
