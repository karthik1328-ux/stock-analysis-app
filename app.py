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

# Function to suggest correct stock symbols from company name
def suggest_symbols(query):
    try:
        response = requests.get(f"https://query2.finance.yahoo.com/v1/finance/search?q={query}")
        if response.status_code == 200:
            results = response.json().get("quotes", [])
            suggestions = [f"{item['symbol']} ({item.get('shortname', '')})" for item in results[:5]]
            if results:
                return results[0]['symbol'], suggestions
        return None, []
    except:
        return None, []

# User Inputs
stock_query = st.text_input("Enter Company Name (e.g., Reliance):")
timeframe = st.selectbox("Select Timeframe:", ["1d", "1wk", "1mo"])

# Sector-based key valuation logic
SECTOR_RATIOS = {
    "Banks": ["priceToBook", "returnOnEquity"],
    "NBFCs": ["priceToBook", "trailingPE"],
    "IT Services": ["trailingPE", "enterpriseToEbitda"],
    "FMCG": ["trailingPE", "enterpriseToEbitda"],
    "Pharmaceuticals": ["trailingPE", "enterpriseToEbitda"],
    "Steel": ["enterpriseToEbitda"],
    "Cement": ["enterpriseToEbitda"],
    "Retail": ["trailingPE", "enterpriseToRevenue"],
    # Add more mappings as needed
}

# Deep fundamental analysis using key ratios

def check_fundamentals(symbol):
    try:
        ticker = yf.Ticker(symbol)
        info = ticker.info
        sector = info.get("sector")
        if not sector:
            return False, None, {}

        ratios = SECTOR_RATIOS.get(sector, [])
        score = 0
        fundamentals = {}

        for ratio in ratios:
            val = info.get(ratio)
            fundamentals[ratio] = val
            if val and isinstance(val, (int, float)) and val > 0:
                score += 1

        high_valued = False
        if "trailingPE" in info and isinstance(info["trailingPE"], (int, float)):
            high_valued = info["trailingPE"] > 40  # threshold for being overvalued

        return score >= len(ratios) // 2, sector, fundamentals, high_valued

    except:
        return False, None, {}, False

# Start analysis only when stock is entered
if stock_query:
    try:
        with st.spinner("Resolving company symbol and fetching data..."):
            symbol, suggestions = suggest_symbols(stock_query)

        if not symbol:
            st.warning("⚠️ Could not resolve the company name. Did you mean:")
            for s in suggestions:
                st.markdown(f"- **{s}**")
            st.stop()

        data = yf.download(symbol, period="1y", interval=timeframe, progress=False, threads=False).dropna()

        if data is None or data.empty or 'Close' not in data.columns:
            st.error("❌ Data unavailable or incorrect.")
            st.stop()

        if len(data) < 15:
            st.warning("Not enough data for analysis. Trying higher timeframe...")
            alt_frames = {"1d": "1wk", "1wk": "1mo", "1mo": None}
            next_tf = alt_frames.get(timeframe)
            if next_tf:
                data = yf.download(symbol, period="1y", interval=next_tf, progress=False, threads=False).dropna()
                timeframe = next_tf
            else:
                st.error("No data found with any timeframe.")
                st.stop()

        st.subheader("\U0001F50D Fundamental Strength Check")
        is_strong, sector, fundamentals, is_high = check_fundamentals(symbol)

        if is_strong:
            st.success(f"Stock appears fundamentally strong in **{sector}** sector. Proceeding with technical analysis.")

            if is_high:
                st.warning("⚠️ The stock appears to be trading at a high valuation based on its sector metrics.")

            st.write("### Key Fundamental Ratios")
            for k, v in fundamentals.items():
                st.write(f"**{k}:** {v}")

            last_close = float(data['Close'].dropna().iloc[-1])
            high = float(data['High'].max())
            low = float(data['Low'].min())

            fib_levels = [0.236, 0.382, 0.5, 0.618, 0.786]
            fib_values = {f"{int(level*100)}%": round(high - (high - low) * level, 2) for level in fib_levels}

            delta = data['Close'].diff()
            gain = delta.where(delta > 0, 0)
            loss = -delta.where(delta < 0, 0)
            avg_gain = gain.rolling(window=14).mean()
            avg_loss = loss.rolling(window=14).mean()
            rs = avg_gain / avg_loss
            rsi = 100 - (100 / (1 + rs))
            current_rsi = round(float(rsi.dropna().iloc[-1]), 2)

            ma20 = round(data['Close'].rolling(window=20).mean().iloc[-1], 2) if len(data) >= 20 else "-"
            ma50 = round(data['Close'].rolling(window=50).mean().iloc[-1], 2) if len(data) >= 50 else "-"
            ma200 = round(data['Close'].rolling(window=200).mean().iloc[-1], 2) if len(data) >= 200 else "-"

            pivot = (high + low + last_close) / 3
            r1 = 2 * pivot - low
            s1 = 2 * pivot - high

            entry_low = round(pivot * 0.98, 2)
            entry_high = round(pivot * 1.02, 2)
            target_low = round(r1, 2)
            target_high = round(r1 + (r1 - pivot), 2)
            stop_loss = round(s1, 2)

            st.subheader("\U0001F4CB Final Trade Plan")
            st.write(f"**Entry Range:** ₹{entry_low} - ₹{entry_high}")
            st.write(f"**Target Range:** ₹{target_low} - ₹{target_high}")
            st.write(f"**Stop Loss:** ₹{stop_loss}")
            st.metric("Current RSI", current_rsi)
            st.metric("20-Day MA", ma20)
            st.metric("50-Day MA", ma50)
            st.metric("200-Day MA", ma200)

            with st.expander("\U0001F4C8 Fibonacci Retracement Levels"):
                for level, val in fib_values.items():
                    st.write(f"{level}: ₹{val}")

            st.subheader("\U0001F4C9 Interactive Stock Chart")
            fig = go.Figure()
            fig.add_trace(go.Candlestick(
                x=data.index,
                open=data['Open'],
                high=data['High'],
                low=data['Low'],
                close=data['Close'],
                name='Candlesticks'))

            if isinstance(ma20, (int, float)):
                fig.add_trace(go.Scatter(x=data.index, y=data['Close'].rolling(window=20).mean(),
                                         mode='lines', name='MA20', line=dict(color='blue')))
            if isinstance(ma50, (int, float)):
                fig.add_trace(go.Scatter(x=data.index, y=data['Close'].rolling(window=50).mean(),
                                         mode='lines', name='MA50', line=dict(color='orange')))
            if isinstance(ma200, (int, float)):
                fig.add_trace(go.Scatter(x=data.index, y=data['Close'].rolling(window=200).mean(),
                                         mode='lines', name='MA200', line=dict(color='green')))

            for level_val in fib_values.values():
                fig.add_shape(type="line", x0=data.index[0], x1=data.index[-1], y0=level_val, y1=level_val,
                              line=dict(color="purple", dash="dot"), opacity=0.5)

            fig.update_layout(xaxis_rangeslider_visible=False, template="plotly_dark", height=600)
            st.plotly_chart(fig, use_container_width=True)

        else:
            st.error("Stock is NOT fundamentally strong. No technical analysis performed.")

    except Exception as e:
        st.error(f"Unexpected Error: {str(e)}")
        with st.expander("\U0001F50D Error Details"):
            st.code(traceback.format_exc())
