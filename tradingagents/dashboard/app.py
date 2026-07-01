"""Local Flask dashboard: live Alpaca account/positions/orders, the latest
``scripts/auto_trader.py`` run, and an equity-history chart.

Optional ``[dashboard]`` extra (``pip install ".[dashboard]"``); Flask is
imported lazily so the rest of the package doesn't require it, mirroring the
alpaca-py / langchain-aws lazy-import pattern used elsewhere.
"""

from __future__ import annotations

from typing import Any

from tradingagents.dashboard.data import build_dashboard_data
from tradingagents.default_config import DEFAULT_CONFIG


def _import_flask():
    try:
        from flask import Flask, jsonify, render_template
    except ImportError as exc:
        raise ImportError(
            "The dashboard requires the optional 'flask' dependency. "
            'Install it with: pip install "tradingagents[dashboard]"'
        ) from exc
    return Flask, jsonify, render_template


def _make_broker():
    try:
        from tradingagents.execution.alpaca_broker import AlpacaBroker

        return AlpacaBroker()
    except Exception:
        return None


def create_app(config: dict[str, Any] | None = None):
    """Build and return the Flask app (factory, so it's testable without running a server)."""
    Flask, jsonify, render_template = _import_flask()
    config = config or DEFAULT_CONFIG

    app = Flask(__name__)

    @app.route("/")
    def index():
        data = build_dashboard_data(config, _make_broker())
        return render_template("index.html", data=data)

    @app.route("/api/data")
    def api_data():
        data = build_dashboard_data(config, _make_broker())
        return jsonify(data)

    return app


def run(host: str = "127.0.0.1", port: int = 5000) -> None:
    """Start the dashboard's development server. Local-only by default (127.0.0.1)."""
    app = create_app()
    app.run(host=host, port=port, debug=False)
