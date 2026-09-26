# Stock Sieve

A simple value/dividend stock screener for the S&P 500. Hebrew-first, English toggle. Free to run forever: one daily fetch script + a Streamlit app that only reads cached data.

## How it works

1. `fetch_data.py` runs once a day (via GitHub Actions), pulls fundamentals for
   every S&P 500 ticker from [yfinance](https://github.com/ranaroussi/yfinance),
   falling back to the [Financial Modeling Prep](https://financialmodelingprep.com/)
   free API for any ticker yfinance fails on, and writes everything to
   `data/stocks.json`.
2. `app.py` (Streamlit) only ever reads `data/stocks.json` — it never calls
   either API on page load, so there's no daily-limit risk from visitors.

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

If you don't set a key, `fetch_data.py` still works — it just can't recover
tickers that yfinance failed on that day (they're listed under
`failed_tickers` in `data/stocks.json` and simply missing from the app until
the next successful run).

## 2. Run fetch_data.py locally

```bash
pip install -r requirements.txt
export FMP_API_KEY=your_key_here   # optional but recommended
python fetch_data.py               # full S&P 500, ~10-15 minutes
python fetch_data.py --limit 20    # quick sanity check on a subset
```

This writes `data/stocks.json`. Commit that file so the deployed app has data
to read.

## 3. Schedule the daily fetch (GitHub Actions)

Already set up in `.github/workflows/daily_fetch.yml` — it runs daily at
06:00 UTC and commits the refreshed `data/stocks.json` back to the repo. Make
sure the `FMP_API_KEY` secret is set (step 1) and that Actions has permission
to push (Settings → Actions → General → Workflow permissions → "Read and
write permissions").

You can also trigger it manually from the Actions tab ("Run workflow").

## 4. Deploy app.py to Streamlit Community Cloud

1. Push this repo to GitHub.
2. Go to https://share.streamlit.io/, sign in, "New app".
3. Point it at this repo, branch `main`, main file `app.py`.
4. Deploy. The app reads `data/stocks.json` from the repo — no secrets
   needed for the app itself (only the fetch workflow needs `FMP_API_KEY`).

## Adding or removing tickers from the universe

The universe is the live S&P 500 list scraped from Wikipedia at fetch time
(`get_sp500_universe()` in `fetch_data.py`), so it updates automatically as
the index changes. To track a custom list instead, edit
`config.FALLBACK_TICKERS` and change `get_sp500_universe()` to return it
directly instead of scraping Wikipedia.

## Adding or fixing a translation string

All UI text lives in `translations.py` as a dict:

```python
"pe_ratio": {"he": "מכפיל רווח", "en": "P/E Ratio"},
```

Add a new key there, then reference it in `app.py` with `t("your_key", lang)`.
Company names, sectors, and descriptions come from the data API in English
and are intentionally left untranslated.

## Data notes

- Missing fields show as "N/A" / "לא זמין" rather than crashing the app.
- The "Value Score" column counts how many of 5 criteria a stock meets
  (P/B < 1, low P/E, high dividend yield, low debt/equity, positive free
  cash flow) — the table defaults to sorting by this, not any single metric.
- A low P/E or P/B alone doesn't mean a stock is a good buy — see the
  in-app disclaimer.
