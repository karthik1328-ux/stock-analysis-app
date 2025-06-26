import yfinance as yf
import pandas as pd
import streamlit as st
import datetime
import traceback
import plotly.graph_objs as go
import requests

st.set_page_config(page_title="Stock Analyzer", layout="wide")
st.title("\U0001F4CA Deep Stock Analysis Tool")

# Function to suggest correct stock symbols
def suggest_symbols(query):
    try:
        response = requests.get(f"https://query2.finance.yahoo.com/v1/finance/search?q={query}")
        if response.status_code == 200:
            results = response.json().get("quotes", [])
            suggestions = [f"{item['symbol']} ({item.get('shortname', '')})" for item in results[:5]]
            return suggestions
        return []
    except:
        return []

# User Inputs
stock_name = st.text_input("Enter Stock Symbol (e.g., TILAK.NS):")
timeframe = st.selectbox("Select Timeframe:", ["1d", "1wk", "1mo"])

# Deep fundamental analysis using key ratios
def check_fundamentals(symbol):
    try:
        ticker = yf.Ticker(symbol)
        info = ticker.info

        # Extract relevant metrics
        pe = info.get("trailingPE")
        pb = info.get("priceToBook")
        roe = info.get("returnOnEquity")
        debt_eq = info.get("debtToEquity")
        current_ratio = info.get("currentRatio")

        score = 0
        if pe and 5 < pe < 35: score += 1
        if pb and 0 < pb < 10: score += 1
        if roe and roe > 0.10: score += 1
        if debt_eq and debt_eq < 1.5: score += 1
        if current_ratio and current_ratio > 1: score += 1

        return score >= 4  # Require at least 4 metrics to be healthy

    except:
        return False

# Start analysis only when stock is entered
if stock_name:
    try:
        with st.spinner("Fetching stock data... Please wait."):
            data = yf.download(stock_name, period="1y", interval=timeframe, progress=False, threads=False).dropna()

        if data is None or data.empty or 'Close' not in data.columns:
            st.warning("⚠️ No data found. Checking for close matches...")
            suggestions = suggest_symbols(stock_name)
            if suggestions:
                st.info("Did you mean one of these?")
                for s in suggestions:
                    st.markdown(f"- **{s}**")
                st.stop()
            else:
                st.error("❌ Could not find any matching stock symbols. Please double-check the symbol.")
                st.stop()

        if len(data) < 15:
            st.warning("Not enough data for RSI or moving averages. Trying higher timeframe...")
            alternative_timeframes = {"1d": "1wk", "1wk": "1mo", "1mo": None}
            next_timeframe = alternative_timeframes.get(timeframe)
            if next_timeframe:
                st.info(f"Automatically retrying with '{next_timeframe}' timeframe.")
                data = yf.download(stock_name, period="1y", interval=next_timeframe, progress=False, threads=False).dropna()
                timeframe = next_timeframe
                if data is None or data.empty or 'Close' not in data.columns:
                    raise ValueError("Failed to fetch data. Even retry failed.")
            else:
                st.error("Unable to find suitable timeframe with enough data.")
                st.stop()

        st.subheader("\U0001F50D Fundamental Strength Check")
        if check_fundamentals(stock_name):
            st.success("Stock appears fundamentally strong. Proceeding with technical analysis.")

            # Price Action
            last_close = float(data['Close'].dropna().iloc[-1])
            high = float(data['High'].max())
            low = float(data['Low'].min())

            # Fibonacci Levels
            fib_levels = [0.236, 0.382, 0.5, 0.618, 0.786]
            fib_values = {f"{int(level*100)}%": round(high - (high - low) * level, 2) for level in fib_levels}

            # RSI
            delta = data['Close'].diff()
            gain = delta.where(delta > 0, 0)
            loss = -delta.where(delta < 0, 0)
            avg_gain = gain.rolling(window=14).mean()
            avg_loss = loss.rolling(window=14).mean()
            rs = avg_gain / avg_loss
            rsi = 100 - (100 / (1 + rs))
            current_rsi = round(float(rsi.dropna().iloc[-1]), 2)

            # Moving Averages with Safe Checks
            ma20 = round(data['Close'].rolling(window=20).mean().iloc[-1], 2) if len(data) >= 20 else "Insufficient data"
            ma50 = round(data['Close'].rolling(window=50).mean().iloc[-1], 2) if len(data) >= 50 else "Insufficient data"
            ma200 = round(data['Close'].rolling(window=200).mean().iloc[-1], 2) if len(data) >= 200 else "Insufficient data"

            # Pivot Points
            pivot = (high + low + last_close) / 3
            r1 = 2 * pivot - low
            s1 = 2 * pivot - high

            entry_low = round(pivot * 0.98, 2)
            entry_high = round(pivot * 1.02, 2)
            target_low = round(r1, 2)
            target_high = round(r1 + (r1 - pivot), 2)
            stop_loss = round(s1, 2)

            # Display Results
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

            # Interactive Chart
            st.subheader("\U0001F4C9 Interactive Stock Chart")
            fig = go.Figure()
            fig.add_trace(go.Candlestick(
                x=data.index,
                open=data['Open'],
                high=data['High'],
                low=data['Low'],
                close=data['Close'],
                name='Candlesticks'
            ))
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
        err_msg = str(e)
        if '-1' in err_msg:
            st.error("⚠️ Data fetch error: Invalid symbol or Yahoo Finance response. Try changing the timeframe.")
        else:
            st.error(f"Unexpected Error: {err_msg}")
        with st.expander("\U0001F50D Error Details"):
            st.code(traceback.format_exc())
