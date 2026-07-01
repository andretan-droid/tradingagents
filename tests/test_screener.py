"""Tests for the non-LLM valuation screener's ranking logic (no network calls)."""

from __future__ import annotations

from unittest.mock import patch

import pytest

from tradingagents.discovery.screener import (
    _rank_ascending,
    rank_sector_by_cheapness,
    screen_sectors,
)


@pytest.mark.unit
def test_rank_ascending_orders_lowest_first():
    ranks = _rank_ascending({"A": 30.0, "B": 10.0, "C": 20.0})
    assert ranks == {"B": 1, "C": 2, "A": 3}


@pytest.mark.unit
def test_rank_ascending_excludes_non_positive_and_none():
    ranks = _rank_ascending({"A": 10.0, "B": None, "C": -5.0, "D": 0.0})
    assert ranks == {"A": 1}


@pytest.mark.unit
def test_rank_sector_by_cheapness_orders_by_combined_pe_pb_rank():
    metrics = {
        "CHEAP": {"pe_ratio": 8.0, "price_to_book": 1.0, "market_cap": 1e9},
        "PRICEY": {"pe_ratio": 40.0, "price_to_book": 10.0, "market_cap": 1e9},
        "MID": {"pe_ratio": 20.0, "price_to_book": 5.0, "market_cap": 1e9},
    }
    ranked = rank_sector_by_cheapness("Technology", metrics)
    assert [c.ticker for c in ranked] == ["CHEAP", "MID", "PRICEY"]
    assert ranked[0].cheapness_rank < ranked[-1].cheapness_rank


@pytest.mark.unit
def test_rank_sector_by_cheapness_uses_whichever_metric_is_available():
    # PE-only and PB-only tickers should still rank against each other.
    metrics = {
        "PE_ONLY": {"pe_ratio": 10.0, "price_to_book": None, "market_cap": None},
        "PB_ONLY": {"pe_ratio": None, "price_to_book": 2.0, "market_cap": None},
        "NO_DATA": {"pe_ratio": None, "price_to_book": None, "market_cap": None},
    }
    ranked = rank_sector_by_cheapness("Technology", metrics)
    tickers = [c.ticker for c in ranked]
    assert "NO_DATA" not in tickers
    assert set(tickers) == {"PE_ONLY", "PB_ONLY"}


@pytest.mark.unit
def test_screen_sectors_returns_top_n_per_sector():
    fake_metrics = {
        "A": {"pe_ratio": 5.0, "price_to_book": 1.0, "market_cap": 1e9},
        "B": {"pe_ratio": 50.0, "price_to_book": 20.0, "market_cap": 1e9},
    }

    def fake_fetch(ticker):
        return fake_metrics.get(ticker)

    with (
        patch(
            "tradingagents.discovery.screener.tickers_for_sectors",
            return_value={"Energy": ["A", "B"]},
        ),
        patch("tradingagents.discovery.screener.fetch_valuation_metrics", side_effect=fake_fetch),
    ):
        results = screen_sectors(["Energy"], top_n_per_sector=1)

    assert len(results) == 1
    assert results[0].ticker == "A"
    assert results[0].sector == "Energy"


@pytest.mark.unit
def test_screen_sectors_skips_tickers_with_no_data():
    with (
        patch(
            "tradingagents.discovery.screener.tickers_for_sectors",
            return_value={"Energy": ["A", "B"]},
        ),
        patch("tradingagents.discovery.screener.fetch_valuation_metrics", return_value=None),
    ):
        results = screen_sectors(["Energy"], top_n_per_sector=5)

    assert results == []
