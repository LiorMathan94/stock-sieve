"""
Daily fundamentals fetch: yfinance primary, FMP fallback for tickers yfinance
can't serve. Run once a day (manually or via the GitHub Action), not on every
Streamlit page load, to stay within free API limits.

Usage:
    python fetch_data.py            # full S&P 500 universe
    python fetch_data.py --limit 20 # quick sanity check on a subset
"""
import argparse
import json
import sys
import time
from datetime import datetime, timezone
from io import StringIO

import requests
import yfinance as yf

import config

WIKI_HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; stock-sieve/1.0)"}


def get_sp500_universe() -> list[str]:
    try:
        import pandas as pd

        resp = requests.get(config.WIKIPEDIA_SP500_URL, headers=WIKI_HEADERS, timeout=15)
        resp.raise_for_status()
        table = pd.read_html(StringIO(resp.text))[0]
        tickers = [str(t).replace(".", "-") for t in table["Symbol"].tolist()]
        if len(tickers) < 400:
            raise ValueError(f"suspiciously short S&P 500 list: {len(tickers)} tickers")
        return tickers
    except Exception as exc:
        print(f"[universe] Wikipedia fetch failed ({exc}); using fallback list", file=sys.stderr)
        return list(config.FALLBACK_TICKERS)


def fetch_price_history(ticker: str) -> list[dict]:
    try:
        hist = yf.Ticker(ticker).history(
            period=config.PRICE_HISTORY_PERIOD, interval=config.PRICE_HISTORY_INTERVAL
        )
        return [
            {"date": idx.strftime("%Y-%m-%d"), "close": round(float(row["Close"]), 2)}
            for idx, row in hist.iterrows()
        ]
    except Exception:
        return []


def fetch_from_yfinance(ticker: str) -> dict | None:
    try:
        info = yf.Ticker(ticker).info
    except Exception as exc:
        print(f"[yfinance] {ticker}: {exc}", file=sys.stderr)
        return None

    price = info.get("currentPrice") or info.get("regularMarketPrice")
    name = info.get("longName") or info.get("shortName")
    if price is None or name is None:
        return None

    debt_to_equity = info.get("debtToEquity")
    roe = info.get("returnOnEquity")

    # yfinance sometimes reports book value per share for a different share
    # class than the traded price (e.g. BRK-B priced against BRK-A book
    # value), producing a near-zero P/B that isn't real. Discard those.
    pb_ratio = info.get("priceToBook")
    if pb_ratio is not None and 0 < pb_ratio < 0.05:
        pb_ratio = None

    return {
        "name": name,
        "sector": info.get("sector"),
        "description": info.get("longBusinessSummary"),
        "price": price,
        "market_cap": info.get("marketCap"),
        "pe_ratio": info.get("trailingPE"),
        "pb_ratio": pb_ratio,
        "dividend_yield": info.get("dividendYield"),
        "roe": roe * 100 if roe is not None else None,
        "debt_to_equity": debt_to_equity / 100 if debt_to_equity is not None else None,
        "book_value_per_share": info.get("bookValue"),
        "free_cash_flow": info.get("freeCashflow"),
        "source": "yfinance",
    }


def fetch_from_fmp(ticker: str, calls_used: list[int]) -> dict | None:
    """Fallback for tickers yfinance couldn't serve. Uses 3 FMP calls per ticker
    (profile, ratios-ttm, key-metrics-ttm); caller tracks the budget."""
    if not config.FMP_API_KEY:
        return None
    if calls_used[0] + config.FMP_CALLS_PER_TICKER > config.FMP_MAX_CALLS_PER_RUN:
        print(f"[fmp] budget exhausted, skipping {ticker}", file=sys.stderr)
        return None

    def get(path: str) -> dict | None:
        calls_used[0] += 1
        try:
            resp = requests.get(
                f"{config.FMP_BASE_URL}/{path}",
                params={"symbol": ticker, "apikey": config.FMP_API_KEY},
                timeout=15,
            )
            resp.raise_for_status()
            data = resp.json()
            return data[0] if isinstance(data, list) and data else None
        except Exception as exc:
            print(f"[fmp] {ticker} {path}: {exc}", file=sys.stderr)
            return None

    profile = get("profile")
    if not profile:
        return None
    ratios = get("ratios-ttm") or {}
    metrics = get("key-metrics-ttm") or {}

    fcf_per_share = metrics.get("freeCashFlowPerShareTTM")
    shares_out = profile.get("mktCap") and profile.get("price") and profile["mktCap"] / profile["price"]
    free_cash_flow = fcf_per_share * shares_out if fcf_per_share and shares_out else None

    return {
        "name": profile.get("companyName"),
        "sector": profile.get("sector"),
        "description": profile.get("description"),
        "price": profile.get("price"),
        "market_cap": profile.get("mktCap"),
        "pe_ratio": ratios.get("priceToEarningsRatioTTM") or ratios.get("peRatioTTM"),
        "pb_ratio": ratios.get("priceToBookRatioTTM"),
        "dividend_yield": (ratios.get("dividendYieldTTM") or 0) * 100 if ratios.get("dividendYieldTTM") else None,
        "roe": (ratios.get("returnOnEquityTTM") or 0) * 100 if ratios.get("returnOnEquityTTM") else None,
        "debt_to_equity": ratios.get("debtToEquityRatioTTM"),
        "book_value_per_share": metrics.get("bookValuePerShareTTM"),
        "free_cash_flow": free_cash_flow,
        "source": "fmp",
    }


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


def fetch_one(ticker: str, calls_used: list[int]) -> dict | None:
    record = fetch_from_yfinance(ticker)
    if record is None:
        record = fetch_from_fmp(ticker, calls_used)
    if record is None:
        return None

    record["ticker"] = ticker
    record["price_history"] = fetch_price_history(ticker) if record["source"] == "yfinance" else []
    return compute_flags(record)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=None, help="Only fetch the first N tickers (testing)")
    args = parser.parse_args()

    universe = get_sp500_universe()
    if args.limit:
        universe = universe[: args.limit]
    print(f"Fetching fundamentals for {len(universe)} tickers...")

    calls_used = [0]
    stocks, failed = [], []
    for i, ticker in enumerate(universe, 1):
        record = fetch_one(ticker, calls_used)
        if record:
            stocks.append(record)
        else:
            failed.append(ticker)
        if i % 25 == 0 or i == len(universe):
            print(f"  {i}/{len(universe)} done ({len(failed)} failed so far)")
        time.sleep(config.YFINANCE_REQUEST_DELAY)

    output = {
        "last_updated": datetime.now(timezone.utc).isoformat(),
        "stocks": stocks,
        "failed_tickers": failed,
    }
    with open(config.DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"Wrote {len(stocks)} stocks to {config.DATA_FILE} ({len(failed)} failed, {calls_used[0]} FMP calls used)")


if __name__ == "__main__":
    main()
