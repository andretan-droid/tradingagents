# Paper Trading Agent

A daily-driven, paper-money investment agent built on top of the
TradingAgents multi-agent pipeline in this repo. Every day, for each ticker
in a watchlist, the full analyst/researcher/risk/portfolio-manager pipeline
runs and produces a rating; that rating is executed as a simulated trade
against a virtual portfolio (no real brokerage, no real money). Results are
viewable in a Streamlit dashboard.

**This is a research/education tool, not investment advice.** Trading
performance depends heavily on the chosen LLM, data quality, and other
non-deterministic factors -- see the root README's "Reproducibility"
section.

## What runs for each ticker

The existing TradingAgents graph, unmodified:

- **Analyst team**: Market (technical) Analyst, Sentiment Analyst (news +
  StockTwits + Reddit), News Analyst (macro), Fundamentals Analyst.
- **Researcher team**: Bull Researcher vs. Bear Researcher debate, judged by
  the Research Manager.
- **Risk management**: Aggressive / Conservative / Neutral risk analysts
  debate the trader's proposal.
- **Portfolio Manager**: renders the final 5-tier rating (Buy / Overweight /
  Hold / Underweight / Sell).

This package (`paper_trading/`) adds the piece the base framework
intentionally leaves out: turning that rating into an actual simulated
buy/sell against a tracked cash+positions ledger, on a schedule, across a
list of candidate tickers.

## Position sizing policy (v1)

Deliberately simple -- long-only, fractional shares, no leverage, no
target-weight rebalancing:

| Rating | Action |
| --- | --- |
| Buy | Spend `buy_pct` (default 10%) of portfolio NAV opening/adding to the position |
| Overweight | Spend `overweight_pct` (default 5%) of NAV adding to the position |
| Hold | No trade |
| Underweight | Sell `underweight_sell_pct` (default 50%) of the current share count |
| Sell | Liquidate the entire position |

All fills use the latest available close price (no slippage, no partial
fills). Tune via env vars in `.env` (see `paper_trading/config.py`):
`PAPER_TRADING_STARTING_CASH`, `PAPER_TRADING_BUY_PCT`,
`PAPER_TRADING_OVERWEIGHT_PCT`, `PAPER_TRADING_UNDERWEIGHT_SELL_PCT`,
`PAPER_TRADING_COMMISSION`.

## Watchlist ("hidden gems" candidates)

Edit the `WATCHLIST` list in `paper_trading/config.py`. Each entry is a
ticker in Yahoo Finance's convention (see the root README's "Markets and
tickers"):

- US: bare ticker, e.g. `AAPL`
- Singapore Exchange (SGX): `.SI` suffix, e.g. `D05.SI` (DBS Group)
- Bursa Malaysia: `.KL` suffix, e.g. `1155.KL` (Maybank)

Keep this list short: **one full multi-agent run happens per ticker per
day**, so a longer list means a longer/slower/more expensive daily run.
There is no automated stock screener in v1 -- you curate the candidates
yourself and the agent tells you what it thinks about each one.

## Running it yourself

```bash
pip install -e .
cp .env.example .env   # fill in the LLM provider you're using
python -m paper_trading.runner                       # today, full watchlist
python -m paper_trading.runner --date 2026-07-01      # a specific date
python -m paper_trading.runner --tickers AAPL,NVDA    # override the watchlist
```

This writes/updates:

- `paper_trading/state/portfolio.json` -- cash, positions, trade history, NAV history
- `paper_trading/state/trading_memory.md` -- the framework's decision log/reflection memory, redirected here (instead of the default `~/.tradingagents`) so it persists across runs/commits
- `paper_trading/runs/<date>/<ticker>/complete_report.md` (+ per-section files) -- the full agent report, same shape the CLI produces
- `paper_trading/runs/<date>/summary.{json,md}` -- that day's ratings/trades across the whole watchlist

## Dashboard

```bash
pip install -e ".[dashboard]"
streamlit run dashboard/app.py
```

Shows current cash/positions/NAV history/trade history, plus a date picker
to browse any day's ratings and drill into a ticker's full agent report.

## Choosing an LLM provider (you said you have no API credits)

The underlying framework already supports free/no-cost options:

- **Ollama (local, free, no API key)**: works well for running this
  yourself on your own machine, where you control the compute. Set
  `TRADINGAGENTS_LLM_PROVIDER=ollama` and pull a model capable of reliable
  tool-calling (the analysts fetch data via tool calls) -- 8B+ parameter
  models are recommended; see the root README's Ollama section and the
  in-CLI model list. Small (1-3B) models are fast but frequently fail at
  tool-calling and will produce broken/incomplete reports.
- **A free-tier hosted API (e.g. OpenRouter)**: sign up for a free API key
  (no card required) and use one of their free-tier models. This is what
  the GitHub Actions workflow below is set up for, since Actions runners are
  shared 2-core/7GB CPU-only machines -- not enough to run an 8B+ Ollama
  model through the ~15-20 LLM calls a single ticker's full pipeline makes
  in reasonable time. Check OpenRouter's current free-model listing and set
  `TRADINGAGENTS_DEEP_THINK_LLM` / `TRADINGAGENTS_QUICK_THINK_LLM` to the
  model slug you want (e.g. `some-provider/some-model:free`).

Either way, nothing else in this package changes -- the provider is
entirely controlled by the standard `TRADINGAGENTS_*` env vars / `.env`
that the rest of the repo already uses.

## Daily automation via GitHub Actions

`.github/workflows/daily_paper_trading.yml` runs the pipeline on a
schedule (weekdays, 22:00 UTC by default) and commits the updated
`paper_trading/state/` and `paper_trading/runs/` back to the repo, so the
dashboard always reflects the latest run. It also supports a manual
"Run workflow" trigger with optional `date`/`tickers` inputs.

Scheduled workflows only fire from the repo's **default branch** -- merge
this feature before expecting the schedule to run; use "Run workflow" to
test it beforehand.

Before it will do anything useful, set these under repo *Settings ->
Secrets and variables -> Actions*:

- **Variables**: `TRADINGAGENTS_LLM_PROVIDER` (e.g. `openrouter`),
  `TRADINGAGENTS_DEEP_THINK_LLM`, `TRADINGAGENTS_QUICK_THINK_LLM`
- **Secrets**: whichever API key matches your provider (e.g.
  `OPENROUTER_API_KEY`)

Without these, the job falls back to the base framework's default
(`openai` + a paid model) and will fail for lack of an API key -- that's
intentional: it fails loudly rather than silently guessing a model that
might not exist or might no longer be free.

## Known limitations (v1)

- No automated stock screening -- candidates are a manually curated
  watchlist.
- No short selling, no leverage, no fractional-share rounding beyond 4
  decimal places, no transaction-cost modeling beyond a flat optional
  commission.
- Fills use the latest daily close, not real intraday execution.
- A ticker whose data fetch or LLM call fails is recorded with an error in
  that day's summary and skipped for trading purposes; it does not block
  the rest of the watchlist.
