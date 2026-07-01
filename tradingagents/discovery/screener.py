"""Cheap, non-LLM valuation screener over a sector universe.

Fetches trailing P/E and price-to-book from yfinance for every ticker in the
requested sectors, ranks each sector's tickers by how cheap they look
relative to their sector peers, and returns the top N per sector. This is a
numeric pre-filter only — no LLM calls — so it is safe (and nearly free) to
run across a couple hundred tickers before handing the handful of survivors
to the full multi-agent pipeline, which is where the real judgment call on
"is this actually a good buy" happens.

P/E and price-to-book live on very different scales (P/E is typically
10-40, P/B is typically 1-10), so a plain average of the raw numbers would
be dominated by whichever happens to be larger. Instead each metric is
converted to a rank *within its sector* (1 = cheapest by that metric) and
the ranks are averaged — a standard way to combine differently-scaled
valuation metrics without one silently overpowering the other.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

import yfinance as yf

from tradingagents.dataflows.stockstats_utils import yf_retry
from tradingagents.dataflows.symbol_utils import normalize_symbol
from tradingagents.discovery.sp500_universe import tickers_for_sectors

logger = logging.getLogger(__name__)


@dataclass
class ValuationCandidate:
    ticker: str
    sector: str
    pe_ratio: float | None
    price_to_book: float | None
    market_cap: float | None
    cheapness_rank: float  # lower = cheaper relative to sector peers


def fetch_valuation_metrics(ticker: str) -> dict | None:
    """Fetch trailing P/E, price-to-book, and market cap for one ticker.

    Returns ``None`` if the ticker's data is unavailable — the screener skips
    it rather than failing the whole scan over one bad symbol.
    """
    canonical = normalize_symbol(ticker)
    try:
        info = yf_retry(lambda: yf.Ticker(canonical).info)
    except Exception:
        logger.warning("Screener: could not fetch data for %s", ticker)
        return None
    if not info:
        return None
    return {
        "pe_ratio": info.get("trailingPE"),
        "price_to_book": info.get("priceToBook"),
        "market_cap": info.get("marketCap"),
    }


def _rank_ascending(values: dict[str, float]) -> dict[str, int]:
    """Rank tickers by value ascending (1 = smallest/cheapest). Only positive values are ranked."""
    positive = {t: v for t, v in values.items() if v is not None and v > 0}
    ordered = sorted(positive, key=lambda t: positive[t])
    return {ticker: i + 1 for i, ticker in enumerate(ordered)}


def rank_sector_by_cheapness(
    sector: str, metrics_by_ticker: dict[str, dict]
) -> list[ValuationCandidate]:
    """Rank a sector's tickers from cheapest to most expensive.

    Tickers with no usable P/E or P/B data at all are excluded — there is
    nothing to rank them on.
    """
    pe_ranks = _rank_ascending({t: m["pe_ratio"] for t, m in metrics_by_ticker.items()})
    pb_ranks = _rank_ascending({t: m["price_to_book"] for t, m in metrics_by_ticker.items()})

    candidates = []
    for ticker, metrics in metrics_by_ticker.items():
        ranks = [r[ticker] for r in (pe_ranks, pb_ranks) if ticker in r]
        if not ranks:
            continue
        candidates.append(
            ValuationCandidate(
                ticker=ticker,
                sector=sector,
                pe_ratio=metrics["pe_ratio"],
                price_to_book=metrics["price_to_book"],
                market_cap=metrics["market_cap"],
                cheapness_rank=sum(ranks) / len(ranks),
            )
        )
    candidates.sort(key=lambda c: c.cheapness_rank)
    return candidates


def screen_sectors(sectors: list[str], top_n_per_sector: int = 5) -> list[ValuationCandidate]:
    """Fetch + rank every ticker in the requested sectors; return the top N cheapest per sector.

    Network calls happen here (one yfinance lookup per ticker in the
    universe), so this is the slow, "scan the whole market" step — the
    caller typically runs it once per scheduled run, then only sends the
    returned candidates through the full agent pipeline.
    """
    universe = tickers_for_sectors(sectors)
    results: list[ValuationCandidate] = []
    for sector, tickers in universe.items():
        metrics_by_ticker = {}
        for ticker in tickers:
            metrics = fetch_valuation_metrics(ticker)
            if metrics is not None:
                metrics_by_ticker[ticker] = metrics

        ranked = rank_sector_by_cheapness(sector, metrics_by_ticker)
        results.extend(ranked[:top_n_per_sector])
        logger.info(
            "Screener: %s — %d/%d tickers had usable data, top %d selected",
            sector, len(metrics_by_ticker), len(tickers), min(top_n_per_sector, len(ranked)),
        )
    return results
