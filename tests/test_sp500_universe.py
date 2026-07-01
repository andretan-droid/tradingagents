"""Tests for the static S&P 500 sector universe used by the screener."""

from __future__ import annotations

import pytest

from tradingagents.discovery.sp500_universe import (
    SECTOR_TICKERS,
    all_sectors,
    ticker_to_sector,
    tickers_for_sectors,
)


@pytest.mark.unit
def test_all_sectors_matches_dict_keys():
    assert set(all_sectors()) == set(SECTOR_TICKERS.keys())


@pytest.mark.unit
def test_no_ticker_appears_in_two_sectors():
    seen: dict[str, str] = {}
    for sector, tickers in SECTOR_TICKERS.items():
        for ticker in tickers:
            assert ticker not in seen, f"{ticker} appears in both {seen.get(ticker)} and {sector}"
            seen[ticker] = sector


@pytest.mark.unit
def test_no_duplicate_tickers_within_a_sector():
    for sector, tickers in SECTOR_TICKERS.items():
        assert len(tickers) == len(set(tickers)), f"duplicate ticker(s) in {sector}"


@pytest.mark.unit
def test_tickers_for_sectors_returns_requested_subset():
    result = tickers_for_sectors(["Energy"])
    assert set(result.keys()) == {"Energy"}
    assert result["Energy"] == SECTOR_TICKERS["Energy"]


@pytest.mark.unit
def test_tickers_for_sectors_rejects_unknown_sector():
    with pytest.raises(ValueError, match="Unknown sector"):
        tickers_for_sectors(["NotASector"])


@pytest.mark.unit
@pytest.mark.parametrize(
    "ticker,expected_sector",
    [
        ("AAPL", "Technology"),
        ("MSFT", "Technology"),
        ("JPM", "Financials"),
        ("XOM", "Energy"),
        ("UNH", "Healthcare"),
        ("brk.b", "Financials"),  # case-insensitive
        ("NFLX", None),  # Communication Services, not one of our 4 sectors
        ("NOTATICKER", None),
    ],
)
def test_ticker_to_sector(ticker, expected_sector):
    assert ticker_to_sector(ticker) == expected_sector
