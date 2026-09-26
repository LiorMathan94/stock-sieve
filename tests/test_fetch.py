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


def test_dedupe_share_classes_keeps_first():
    stocks = [{"ticker": "GOOGL", "name": "Alphabet Inc."}, {"ticker": "GOOG", "name": "Alphabet Inc."}]
    assert [s["ticker"] for s in fetch_data.dedupe_share_classes(stocks)] == ["GOOGL"]
