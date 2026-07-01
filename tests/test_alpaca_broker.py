"""Alpaca paper-trading broker: credential checks and lazy-import behavior.

alpaca-py is imported lazily with a clear install hint when the [alpaca]
extra is absent, mirroring tests/test_bedrock_provider.py for langchain-aws.
"""

from __future__ import annotations

import sys

import pytest

from tradingagents.execution.alpaca_broker import AlpacaBroker, AlpacaNotConfigured


@pytest.mark.unit
def test_raises_when_credentials_missing(monkeypatch):
    monkeypatch.delenv("ALPACA_API_KEY", raising=False)
    monkeypatch.delenv("ALPACA_SECRET_KEY", raising=False)
    with pytest.raises(AlpacaNotConfigured):
        AlpacaBroker()


@pytest.mark.unit
def test_raises_when_only_one_credential_set(monkeypatch):
    monkeypatch.setenv("ALPACA_API_KEY", "key")
    monkeypatch.delenv("ALPACA_SECRET_KEY", raising=False)
    with pytest.raises(AlpacaNotConfigured):
        AlpacaBroker()


@pytest.mark.unit
def test_helpful_error_when_alpaca_py_absent(monkeypatch):
    import tradingagents.execution.alpaca_broker as ab

    monkeypatch.setattr(ab, "_TRADING_CLIENT_CLASS", None)
    monkeypatch.setitem(sys.modules, "alpaca.trading.client", None)  # force ImportError
    monkeypatch.setenv("ALPACA_API_KEY", "key")
    monkeypatch.setenv("ALPACA_SECRET_KEY", "secret")
    with pytest.raises(ImportError, match=r"alpaca-py"):
        AlpacaBroker()


@pytest.mark.unit
def test_construction_when_extra_installed(monkeypatch):
    pytest.importorskip("alpaca")
    import tradingagents.execution.alpaca_broker as ab

    monkeypatch.setattr(ab, "_TRADING_CLIENT_CLASS", None)
    monkeypatch.setenv("ALPACA_API_KEY", "key")
    monkeypatch.setenv("ALPACA_SECRET_KEY", "secret")
    broker = AlpacaBroker()
    assert broker._client is not None
