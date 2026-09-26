"""UI strings for Hebrew (default) and English. Add a new key here, not in app.py."""

STRINGS = {
    "app_title": {"he": "מסנן מניות ערך ודיבידנד", "en": "Value & Dividend Stock Screener"},
    "language_toggle": {"he": "English", "en": "עברית"},
    "last_updated": {"he": "עודכן לאחרונה", "en": "Last updated"},
    "israel_time": {"he": "שעון ישראל", "en": "Israel time"},
    "stale_warning": {
        "he": "הנתונים לא עודכנו כבר {days} ימים — ייתכן שהעדכון היומי נכשל.",
        "en": "Data hasn't been refreshed for {days} days — the daily update may be failing.",
    },
    "disclaimer": {
        "he": "מכפיל רווח או הון נמוך לבדם אינם מעידים שמניה כדאית — גם עסקים בדעיכה יכולים להיראות \"זולים\".",
        "en": "A low P/E or P/B alone doesn't mean a stock is a good buy — declining businesses can look \"cheap\" too.",
    },

    "tab_recommended": {"he": "מומלצות", "en": "Recommended"},
    "tab_all_stocks": {"he": "כל המניות", "en": "All Stocks"},
    "recommended_explainer": {
        "he": "המניות המובילות שעומדות בשלושת קריטריוני הערך: מכפיל רווח נמוך, תשואת דיבידנד גבוהה וחוב נמוך.",
        "en": "The top stocks meeting all 3 value criteria: low P/E, high dividend yield, and low debt.",
    },

    "filters_header": {"he": "סינון", "en": "Filters"},
    "max_pe": {"he": "מכפיל רווח מקסימלי", "en": "Max P/E"},
    "max_pb": {"he": "מכפיל הון מקסימלי", "en": "Max P/B"},
    "min_dividend_yield": {"he": "תשואת דיבידנד מינימלית (%)", "en": "Min dividend yield (%)"},
    "min_roe": {"he": "תשואה על ההון מינימלית (%)", "en": "Min ROE (%)"},
    "no_limit_help": {"he": "גררו עד הסוף לביטול ההגבלה", "en": "Slide all the way to the end for no limit"},
    "book_over_market_only": {"he": "רק הון עצמי גבוה משווי שוק", "en": "Book value > market cap only"},
    "sector_filter": {"he": "סקטור", "en": "Sector"},
    "all_sectors": {"he": "כל הסקטורים", "en": "All sectors"},
    "reset_filters": {"he": "איפוס סינון", "en": "Reset filters"},
    "results_count": {"he": "{n} מתוך {total} מניות", "en": "{n} of {total} stocks"},
    "sort_hint": {"he": "לחצו על כותרת עמודה כדי למיין", "en": "Click a column header to sort"},

    "col_ticker": {"he": "טיקר", "en": "Ticker"},
    "col_name": {"he": "שם", "en": "Name"},
    "col_sector": {"he": "סקטור", "en": "Sector"},
    "col_price": {"he": "מחיר", "en": "Price"},
    "col_pe": {"he": "מכפיל רווח", "en": "P/E"},
    "col_pb": {"he": "מכפיל הון", "en": "P/B"},
    "col_dividend_yield": {"he": "תשואת דיבידנד", "en": "Dividend Yield"},
    "col_roe": {"he": "תשואה על ההון", "en": "ROE"},
    "col_debt_to_equity": {"he": "חוב להון", "en": "Debt / Equity"},
    "col_market_cap": {"he": "שווי שוק", "en": "Market Cap"},
    "col_value_score": {"he": "ציון ערך", "en": "Value Score"},

    # Plain-language explanations shown as header tooltips.
    "tip_ticker": {"he": "סימול המניה בבורסה — לחצו עליו לפרטים", "en": "Stock symbol — click it for details"},
    "tip_price": {"he": "מחיר המניה האחרון, במטבע המקומי שלה", "en": "Latest share price, in the stock's local currency"},
    "tip_pe": {
        "he": "מחיר המניה חלקי הרווח השנתי למניה. נמוך יותר = זול יותר ביחס לרווחים",
        "en": "Share price divided by yearly earnings per share. Lower = cheaper relative to profits",
    },
    "tip_pb": {
        "he": "מחיר המניה חלקי ההון העצמי למניה. מתחת ל-1 = השוק מעריך את החברה בפחות מההון העצמי שלה",
        "en": "Share price divided by book value per share. Below 1 = the market values the company below its net assets",
    },
    "tip_dividend_yield": {
        "he": "הדיבידנד השנתי כאחוז ממחיר המניה",
        "en": "Yearly dividend as a percentage of the share price",
    },
    "tip_roe": {
        "he": "הרווח הנקי כאחוז מההון העצמי — מדד לאיכות ולרווחיות העסק",
        "en": "Net profit as a percentage of shareholders' equity — a measure of business quality",
    },
    "tip_debt_to_equity": {
        "he": "סך החוב חלקי ההון העצמי. נמוך יותר = פחות מינוף וסיכון",
        "en": "Total debt divided by equity. Lower = less leverage and risk",
    },
    "tip_market_cap": {"he": "השווי הכולל של כל מניות החברה", "en": "Total value of all the company's shares"},
    "tip_value_score": {
        "he": "בכמה מתוך 5 קריטריוני הערך המניה עומדת (הפירוט בדף המניה)",
        "en": "How many of the 5 value criteria the stock meets (details on the stock page)",
    },

    "back_to_table": {"he": "חזרה לטבלה", "en": "Back to table"},
    "description": {"he": "תיאור החברה", "en": "Company Description"},
    "price_chart": {"he": "מחיר ב-12 החודשים האחרונים", "en": "Price over the last 12 months"},
    "change_1y": {"he": "שינוי ב-12 חודשים", "en": "12-month change"},
    "key_stats": {"he": "נתונים עיקריים", "en": "Key Stats"},
    "free_cash_flow": {"he": "תזרים מזומנים חופשי", "en": "Free Cash Flow"},
    "book_value_per_share": {"he": "הון עצמי למניה", "en": "Book Value / Share"},
    "data_as_of": {
        "he": "העדכון האחרון לא הצליח עבור מניה זו — הנתונים נכונים ל-{date}",
        "en": "The latest refresh failed for this stock — data is as of {date}",
    },
    "data_source": {"he": "מקור הנתונים", "en": "Data source"},
    "as_of_date": {"he": "נכון לתאריך {date}", "en": "as of {date}"},

    "criteria_header": {"he": "קריטריוני ערך — {n} מתוך 5", "en": "Value criteria — {n} of 5 met"},
    "crit_pb": {"he": "מכפיל הון מתחת ל-1 (הון עצמי גבוה משווי השוק)", "en": "P/B below 1 (book value above market cap)"},
    "crit_pe": {"he": "מכפיל רווח מתחת ל-{v}", "en": "P/E below {v}"},
    "crit_div": {"he": "תשואת דיבידנד מעל {v}%", "en": "Dividend yield above {v}%"},
    "crit_debt": {"he": "יחס חוב להון מתחת ל-{v}", "en": "Debt/equity below {v}"},
    "crit_fcf": {"he": "תזרים מזומנים חופשי חיובי", "en": "Positive free cash flow"},

    "not_available": {"he": "לא זמין", "en": "N/A"},
    "no_results": {"he": "לא נמצאו מניות התואמות את הסינון", "en": "No stocks match these filters"},
    "no_chart_data": {"he": "אין נתוני מחיר זמינים", "en": "No price data available"},
}


def t(key: str, lang: str, **kwargs) -> str:
    entry = STRINGS.get(key, {})
    text = entry.get(lang) or entry.get("en") or key
    return text.format(**kwargs) if kwargs else text
