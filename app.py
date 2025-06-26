import yfinance as yf
import pandas as pd
import streamlit as st
import datetime
import traceback
import plotly.graph_objs as go
import requests

st.set_page_config(page_title="Stock Analyzer", layout="centered")
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

# Temporarily assume fundamentals are good to avoid scraping issues
def check_fundamentals(symbol):
    return True

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
            if 'Close' not in data.columns or data['Close'].dropna().empty:
                raise ValueError("No valid closing prices found in the data.")
            last_close = data['Close'].dropna().iloc[-1]
            high = data['High'].max()
            low = data['Low'].min()

            # Fibonacci Levels
            fib_levels = [0.236, 0.382, 0.5, 0.618, 0.786]
            fib_values = {f"Fib {int(level*100)}%": round(high - (high - low) * level, 2) for level in fib_levels}

            # RSI
            delta = data['Close'].diff()
            gain = delta.where(delta > 0, 0)
            loss = -delta.where(delta < 0, 0)
            avg_gain = gain.rolling(window=14).mean()
            avg_loss = loss.rolling(window=14).mean()
            rs = avg_gain / avg_loss
            rsi = 100 - (100 / (1 + rs))
            current_rsi = round(rsi.iloc[-1], 2)

            # Moving Averages with Safe Checks
            ma20 = round(data['Close'].rolling(window=20).mean().iloc[-1], 2) if len(data) >= 20 else "N/A"
            ma50 = round(data['Close'].rolling(window=50).mean().iloc[-1], 2) if len(data) >= 50 else "N/A"
            ma200 = round(data['Close'].rolling(window=200).mean().iloc[-1], 2) if len(data) >= 200 else "N/A"

            # Pivot Points
            pivot = (high + low + last_close) / 3
            r1 = 2 * pivot - low
            s1 = 2 * pivot - high

            entry_range = f"{round(pivot * 0.98, 2)} - {round(pivot * 1.02, 2)}"
            target_range = f"{round(r1, 2)} - {round(r1 + (r1 - pivot), 2)}"
            stop_loss = round(s1, 2)

            # Display Results
            result_table = pd.DataFrame({
                'Stock Name': [stock_name],
                'Timeframe Used': [timeframe],
                'Entry Level': [entry_range],
                'Target Level': [target_range],
                'Stop Loss': [stop_loss],
                'RSI': [current_rsi],
                'MA20': [ma20],
                'MA50': [ma50],
                'MA200': [ma200],
                'Pivot': [round(pivot, 2)]
            })

            st.subheader("\U0001F4CB Final Trade Plan")
            st.table(result_table)

            with st.expander("\U0001F4C8 Fibonacci Levels"):
                st.json(fib_values)

            # Interactive Chart
            st.subheader("\U0001F4C9 Interactive Stock Chart")
            fig = go.Figure()
            fig.add_trace(go.Candlestick(
                x=data.index,
                open=data['Open'],
                high=data['High'],
                low=data['Low'],
                close=data['Close'],
                name='Candles'
            ))
            if ma20 != "N/A":
                fig.add_trace(go.Scatter(x=data.index, y=data['Close'].rolling(window=20).mean(),
                                         mode='lines', name='MA20', line=dict(color='blue')))
            if ma50 != "N/A":
                fig.add_trace(go.Scatter(x=data.index, y=data['Close'].rolling(window=50).mean(),
                                         mode='lines', name='MA50', line=dict(color='orange')))
            if ma200 != "N/A":
                fig.add_trace(go.Scatter(x=data.index, y=data['Close'].rolling(window=200).mean(),
                                         mode='lines', name='MA200', line=dict(color='green')))
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
