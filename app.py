"""
Streamlit UI. Reads only the cached data/stocks.json produced by fetch_data.py
-- no live API calls on page load, to stay within free API limits.
"""
import json
from datetime import datetime

import pandas as pd
import streamlit as st

import config
from translations import t

st.set_page_config(page_title="Stock Sieve", layout="wide")

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


@st.cache_data
def load_data():
    with open(config.DATA_FILE, encoding="utf-8") as f:
        return json.load(f)


def ltr(html: str) -> str:
    """Wrap a value so it renders left-to-right even inside an RTL row/sentence."""
    return f'<span dir="ltr">{html}</span>'


def fmt_num(value, decimals=1, suffix=""):
    if value is None or pd.isna(value):
        return None
    return f"{value:,.{decimals}f}{suffix}"


def fmt_market_cap(value):
    if value is None or pd.isna(value):
        return None
    for divisor, label in ((1e12, "T"), (1e9, "B"), (1e6, "M")):
        if value >= divisor:
            return f"${value / divisor:,.1f}{label}"
    return f"${value:,.0f}"


def na_or(value, lang):
    return value if value is not None else t("not_available", lang)


def get_lang() -> str:
    return st.query_params.get("lang", "he")


def nav_link(label: str, **params) -> str:
    query = st.query_params.to_dict()
    query.update(params)
    qs = "&".join(f"{k}={v}" for k, v in query.items() if v is not None)
    return f'<a href="?{qs}" target="_self">{label}</a>'


def inject_css(lang: str):
    rtl = lang == "he"
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
        /* Table columns still flow right-to-left; cells themselves stay centered */
        table.stock-table thead tr, table.stock-table tbody tr { direction: rtl; }
    """ if rtl else ""
    st.markdown(
        f"""
        <style>
        html, body, [class*="css"] {{
            font-family: -apple-system, "Segoe UI", Roboto, "Noto Sans Hebrew", Arial, sans-serif;
        }}
        {rtl_rules}
        section[data-testid="stSidebar"] {{ width: 260px !important; min-width: 260px !important; }}

        h1 {{ font-weight: 800; letter-spacing: -0.01em; }}
        .last-updated {{ color: #94a3b8; font-size: 0.82rem; margin-bottom: 2px; }}
        .disclaimer {{
            color: #94a3b8; font-size: 0.82rem; font-style: italic; margin-top: 0;
            border-inline-start: 3px solid #e2e8f0; padding-inline-start: 10px;
        }}
        .results-badge {{
            display: inline-block; background: #1a6f4c; color: white; font-weight: 700;
            padding: 4px 14px; border-radius: 999px; font-size: 0.95rem;
        }}
        .lang-toggle {{
            display: inline-block; padding: 6px 18px; border-radius: 999px;
            border: 1.5px solid #1a6f4c; color: #1a6f4c !important; font-weight: 600;
            text-decoration: none !important; font-size: 0.85rem; background: white;
            transition: background-color 0.15s, color 0.15s;
        }}
        .lang-toggle:hover {{ background: #1a6f4c; color: white !important; }}

        .table-wrapper {{
            max-height: 70vh; overflow-y: auto; overflow-x: hidden;
            border: 1px solid #e2e8f0; border-radius: 12px;
            box-shadow: 0 1px 4px rgba(15, 23, 42, 0.06); margin-top: 4px;
        }}
        table.stock-table {{
            width: 100%; table-layout: fixed; border-collapse: separate; border-spacing: 0;
            font-variant-numeric: tabular-nums; background: white;
        }}
        table.stock-table thead th {{
            position: sticky; top: 0; z-index: 2; background: #16543c; color: #ffffff;
            font-size: 0.7rem; text-transform: uppercase; letter-spacing: 0.03em;
            font-weight: 700; padding: 10px 4px; text-align: center;
            word-break: keep-all; overflow-wrap: normal;
        }}
        table.stock-table td {{
            padding: 7px 4px; border-bottom: 1px solid #eef1ef; font-size: 0.82rem;
            color: #1e293b; text-align: center; overflow: hidden;
            text-overflow: ellipsis; white-space: nowrap;
        }}
        table.stock-table td.wrap-cell {{ white-space: normal; word-break: break-word; }}
        table.stock-table tbody tr:nth-child(even) {{ background-color: #fafbfa; }}
        table.stock-table tbody tr:hover {{ background-color: #eaf4ee; }}

        .ticker-badge {{
            display: inline-block; padding: 3px 8px; border-radius: 6px;
            background: #e6f4ee; color: #15633f !important; font-weight: 700;
            text-decoration: none !important; font-size: 0.8rem;
        }}
        .ticker-badge:hover {{ background: #c9e9d8; }}
        .sector-pill {{
            display: inline-block; padding: 2px 8px; border-radius: 999px;
            font-size: 0.68rem; font-weight: 600; max-width: 100%;
            overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
            vertical-align: middle;
        }}
        .score-badge {{
            display: inline-block; min-width: 20px; padding: 2px 8px; border-radius: 999px;
            font-weight: 700; font-size: 0.78rem;
        }}

        .description-block {{ direction: ltr; text-align: left; color: #333; line-height: 1.6; }}
        ul.key-stats {{ list-style-position: inside; padding: 0; margin: 0; }}
        ul.key-stats li {{ padding: 4px 0; border-bottom: 1px solid #f1f5f9; }}
        </style>
        """,
        unsafe_allow_html=True,
    )


def sector_pill(sector: str | None, lang: str) -> str:
    if not sector:
        return ltr(t("not_available", lang))
    bg, fg = SECTOR_COLORS.get(sector, SECTOR_FALLBACK_COLOR)
    return f'<span class="sector-pill" style="background:{bg};color:{fg};">{ltr(sector)}</span>'


def score_badge(score: int) -> str:
    for threshold in sorted(SCORE_COLORS, reverse=True):
        if score >= threshold:
            bg, fg = SCORE_COLORS[threshold]
            break
    return f'<span class="score-badge" style="background:{bg};color:{fg};">{score}</span>'


def render_table(df: pd.DataFrame, lang: str):
    # (field, translation key, column width %, wraps instead of truncating)
    cols = [
        ("ticker", "col_ticker", 7, False), ("name", "col_name", 22, True),
        ("sector", "col_sector", 12, False), ("price", "col_price", 8, False),
        ("pe_ratio", "col_pe", 7, False), ("pb_ratio", "col_pb", 7, False),
        ("dividend_yield", "col_dividend_yield", 8, False), ("roe", "col_roe", 7, False),
        ("debt_to_equity", "col_debt_to_equity", 8, False), ("market_cap", "col_market_cap", 9, False),
        ("value_score", "col_value_score", 5, False),
    ]
    colgroup = "".join(f'<col style="width:{w}%">' for _, _, w, _ in cols)
    header = "".join(f"<th>{t(label_key, lang)}</th>" for _, label_key, _, _ in cols)
    rows_html = []
    for _, row in df.iterrows():
        cells = []
        for field, _, _, wraps in cols:
            if field == "ticker":
                value = nav_link(row["ticker"], ticker=row["ticker"]).replace(
                    "<a ", '<a class="ticker-badge" '
                )
            elif field == "name":
                value = ltr(row["name"] or "")
            elif field == "sector":
                value = sector_pill(row["sector"], lang)
            elif field == "price":
                value = ltr(na_or(fmt_num(row["price"], 2, " $"), lang))
            elif field == "pe_ratio":
                value = ltr(na_or(fmt_num(row["pe_ratio"], 1), lang))
            elif field == "pb_ratio":
                value = ltr(na_or(fmt_num(row["pb_ratio"], 2), lang))
            elif field == "dividend_yield":
                value = ltr(na_or(fmt_num(row["dividend_yield"], 2, "%"), lang))
            elif field == "roe":
                value = ltr(na_or(fmt_num(row["roe"], 1, "%"), lang))
            elif field == "debt_to_equity":
                value = ltr(na_or(fmt_num(row["debt_to_equity"], 2), lang))
            elif field == "market_cap":
                value = ltr(na_or(fmt_market_cap(row["market_cap"]), lang))
            elif field == "value_score":
                value = score_badge(int(row["value_score"]))
            cls = ' class="wrap-cell"' if wraps else ""
            cells.append(f"<td{cls}>{value}</td>")
        rows_html.append(f"<tr>{''.join(cells)}</tr>")
    st.markdown(
        f'<div class="table-wrapper"><table class="stock-table"><colgroup>{colgroup}</colgroup>'
        f'<thead><tr>{header}</tr></thead><tbody>{"".join(rows_html)}</tbody></table></div>',
        unsafe_allow_html=True,
    )


def render_detail(stock: dict, lang: str):
    st.markdown(nav_link(f"← {t('back_to_table', lang)}", ticker=None), unsafe_allow_html=True)
    st.header(f"{stock['ticker']} — {stock['name']}")

    stats = [
        ("col_price", fmt_num(stock["price"], 2, " $")),
        ("col_pe", fmt_num(stock["pe_ratio"], 1)),
        ("col_pb", fmt_num(stock["pb_ratio"], 2)),
        ("col_dividend_yield", fmt_num(stock["dividend_yield"], 2, "%")),
        ("col_roe", fmt_num(stock["roe"], 1, "%")),
        ("col_debt_to_equity", fmt_num(stock["debt_to_equity"], 2)),
        ("col_market_cap", fmt_market_cap(stock["market_cap"])),
        ("book_value_per_share", fmt_num(stock["book_value_per_share"], 2, " $")),
        ("free_cash_flow", fmt_market_cap(stock["free_cash_flow"])),
    ]
    st.subheader(t("key_stats", lang))
    items = "".join(
        f"<li>{t(key, lang)}: {ltr(na_or(value, lang))}</li>" for key, value in stats
    )
    st.markdown(f'<ul class="key-stats">{items}</ul>', unsafe_allow_html=True)

    if stock.get("description"):
        st.subheader(t("description", lang))
        st.markdown(f'<div class="description-block">{stock["description"]}</div>', unsafe_allow_html=True)

    st.subheader(t("price_chart", lang))
    history = stock.get("price_history") or []
    if history:
        hist_df = pd.DataFrame(history)
        hist_df["date"] = pd.to_datetime(hist_df["date"])
        st.line_chart(hist_df.set_index("date")["close"])
    else:
        st.info(t("no_chart_data", lang))


def main():
    lang = get_lang()
    inject_css(lang)
    data = load_data()
    stocks_by_ticker = {s["ticker"]: s for s in data["stocks"]}

    top_cols = st.columns([6, 1])
    with top_cols[0]:
        st.title(t("app_title", lang))
    with top_cols[1]:
        other_lang = "en" if lang == "he" else "he"
        toggle_link = nav_link(t("language_toggle", lang), lang=other_lang).replace(
            "<a ", '<a class="lang-toggle" '
        )
        st.markdown(toggle_link, unsafe_allow_html=True)

    last_updated = datetime.fromisoformat(data["last_updated"]).strftime("%Y-%m-%d %H:%M UTC")
    st.markdown(f'<p class="last-updated">{t("last_updated", lang)}: {ltr(last_updated)}</p>', unsafe_allow_html=True)
    st.markdown(f'<p class="disclaimer">{t("disclaimer", lang)}</p>', unsafe_allow_html=True)

    selected_ticker = st.query_params.get("ticker")
    if selected_ticker and selected_ticker in stocks_by_ticker:
        render_detail(stocks_by_ticker[selected_ticker], lang)
        return

    df = pd.DataFrame(data["stocks"])

    st.sidebar.header(t("filters_header", lang))
    max_pe = st.sidebar.slider(t("max_pe", lang), 0, 100, 100)
    max_pb = st.sidebar.slider(t("max_pb", lang), 0.0, 20.0, 20.0)
    min_div = st.sidebar.slider(t("min_dividend_yield", lang), 0.0, 10.0, 0.0)
    min_roe = st.sidebar.slider(t("min_roe", lang), 0, 50, 0)
    pb_only = st.sidebar.checkbox(t("book_over_market_only", lang))

    sectors = sorted(s for s in df["sector"].dropna().unique())
    sector_choice = st.sidebar.selectbox(t("sector_filter", lang), [t("all_sectors", lang)] + sectors)

    mask = pd.Series(True, index=df.index)
    mask &= df["pe_ratio"].isna() | (df["pe_ratio"] <= max_pe)
    mask &= df["pb_ratio"].isna() | (df["pb_ratio"] <= max_pb)
    mask &= df["dividend_yield"].isna() | (df["dividend_yield"] >= min_div)
    mask &= df["roe"].isna() | (df["roe"] >= min_roe)
    if pb_only:
        mask &= df["flag_pb_under_1"]
    if sector_choice != t("all_sectors", lang):
        mask &= df["sector"] == sector_choice

    filtered = df[mask].sort_values("value_score", ascending=False)

    st.markdown(
        f'<h3><span class="results-badge">{t("results_count", lang, n=len(filtered))}</span></h3>',
        unsafe_allow_html=True,
    )
    if filtered.empty:
        st.info(t("no_results", lang))
    else:
        render_table(filtered, lang)


if __name__ == "__main__":
    main()
