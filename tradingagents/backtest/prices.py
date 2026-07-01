"""Historical price access for the backtester.

Batch-fetches adjusted daily Close series once per run and serves point-in-time
lookups. The benchmark's own trading sessions define the simulation calendar,
so we never reimplement a market holiday calendar.
"""

from __future__ import annotations

import datetime
import logging
from collections.abc import Iterable

import pandas as pd
import yfinance as yf

from tradingagents.dataflows.stockstats_utils import yf_retry
from tradingagents.dataflows.symbol_utils import normalize_symbol

logger = logging.getLogger(__name__)


def _to_date(value) -> datetime.date:
    if isinstance(value, datetime.datetime):
        return value.date()
    if isinstance(value, datetime.date):
        return value
    return datetime.datetime.strptime(str(value), "%Y-%m-%d").date()


class PriceProvider:
    """Point-in-time historical Close prices for a fixed set of tickers.

    Construct via :meth:`fetch` (does the network I/O) or directly from a
    ``{ticker: pandas.Series}`` mapping (used by tests, no network). Each series
    is indexed by ``datetime.date`` ascending. yfinance ``history()`` returns a
    split/dividend-adjusted series, i.e. total-return prices — the right basis
    for both the strategy and the benchmark curves.
    """

    def __init__(self, close_by_ticker: dict[str, pd.Series], benchmark: str = "SPY"):
        self._close: dict[str, pd.Series] = {}
        for ticker, series in close_by_ticker.items():
            self._close[ticker.upper()] = self._normalize_series(series)
        self.benchmark = benchmark.upper()
        self._missing = [t for t, s in self._close.items() if s.empty]

    @staticmethod
    def _normalize_series(series: pd.Series) -> pd.Series:
        if series is None or len(series) == 0:
            return pd.Series(dtype="float64")
        s = series.copy()
        s.index = [_to_date(idx) for idx in s.index]
        s = s[~pd.Index(s.index).duplicated(keep="last")]
        return s.sort_index()

    @classmethod
    def fetch(
        cls,
        tickers: Iterable[str],
        start: str,
        end: str,
        benchmark: str = "SPY",
        *,
        pad_days: int = 7,
    ) -> PriceProvider:
        """Fetch adjusted Close for each ticker + the benchmark over the range.

        ``end`` is padded by ``pad_days`` so an as-of lookup on the final
        simulation day (and any next-session roll) still resolves. Tickers with
        no data are stored as empty series and surfaced via ``missing_tickers``
        rather than aborting the whole run.
        """
        end_dt = datetime.datetime.strptime(end, "%Y-%m-%d")
        fetch_end = (end_dt + datetime.timedelta(days=pad_days + 1)).strftime("%Y-%m-%d")

        wanted = {t.upper() for t in tickers}
        wanted.add(benchmark.upper())

        close_by_ticker: dict[str, pd.Series] = {}
        for ticker in sorted(wanted):
            try:
                hist = yf_retry(
                    lambda t=ticker: yf.Ticker(normalize_symbol(t)).history(
                        start=start, end=fetch_end
                    )
                )
                close_by_ticker[ticker] = hist["Close"] if not hist.empty else pd.Series(dtype="float64")
            except Exception:
                logger.warning("Backtest price fetch failed for %s", ticker)
                close_by_ticker[ticker] = pd.Series(dtype="float64")

        return cls(close_by_ticker, benchmark=benchmark)

    @property
    def missing_tickers(self) -> list[str]:
        return list(self._missing)

    def has(self, ticker: str) -> bool:
        series = self._close.get(ticker.upper())
        return series is not None and not series.empty

    def asof(self, ticker: str, day: datetime.date) -> float | None:
        """Last available Close on or before ``day``; None if unavailable.

        Returns None when the ticker is unknown/empty or ``day`` precedes its
        first bar (so callers never price against a future/absent bar).
        """
        series = self._close.get(ticker.upper())
        if series is None or series.empty:
            return None
        day = _to_date(day)
        # Series index is sorted dates; find the rightmost index <= day.
        idx = pd.Index(series.index)
        pos = idx.searchsorted(day, side="right") - 1
        if pos < 0:
            return None
        return float(series.iloc[pos])

    def trading_days(self, start: str, end: str) -> list[datetime.date]:
        """The benchmark's actual session dates within [start, end], inclusive.

        This is the simulation clock: only days the market was open appear, so
        weekends/holidays are skipped without a hand-maintained calendar.
        """
        series = self._close.get(self.benchmark)
        if series is None or series.empty:
            return []
        start_d = _to_date(start)
        end_d = _to_date(end)
        return [d for d in series.index if start_d <= d <= end_d]
