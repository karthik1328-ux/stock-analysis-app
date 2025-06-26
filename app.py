import yfinance as yf
import pandas as pd
import streamlit as st
import datetime
import traceback
import plotly.graph_objs as go
import requests
from difflib import get_close_matches

st.set_page_config(page_title="Stock Analyzer", layout="wide")
st.title("\U0001F4CA Deep Stock Analysis Tool")

# Sector Rotation Highlighting
SECTOR_LIST = [
    ("Banks", False), ("NBFCs", False), ("IT Services", True), ("FMCG", True),
    ("Pharmaceuticals", True), ("Steel", False), ("Cement", False), ("Retail", True),
    ("Automobiles", True), ("Capital Goods / Infra", True), ("Power Utilities", True)
]

selected_sector = st.selectbox("Select Sector:", [f"\033[92m{s[0]}\033[0m" if s[1] else s[0] for s in SECTOR_LIST])
st.markdown("_Sectors in green are short-term favorable_", unsafe_allow_html=True)

# Function to fetch good companies by sector
@st.cache_data(show_spinner=False)
def get_good_fundamentals(sector_name):
    all_symbols = ["TCS", "INFY", "HDFCBANK", "ASIANPAINT", "SUNPHARMA", "ITC", "RELIANCE", "ICICIBANK", "MARUTI"]
    results = []
    for symbol in all_symbols:
        try:
            ticker = yf.Ticker(symbol)
            info = ticker.info
            if sector_name.lower() in str(info.get("sector", "")).lower():
                pe = info.get("trailingPE") or 0
                roe = info.get("returnOnEquity") or 0
                if pe > 10 and roe > 10:
                    last_close = ticker.history(period="1mo")['Close'].iloc[-1]
                    target = round(last_close * 1.08, 2)
                    stop = round(last_close * 0.95, 2)
                    results.append({
                        "Company": info.get("shortName"),
                        "Symbol": symbol,
                        "Entry": round(last_close, 2),
                        "Target": target,
                        "Stop Loss": stop
                    })
        except:
            continue
    return pd.DataFrame(results)

if selected_sector:
    st.subheader(f"\U0001F4BC Top Fundamental Stocks in {selected_sector.strip(chr(27))} Sector")
    df = get_good_fundamentals(selected_sector.strip(chr(27)))
    if not df.empty:
        st.dataframe(df, use_container_width=True)
    else:
        st.info("No strong fundamental stocks found in this sector.")
