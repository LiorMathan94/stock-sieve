"""
Daily fundamentals fetch: yfinance primary, FMP fallback for tickers yfinance
can't serve. Run once a day (manually or via the GitHub Action), not on every
Streamlit page load, to stay within free API limits.

A failed ticker keeps its previous record (with its older `as_of` date) instead
of disappearing. If most tickers fail, nothing is written and the script exits
non-zero, so a blocked run can never wipe out good data.

Usage:
    python fetch_data.py            # full S&P 500 universe
    python fetch_data.py --limit 20 # quick sanity check on a subset
"""
import argparse
import json
import os
import sys
import time
from datetime import datetime, timezone
from io import StringIO

import pandas as pd
import requests
import yfinance as yf

import config

WIKI_HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; stock-sieve/1.0)"}
# After this many consecutive yfinance failures, assume Yahoo is blocking us
# and stop hammering it (retries would otherwise run for hours).
YAHOO_BLOCKED_AFTER = 10


def load_previous() -> dict:
    if not os.path.exists(config.DATA_FILE):
        return {}
    try:
        with open(config.DATA_FILE, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError) as exc:
        print(f"[previous] could not read {config.DATA_FILE}: {exc}", file=sys.stderr)
        return {}


def get_universe(previous: dict) -> list[str]:
    try:
        resp = requests.get(config.WIKIPEDIA_SP500_URL, headers=WIKI_HEADERS, timeout=15)
        resp.raise_for_status()
        table = pd.read_html(StringIO(resp.text))[0]
        tickers = [str(t).replace(".", "-") for t in table["Symbol"].tolist()]
        if len(tickers) < 400:
            raise ValueError(f"suspiciously short S&P 500 list: {len(tickers)} tickers")
        return tickers
    except Exception as exc:
        prev_tickers = [s["ticker"] for s in previous.get("stocks", [])]
        prev_tickers += previous.get("failed_tickers", [])
        if prev_tickers:
            print(f"[universe] Wikipedia failed ({exc}); reusing previous universe", file=sys.stderr)
            return prev_tickers
        print(f"[universe] Wikipedia failed ({exc}); using fallback list", file=sys.stderr)
        return list(config.FALLBACK_TICKERS)


def _round(value, ndigits=4):
    return round(value, ndigits) if isinstance(value, float) else value


def parse_yfinance_info(info: dict) -> dict | None:
    price = info.get("currentPrice") or info.get("regularMarketPrice")
    name = info.get("longName") or info.get("shortName")
    if not price or not name:
        return None

    # Computed from the dollar dividend so we don't depend on yfinance's
    # dividendYield units (which changed from fraction to percent across versions).
    rate = info.get("dividendRate")
    if rate is not None:
        dividend_yield = rate / price * 100
    elif info.get("trailingAnnualDividendRate") == 0:
        dividend_yield = 0.0  # confirmed non-payer, not missing data
    else:
        dividend_yield = None

    # yfinance sometimes reports book value per share for a different share
    # class than the traded price (e.g. BRK-B priced against BRK-A book
    # value), producing a near-zero P/B that isn't real. Discard those.
    pb_ratio = info.get("priceToBook")
    if pb_ratio is not None and 0 < pb_ratio < 0.05:
        pb_ratio = None

    roe = info.get("returnOnEquity")
    debt_to_equity = info.get("debtToEquity")  # yfinance reports this as a percent
    return {
        "name": name,
        "sector": info.get("sector"),
        "description": info.get("longBusinessSummary"),
        "price": price,
        "market_cap": info.get("marketCap"),
        "pe_ratio": info.get("trailingPE"),
        "pb_ratio": pb_ratio,
        "dividend_yield": dividend_yield,
        "roe": roe * 100 if roe is not None else None,
        "debt_to_equity": debt_to_equity / 100 if debt_to_equity is not None else None,
        "book_value_per_share": info.get("bookValue"),
        "free_cash_flow": info.get("freeCashflow"),
        "source": "yfinance",
    }


def fetch_from_yfinance(ticker: str) -> tuple[dict | None, bool]:
    """Returns (record, errored). errored=True means a request error, as
    opposed to Yahoo answering but lacking data for this ticker."""
    for attempt in range(1, config.YFINANCE_RETRIES + 1):
        try:
            return parse_yfinance_info(yf.Ticker(ticker).info), False
        except Exception as exc:
            print(f"[yfinance] {ticker} attempt {attempt}: {exc}", file=sys.stderr)
            if attempt < config.YFINANCE_RETRIES:
                time.sleep(config.YFINANCE_RETRY_BACKOFF * attempt)
    return None, True


def _pick(*sources_and_keys):
    """_pick((dict_a, "k1", "k2"), (dict_b, "k3")) -> first non-None value."""
    for source, *keys in sources_and_keys:
        for key in keys:
            if source.get(key) is not None:
                return source[key]
    return None


def fetch_from_fmp(ticker: str, calls_used: list[int]) -> dict | None:
    """Fallback for tickers yfinance couldn't serve (3 FMP calls per ticker).
    Field names vary between FMP API versions, so several spellings are tried."""
    if not config.FMP_API_KEY:
        return None
    if calls_used[0] + config.FMP_CALLS_PER_TICKER > config.FMP_MAX_CALLS_PER_RUN:
        print(f"[fmp] budget exhausted, skipping {ticker}", file=sys.stderr)
        return None

    def get(path: str) -> dict:
        calls_used[0] += 1
        try:
            resp = requests.get(
                f"{config.FMP_BASE_URL}/{path}",
                params={"symbol": ticker, "apikey": config.FMP_API_KEY},
                timeout=15,
            )
            resp.raise_for_status()
            data = resp.json()
            return data[0] if isinstance(data, list) and data else {}
        except Exception as exc:
            print(f"[fmp] {ticker} {path}: {exc}", file=sys.stderr)
            return {}

    profile = get("profile")
    price = profile.get("price")
    if not profile or not price:
        return None
    ratios = get("ratios-ttm")
    metrics = get("key-metrics-ttm")

    market_cap = _pick((profile, "marketCap", "mktCap"))
    fcf_per_share = _pick((metrics, "freeCashFlowPerShareTTM"), (ratios, "freeCashFlowPerShareTTM"))
    free_cash_flow = fcf_per_share * market_cap / price if fcf_per_share and market_cap else None
    div_fraction = _pick((ratios, "dividendYieldTTM", "dividendYielTTM"))
    roe_fraction = _pick((metrics, "returnOnEquityTTM"), (ratios, "returnOnEquityTTM"))

    return {
        "name": profile.get("companyName"),
        "sector": profile.get("sector"),
        "description": profile.get("description"),
        "price": price,
        "market_cap": market_cap,
        "pe_ratio": _pick((ratios, "priceToEarningsRatioTTM", "peRatioTTM")),
        "pb_ratio": _pick((ratios, "priceToBookRatioTTM")),
        "dividend_yield": div_fraction * 100 if div_fraction is not None else None,
        "roe": roe_fraction * 100 if roe_fraction is not None else None,
        "debt_to_equity": _pick((ratios, "debtToEquityRatioTTM", "debtEquityRatioTTM")),
        "book_value_per_share": _pick((metrics, "bookValuePerShareTTM"), (ratios, "bookValuePerShareTTM")),
        "free_cash_flow": free_cash_flow,
        "source": "fmp",
    }


def fetch_price_histories(tickers: list[str]) -> dict[str, list[dict]]:
    """Bulk weekly closes: one request per chunk instead of one per ticker."""
    histories = {}
    for start in range(0, len(tickers), config.PRICE_HISTORY_CHUNK):
        chunk = tickers[start : start + config.PRICE_HISTORY_CHUNK]
        try:
            df = yf.download(
                chunk, period=config.PRICE_HISTORY_PERIOD, interval=config.PRICE_HISTORY_INTERVAL,
                group_by="ticker", auto_adjust=True, progress=False, threads=True,
            )
        except Exception as exc:
            print(f"[history] chunk starting {chunk[0]} failed: {exc}", file=sys.stderr)
            continue
        for ticker in chunk:
            try:
                closes = df[ticker]["Close"] if isinstance(df.columns, pd.MultiIndex) else df["Close"]
                histories[ticker] = [
                    {"date": idx.strftime("%Y-%m-%d"), "close": round(float(close), 2)}
                    for idx, close in closes.dropna().items()
                ]
            except KeyError:
                pass
    return histories


def compute_flags(record: dict) -> dict:
    pe, pb = record.get("pe_ratio"), record.get("pb_ratio")
    div_yield, debt_eq = record.get("dividend_yield"), record.get("debt_to_equity")
    fcf = record.get("free_cash_flow")

    record["flag_pb_under_1"] = pb is not None and 0 < pb < 1
    record["flag_low_pe"] = pe is not None and 0 < pe < config.PE_MAX
    record["flag_high_dividend"] = div_yield is not None and div_yield > config.DIVIDEND_YIELD_MIN
    record["flag_low_debt"] = debt_eq is not None and debt_eq < config.DEBT_TO_EQUITY_MAX
    record["flag_positive_fcf"] = fcf is not None and fcf > 0
    record["value_score"] = sum(
        record[f]
        for f in (
            "flag_pb_under_1",
            "flag_low_pe",
            "flag_high_dividend",
            "flag_low_debt",
            "flag_positive_fcf",
        )
    )
    return record


def merge_results(
    universe: list[str], fresh: dict[str, dict], previous: dict, today: str
) -> tuple[list[dict], list[str]]:
    """Fresh records win; tickers that failed today fall back to their previous
    record (keeping its older as_of date). Returns (stocks, failed_tickers)."""
    prev_date = (previous.get("last_updated") or today)[:10]
    prev_by_ticker = {s["ticker"]: s for s in previous.get("stocks", [])}
    stocks, failed = [], []
    for ticker in universe:
        if ticker in fresh:
            stocks.append({**fresh[ticker], "as_of": today})
        elif ticker in prev_by_ticker:
            old = prev_by_ticker[ticker]
            stocks.append({**old, "as_of": old.get("as_of", prev_date)})
            failed.append(ticker)
        else:
            failed.append(ticker)
    return stocks, failed


def dedupe_share_classes(stocks: list[dict]) -> list[dict]:
    """Keep one listing per company (e.g. GOOGL over GOOG): the first one in
    universe order, which is the class Wikipedia lists first."""
    seen, result = set(), []
    for stock in stocks:
        if stock["name"] in seen:
            continue
        seen.add(stock["name"])
        result.append(stock)
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=None, help="Only fetch the first N tickers (testing)")
    parser.add_argument("--output", default=None, help="Output path (default: data file, or a sample file with --limit)")
    args = parser.parse_args()
    # A --limit test run must not replace the real 500-stock file.
    output_path = args.output or (config.SAMPLE_DATA_FILE if args.limit else config.DATA_FILE)

    previous = load_previous()
    universe = get_universe(previous)
    if args.limit:
        universe = universe[: args.limit]
    print(f"Fetching fundamentals for {len(universe)} tickers...")

    calls_used = [0]
    fresh: dict[str, dict] = {}
    consecutive_errors, yahoo_blocked = 0, False
    for i, ticker in enumerate(universe, 1):
        record = None
        if not yahoo_blocked:
            record, errored = fetch_from_yfinance(ticker)
            consecutive_errors = consecutive_errors + 1 if errored else 0
            if consecutive_errors >= YAHOO_BLOCKED_AFTER:
                print("[yfinance] too many consecutive errors; assuming blocked", file=sys.stderr)
                yahoo_blocked = True
            time.sleep(config.YFINANCE_REQUEST_DELAY)
        if record is None:
            record = fetch_from_fmp(ticker, calls_used)
        if record is not None:
            fresh[ticker] = {k: _round(v) for k, v in record.items()} | {"ticker": ticker}
        if i % 25 == 0 or i == len(universe):
            print(f"  {i}/{len(universe)} done ({i - len(fresh)} failed so far)")

    success_ratio = len(fresh) / len(universe) if universe else 0
    if success_ratio < config.MIN_SUCCESS_RATIO:
        print(
            f"Only {len(fresh)}/{len(universe)} tickers fetched ({success_ratio:.0%}); "
            f"keeping previous data untouched.",
            file=sys.stderr,
        )
        sys.exit(1)

    histories = fetch_price_histories(list(fresh))
    for ticker, record in fresh.items():
        record["price_history"] = histories.get(ticker, [])
        compute_flags(record)

    now = datetime.now(timezone.utc)
    stocks, failed = merge_results(universe, fresh, previous, now.date().isoformat())
    stocks = dedupe_share_classes(stocks)

    output = {"last_updated": now.isoformat(), "stocks": stocks, "failed_tickers": failed}
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=1)

    print(
        f"Wrote {len(stocks)} stocks to {output_path} "
        f"({len(fresh)} fresh, {len(failed)} failed, {calls_used[0]} FMP calls used)"
    )


if __name__ == "__main__":
    main()
