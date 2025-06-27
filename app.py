"""
Deep Stock Analysis Tool - Candles & Capital

Streamlit application that pulls live Nifty‑500 constituents, allows fuzzy
search, checks sector‑specific fundamental ratios and suggests trading
levels.

Requirements:
    streamlit >=1.20
    pandas
    yfinance
    lxml           # for pandas.read_html
"""

import yfinance as yf
import pandas as pd
import streamlit as st
from difflib import get_close_matches

# -------------------------------------------------------------
# Streamlit page configuration
# -------------------------------------------------------------
st.set_page_config(page_title="Stock Analyzer - Candles & Capital", layout="wide")
st.title("📊 Deep Stock Analysis Tool")

# -------------------------------------------------------------
# Sidebar
# -------------------------------------------------------------
with st.sidebar:
    st.image(
        "https://upload.wikimedia.org/wikipedia/commons/thumb/2/23/Candlestick_chart_icon.svg/1200px-Candlestick_chart_icon.svg.png",
        use_container_width=True,
    )
    st.title("Candles & Capital")
    st.markdown("📍 Visakhapatnam, Andhra Pradesh")
    st.markdown("Professional Stock Market Training Institute")

# -------------------------------------------------------------
# Helper utilities
# -------------------------------------------------------------

@st.cache_data(show_spinner="Downloading Nifty‑500 list…")
def load_company_map() -> dict[str, str]:
    """Scrape latest Nifty‑500 constituents and return {SYMBOL: FULL_NAME}."""
    url = "https://www.moneyseth.com/blogs/Nifty-500-Stocks-List"
    try:
        tables = pd.read_html(url, flavor="bs4")
        nifty500 = next(t for t in tables if "Symbol" in t.columns)
        nifty500.columns = nifty500.columns.str.strip().str.title()
        nifty500["Symbol"] = nifty500["Symbol"].str.upper()
        nifty500["Company Name"] = nifty500["Company Name"].str.upper()
        return dict(zip(nifty500["Symbol"], nifty500["Company Name"]))
    except Exception as err:
        st.warning(
            "⚠️ Could not fetch the live Nifty‑500 list. "
            "Reverting to a minimal built‑in sample."
        )
        st.exception(err)
        return {
            "RELIANCE": "RELIANCE INDUSTRIES LTD",
            "TCS": "TATA CONSULTANCY SERVICES LTD",
            "INFY": "INFOSYS LTD",
            "HDFCBANK": "HDFC BANK LTD",
            "SBIN": "STATE BANK OF INDIA",
        }

# Load map once per session
company_map = load_company_map()

# Sector‑specific ratios
SECTOR_RATIOS = {
    "Banks": ["priceToBook", "returnOnEquity"],
    "NBFCs": ["priceToBook", "trailingPE"],
    "Information Technology": ["trailingPE", "enterpriseToEbitda"],
    "IT Services": ["trailingPE", "enterpriseToEbitda"],
    "FMCG": ["trailingPE", "enterpriseToEbitda"],
    "Pharmaceuticals": ["trailingPE", "enterpriseToEbitda"],
    "Steel": ["enterpriseToEbitda"],
    "Cement": ["enterpriseToEbitda"],
    "Retail": ["trailingPE", "enterpriseToRevenue"],
}


def get_symbol_from_name(company_input: str) -> str | None:
    """Resolve a user‑supplied company name/ticker to an NSE symbol."""
    if not company_input:
        return None

    input_clean = company_input.strip().upper()
    input_lower = company_input.strip().lower()

    # 1️⃣ Exact symbol match
    if input_clean in company_map:
        return input_clean

    # 2️⃣ Exact full‑name match
    for symbol, name in company_map.items():
        if name.lower() == input_lower:
            return symbol

    # 3️⃣ Sub‑string match
    for symbol, name in company_map.items():
        if input_lower in name.lower():
            return symbol

    # 4️⃣ Fuzzy match
    closest = get_close_matches(
        input_lower,
        [n.lower() for n in company_map.values()],
        n=1,
        cutoff=0.6,
    )
    if closest:
        for symbol, name in company_map.items():
            if name.lower() == closest[0]:
                return symbol

    return None


def check_fundamentals(symbol: str) -> tuple[bool, str | None]:
    """Return (is_fundamentally_strong, sector)."""
    try:
        info = yf.Ticker(symbol).info
        sector = info.get("sector")
        ratios = SECTOR_RATIOS.get(sector, [])
        score = sum(
            1 for ratio in ratios if isinstance(info.get(ratio), (int, float)) and info[ratio] > 0
        )
        return score >= max(1, len(ratios) // 2), sector
    except Exception:
        return False, None


# -------------------------------------------------------------
# UI: Main panel
# -------------------------------------------------------------
st.markdown("## 🧠 Enter Analysis Criteria")
company_input = st.text_input("Enter Company Name or Symbol (e.g., Infosys, TCS)")
timeframe = st.selectbox("Select Timeframe", ["1d", "1wk", "1mo"])

if company_input:
    symbol = get_symbol_from_name(company_input)
    if not symbol:
        st.error("❌ Could not resolve the company name. Please check spelling or try another.")
        st.stop()

    try:
        ticker = yf.Ticker(symbol)
        info = ticker.info

        # Map interval → reasonable lookback period
        interval_period_map = {"1d": "1mo", "1wk": "1y", "1mo": "2y"}
        selected_period = interval_period_map.get(timeframe, "6mo")
        df = ticker.history(period=selected_period, interval=timeframe)

        # Fallback if empty
        fallback_intervals = {"1d": "5d", "1wk": "1mo", "1mo": "3mo"}
        if df.empty or df.Close.isna().all():
            fallback = fallback_intervals.get(timeframe)
            if fallback:
                st.warning(f"No data for '{timeframe}'. Trying fallback '{fallback}'…")
                df = ticker.history(period=selected_period, interval=fallback)
                timeframe = fallback

        if df.empty or df.Close.isna().all():
            st.error("❌ No data available even after fallback. Please try another stock/timeframe.")
            st.stop()

        is_strong, sector = check_fundamentals(symbol)

        st.subheader(f"📄 {info.get('shortName', symbol)} ({symbol})")
        st.markdown(f"**Sector:** {sector or 'Unknown'}")

        if is_strong:
            st.success("✅ Fundamentally strong based on sector‑specific ratios.")
        else:
            st.error("❌ Fundamentally weak based on sector criteria.")

        last_close = df.Close.iloc[-1]
        high_6m = df.High.max()
        low_6m = df.Low.min()

        entry = round(last_close * 0.98, 2)
        target = round(last_close * 1.08, 2)
        stop = round(last_close * 0.94, 2)

        valuation_comment = (
            "📍 Trading near 6‑month highs (possibly overvalued)."
            if last_close >= high_6m * 0.95 else
            "📉 Trading near lower end (possibly undervalued)."
            if last_close <= low_6m * 1.05 else
            "🔄 Mid‑range valuation."
        )

        st.markdown("### 📌 Suggested Levels")
        levels_df = pd.DataFrame([
            {
                "Stock Name": info.get("shortName", symbol),
                "Entry Range (₹)": float(entry),
                "Target Range (₹)": float(target),
                "Stop Loss (₹)": float(stop),
                "Valuation Position": valuation_comment,
            }
        ])
        st.dataframe(
            levels_df.style.set_table_styles([
                {"selector": "thead th", "props": [("font-size", "14px")]},
                {"selector": "td", "props": [("font-size", "13px")]},
            ]),
            use_container_width=True,
        )

    except Exception as err:
        st.error("An unexpected error occurred while processing your request.")
        st.exception(err)
