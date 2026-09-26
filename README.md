# Stock Sieve

A simple value/dividend stock screener for the S&P 500. Hebrew-first, English toggle. Free to run forever: one daily fetch script + a Streamlit app that only reads cached data.

## How it works

1. `fetch_data.py` runs once per trading day (via GitHub Actions), pulls
   fundamentals for every S&P 500 ticker from
   [yfinance](https://github.com/ranaroussi/yfinance), falling back to the
   [Financial Modeling Prep](https://financialmodelingprep.com/) free API for
   any ticker yfinance fails on, and writes everything to `data/stocks.json`.
2. `app.py` (Streamlit) only ever reads `data/stocks.json` — it never calls
   either API on page load, so there's no daily-limit risk from visitors.

| File | What it does |
|---|---|
| `fetch_data.py` | Daily data pull, value flags, merge with the previous day's data |
| `screener.py` | Filtering, sorting and ranking (pure pandas, unit-tested) |
| `app.py` | Streamlit UI: layout, HTML table, stock page, RTL styling |
| `translations.py` | Every UI string, in Hebrew and English |
| `config.py` | Thresholds, paths, retry/timeout settings |

## 1. Get an FMP API key (fallback source)

yfinance is unofficial and occasionally rate-limits or blocks requests
(especially from shared IPs like GitHub Actions runners). When that happens
for a ticker, `fetch_data.py` falls back to FMP, so you want a key even
though it's rarely used:

1. Sign up free at https://site.financialmodelingprep.com/ (250 requests/day).
2. Copy your API key.
3. Set it as the `FMP_API_KEY` environment variable locally, and as a
   repository secret named `FMP_API_KEY` on GitHub (Settings → Secrets and
   variables → Actions → New repository secret) for the scheduled workflow.

## What happens when a fetch goes wrong

- **A few tickers fail**: they keep their previous day's data (the stock page
  shows a "data is as of …" note) and are listed under `failed_tickers`.
- **Most tickers fail** (e.g. Yahoo blocks the runner): nothing is written,
  the script exits with an error, and the GitHub Action fails — GitHub emails
  you. Yesterday's data stays in place.
- **Wikipedia is unreachable**: the previous day's ticker list is reused.
- **Data hasn't refreshed for 4+ days**: the app shows a warning banner, so a
  silently broken schedule doesn't go unnoticed.

## 2. Run fetch_data.py locally

```bash
pip install -r requirements.txt
export FMP_API_KEY=your_key_here   # optional but recommended
python fetch_data.py               # full S&P 500, ~15 minutes
python fetch_data.py --limit 20    # quick check; writes data/stocks.sample.json
```

A `--limit` run writes to `data/stocks.sample.json` (gitignored) so it can't
replace the real data file.

## 3. Schedule the daily fetch (GitHub Actions)

Already set up in `.github/workflows/daily_fetch.yml` — it runs at 06:00 UTC
Tuesday–Saturday (after each US trading day) and commits the refreshed
`data/stocks.json` back to the repo. Make sure the `FMP_API_KEY` secret is
set (step 1) and that Actions has permission to push (Settings → Actions →
General → Workflow permissions → "Read and write permissions").

You can also trigger it manually from the Actions tab ("Run workflow").

## 4. Deploy app.py to Streamlit Community Cloud

1. Go to https://share.streamlit.io/, sign in with GitHub, "New app".
2. Point it at this repo, branch `main`, main file `app.py`.
3. Deploy. The app reads `data/stocks.json` from the repo and picks up each
   daily refresh automatically — no secrets needed for the app itself.

## Using the app

- **Sort** by clicking any column header (click again to reverse). Missing
  values always sort last.
- **Filters** live in the sidebar. A slider left at its maximum means "no
  limit"; any active filter excludes stocks missing that metric.
- The current filters and sort are part of the page URL, so they survive
  opening a stock and coming back, switching language, and can be bookmarked
  or shared.
- Hover a column header for a plain-language explanation of the metric.
- A stock's page shows which of the 5 value criteria it meets.

## Adding or removing tickers from the universe

The universe is the live S&P 500 list scraped from Wikipedia at fetch time
(`get_universe()` in `fetch_data.py`), so it updates automatically as the
index changes. When a company has several share classes (GOOGL/GOOG) only the
first listing is kept. To track a custom list instead, change
`get_universe()` to return your own list.

## Adding or fixing a translation string

All UI text lives in `translations.py` as a dict:

```python
"col_pe": {"he": "מכפיל רווח", "en": "P/E"},
```

Add a new key there, then reference it in `app.py` with `t("your_key", lang)`.
Company names, sectors, and descriptions come from the data API in English
and are intentionally left untranslated.

## Tests

```bash
pip install -r requirements-dev.txt
pytest
```

They also run on GitHub on every push (`.github/workflows/tests.yml`).

## Data notes

- Missing fields show as "N/A" / "לא זמין" rather than crashing the app.
  Companies that pay no dividend show 0%, not N/A.
- The "Value Score" counts how many of 5 criteria a stock meets (P/B < 1,
  P/E < 15, dividend yield > 3%, debt/equity < 1, positive free cash flow;
  thresholds in `config.py`). Stocks with the same score are ordered by a
  composite percentile of P/E, P/B, yield, ROE and debt.
- A low P/E or P/B alone doesn't mean a stock is a good buy — see the
  in-app disclaimer.
