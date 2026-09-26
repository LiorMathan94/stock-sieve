"""Shared configuration: universe source, value/dividend thresholds, file paths."""
import os

DATA_FILE = os.path.join(os.path.dirname(__file__), "data", "stocks.json")
SAMPLE_DATA_FILE = os.path.join(os.path.dirname(__file__), "data", "stocks.sample.json")

FMP_API_KEY = os.environ.get("FMP_API_KEY", "")
FMP_BASE_URL = "https://financialmodelingprep.com/stable"

WIKIPEDIA_SP500_URL = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"
WIKIPEDIA_SP400_URL = "https://en.wikipedia.org/wiki/List_of_S%26P_400_companies"
WIKIPEDIA_STOXX600_URL = "https://en.wikipedia.org/wiki/STOXX_Europe_600"

# STOXX Europe 600's Wikipedia table gives bare local-exchange tickers with no
# Yahoo suffix; this maps its "Country" column to the right one. Countries not
# listed here (a handful of rows: Luxembourg, Bermuda, Greece, Israel) are
# skipped rather than guessed.
EU_EXCHANGE_SUFFIX = {
    "United Kingdom": ".L",
    "Germany": ".DE",
    "France": ".PA",
    "Switzerland": ".SW",
    "Netherlands": ".AS",
    "Italy": ".MI",
    "Spain": ".MC",
    "Sweden": ".ST",
    "Belgium": ".BR",
    "Finland": ".HE",
    "Norway": ".OL",
    "Denmark": ".CO",
    "Austria": ".VI",
    "Portugal": ".LS",
    "Ireland": ".IR",
    "Poland": ".WA",
}

# Last-resort universe, used only if every Wikipedia source and the previous
# data file are unavailable (e.g. the very first run with no network access).
FALLBACK_TICKERS = [
    "AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "META", "BRK-B", "JPM", "JNJ", "XOM",
    "PG", "KO", "PEP", "T", "VZ", "WMT", "HD", "CVX", "ABBV", "PFE",
    "MRK", "BAC", "DIS", "CSCO", "INTC", "MCD", "IBM", "GE", "CAT", "MMM",
]

# Pause between per-ticker Yahoo calls, and retry policy for transient errors.
YFINANCE_REQUEST_DELAY = 0.6
YFINANCE_RETRIES = 3
YFINANCE_RETRY_BACKOFF = 5  # seconds, multiplied by the attempt number
PRICE_HISTORY_CHUNK = 100  # tickers per bulk price-history download

# If fewer than this share of tickers fetch successfully, the run is treated as
# broken (e.g. Yahoo blocking the runner): nothing is written and the script
# exits non-zero so the GitHub Action fails visibly instead of wiping good data.
MIN_SUCCESS_RATIO = 0.5

# Hard ceiling on FMP fallback calls per run, kept under the 250/day free limit.
FMP_MAX_CALLS_PER_RUN = 210
FMP_CALLS_PER_TICKER = 3  # profile + ratios-ttm + key-metrics-ttm

# Value/dividend criteria behind the derived flags and the value score.
PE_MAX = 15
DIVIDEND_YIELD_MIN = 3.0  # percent
DEBT_TO_EQUITY_MAX = 1.0  # ratio, not percent

# Size bounds for the "recommended" view: stocks passing all 3 criteria above.
RECOMMENDED_MIN = 10
RECOMMENDED_MAX = 20

PRICE_HISTORY_PERIOD = "1y"
PRICE_HISTORY_INTERVAL = "1wk"

# The app warns when data is older than this (covers a normal weekend gap).
STALE_AFTER_DAYS = 4
DISPLAY_TIMEZONE = "Asia/Jerusalem"
