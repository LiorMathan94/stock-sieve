import math

import pandas as pd
import pytest

import screener
from screener import Filters


@pytest.fixture
def df():
    rows = [
        # ticker, pe, pb, div, roe, d/e, score, pb_flag, sector
        ("CHEAP", 8.0, 0.8, 5.0, 15.0, 0.3, 5, True, "Energy"),
        ("NODIV", 12.0, 2.0, 0.0, 20.0, 0.5, 3, False, "Technology"),
        ("NEGEQ", 14.0, -40.0, 6.0, None, None, 2, False, "Consumer Defensive"),
        ("MISSING", None, None, None, None, None, 0, False, None),
        ("PRICEY", 150.0, 25.0, 0.5, 30.0, 2.0, 1, False, "Technology"),
    ]
    frame = pd.DataFrame(rows, columns=[
        "ticker", "pe_ratio", "pb_ratio", "dividend_yield", "roe", "debt_to_equity",
        "value_score", "flag_pb_under_1", "sector",
    ])
    frame["name"] = frame["ticker"].str.title()
    return screener.add_value_rank(frame)


def tickers(frame):
    return list(frame["ticker"])


def test_default_filters_show_everything(df):
    assert len(screener.apply_filters(df, Filters())) == len(df)


def test_min_dividend_excludes_missing_and_non_payers(df):
    result = screener.apply_filters(df, Filters(min_div=3.0))
    assert tickers(result) == ["CHEAP", "NEGEQ"]


def test_max_pb_excludes_negative_book_equity(df):
    result = screener.apply_filters(df, Filters(max_pb=1.0))
    assert tickers(result) == ["CHEAP"]


def test_max_pe_excludes_missing(df):
    result = screener.apply_filters(df, Filters(max_pe=15))
    assert "MISSING" not in tickers(result) and "PRICEY" not in tickers(result)


def test_slider_at_max_is_no_limit(df):
    assert "PRICEY" in tickers(screener.apply_filters(df, Filters(max_pe=screener.PE_SLIDER_MAX)))


def test_sector_and_book_value_filters(df):
    assert tickers(screener.apply_filters(df, Filters(sector="Technology"))) == ["NODIV", "PRICEY"]
    assert tickers(screener.apply_filters(df, Filters(book_over_market=True))) == ["CHEAP"]


@pytest.mark.parametrize("direction", ["asc", "desc"])
def test_sort_puts_missing_and_nonsensical_last(df, direction):
    result = tickers(screener.sort_stocks(df, "pb_ratio", direction))
    assert result[-2:] == ["NEGEQ", "MISSING"] or result[-2:] == ["MISSING", "NEGEQ"]


def test_sort_pe_ascending(df):
    assert tickers(screener.sort_stocks(df, "pe_ratio", "asc"))[:3] == ["CHEAP", "NODIV", "NEGEQ"]


def test_default_sort_is_score_then_rank(df):
    tied = df.assign(value_score=[3, 3, 3, 0, 3])
    result = tickers(screener.sort_stocks(tied, "value_score", "desc"))
    assert result[0] == "CHEAP"  # best composite rank wins the tie
    assert result[-1] == "MISSING"


def test_value_rank_is_between_0_and_1(df):
    ranks = df["value_rank"].dropna()
    assert ((ranks >= 0) & (ranks <= 1)).all()


def test_query_roundtrip():
    f = Filters(max_pe=15, max_pb=1.5, min_div=3.25, book_over_market=True, sector="Energy",
                sort="dividend_yield", direction="asc")
    assert Filters.from_query(f.to_query()) == f


def test_default_filters_have_clean_query():
    assert Filters().to_query() == {}
    assert not Filters().has_active_filters()
    assert not Filters(sort="pe_ratio").has_active_filters()
    assert Filters(min_div=1.0).has_active_filters()


@pytest.mark.parametrize("params", [
    {"pe": "abc"}, {"pe": "nan"}, {"pe": "inf"}, {"pb": "-5"}, {"sort": "evil"}, {"dir": "sideways"},
])
def test_malformed_query_never_crashes(params):
    f = Filters.from_query(params)
    assert 1 <= f.max_pe <= screener.PE_SLIDER_MAX
    assert 0.5 <= f.max_pb <= screener.PB_SLIDER_MAX and math.isfinite(f.max_pb)
    assert f.sort in screener.NATURAL_DIRECTION
    assert f.direction in ("asc", "desc")


def recommendation_rows(*rows):
    """rows: (ticker, qualifies_all_3_criteria, value_score, value_rank)."""
    frame = pd.DataFrame(rows, columns=["ticker", "qualifies", "value_score", "value_rank"])
    for flag in ("flag_low_pe", "flag_high_dividend", "flag_low_debt"):
        frame[flag] = frame["qualifies"]
    return frame.drop(columns="qualifies")


def test_recommendations_no_backfill_when_exactly_min_qualify(monkeypatch):
    monkeypatch.setattr(screener.config, "RECOMMENDED_MIN", 2)
    monkeypatch.setattr(screener.config, "RECOMMENDED_MAX", 4)
    df = recommendation_rows(
        ("BEST", True, 4, 0.9), ("GOOD", True, 4, 0.7),
        ("HIGHRANK_BUT_FAILS", False, 4, 0.99), ("ALSO_FAILS", False, 4, 0.5),
    )
    assert tickers(screener.top_recommendations(df)) == ["BEST", "GOOD"]


def test_recommendations_sort_by_score_before_rank(monkeypatch):
    """Regression test: a stock meeting more of the 5 criteria (higher
    value_score) must outrank one meeting fewer, even if its continuous
    value_rank percentile happens to be lower -- matching the main table's
    default sort convention (value_score first, value_rank as tiebreak)."""
    monkeypatch.setattr(screener.config, "RECOMMENDED_MIN", 2)
    monkeypatch.setattr(screener.config, "RECOMMENDED_MAX", 4)
    df = recommendation_rows(("HIGHER_SCORE", True, 5, 0.60), ("LOWER_SCORE", True, 4, 0.90))
    assert tickers(screener.top_recommendations(df)) == ["HIGHER_SCORE", "LOWER_SCORE"]


def test_recommendations_backfill_when_too_few_qualify(monkeypatch):
    monkeypatch.setattr(screener.config, "RECOMMENDED_MIN", 3)
    monkeypatch.setattr(screener.config, "RECOMMENDED_MAX", 5)
    df = recommendation_rows(
        ("ONLY_QUALIFIER", True, 3, 0.6),
        ("NEXT_BEST", False, 3, 0.9), ("SECOND_BEST", False, 3, 0.8), ("WORST", False, 3, 0.1),
    )
    # The qualifier comes first regardless of rank, then the best-ranked non-qualifiers backfill.
    assert tickers(screener.top_recommendations(df)) == ["ONLY_QUALIFIER", "NEXT_BEST", "SECOND_BEST"]


def test_recommendations_capped_at_max_when_many_qualify(monkeypatch):
    monkeypatch.setattr(screener.config, "RECOMMENDED_MIN", 1)
    monkeypatch.setattr(screener.config, "RECOMMENDED_MAX", 2)
    df = recommendation_rows(("A", True, 3, 0.5), ("B", True, 3, 0.9), ("C", True, 3, 0.7))
    assert tickers(screener.top_recommendations(df)) == ["B", "C"]
