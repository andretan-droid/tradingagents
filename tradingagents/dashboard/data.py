"""Read-only data assembly for the local dashboard.

Deliberately has no Flask (or any web framework) import, so this module —
and its tests — work without the optional ``[dashboard]`` extra installed.
Combines live Alpaca account state with locally-written run artifacts
(``scripts/auto_trader.py``'s JSON summaries and equity-history CSV).
"""

from __future__ import annotations

import csv
import json
from pathlib import Path


def latest_run_artifact(results_dir: str) -> dict | None:
    """Return the most recent scripts/auto_trader.py run artifact, or None if none exist yet."""
    out_dir = Path(results_dir) / "auto_trader"
    if not out_dir.exists():
        return None
    files = sorted(out_dir.glob("*.json"))
    if not files:
        return None
    return json.loads(files[-1].read_text(encoding="utf-8"))


def equity_history(results_dir: str) -> list[dict]:
    """Return the equity-history CSV rows as dicts, oldest first. Empty list if none yet."""
    path = Path(results_dir) / "equity_history.csv"
    if not path.exists():
        return []
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def latest_backtest_artifact(results_dir: str) -> dict | None:
    """Return the most recent backtest report (backtest/latest.json), or None."""
    path = Path(results_dir) / "backtest" / "latest.json"
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None


def account_snapshot(broker) -> dict:
    account = broker.get_account()
    return {
        "equity": float(account.equity),
        "cash": float(account.cash),
        "buying_power": float(account.buying_power),
    }


def positions_snapshot(broker) -> list[dict]:
    positions = broker.list_positions()
    return [
        {
            "symbol": p.symbol,
            "qty": p.qty,
            "avg_entry_price": float(p.avg_entry_price),
            "market_value": float(p.market_value),
            "unrealized_pl": float(p.unrealized_pl),
        }
        for p in positions
    ]


def recent_orders_snapshot(broker, limit: int = 20) -> list[dict]:
    orders = broker.list_recent_orders(limit=limit)
    result = []
    for o in orders:
        result.append({
            "submitted_at": str(o.submitted_at)[:19] if o.submitted_at else "-",
            "symbol": o.symbol,
            "side": o.side.value if hasattr(o.side, "value") else str(o.side),
            "notional": float(o.notional) if o.notional else None,
            "status": o.status.value if hasattr(o.status, "value") else str(o.status),
        })
    return result


def build_dashboard_data(config: dict, broker) -> dict:
    """Assemble everything the dashboard page needs into one JSON-able dict.

    ``broker`` may be None (Alpaca not configured) — the local artifacts
    still render, just without live account/position/order data.
    """
    data: dict = {
        "account": None,
        "positions": [],
        "orders": [],
        "equity_history": equity_history(config["results_dir"]),
        "latest_run": latest_run_artifact(config["results_dir"]),
        "latest_backtest": latest_backtest_artifact(config["results_dir"]),
        "broker_error": None,
    }
    if broker is None:
        data["broker_error"] = "Alpaca not configured (set ALPACA_API_KEY / ALPACA_SECRET_KEY)."
        return data
    try:
        data["account"] = account_snapshot(broker)
        data["positions"] = positions_snapshot(broker)
        data["orders"] = recent_orders_snapshot(broker)
    except Exception as e:
        data["broker_error"] = str(e)
    return data
