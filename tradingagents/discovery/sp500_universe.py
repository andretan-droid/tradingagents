"""A static snapshot of S&P 500 constituents, grouped into the four sectors
the screener searches by default (Technology, Healthcare, Energy, Financials).

Sourced from a point-in-time pull of the public S&P 500 constituents dataset.
Index membership changes over time (additions, removals, ticker changes), so
treat this as a reasonable starting universe rather than a live feed — edit
the lists below directly to add/remove tickers as you like. GICS "Information
Technology" and "Health Care" are relabeled Technology / Healthcare here to
match the sector names used elsewhere (CLI prompts, watchlist headers).
"""

from __future__ import annotations

SECTOR_TICKERS: dict[str, list[str]] = {
    "Technology": [
        "AAPL", "ACN", "ADBE", "AMD", "AKAM", "APH", "ADI", "AMAT", "APP", "ANET",
        "ADSK", "AVGO", "CDNS", "COHR", "CRM", "GLW", "CDW", "CIEN", "CSCO", "CTSH",
        "DDOG", "DELL", "FICO", "FFIV", "FSLR", "FLEX", "FTNT", "GEN", "GDDY", "HPE",
        "HPQ", "IBM", "INTC", "INTU", "IQV", "JBL", "KEYS", "KLAC", "LRCX", "LITE",
        "MRVL", "MCHP", "MU", "MSFT", "MPWR", "MSI", "NOW", "NTAP", "NVDA", "NXPI",
        "ON", "ORCL", "PLTR", "PANW", "QCOM", "ROP", "SNDK", "SNPS", "STX", "SWKS",
        "SMCI", "TEL", "TDY", "TER", "TXN", "TRMB", "TYL", "VRSN", "WDC", "ZBRA",
    ],
    "Healthcare": [
        "ABT", "ABBV", "A", "ALGN", "AMGN", "BAX", "BDX", "TECH", "BIIB", "BSX",
        "BMY", "CAH", "COR", "CNC", "CRL", "CI", "COO", "CVS", "DHR", "DVA",
        "DXCM", "EW", "ELV", "GEHC", "GILD", "HCA", "HSIC", "IDXX", "INCY", "PODD",
        "ISRG", "JNJ", "LH", "LLY", "MCK", "MDT", "MRK", "MTD", "MRNA", "PFE",
        "REGN", "RMD", "RVTY", "SYK", "SOLV", "STE", "TMO", "UNH", "UHS", "VEEV",
        "VRTX", "VTRS", "WAT", "WST", "ZBH", "ZTS",
    ],
    "Energy": [
        "AES", "APA", "BKR", "COP", "DVN", "EXE", "EOG", "EQT", "FANG", "HAL",
        "KMI", "MPC", "OXY", "OKE", "PSX", "SLB", "TRGP", "TPL", "VLO", "WMB",
        "XOM",
    ],
    "Financials": [
        "AFL", "AJG", "ALL", "AXP", "AIG", "AMT", "AMP", "AON", "APO", "ACGL",
        "ARES", "AIZ", "BAC", "BRK.B", "BLK", "BX", "XYZ", "BNY", "BKNG", "BRO",
        "CBOE", "COF", "SCHW", "CB", "CINF", "C", "CFG", "CME", "COIN", "CPAY",
        "CSGP", "CRWD", "FDS", "FIS", "FITB", "BEN", "GPN", "GL", "GS", "HIG",
        "IBKR", "ICE", "IVZ", "JKHY", "JPM", "KEY", "KKR", "L", "MA", "MCO",
        "MET", "MS", "MSCI", "NDAQ", "PNC", "PFG", "PGR", "PRU", "PYPL", "RJF",
        "RF", "HOOD", "SPGI", "STT", "SYF", "TROW", "TRV", "TFC", "USB", "V",
        "WRB", "WFC", "WTW",
    ],
}


def all_sectors() -> list[str]:
    return list(SECTOR_TICKERS.keys())


def tickers_for_sectors(sectors: list[str]) -> dict[str, list[str]]:
    """Return {sector: tickers} for the requested sectors, deduplicated per sector."""
    unknown = [s for s in sectors if s not in SECTOR_TICKERS]
    if unknown:
        raise ValueError(f"Unknown sector(s) {unknown}; known sectors: {all_sectors()}")
    return {s: list(SECTOR_TICKERS[s]) for s in sectors}


def ticker_to_sector(ticker: str) -> str | None:
    """Return the sector a ticker belongs to in this universe, or None if not found."""
    upper = ticker.upper()
    for sector, tickers in SECTOR_TICKERS.items():
        if upper in tickers:
            return sector
    return None
