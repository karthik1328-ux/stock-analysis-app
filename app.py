import yfinance as yf
import pandas as pd
import streamlit as st
import datetime
import traceback
import plotly.graph_objs as go
import requests
from difflib import get_close_matches

st.set_page_config(page_title="Stock Analyzer - Candles & Capital", layout="wide")
st.title("📊 Deep Stock Analysis Tool")

# Institute branding (corrected logo URL and updated parameter)
st.sidebar.image("https://upload.wikimedia.org/wikipedia/commons/thumb/2/23/Candlestick_chart_icon.svg/1200px-Candlestick_chart_icon.svg.png", use_container_width=True)
st.sidebar.title("Candles & Capital")
st.sidebar.markdown("📍 Visakhapatnam, Andhra Pradesh")
st.sidebar.markdown("Professional Stock Market Training Institute")

# Map for fuzzy match
company_map = {
    "TCS": "Tata Consultancy Services",
    "INFY": "Infosys",
    "RELIANCE": "Reliance Industries",
    "HDFCBANK": "HDFC Bank",
    "ICICIBANK": "ICICI Bank",
    "ASIANPAINT": "Asian Paints",
    "SUNPHARMA": "Sun Pharma",
    "ITC": "ITC Limited",
    "MARUTI": "Maruti Suzuki"
}

# Sector-based valuation check
SECTOR_RATIOS = {
    "Banks": ["priceToBook", "returnOnEquity"],
    "NBFCs": ["priceToBook", "trailingPE"],
    "IT Services": ["trailingPE", "enterpriseToEbitda"],
    "FMCG": ["trailingPE", "enterpriseToEbitda"],
    "Pharmaceuticals": ["trailingPE", "enterpriseToEbitda"],
    "Steel": ["enterpriseToEbitda"],
    "Cement": ["enterpriseToEbitda"],
    "Retail": ["trailingPE", "enterpriseToRevenue"],
}

# Resolve stock symbol
def get_symbol_from_name(company_name):
    closest = get_close_matches(company_name.lower(), [v.lower() for v in company_map.values()], n=1, cutoff=0.6)
    if closest:
        for symbol, name in company_map.items():
            if name.lower() == closest[0]:
                return symbol
    return None

# Fundamental check
def check_fundamentals(symbol):
    try:
        ticker = yf.Ticker(symbol)
        info = ticker.info
        sector = info.get("sector")
        ratios = SECTOR_RATIOS.get(sector, [])
        score = 0
        for ratio in ratios:
            val = info.get(ratio)
            if isinstance(val, (int, float)) and val > 0:
                score += 1
        return score >= max(1, len(ratios)//2), sector
    except:
        return False, None

# UI
company_input = st.text_input("Enter Company Name (e.g., Infosys, Reliance)")
timeframe = st.selectbox("Select Timeframe", ["1d", "1wk", "1mo"])

if company_input:
    symbol = get_symbol_from_name(company_input)
    if not symbol:
        st.error("❌ Could not resolve the company name. Please check spelling or try another.")
    else:
        try:
            ticker = yf.Ticker(symbol)
            info = ticker.info
            df = ticker.history(period="6mo", interval=timeframe)

            if df.empty:
                st.warning("No data available for the selected timeframe.")
                st.stop()

            is_strong, sector = check_fundamentals(symbol)

            st.subheader(f"📈 {info.get('shortName')} ({symbol})")
            st.markdown(f"**Sector:** {sector or 'Unknown'}")

            if is_strong:
                st.success("✅ Fundamentally strong based on sector-specific key ratios.")
            else:
                st.error("❌ Fundamentally weak based on sector criteria.")

            # Chart
            fig = go.Figure()
            fig.add_trace(go.Candlestick(x=df.index,
                            open=df['Open'], high=df['High'],
                            low=df['Low'], close=df['Close']))
            fig.update_layout(xaxis_rangeslider_visible=False)
            st.plotly_chart(fig, use_container_width=True)

            # Technicals
            last_close = df['Close'].iloc[-1]
            high_6m = df['High'].max()
            low_6m = df['Low'].min()

            entry = round(last_close * 0.98, 2)
            target = round(last_close * 1.08, 2)
            stop = round(last_close * 0.94, 2)

            valuation_comment = "📍 Trading near 6-month highs (possibly overvalued)." if last_close >= high_6m * 0.95 else \
                                "📉 Trading near lower end (possibly undervalued)." if last_close <= low_6m * 1.05 else \
                                "🔄 Mid-range valuation."

            st.markdown("### 📌 Suggested Levels")
            levels_df = pd.DataFrame([{
                "Stock Name": info.get("shortName", symbol),
                "Entry Range (₹)": entry,
                "Target Range (₹)": target,
                "Stop Loss (₹)": stop,
                "Valuation Position": valuation_comment
            }])
            st.dataframe(levels_df, use_container_width=True)

        except Exception as e:
            st.error("An error occurred during processing.")
            st.exception(e)
