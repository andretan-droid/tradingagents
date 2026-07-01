"""Tests for the portfolio-aware order router's risk-limit logic (mocked broker, no network)."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from tradingagents.execution.portfolio_router import RiskLimits, route_portfolio_decision


def _position(symbol: str, market_value: float):
    return SimpleNamespace(symbol=symbol, market_value=market_value)


def _broker(equity: float, positions: list, notional_result=None, close_result=None):
    broker = MagicMock()
    broker.get_account.return_value = SimpleNamespace(equity=equity)
    broker.list_positions.return_value = positions
    broker.submit_market_order.return_value = notional_result or MagicMock()
    broker.close_position.return_value = close_result or MagicMock()
    return broker


@pytest.mark.unit
def test_hold_places_no_order():
    broker = _broker(equity=100_000, positions=[])
    result = route_portfolio_decision(broker, "AAPL", "Hold")
    assert result is None
    broker.submit_market_order.assert_not_called()
    broker.close_position.assert_not_called()


@pytest.mark.unit
def test_buy_sizes_order_as_pct_of_equity():
    broker = _broker(equity=100_000, positions=[])
    limits = RiskLimits(position_pct_per_trade=0.05, max_open_positions=15, max_sector_pct=0.35)

    route_portfolio_decision(broker, "AAPL", "Buy", limits=limits)

    broker.submit_market_order.assert_called_once_with(symbol="AAPL", side="buy", notional=5_000.0)


@pytest.mark.unit
def test_buy_skipped_when_already_holding():
    broker = _broker(equity=100_000, positions=[_position("AAPL", 5_000)])

    result = route_portfolio_decision(broker, "AAPL", "Overweight")

    assert result is None
    broker.submit_market_order.assert_not_called()


@pytest.mark.unit
def test_buy_skipped_at_max_open_positions():
    positions = [_position(f"T{i}", 1_000) for i in range(15)]
    broker = _broker(equity=100_000, positions=positions)
    limits = RiskLimits(max_open_positions=15)

    result = route_portfolio_decision(broker, "AAPL", "Buy", limits=limits)

    assert result is None
    broker.submit_market_order.assert_not_called()


@pytest.mark.unit
def test_buy_skipped_when_sector_cap_would_be_breached():
    # AAPL is Technology in the sp500_universe. Fill Technology exposure to
    # just under the 35% cap so a new 5%-of-equity order would breach it.
    positions = [_position("MSFT", 33_000)]  # also Technology
    broker = _broker(equity=100_000, positions=positions)
    limits = RiskLimits(position_pct_per_trade=0.05, max_sector_pct=0.35, max_open_positions=15)

    result = route_portfolio_decision(broker, "AAPL", "Buy", limits=limits)

    assert result is None
    broker.submit_market_order.assert_not_called()


@pytest.mark.unit
def test_buy_allowed_when_under_sector_cap():
    positions = [_position("MSFT", 10_000)]  # Technology, well under cap
    broker = _broker(equity=100_000, positions=positions)
    limits = RiskLimits(position_pct_per_trade=0.05, max_sector_pct=0.35, max_open_positions=15)

    route_portfolio_decision(broker, "AAPL", "Buy", limits=limits)

    broker.submit_market_order.assert_called_once_with(symbol="AAPL", side="buy", notional=5_000.0)


@pytest.mark.unit
def test_buy_skips_sector_cap_check_for_unknown_sector_ticker():
    broker = _broker(equity=100_000, positions=[])

    # ZZZZ isn't in the sp500_universe, so there's no sector to check —
    # it should still be allowed to buy (position-count cap still applies).
    route_portfolio_decision(broker, "ZZZZ", "Buy")

    broker.submit_market_order.assert_called_once()


@pytest.mark.unit
def test_sell_closes_position_when_held():
    broker = _broker(equity=100_000, positions=[_position("AAPL", 5_000)])

    route_portfolio_decision(broker, "AAPL", "Sell")

    broker.close_position.assert_called_once_with("AAPL")
    broker.submit_market_order.assert_not_called()


@pytest.mark.unit
def test_sell_skipped_when_not_holding():
    broker = _broker(equity=100_000, positions=[])

    result = route_portfolio_decision(broker, "AAPL", "Underweight")

    assert result is None
    broker.close_position.assert_not_called()
