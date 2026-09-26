"""
Streamlit UI. Reads only the cached data/stocks.json produced by fetch_data.py
-- no live API calls on page load, to stay within free API limits.

Navigation (stock pages, sorting, language) uses plain links, which start a new
Streamlit session; all view state therefore lives in the URL query string.
"""
import html
import json
import os
from dataclasses import replace
from datetime import datetime, timezone
from urllib.parse import urlencode
from zoneinfo import ZoneInfo

import altair as alt
import pandas as pd
import streamlit as st

import config
import screener
from screener import Filters
from translations import t

st.set_page_config(page_title="Stock Sieve | מסנן מניות", layout="wide")

PRIMARY = "#1a6f4c"

SECTOR_COLORS = {
    "Technology": ("#e8f0fe", "#1a56c4"),
    "Healthcare": ("#e6f7f0", "#0f766e"),
    "Financial Services": ("#fef3e2", "#b45309"),
    "Consumer Cyclical": ("#fce8f3", "#a3175c"),
    "Consumer Defensive": ("#eef2ff", "#4338ca"),
    "Communication Services": ("#f3e8ff", "#6d28d9"),
    "Industrials": ("#eef1f4", "#374151"),
    "Energy": ("#fee2e2", "#b91c1c"),
    "Real Estate": ("#ecfccb", "#4d7c0f"),
    "Basic Materials": ("#fef9c3", "#854d0e"),
    "Utilities": ("#e0f2fe", "#075985"),
}
SECTOR_FALLBACK_COLOR = ("#f1f5f9", "#475569")

SCORE_COLORS = {  # (background, text) keyed by min score threshold, checked descending
    4: ("#dcf5e6", "#15803d"),
    2: ("#fef3c7", "#92400e"),
    0: ("#f1f5f9", "#64748b"),
}

# (field, label key, tooltip key or None, column width %, wraps instead of truncating)
TABLE_COLUMNS = [
    ("ticker", "col_ticker", "tip_ticker", 7, False),
    ("name", "col_name", None, 22, True),
    ("sector", "col_sector", None, 12, False),
    ("price", "col_price", "tip_price", 8, False),
    ("pe_ratio", "col_pe", "tip_pe", 7, False),
    ("pb_ratio", "col_pb", "tip_pb", 7, False),
    ("dividend_yield", "col_dividend_yield", "tip_dividend_yield", 8, False),
    ("roe", "col_roe", "tip_roe", 7, False),
    ("debt_to_equity", "col_debt_to_equity", "tip_debt_to_equity", 8, False),
    ("market_cap", "col_market_cap", "tip_market_cap", 9, False),
    ("value_score", "col_value_score", "tip_value_score", 5, False),
]
WIDGET_KEYS = {  # session-state key for each sidebar widget
    "max_pe": "f_pe", "max_pb": "f_pb", "min_div": "f_div", "min_roe": "f_roe",
    "book_over_market": "f_bv", "sector": "f_sector",
}


@st.cache_resource(max_entries=2)
def load_data(mtime: float) -> tuple[dict, pd.DataFrame]:
    """Keyed on the file's mtime so a data refresh is picked up without a restart.
    Returned objects are shared across sessions and must not be mutated."""
    with open(config.DATA_FILE, encoding="utf-8") as f:
        data = json.load(f)
    df = pd.DataFrame(data["stocks"]).drop(columns=["price_history", "description"], errors="ignore")
    return data, screener.add_value_rank(df)


# ---------- formatting ----------

def esc(value) -> str:
    return html.escape(str(value)) if value is not None else ""


def ltr(content: str) -> str:
    """Keep numbers/tickers left-to-right even inside an RTL row or sentence."""
    return f'<span dir="ltr">{content}</span>'


def is_missing(value) -> bool:
    return value is None or pd.isna(value)


def fmt_num(value, decimals=1, suffix=""):
    return None if is_missing(value) else f"{value:,.{decimals}f}{suffix}"


def fmt_price(value):
    return None if is_missing(value) else f"${value:,.2f}"


def fmt_money(value):
    if is_missing(value):
        return None
    sign = "-" if value < 0 else ""
    for divisor, label in ((1e12, "T"), (1e9, "B"), (1e6, "M")):
        if abs(value) >= divisor:
            return f"{sign}${abs(value) / divisor:,.1f}{label}"
    return f"{sign}${abs(value):,.0f}"


def cell_value(formatted, lang) -> str:
    return ltr(esc(formatted)) if formatted is not None else f'<span class="na">{t("not_available", lang)}</span>'


def sector_pill(sector, lang) -> str:
    if is_missing(sector) or not sector:
        return cell_value(None, lang)
    bg, fg = SECTOR_COLORS.get(sector, SECTOR_FALLBACK_COLOR)
    return f'<span class="sector-pill" style="background:{bg};color:{fg};" title="{esc(sector)}">{ltr(esc(sector))}</span>'


def score_badge(score: int) -> str:
    bg, fg = next(SCORE_COLORS[th] for th in sorted(SCORE_COLORS, reverse=True) if score >= th)
    return f'<span class="score-badge" style="background:{bg};color:{fg};">{score}</span>'


# ---------- navigation ----------

def get_lang() -> str:
    return "en" if st.query_params.get("lang") == "en" else "he"


def href(**overrides) -> str:
    """Link to the current URL with some params replaced (None removes one)."""
    query = st.query_params.to_dict()
    for key, value in overrides.items():
        if value is None:
            query.pop(key, None)
        else:
            query[key] = value
    return "?" + urlencode(query)


def link(label_html: str, url: str, css_class: str, title: str = "") -> str:
    title_attr = f' title="{esc(title)}"' if title else ""
    return f'<a class="{css_class}" href="{esc(url)}" target="_self"{title_attr}>{label_html}</a>'


# ---------- page pieces ----------

def inject_css(lang: str):
    rtl_rules = """
        div[data-testid="stAppViewContainer"], section[data-testid="stSidebar"],
        div[data-testid="stMainBlockContainer"] { direction: rtl !important; }
        h1, h2, h3, p, label, .stMarkdown { text-align: right !important; }
        /* Keep slider drag mechanics left-to-right; only right-align its label */
        div[data-testid="stSlider"] { direction: ltr !important; }
        div[data-testid="stSlider"] label { direction: rtl !important; text-align: right !important; }
        div[data-testid="stSelectbox"] label, div[data-testid="stCheckbox"] label {
            direction: rtl !important; text-align: right !important;
        }
        table.stock-table thead tr, table.stock-table tbody tr { direction: rtl; }
    """ if lang == "he" else ""
    st.markdown(
        f"""
        <style>
        html, body, [class*="css"] {{
            font-family: -apple-system, "Segoe UI", Roboto, "Noto Sans Hebrew", Arial, sans-serif;
        }}
        {rtl_rules}
        div[data-testid="stMainBlockContainer"] {{ padding-top: 2.5rem; }}
        /* Streamlit collapses the sidebar by sliding it left, which in RTL slides it
           into view instead of off-screen; remove it from layout when collapsed. */
        section[data-testid="stSidebar"][aria-expanded="false"] {{ display: none !important; }}
        /* Desktop only: forcing a width on mobile breaks Streamlit's sidebar collapse */
        @media (min-width: 901px) {{
            section[data-testid="stSidebar"] {{ width: 260px !important; min-width: 260px !important; }}
        }}

        h1 {{ font-weight: 800; letter-spacing: -0.01em; }}
        .meta-line {{ color: #94a3b8; font-size: 0.82rem; margin-bottom: 2px; }}
        .disclaimer {{
            color: #94a3b8; font-size: 0.82rem; font-style: italic; margin-top: 0;
            border-inline-start: 3px solid #e2e8f0; padding-inline-start: 10px;
        }}
        .stale-warning {{
            background: #fef3c7; color: #92400e; border-radius: 8px; padding: 8px 14px;
            font-size: 0.88rem; margin: 6px 0;
        }}
        .results-row {{ display: flex; align-items: center; gap: 14px; flex-wrap: wrap; margin: 10px 0 8px; }}
        .results-badge {{
            display: inline-block; background: {PRIMARY}; color: white; font-weight: 700;
            padding: 4px 14px; border-radius: 999px; font-size: 0.95rem;
        }}
        .hint {{ color: #94a3b8; font-size: 0.8rem; }}
        .pill-button {{
            display: inline-block; padding: 5px 16px; border-radius: 999px;
            border: 1.5px solid {PRIMARY}; color: {PRIMARY} !important; font-weight: 600;
            text-decoration: none !important; font-size: 0.85rem; background: white;
            transition: background-color 0.15s, color 0.15s;
        }}
        .pill-button:hover {{ background: {PRIMARY}; color: white !important; }}
        .pill-button.subtle {{ border-color: #cbd5e1; color: #475569 !important; }}
        .pill-button.subtle:hover {{ background: #475569; border-color: #475569; color: white !important; }}

        .table-wrapper {{
            max-height: 70vh; overflow-y: auto; overflow-x: hidden;
            border: 1px solid #e2e8f0; border-radius: 12px;
            box-shadow: 0 1px 4px rgba(15, 23, 42, 0.06);
        }}
        table.stock-table {{
            width: 100%; table-layout: fixed; border-collapse: separate; border-spacing: 0;
            font-variant-numeric: tabular-nums; background: white;
        }}
        table.stock-table thead th {{
            position: sticky; top: 0; z-index: 2; background: #16543c;
            font-size: 0.7rem; text-transform: uppercase; letter-spacing: 0.03em;
            font-weight: 700; padding: 0; text-align: center;
            word-break: keep-all; overflow-wrap: normal;
        }}
        a.sort-link {{
            display: block; padding: 10px 4px; color: #ffffff !important;
            text-decoration: none !important; cursor: pointer;
        }}
        a.sort-link:hover {{ background: #1f6b4d; }}
        a.sort-link.active {{ background: #0f3d2b; }}
        table.stock-table td {{
            padding: 7px 4px; border-bottom: 1px solid #eef1ef; font-size: 0.82rem;
            color: #1e293b; text-align: center; overflow: hidden;
            text-overflow: ellipsis; white-space: nowrap;
        }}
        table.stock-table td.wrap-cell {{ white-space: normal; word-break: break-word; }}
        table.stock-table tbody tr:nth-child(even) {{ background-color: #fafbfa; }}
        table.stock-table tbody tr:hover {{ background-color: #eaf4ee; }}
        .na {{ color: #cbd5e1; }}
        /* On narrow screens squeezing 11 columns is unreadable; scroll instead */
        @media (max-width: 900px) {{
            .table-wrapper {{ overflow-x: auto; }}
            table.stock-table {{ min-width: 860px; }}
        }}

        .ticker-badge {{
            display: inline-block; padding: 3px 8px; border-radius: 6px;
            background: #e6f4ee; color: #15633f !important; font-weight: 700;
            text-decoration: none !important; font-size: 0.8rem;
        }}
        .ticker-badge:hover {{ background: #c9e9d8; }}
        .sector-pill {{
            display: inline-block; padding: 2px 8px; border-radius: 999px;
            font-size: 0.68rem; font-weight: 600; max-width: 100%;
            overflow: hidden; text-overflow: ellipsis; white-space: nowrap; vertical-align: middle;
        }}
        .score-badge {{
            display: inline-block; min-width: 20px; padding: 2px 8px; border-radius: 999px;
            font-weight: 700; font-size: 0.78rem;
        }}

        .detail-title {{ display: flex; align-items: center; gap: 12px; flex-wrap: wrap; margin: 14px 0 4px; }}
        .detail-title h2 {{ margin: 0; padding: 0; }}
        .metric-grid {{
            display: grid; grid-template-columns: repeat(auto-fill, minmax(150px, 1fr));
            gap: 10px; margin: 8px 0 18px;
        }}
        .metric-card {{
            border: 1px solid #e2e8f0; border-radius: 10px; padding: 10px 14px; background: white;
        }}
        .metric-label {{ color: #64748b; font-size: 0.76rem; }}
        .metric-value {{ font-size: 1.25rem; font-weight: 700; color: #0f172a; font-variant-numeric: tabular-nums; }}
        ul.criteria {{ list-style: none; padding: 0; margin: 6px 0 18px; }}
        /* Streamlit styles list items itself, so alignment must be set explicitly */
        ul.criteria li {{ padding: 5px 0; border-bottom: 1px solid #f1f5f9; text-align: start !important; }}
        .crit-yes {{ color: #15803d; font-weight: 700; }}
        .crit-no {{ color: #cbd5e1; font-weight: 700; }}
        .crit-value {{ color: #94a3b8; font-size: 0.85rem; }}
        .change-up {{ color: #15803d; font-weight: 700; }}
        .change-down {{ color: #b91c1c; font-weight: 700; }}
        .description-block {{ direction: ltr; text-align: left; color: #333; line-height: 1.6; }}
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_header(data: dict, lang: str):
    title_col, toggle_col = st.columns([6, 1])
    with title_col:
        st.title(t("app_title", lang))
    with toggle_col:
        other = "en" if lang == "he" else "he"
        st.markdown(
            link(t("language_toggle", lang), href(lang=None if other == "he" else other), "pill-button"),
            unsafe_allow_html=True,
        )

    updated = datetime.fromisoformat(data["last_updated"])
    local = updated.astimezone(ZoneInfo(config.DISPLAY_TIMEZONE))
    st.markdown(
        f'<p class="meta-line">{t("last_updated", lang)}: '
        f'{ltr(local.strftime("%d/%m/%Y %H:%M"))} ({t("israel_time", lang)})</p>',
        unsafe_allow_html=True,
    )
    age_days = (datetime.now(timezone.utc) - updated).days
    if age_days > config.STALE_AFTER_DAYS:
        st.markdown(f'<div class="stale-warning">{t("stale_warning", lang, days=age_days)}</div>', unsafe_allow_html=True)
    st.markdown(f'<p class="disclaimer">{t("disclaimer", lang)}</p>', unsafe_allow_html=True)


def sidebar_filters(df: pd.DataFrame, lang: str) -> Filters:
    """Widgets are seeded from the URL once per session, and every change is
    written back to the URL so links (stock page, sort, language) keep it."""
    from_url = Filters.from_query(st.query_params.to_dict())
    sectors = sorted(df["sector"].dropna().unique())
    if from_url.sector not in sectors:
        from_url = replace(from_url, sector="")
    for field, key in WIDGET_KEYS.items():
        st.session_state.setdefault(key, getattr(from_url, field))

    sb = st.sidebar
    sb.header(t("filters_header", lang))
    no_limit = t("no_limit_help", lang)
    current = replace(
        from_url,
        max_pe=sb.slider(t("max_pe", lang), 1, screener.PE_SLIDER_MAX, key="f_pe", help=no_limit),
        max_pb=sb.slider(t("max_pb", lang), 0.5, screener.PB_SLIDER_MAX, step=0.1, key="f_pb", help=no_limit),
        min_div=sb.slider(t("min_dividend_yield", lang), 0.0, screener.DIV_SLIDER_MAX, step=0.25, key="f_div"),
        min_roe=sb.slider(t("min_roe", lang), 0, screener.ROE_SLIDER_MAX, key="f_roe"),
        book_over_market=sb.checkbox(t("book_over_market_only", lang), key="f_bv"),
        sector=sb.selectbox(
            t("sector_filter", lang), [""] + sectors, key="f_sector",
            format_func=lambda s: s or t("all_sectors", lang),
        ),
    )

    wanted = current.to_query()
    for query_key in screener.QUERY_KEYS.values():
        if query_key in wanted:
            if st.query_params.get(query_key) != wanted[query_key]:
                st.query_params[query_key] = wanted[query_key]
        elif query_key in st.query_params:
            del st.query_params[query_key]
    return current


def header_cell(field: str, label_key: str, tip_key: str | None, f: Filters, lang: str) -> str:
    active = f.sort == field
    if active:
        next_dir = "asc" if f.direction == "desc" else "desc"
    else:
        next_dir = screener.NATURAL_DIRECTION[field]
    is_default = field == screener.DEFAULT_SORT and next_dir == screener.NATURAL_DIRECTION[field]
    url = href(sort=None if is_default else field, dir=None if is_default else next_dir)
    arrow = (" ▲" if f.direction == "asc" else " ▼") if active else ""
    css = "sort-link active" if active else "sort-link"
    tooltip = t(tip_key, lang) if tip_key else ""
    return f"<th>{link(esc(t(label_key, lang)) + arrow, url, css, tooltip)}</th>"


def render_table(df: pd.DataFrame, f: Filters, lang: str):
    colgroup = "".join(f'<col style="width:{w}%">' for _, _, _, w, _ in TABLE_COLUMNS)
    header = "".join(header_cell(field, label, tip, f, lang) for field, label, tip, _, _ in TABLE_COLUMNS)
    rows = []
    for row in df.itertuples(index=False):
        cells = {
            "ticker": link(esc(row.ticker), href(ticker=row.ticker), "ticker-badge"),
            "name": f'<span title="{esc(row.name)}">{ltr(esc(row.name))}</span>',
            "sector": sector_pill(row.sector, lang),
            "price": cell_value(fmt_price(row.price), lang),
            "pe_ratio": cell_value(fmt_num(row.pe_ratio, 1), lang),
            "pb_ratio": cell_value(fmt_num(row.pb_ratio, 2), lang),
            "dividend_yield": cell_value(fmt_num(row.dividend_yield, 2, "%"), lang),
            "roe": cell_value(fmt_num(row.roe, 1, "%"), lang),
            "debt_to_equity": cell_value(fmt_num(row.debt_to_equity, 2), lang),
            "market_cap": cell_value(fmt_money(row.market_cap), lang),
            "value_score": score_badge(int(row.value_score)),
        }
        tds = "".join(
            f'<td class="wrap-cell">{cells[field]}</td>' if wraps else f"<td>{cells[field]}</td>"
            for field, _, _, _, wraps in TABLE_COLUMNS
        )
        rows.append(f"<tr>{tds}</tr>")
    st.markdown(
        f'<div class="table-wrapper"><table class="stock-table"><colgroup>{colgroup}</colgroup>'
        f'<thead><tr>{header}</tr></thead><tbody>{"".join(rows)}</tbody></table></div>',
        unsafe_allow_html=True,
    )


def render_price_chart(history: list[dict], lang: str):
    if not history:
        st.info(t("no_chart_data", lang))
        return
    hist = pd.DataFrame(history)
    hist["date"] = pd.to_datetime(hist["date"])
    first, last = hist["close"].iloc[0], hist["close"].iloc[-1]
    change = (last / first - 1) * 100
    change_cls = "change-up" if change >= 0 else "change-down"
    st.markdown(
        f'<p>{t("change_1y", lang)}: <span class="{change_cls}">{ltr(f"{change:+.1f}%")}</span></p>',
        unsafe_allow_html=True,
    )
    # Explicit padded domain: an area mark would otherwise force the axis to start
    # at $0, flattening the price movement that matters.
    low, high = hist["close"].min(), hist["close"].max()
    pad = max((high - low) * 0.1, high * 0.01)
    domain = [low - pad, high + pad]
    base = alt.Chart(hist).encode(
        x=alt.X(
            "date:T", title=None,
            axis=alt.Axis(format="%b %y", grid=False, tickCount={"interval": "month", "step": 2}),
        ),
        y=alt.Y("close:Q", title=None, scale=alt.Scale(domain=domain, nice=False), axis=alt.Axis(format="$,.0f")),
    )
    chart = (
        base.mark_area(color=PRIMARY, opacity=0.08).encode(y2=alt.datum(domain[0]))
        + base.mark_line(color=PRIMARY, strokeWidth=2)
        + base.mark_point(opacity=0, size=80).encode(
            tooltip=[
                alt.Tooltip("date:T", title="", format="%d/%m/%Y"),
                alt.Tooltip("close:Q", title="", format="$,.2f"),
            ]
        )
    ).properties(height=300)
    st.altair_chart(chart, width="stretch")


def render_detail(stock: dict, data: dict, lang: str):
    st.markdown(link(f"← {t('back_to_table', lang)}", href(ticker=None), "pill-button subtle"), unsafe_allow_html=True)
    st.markdown(
        f'<div class="detail-title"><h2>{ltr(esc(stock["ticker"]))} — {ltr(esc(stock["name"]))}</h2>'
        f'{sector_pill(stock.get("sector"), lang)}{score_badge(int(stock["value_score"]))}</div>',
        unsafe_allow_html=True,
    )
    as_of = stock.get("as_of")
    if as_of and as_of < data["last_updated"][:10]:
        st.markdown(f'<div class="stale-warning">{t("data_as_of", lang, date=as_of)}</div>', unsafe_allow_html=True)

    stats = [
        ("col_price", fmt_price(stock.get("price"))),
        ("col_pe", fmt_num(stock.get("pe_ratio"), 1)),
        ("col_pb", fmt_num(stock.get("pb_ratio"), 2)),
        ("col_dividend_yield", fmt_num(stock.get("dividend_yield"), 2, "%")),
        ("col_roe", fmt_num(stock.get("roe"), 1, "%")),
        ("col_debt_to_equity", fmt_num(stock.get("debt_to_equity"), 2)),
        ("col_market_cap", fmt_money(stock.get("market_cap"))),
        ("book_value_per_share", fmt_price(stock.get("book_value_per_share"))),
        ("free_cash_flow", fmt_money(stock.get("free_cash_flow"))),
    ]
    cards = "".join(
        f'<div class="metric-card"><div class="metric-label">{t(key, lang)}</div>'
        f'<div class="metric-value">{cell_value(value, lang)}</div></div>'
        for key, value in stats
    )
    st.subheader(t("key_stats", lang))
    st.markdown(f'<div class="metric-grid">{cards}</div>', unsafe_allow_html=True)

    criteria = [
        ("flag_pb_under_1", t("crit_pb", lang), fmt_num(stock.get("pb_ratio"), 2)),
        ("flag_low_pe", t("crit_pe", lang, v=config.PE_MAX), fmt_num(stock.get("pe_ratio"), 1)),
        ("flag_high_dividend", t("crit_div", lang, v=f"{config.DIVIDEND_YIELD_MIN:g}"),
         fmt_num(stock.get("dividend_yield"), 2, "%")),
        ("flag_low_debt", t("crit_debt", lang, v=f"{config.DEBT_TO_EQUITY_MAX:g}"),
         fmt_num(stock.get("debt_to_equity"), 2)),
        ("flag_positive_fcf", t("crit_fcf", lang), fmt_money(stock.get("free_cash_flow"))),
    ]
    items = "".join(
        f'<li><span class="{"crit-yes" if stock.get(flag) else "crit-no"}">{"✓" if stock.get(flag) else "✗"}</span> '
        f'{label} <span class="crit-value">({cell_value(value, lang)})</span></li>'
        for flag, label, value in criteria
    )
    st.subheader(t("criteria_header", lang, n=int(stock["value_score"])))
    st.markdown(f'<ul class="criteria">{items}</ul>', unsafe_allow_html=True)

    st.subheader(t("price_chart", lang))
    render_price_chart(stock.get("price_history") or [], lang)

    if stock.get("description"):
        st.subheader(t("description", lang))
        # Newlines would end the raw-HTML block and let Markdown (and $...$ math) parse the text.
        description = esc(stock["description"]).replace("\n", " ")
        st.markdown(f'<div class="description-block">{description}</div>', unsafe_allow_html=True)


def main():
    lang = get_lang()
    inject_css(lang)
    data, df = load_data(os.path.getmtime(config.DATA_FILE))

    ticker = st.query_params.get("ticker")
    stock = next((s for s in data["stocks"] if s["ticker"] == ticker), None) if ticker else None
    if stock:
        render_header(data, lang)
        render_detail(stock, data, lang)
        return

    # Filters run before the header so every link built below carries the current state.
    filters = sidebar_filters(df, lang)
    render_header(data, lang)

    result = screener.sort_stocks(screener.apply_filters(df, filters), filters.sort, filters.direction)
    reset = (
        link(t("reset_filters", lang), "?" + urlencode({"lang": "en"} if lang == "en" else {}), "pill-button subtle")
        if filters.has_active_filters() else ""
    )
    st.markdown(
        f'<div class="results-row"><span class="results-badge">'
        f'{t("results_count", lang, n=len(result), total=len(df))}</span>{reset}'
        f'<span class="hint">{t("sort_hint", lang)}</span></div>',
        unsafe_allow_html=True,
    )
    if result.empty:
        st.info(t("no_results", lang))
    else:
        render_table(result, filters, lang)


if __name__ == "__main__":
    main()
