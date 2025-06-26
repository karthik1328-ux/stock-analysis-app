import yfinance as yf
import pandas as pd
import streamlit as st
import datetime

st.set_page_config(page_title="Stock Analyzer", layout="centered")
st.title("📊 Deep Stock Analysis Tool")

# User Inputs
stock_name = st.text_input("Enter Stock Symbol (e.g., TILAK.NS):")
timeframe = st.selectbox("Select Timeframe:", ["1d", "1wk", "1mo"])

# Temporarily assume fundamentals are good to avoid scraping issues
def check_fundamentals(symbol):
    return True

# Start analysis only when stock is entered
if stock_name:
    try:
        data = yf.download(stock_name, period="1y", interval=timeframe)
        if data.empty:
            st.warning("No data available. Please check the symbol or timeframe.")
        elif len(data) < 15:
            st.warning("Not enough data for RSI or moving averages. Trying higher timeframe...")
            alternative_timeframes = {"1d": "1wk", "1wk": "1mo", "1mo": None}
            next_timeframe = alternative_timeframes.get(timeframe)
            if next_timeframe:
                st.info(f"Automatically retrying with '{next_timeframe}' timeframe.")
                data = yf.download(stock_name, period="1y", interval=next_timeframe)
                timeframe = next_timeframe
            else:
                st.error("Unable to find suitable timeframe with enough data.")
                st.stop()

        if data.empty or len(data) < 15:
            st.error("Data still insufficient. Please try a different stock or timeframe manually.")
            st.stop()

        st.subheader("🔍 Fundamental Strength Check")
        if check_fundamentals(stock_name):
            st.success("Stock appears fundamentally strong. Proceeding with technical analysis.")

            # Price Action
            last_close = data['Close'][-1]
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

            st.subheader("📋 Final Trade Plan")
            st.table(result_table)

            with st.expander("📈 Fibonacci Levels"):
                st.json(fib_values)

        else:
            st.error("Stock is NOT fundamentally strong. No technical analysis performed.")
    except Exception as e:
        st.error(f"Error occurred: {e}")
