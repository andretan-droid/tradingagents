"""BacktestResult / ClosedTrade dataclasses and their JSON/CSV serialization.

Kept import-light (no broker/engine imports) so ``broker.py`` can import
``ClosedTrade`` from here without a circular dependency.
"""

from __future__ import annotations

import csv
import json
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path


@dataclass
class ClosedTrade:
    symbol: str
    entry_date: str  # ISO
    exit_date: str   # ISO
    entry_price: float
    exit_price: float
    shares: float
    pnl: float
    return_pct: float
    holding_days: int
    exit_reason: str  # "sell" | "max_hold" | "eod"


@dataclass
class BacktestResult:
    config: dict                     # echoed run params (source, dates, limits, cash, benchmark)
    dates: list[str]                 # ISO trading days
    equity_curve: list[float]
    benchmark_curve: list[float]     # buy-and-hold, same initial cash base
    closed_trades: list[ClosedTrade]
    open_positions: list[dict]       # {symbol, shares, market_value} at final close (usually empty)
    skipped: list[dict]              # {date, ticker, rating, reason} events not applied
    metrics: dict
    generated_at: str = field(default_factory=lambda: datetime.now().strftime("%Y%m%d_%H%M%S"))

    def to_json(self) -> dict:
        return {
            "config": self.config,
            "generated_at": self.generated_at,
            "metrics": self.metrics,
            "dates": self.dates,
            "equity_curve": self.equity_curve,
            "benchmark_curve": self.benchmark_curve,
            "closed_trades": [asdict(t) for t in self.closed_trades],
            "open_positions": self.open_positions,
            "skipped": self.skipped,
        }

    def write(self, results_dir: str) -> tuple[Path, Path]:
        """Write the timestamped JSON report + equity CSV, and refresh latest.json.

        Returns ``(json_path, equity_csv_path)``.
        """
        out_dir = Path(results_dir) / "backtest"
        out_dir.mkdir(parents=True, exist_ok=True)

        payload = self.to_json()
        json_path = out_dir / f"{self.generated_at}.json"
        json_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        # latest.json powers the dashboard's "Latest Backtest" section.
        (out_dir / "latest.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")

        equity_path = out_dir / f"{self.generated_at}_equity.csv"
        with open(equity_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["date", "equity", "benchmark"])
            for date, equity, bench in zip(
                self.dates, self.equity_curve, self.benchmark_curve, strict=False
            ):
                writer.writerow([date, equity, bench])

        return json_path, equity_path
