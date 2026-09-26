"""Filtering, sorting and ranking logic. Pure pandas (no Streamlit) so it's unit-testable."""
import math
from dataclasses import asdict, dataclass
from typing import Mapping

import pandas as pd

import config

# A slider left at its maximum means "no limit" rather than a real cap, so
# stocks above it (or with missing values) aren't silently hidden.
PE_SLIDER_MAX = 100
PB_SLIDER_MAX = 20.0
DIV_SLIDER_MAX = 10.0
ROE_SLIDER_MAX = 50

DEFAULT_SORT = "value_score"

# Direction used on the first click of a column header: "better" values first.
NATURAL_DIRECTION = {
    "ticker": "asc", "name": "asc", "sector": "asc", "price": "desc",
    "pe_ratio": "asc", "pb_ratio": "asc", "dividend_yield": "desc", "roe": "desc",
    "debt_to_equity": "asc", "market_cap": "desc", "value_score": "desc",
}
TEXT_COLUMNS = {"ticker", "name", "sector"}

# Query-string key for each Filters field (kept short for readable URLs).
QUERY_KEYS = {
    "max_pe": "pe", "max_pb": "pb", "min_div": "div", "min_roe": "roe",
    "book_over_market": "bv", "sector": "sector", "sort": "sort", "direction": "dir",
}


@dataclass(frozen=True)
class Filters:
    max_pe: int = PE_SLIDER_MAX
    max_pb: float = PB_SLIDER_MAX
    min_div: float = 0.0
    min_roe: int = 0
    book_over_market: bool = False
    sector: str = ""
    sort: str = DEFAULT_SORT
    direction: str = NATURAL_DIRECTION[DEFAULT_SORT]

    @classmethod
    def from_query(cls, params: Mapping[str, str]) -> "Filters":
        """Parse URL params, falling back to defaults for anything missing or malformed."""
        d = cls()

        def num(key, cast, lo, hi, default):
            try:
                raw = float(params[QUERY_KEYS[key]])
            except (KeyError, ValueError, TypeError):
                return default
            if not math.isfinite(raw):
                return default
            return min(max(cast(raw), lo), hi)

        sort = params.get("sort", d.sort)
        if sort not in NATURAL_DIRECTION:
            sort = d.sort
        direction = params.get("dir", NATURAL_DIRECTION[sort])
        if direction not in ("asc", "desc"):
            direction = NATURAL_DIRECTION[sort]
        return cls(
            max_pe=num("max_pe", int, 1, PE_SLIDER_MAX, d.max_pe),
            max_pb=num("max_pb", float, 0.5, PB_SLIDER_MAX, d.max_pb),
            min_div=num("min_div", float, 0.0, DIV_SLIDER_MAX, d.min_div),
            min_roe=num("min_roe", int, 0, ROE_SLIDER_MAX, d.min_roe),
            book_over_market=params.get("bv") == "1",
            sector=params.get("sector", ""),
            sort=sort,
            direction=direction,
        )

    def to_query(self) -> dict[str, str]:
        """Only non-default values, so a default view has a clean URL."""
        defaults = asdict(Filters())
        out = {}
        for field, value in asdict(self).items():
            if field == "direction":
                if value == NATURAL_DIRECTION[self.sort]:
                    continue
            elif value == defaults[field]:
                continue
            out[QUERY_KEYS[field]] = "1" if value is True else f"{value:g}" if isinstance(value, float) else str(value)
        return out

    def has_active_filters(self) -> bool:
        return self.to_query().keys() - {"sort", "dir"} != set()


def apply_filters(df: pd.DataFrame, f: Filters) -> pd.DataFrame:
    # An active filter excludes stocks with missing data for that metric:
    # a stock with unknown P/E shouldn't appear under "P/E at most 15".
    mask = pd.Series(True, index=df.index)
    if f.max_pe < PE_SLIDER_MAX:
        mask &= (df["pe_ratio"] > 0) & (df["pe_ratio"] <= f.max_pe)
    if f.max_pb < PB_SLIDER_MAX:
        # Negative P/B means negative book equity, not a cheap stock.
        mask &= (df["pb_ratio"] > 0) & (df["pb_ratio"] <= f.max_pb)
    if f.min_div > 0:
        mask &= df["dividend_yield"] >= f.min_div
    if f.min_roe > 0:
        mask &= df["roe"] >= f.min_roe
    if f.book_over_market:
        mask &= df["flag_pb_under_1"].astype(bool)
    if f.sector:
        mask &= df["sector"] == f.sector
    return df[mask]


def _meaningful(df: pd.DataFrame, column: str) -> pd.Series:
    """Values usable for ranking; nonsensical ones (e.g. negative P/E) become NaN."""
    series = df[column]
    if column in ("pe_ratio", "pb_ratio"):
        return series.where(series > 0)
    if column == "debt_to_equity":
        return series.where(series >= 0)
    return series


def add_value_rank(df: pd.DataFrame) -> pd.DataFrame:
    """Continuous 0-1 value/quality percentile, used to order stocks that tie
    on the (integer) value score. Averages whichever metrics a stock has."""
    parts = pd.DataFrame({
        "pe": _meaningful(df, "pe_ratio").rank(pct=True, ascending=False),
        "pb": _meaningful(df, "pb_ratio").rank(pct=True, ascending=False),
        "div": df["dividend_yield"].rank(pct=True),
        "roe": df["roe"].rank(pct=True),
        "debt": _meaningful(df, "debt_to_equity").rank(pct=True, ascending=False),
    })
    return df.assign(value_rank=parts.mean(axis=1))


def top_recommendations(df: pd.DataFrame) -> pd.DataFrame:
    """The best value/dividend picks: stocks passing all 3 tunable criteria
    (low P/E, high dividend yield, low debt-to-equity), best `value_score`
    first (ties broken by `value_rank`) -- the same ordering convention as
    the main table's default sort. If fewer than RECOMMENDED_MIN qualify,
    backfilled with the next-best non-qualifying stocks so the view is never
    near-empty; capped at RECOMMENDED_MAX either way. Assumes `add_value_rank`
    was already applied (as `load_data` does upstream)."""
    ranked = df.sort_values(["value_score", "value_rank"], ascending=False, kind="mergesort")
    qualifies = (
        ranked["flag_low_pe"].astype(bool)
        & ranked["flag_high_dividend"].astype(bool)
        & ranked["flag_low_debt"].astype(bool)
    )
    picks = ranked[qualifies]
    if len(picks) < config.RECOMMENDED_MIN:
        backfill = ranked[~qualifies]
        picks = pd.concat([picks, backfill.head(config.RECOMMENDED_MIN - len(picks))])
    return picks.head(config.RECOMMENDED_MAX)


def sort_stocks(df: pd.DataFrame, sort: str, direction: str) -> pd.DataFrame:
    """Missing/nonsensical values always sort last, whatever the direction."""
    primary = _meaningful(df, sort)
    if sort in TEXT_COLUMNS:
        primary = primary.str.lower()
    secondary = "value_rank" if sort == DEFAULT_SORT else "value_score"
    return (
        df.assign(_primary=primary)
        .sort_values(
            ["_primary", secondary],
            ascending=[direction == "asc", False],
            na_position="last",
            kind="mergesort",
        )
        .drop(columns="_primary")
    )
