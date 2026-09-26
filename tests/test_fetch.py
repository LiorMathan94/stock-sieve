import pandas as pd

import fetch_data


def yahoo_info(**overrides):
    info = {
        "currentPrice": 100.0, "longName": "Example Corp", "sector": "Energy",
        "trailingPE": 10.0, "priceToBook": 1.5, "returnOnEquity": 0.2,
        "debtToEquity": 50.0, "marketCap": 1e10, "freeCashflow": 1e9,
        "dividendRate": 4.0, "trailingAnnualDividendRate": 4.0,
    }
    return info | overrides


def test_dividend_yield_computed_from_dollar_rate():
    assert fetch_data.parse_yfinance_info(yahoo_info())["dividend_yield"] == 4.0


def test_confirmed_non_payer_is_zero_not_missing():
    record = fetch_data.parse_yfinance_info(yahoo_info(dividendRate=None, trailingAnnualDividendRate=0.0))
    assert record["dividend_yield"] == 0.0


def test_unknown_dividend_stays_missing():
    record = fetch_data.parse_yfinance_info(yahoo_info(dividendRate=None, trailingAnnualDividendRate=None))
    assert record["dividend_yield"] is None


def test_units_normalised():
    record = fetch_data.parse_yfinance_info(yahoo_info())
    assert record["roe"] == 20.0
    assert record["debt_to_equity"] == 0.5


def test_share_class_pb_artifact_discarded():
    assert fetch_data.parse_yfinance_info(yahoo_info(priceToBook=0.001))["pb_ratio"] is None


def test_missing_price_is_a_failure():
    assert fetch_data.parse_yfinance_info(yahoo_info(currentPrice=None)) is None


def test_gbp_price_converted_to_pounds():
    # yfinance reports London-listed prices in pence, but dividendRate and
    # bookValue for the same stock are already in pounds (confirmed against
    # real GSK.L data) -- only price needs the /100 conversion.
    record = fetch_data.parse_yfinance_info(
        yahoo_info(currency="GBp", currentPrice=1851.0, dividendRate=0.68, bookValue=4.404)
    )
    assert record["currency"] == "GBP"
    assert record["price"] == 18.51
    assert record["book_value_per_share"] == 4.404
    assert round(record["dividend_yield"], 2) == 3.67


def test_usd_currency_passed_through_unchanged():
    record = fetch_data.parse_yfinance_info(yahoo_info(currency="USD"))
    assert record["currency"] == "USD"
    assert record["price"] == 100.0


class _FakeResponse:
    def __init__(self, payload):
        self.payload = payload

    def raise_for_status(self):
        pass

    def json(self):
        return self.payload


def test_fmp_record_has_usd_currency(monkeypatch):
    monkeypatch.setattr(fetch_data.config, "FMP_API_KEY", "test-key")
    responses = {
        "profile": [{"price": 50.0, "marketCap": 1e9, "companyName": "Example Corp"}],
        "ratios-ttm": [{}],
        "key-metrics-ttm": [{}],
    }
    monkeypatch.setattr(
        fetch_data.requests, "get",
        lambda url, **kwargs: _FakeResponse(responses[url.rsplit("/", 1)[-1]]),
    )
    record = fetch_data.fetch_from_fmp("EX", [0])
    assert record["currency"] == "USD"


def test_negative_pb_is_not_flagged_as_cheap():
    record = fetch_data.compute_flags({"pb_ratio": -40.0, "pe_ratio": None, "dividend_yield": None,
                                       "debt_to_equity": None, "free_cash_flow": None})
    assert not record["flag_pb_under_1"] and record["value_score"] == 0


def test_flags_and_score():
    record = fetch_data.compute_flags({"pb_ratio": 0.9, "pe_ratio": 9.0, "dividend_yield": 5.0,
                                       "debt_to_equity": 0.2, "free_cash_flow": 1.0})
    assert record["value_score"] == 5


def test_merge_keeps_previous_record_for_failed_ticker():
    previous = {"last_updated": "2026-09-20T06:00:00+00:00", "stocks": [
        {"ticker": "OLD", "name": "Old Co"}, {"ticker": "BOTH", "name": "Both Co"},
    ]}
    fresh = {"BOTH": {"ticker": "BOTH", "name": "Both Co v2"}, "NEW": {"ticker": "NEW", "name": "New Co"}}
    stocks, failed = fetch_data.merge_results(["OLD", "BOTH", "NEW", "GONE"], fresh, previous, "2026-09-26")
    by_ticker = {s["ticker"]: s for s in stocks}
    assert by_ticker["OLD"]["as_of"] == "2026-09-20"
    assert by_ticker["BOTH"] == {"ticker": "BOTH", "name": "Both Co v2", "as_of": "2026-09-26"}
    assert failed == ["OLD", "GONE"]


def test_universe_falls_back_to_previous_tickers(monkeypatch):
    def boom(*args, **kwargs):
        raise ConnectionError("no network")

    monkeypatch.setattr(fetch_data.requests, "get", boom)
    previous = {"stocks": [{"ticker": "AAA"}, {"ticker": "BBB"}], "failed_tickers": ["CCC"]}
    assert fetch_data.get_universe(previous) == ["AAA", "BBB", "CCC"]


def test_universe_combines_us_and_eu_sources_independently(monkeypatch):
    """One source failing (STOXX 600's page format changing, say) shouldn't
    take down the other two."""
    monkeypatch.setattr(fetch_data, "_fetch_sp500", lambda: ["AAPL", "MSFT"])
    monkeypatch.setattr(fetch_data, "_fetch_sp400", lambda: ["AAON"])

    def boom():
        raise ValueError("STOXX 600 page changed shape")

    monkeypatch.setattr(fetch_data, "_fetch_stoxx600", boom)
    assert fetch_data.get_universe({}) == ["AAPL", "MSFT", "AAON"]


def test_universe_falls_back_when_all_three_sources_fail(monkeypatch):
    def boom():
        raise ValueError("no network")

    monkeypatch.setattr(fetch_data, "_fetch_sp500", boom)
    monkeypatch.setattr(fetch_data, "_fetch_sp400", boom)
    monkeypatch.setattr(fetch_data, "_fetch_stoxx600", boom)
    previous = {"stocks": [{"ticker": "AAA"}], "failed_tickers": []}
    assert fetch_data.get_universe(previous) == ["AAA"]


def test_stoxx_ticker_suffix_mapped_by_country():
    table = pd.DataFrame({
        "Ticker": ["ZURN", "GSK", "UNKNOWNCO"],
        "Country": ["Switzerland", "United Kingdom", "Atlantis"],  # last one isn't in the suffix map
    })
    assert fetch_data._stoxx_symbols_from_table(table) == ["ZURN.SW", "GSK.L"]


def test_dedupe_share_classes_keeps_first():
    stocks = [{"ticker": "GOOGL", "name": "Alphabet Inc."}, {"ticker": "GOOG", "name": "Alphabet Inc."}]
    assert [s["ticker"] for s in fetch_data.dedupe_share_classes(stocks)] == ["GOOGL"]
