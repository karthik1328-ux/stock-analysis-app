import yfinance as yf
import pandas as pd
import streamlit as st
import datetime
import traceback
import plotly.graph_objs as go
import requests
from difflib import get_close_matches

st.set_page_config(page_title="Stock Analyzer", layout="wide")
st.title("📊 Deep Stock Analysis Tool")

# Stock symbol finder with fuzzy match
def get_symbol_from_name(company_name):
    all_tickers = ["TCS", "INFY", "RELIANCE", "HDFCBANK", "ICICIBANK", "ASIANPAINT", "SUNPHARMA", "ITC", "MARUTI"]
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
    closest = get_close_matches(company_name.lower(), [v.lower() for v in company_map.values()], n=1, cutoff=0.6)
    if closest:
        for k, v in company_map.items():
            if v.lower() == closest[0]:
                return k
    return None

# Input
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
            else:
                st.subheader(f"📈 Price Chart: {info.get('shortName')} ({symbol})")
                fig = go.Figure()
                fig.add_trace(go.Candlestick(x=df.index,
                                open=df['Open'], high=df['High'],
                                low=df['Low'], close=df['Close']))
                st.plotly_chart(fig, use_container_width=True)

                # Basic Technical Levels
                last_close = df['Close'].iloc[-1]
                entry = round(last_close * 0.98, 2)
                target = round(last_close * 1.08, 2)
                stop = round(last_close * 0.94, 2)

                st.markdown("### Suggested Levels")
                levels_df = pd.DataFrame([{
                    "Stock Name": info.get("shortName"),
                    "Entry Range": entry,
                    "Target Range": target,
                    "Stop Loss": stop
                }])
                st.dataframe(levels_df, use_container_width=True)

        except Exception as e:
            st.error("An error occurred while fetching data.")
            st.exception(e)
