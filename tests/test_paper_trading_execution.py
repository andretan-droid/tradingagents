"""Tests for TradingAgentsGraph's paper-trading execution hook.

Constructs TradingAgentsGraph via __new__ (bypassing __init__, which compiles
the full LangGraph and creates LLM clients) and sets only the attributes the
methods under test touch, mirroring how default_config's ticker/benchmark
tables are consumed elsewhere in the codebase.
"""

from __future__ import annotations

import copy
from unittest.mock import MagicMock

import pytest

import tradingagents.default_config as default_config
from tradingagents.graph.trading_graph import TradingAgentsGraph


def _make_graph(**config_overrides):
    graph = TradingAgentsGraph.__new__(TradingAgentsGraph)
    graph.config = copy.deepcopy(default_config.DEFAULT_CONFIG)
    graph.config.update(config_overrides)
    graph._broker = None
    return graph


@pytest.mark.unit
def test_default_config_broker_off():
    assert default_config.DEFAULT_CONFIG["broker_enabled"] is False
    assert default_config.DEFAULT_CONFIG["broker_provider"] == "alpaca"
    assert default_config.DEFAULT_CONFIG["broker_order_notional_usd"] == 1000.0


@pytest.mark.unit
@pytest.mark.parametrize(
    "ticker,expected",
    [
        ("AAPL", True),
        ("NVDA", True),
        ("BRK.B", True),  # dotted US ticker, not a recognised non-US suffix
        ("0700.HK", False),
        ("RELIANCE.NS", False),
        ("AZN.L", False),
        ("XAUUSD", False),  # normalizes to GC=F (futures)
        ("EURUSD", False),  # normalizes to EURUSD=X (forex)
        ("SPX500", False),  # normalizes to ^GSPC (index)
    ],
)
def test_is_broker_tradeable_ticker(ticker, expected):
    graph = _make_graph()
    assert graph._is_broker_tradeable_ticker(ticker) is expected


@pytest.mark.unit
def test_maybe_execute_paper_trade_noop_when_disabled():
    graph = _make_graph(broker_enabled=False)
    graph._get_broker = MagicMock()

    graph._maybe_execute_paper_trade("AAPL", "Buy", "stock")

    graph._get_broker.assert_not_called()


@pytest.mark.unit
def test_maybe_execute_paper_trade_skips_crypto():
    graph = _make_graph(broker_enabled=True)
    graph._get_broker = MagicMock()

    graph._maybe_execute_paper_trade("BTC-USD", "Buy", "crypto")

    graph._get_broker.assert_not_called()


@pytest.mark.unit
def test_maybe_execute_paper_trade_skips_non_us_ticker():
    graph = _make_graph(broker_enabled=True)
    graph._get_broker = MagicMock()

    graph._maybe_execute_paper_trade("0700.HK", "Buy", "stock")

    graph._get_broker.assert_not_called()


@pytest.mark.unit
def test_maybe_execute_paper_trade_submits_buy_order():
    graph = _make_graph(broker_enabled=True, broker_order_notional_usd=250.0)
    broker = MagicMock()
    graph._get_broker = MagicMock(return_value=broker)

    graph._maybe_execute_paper_trade("AAPL", "Buy", "stock")

    broker.submit_market_order.assert_called_once_with(
        symbol="AAPL", side="buy", notional=250.0
    )


@pytest.mark.unit
def test_maybe_execute_paper_trade_hold_places_no_order():
    graph = _make_graph(broker_enabled=True)
    broker = MagicMock()
    graph._get_broker = MagicMock(return_value=broker)

    graph._maybe_execute_paper_trade("AAPL", "Hold", "stock")

    broker.submit_market_order.assert_not_called()


@pytest.mark.unit
def test_maybe_execute_paper_trade_swallows_broker_errors():
    graph = _make_graph(broker_enabled=True)
    graph._get_broker = MagicMock(side_effect=RuntimeError("network down"))

    # Must not raise: a broker outage must never fail a completed analysis run.
    graph._maybe_execute_paper_trade("AAPL", "Buy", "stock")


@pytest.mark.unit
def test_get_broker_rejects_unsupported_provider():
    graph = _make_graph(broker_provider="robinhood")
    with pytest.raises(ValueError, match="robinhood"):
        graph._get_broker()
