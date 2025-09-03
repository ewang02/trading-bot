import requests
import pandas as pd
import time
import os

# CONFIG
SYMBOL = 'XRP-USD'
CSV_FILE = 'data/xrp_usd_1h.csv'
GRANULARITY = 3600  # 1 hour in seconds
columns = ['timestamp', 'low', 'high', 'open', 'close', 'volume']

# Fetch historical candle data from Coinbase Pro API
def get_candles(start=None, end=None):
    url = f"https://api.exchange.coinbase.com/products/{SYMBOL}/candles"
    params = {
        "granularity": GRANULARITY,
        "start": start,
        "end": end
    }
    response = requests.get(url, params=params)
    data = response.json()
    return data

def update_candles():
    current_time = int(time.time())
    if not os.path.exists(CSV_FILE):
        start = current_time - 15778376 # 6 months ago
        end = start + 86400*10  # 10 days of candles per request

        candles = get_candles(start, end)

        candles.sort(key=lambda x: x[0])  # sort by timestamp

        # Construct DataFrame and send it to CSV file
        df = pd.DataFrame(candles, columns=columns)
        df['date'] = pd.to_datetime(df['timestamp'], unit='s')
        df.to_csv(CSV_FILE)

    df = pd.read_csv(CSV_FILE, index_col=0)
    last_timestamp = df.iloc[-1]['timestamp']
    while last_timestamp < current_time - GRANULARITY:
        start = last_timestamp + 1
        end = min(start + 86400 * 10, current_time)
        new_candles = get_candles(start, end)
        if not new_candles:
            break
        
        df = pd.concat([df, pd.DataFrame(new_candles, columns=columns)], ignore_index=True)
        df['date'] = pd.to_datetime(df['timestamp'], unit='s')
        df = df.drop_duplicates(subset="timestamp").sort_values("timestamp")
        df.to_csv(CSV_FILE)
        last_timestamp = df.iloc[-1]['timestamp']

def verify_candles():
    df = pd.read_csv(CSV_FILE, index_col=0)
    timestamps = df['timestamp']
    time_diffs = timestamps.diff().dropna()
    if time_diffs.nunique() == 1 and time_diffs.iloc[0] == 3600.0:
        print("All candles are present and correctly spaced.")
    else:
        print("Missing or irregular candles detected.")
        print(time_diffs.value_counts())