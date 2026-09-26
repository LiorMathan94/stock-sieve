"""UI strings for Hebrew (default) and English. Add a new key here, not in app.py."""

STRINGS = {
    "app_title": {"he": "מסנן מניות ערך ודיבידנד", "en": "Value & Dividend Stock Screener"},
    "language_toggle": {"he": "English", "en": "עברית"},
    "last_updated": {"he": "עודכן לאחרונה", "en": "Last updated"},
    "disclaimer": {
        "he": "מכפיל רווח או הון נמוך לבדם אינם מעידים שמניה כדאית — גם עסקים בדעיכה יכולים להיראות \"זולים\".",
        "en": "A low P/E or P/B alone doesn't mean a stock is a good buy — declining businesses can look \"cheap\" too.",
    },
    "filters_header": {"he": "סינון", "en": "Filters"},
    "max_pe": {"he": "מכפיל רווח מקסימלי", "en": "Max P/E"},
    "max_pb": {"he": "מכפיל הון מקסימלי", "en": "Max P/B"},
    "min_dividend_yield": {"he": "תשואת דיבידנד מינימלית (%)", "en": "Min dividend yield (%)"},
    "min_roe": {"he": "תשואה על ההון מינימלית (%)", "en": "Min ROE (%)"},
    "book_over_market_only": {"he": "רק הון עצמי גבוה משווי שוק", "en": "Book value > market cap only"},
    "sector_filter": {"he": "סקטור", "en": "Sector"},
    "all_sectors": {"he": "כל הסקטורים", "en": "All sectors"},
    "results_count": {"he": "נמצאו {n} מניות", "en": "{n} stocks found"},
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
    "detail_header": {"he": "פרטי מניה", "en": "Stock Detail"},
    "select_stock": {"he": "בחר מניה לצפייה בפרטים", "en": "Select a stock to view details"},
    "back_to_table": {"he": "חזרה לטבלה", "en": "Back to table"},
    "description": {"he": "תיאור החברה", "en": "Company Description"},
    "price_chart": {"he": "גרף מחיר (12 חודשים אחרונים)", "en": "Price Chart (last 12 months)"},
    "key_stats": {"he": "נתונים עיקריים", "en": "Key Stats"},
    "free_cash_flow": {"he": "תזרים מזומנים חופשי", "en": "Free Cash Flow"},
    "book_value_per_share": {"he": "הון עצמי למניה", "en": "Book Value / Share"},
    "not_available": {"he": "לא זמין", "en": "N/A"},
    "no_results": {"he": "לא נמצאו מניות התואמות את הסינון", "en": "No stocks match these filters"},
    "no_chart_data": {"he": "אין נתוני מחיר זמינים", "en": "No price data available"},
}


def t(key: str, lang: str, **kwargs) -> str:
    entry = STRINGS.get(key, {})
    text = entry.get(lang) or entry.get("en") or key
    return text.format(**kwargs) if kwargs else text
