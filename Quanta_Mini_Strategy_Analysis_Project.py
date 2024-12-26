#!/usr/bin/env python
# coding: utf-8

# In[ ]:


# Import libraries
import requests
import pandas as pd
import numpy as np
import streamlit as st
from datetime import datetime
from pandas.tseries.offsets import BusinessDay

# Alpha Vantage API Key
ALPHA_VANTAGE_API_KEY = "EQOXGHP1BKXT075K"

# Fetch stock data from Alpha Vantage
def fetch_stock_data(symbol, start_date, end_date):
    url = f"https://www.alphavantage.co/query"
    params = {
        "function": "TIME_SERIES_DAILY",
        "symbol": symbol,
        "apikey": ALPHA_VANTAGE_API_KEY,
        "outputsize": "full"
    }
    response = requests.get(url, params=params)
    data = response.json()

    if "Time Series (Daily)" not in data:
        raise ValueError(f"Error fetching data: {data.get('Error Message', 'Unknown error')}")

    daily_data = data["Time Series (Daily)"]
    df = pd.DataFrame.from_dict(daily_data, orient="index")
    df = df.rename(columns={
        "1. open": "Open",
        "2. high": "High",
        "3. low": "Low",
        "4. close": "Close",
        "5. volume": "Volume"
    })
    df = df.apply(pd.to_numeric)
    df.index = pd.to_datetime(df.index)
    df = df.sort_index()

    # Filter data by date range
    return df.loc[start_date:end_date]

# Streamlit Setup
st.title("Quanta Mini Strategy Analysis Project")

# User Inputs
ticker = st.text_input("Ticker:")
start_date = st.date_input("Start Date:", value=datetime(2024, 1, 1))
end_date = st.date_input("End Date:", value=datetime.today())
volume_change_threshold = st.number_input("Volume Change Threshold (%)", value=200.0, step=1.0)
price_change_threshold = st.number_input("Price Change Threshold (%)", value=2.0, step=0.1)
holding_period = st.number_input("Holding Period (Days)", value=10, step=1)

if st.button("Test Strategy"):
    try:
        # Fetch Historical Data
        data = fetch_stock_data(ticker, start_date, end_date)
        if data.empty:
            st.error("No data found for the given ticker and date range.")
        else:
            data["20-Day_Avg_Volume"] = data["Volume"].rolling(window=20).mean()
            data["Price_Change (%)"] = data["Close"].pct_change() * 100
            data["Price_Breakout"] = data["Price_Change (%)"] > price_change_threshold
            data["Volume_Change (%)"] = (data["Volume"]/data["20-Day_Avg_Volume"]) * 100
            data["Volume_Breakout"] = data["Volume_Change (%)"] > volume_change_threshold

            # Identify Breakout Days
            breakout_days = data[data["Volume_Breakout"] & data["Price_Breakout"]]

            results = []
            for date in breakout_days.index:
                buy_price = breakout_days.loc[date, "Close"]
                sell_date = date + BusinessDay(n=holding_period) # Excluding Saturday & Sunday

                if sell_date in data.index:
                    sell_price = data.loc[sell_date, "Close"]
                    return_pct = (sell_price - buy_price) / buy_price * 100
                else:
                    sell_price = np.nan
                    return_pct = np.nan

                results.append({
                    "Buy Date": date,
                    "Volume Change (%)": breakout_days.loc[date, "Volume_Change (%)"],
                    "Price Change (%)": breakout_days.loc[date, "Price_Change (%)"],
                    "Buy Price": buy_price,
                    "Sell Date": sell_date,
                    "Sell Price": sell_price,
                    "Return (%)": return_pct
                })

            results_df = pd.DataFrame(results)

            # Save to CSV
            csv = results_df.to_csv(index=False)
            st.download_button(label="Download CSV",
                                data=csv,
                                file_name=f"{ticker}_strategy_analysis.csv",
                                mime="text/csv")

            # Display Summary Statistics
            st.write("Breakout Days/Total Trades:", breakout_days.shape[0])
            st.write("Average Return (%):", results_df["Return (%)"].mean())
            st.write(results_df)
        
    except Exception as e:
            st.error(f"An error occurred: {e}")

