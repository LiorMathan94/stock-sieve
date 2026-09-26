"""Shared configuration: universe source, value/dividend thresholds, file paths."""
import os

DATA_FILE = os.path.join(os.path.dirname(__file__), "data", "stocks.json")

FMP_API_KEY = os.environ.get("FMP_API_KEY", "")
FMP_BASE_URL = "https://financialmodelingprep.com/stable"

# Safety net only, used if the live Wikipedia S&P 500 list can't be fetched.
# Not a substitute for the real universe.
FALLBACK_TICKERS = [
    "AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "META", "BRK-B", "JPM", "JNJ", "XOM",
    "PG", "KO", "PEP", "T", "VZ", "WMT", "HD", "CVX", "ABBV", "PFE",
    "MRK", "BAC", "DIS", "CSCO", "INTC", "MCD", "IBM", "GE", "CAT", "MMM",
]

WIKIPEDIA_SP500_URL = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"

# How politely to treat Yahoo Finance between per-ticker calls (seconds).
YFINANCE_REQUEST_DELAY = 0.6

# Hard ceiling on FMP fallback calls per run, kept well under the 250/day free
# limit so a normal run still leaves headroom for a retry the same day.
FMP_MAX_CALLS_PER_RUN = 210
FMP_CALLS_PER_TICKER = 3  # profile + ratios-ttm + key-metrics-ttm

# Value/dividend screening thresholds used to compute the derived flags.
PE_MAX = 15
PB_MAX = 1.5
DIVIDEND_YIELD_MIN = 3.0  # percent
DEBT_TO_EQUITY_MAX = 1.0  # ratio, not percent

PRICE_HISTORY_PERIOD = "1y"
PRICE_HISTORY_INTERVAL = "1wk"
