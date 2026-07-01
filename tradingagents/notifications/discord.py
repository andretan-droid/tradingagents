"""Discord webhook notifications for paper trades and daily run summaries.

A notification failure (bad webhook URL, Discord outage, network blip) must
never break the trading pipeline that's already completed — every function
here logs and swallows errors instead of raising.
"""

from __future__ import annotations

import logging
import os

import requests

logger = logging.getLogger(__name__)

_DISCORD_MESSAGE_LIMIT = 2000


def send_discord_message(content: str, webhook_url: str | None = None) -> bool:
    """POST a message to a Discord webhook. Returns True on success, False otherwise."""
    url = webhook_url or os.environ.get("DISCORD_WEBHOOK_URL")
    if not url:
        logger.info("DISCORD_WEBHOOK_URL not set; skipping Discord notification.")
        return False

    if len(content) > _DISCORD_MESSAGE_LIMIT:
        content = content[: _DISCORD_MESSAGE_LIMIT - 20] + "\n... (truncated)"

    try:
        response = requests.post(url, json={"content": content}, timeout=10)
        response.raise_for_status()
        return True
    except Exception:
        logger.exception("Failed to send Discord notification.")
        return False


def format_trade_message(ticker: str, rating: str, order_result) -> str:
    """Format a single order-placed notification.

    ``order_result`` is the OrderResult returned by AlpacaBroker
    (submit_market_order or close_position) — duck-typed here so this
    doesn't import the broker module just for a type hint.
    """
    notional = f"${order_result.notional:,.2f}" if order_result.notional else "(full position)"
    emoji = "\U0001f7e2" if order_result.side == "buy" else "\U0001f534"
    return (
        f"{emoji} **{order_result.side.upper()} {ticker}** — {notional}\n"
        f"Rating: {rating} · Status: {order_result.status} · Order ID: `{order_result.order_id}`"
    )


def format_run_summary(results: list[dict]) -> str:
    """Format a daily-run digest from a list of {ticker, sector, rating, action, error} dicts."""
    ok = [r for r in results if not r.get("error")]
    failed = [r for r in results if r.get("error")]
    orders = [r for r in ok if r.get("action") in ("BUY", "SELL")]

    lines = [
        "**TradingAgents daily run summary**",
        f"{len(ok)}/{len(results)} analyzed · {len(orders)} order(s) placed · {len(failed)} failed",
        "",
    ]
    for r in orders:
        lines.append(f"- {r['ticker']} ({r.get('sector', '?')}): {r['rating']} → {r['action']}")
    if failed:
        lines.append("")
        lines.append("Failed:")
        for r in failed:
            lines.append(f"- {r['ticker']}: {r['error']}")
    return "\n".join(lines)
