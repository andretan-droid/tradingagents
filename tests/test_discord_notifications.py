"""Tests for Discord webhook notifications (network calls mocked)."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from tradingagents.notifications.discord import (
    format_run_summary,
    format_trade_message,
    send_discord_message,
)


@pytest.mark.unit
def test_send_discord_message_no_webhook_configured(monkeypatch):
    monkeypatch.delenv("DISCORD_WEBHOOK_URL", raising=False)
    with patch("tradingagents.notifications.discord.requests.post") as mock_post:
        result = send_discord_message("hello")
    assert result is False
    mock_post.assert_not_called()


@pytest.mark.unit
def test_send_discord_message_posts_to_webhook():
    with patch("tradingagents.notifications.discord.requests.post") as mock_post:
        mock_post.return_value = SimpleNamespace(raise_for_status=lambda: None)
        result = send_discord_message("hello", webhook_url="https://discord.example/webhook")
    assert result is True
    mock_post.assert_called_once_with(
        "https://discord.example/webhook", json={"content": "hello"}, timeout=10
    )


@pytest.mark.unit
def test_send_discord_message_returns_false_on_failure():
    with patch("tradingagents.notifications.discord.requests.post", side_effect=Exception("boom")):
        result = send_discord_message("hello", webhook_url="https://discord.example/webhook")
    assert result is False


@pytest.mark.unit
def test_format_trade_message_includes_key_fields():
    order = MagicMock(side="buy", notional=1234.5, status="filled", order_id="abc123")
    message = format_trade_message("AAPL", "Buy", order)
    assert "AAPL" in message
    assert "BUY" in message
    assert "$1,234.50" in message
    assert "abc123" in message


@pytest.mark.unit
def test_format_trade_message_handles_full_position_close():
    order = MagicMock(side="sell", notional=None, status="filled", order_id="xyz")
    message = format_trade_message("AAPL", "Sell", order)
    assert "full position" in message


@pytest.mark.unit
def test_format_run_summary_counts_and_lists_orders():
    results = [
        {"ticker": "AAPL", "sector": "Technology", "rating": "Buy", "action": "BUY", "error": ""},
        {"ticker": "MSFT", "sector": "Technology", "rating": "Hold", "action": "HOLD", "error": ""},
        {"ticker": "BADCO", "sector": "Energy", "rating": "", "action": "", "error": "boom"},
    ]
    summary = format_run_summary(results)
    assert "2/3 analyzed" in summary
    assert "1 order(s) placed" in summary
    assert "1 failed" in summary
    assert "AAPL (Technology): Buy → BUY" in summary
    assert "BADCO: boom" in summary
