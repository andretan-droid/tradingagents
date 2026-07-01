"""Tests for the rating->order mapping used by paper-trading execution."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from tradingagents.execution.order_router import rating_to_side, route_decision


@pytest.mark.parametrize(
    "rating,expected",
    [
        ("Buy", "buy"),
        ("buy", "buy"),
        ("Overweight", "buy"),
        ("  BUY  ", "buy"),
        ("Sell", "sell"),
        ("Underweight", "sell"),
        ("Hold", None),
        ("hold", None),
        ("Nonsense", None),
        ("", None),
    ],
)
def test_rating_to_side(rating, expected):
    assert rating_to_side(rating) == expected


def test_route_decision_submits_buy_order():
    broker = MagicMock()
    broker.submit_market_order.return_value = "order-result"

    result = route_decision(broker, "AAPL", "Buy", 1000.0)

    broker.submit_market_order.assert_called_once_with(
        symbol="AAPL", side="buy", notional=1000.0
    )
    assert result == "order-result"


def test_route_decision_submits_sell_order():
    broker = MagicMock()

    route_decision(broker, "AAPL", "Underweight", 500.0)

    broker.submit_market_order.assert_called_once_with(
        symbol="AAPL", side="sell", notional=500.0
    )


def test_route_decision_hold_is_a_no_op():
    broker = MagicMock()

    result = route_decision(broker, "AAPL", "Hold", 1000.0)

    broker.submit_market_order.assert_not_called()
    assert result is None
