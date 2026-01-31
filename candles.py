import requests
import pandas as pd
import time
import os
import config
from analysis import calculate_indicators

# CONFIG
columns = ['timestamp', 'low', 'high', 'open', 'close', 'volume']

SIX_MONTHS = 15778376  # seconds in six months

# Fetch historical candle data from Coinbase Pro API
def get_candles(start=None, end=None, symbol=config.SYMBOL, granularity=config.GRANULARITY):
    url = f"https://api.exchange.coinbase.com/products/{symbol}/candles"
    params = {
        "granularity": granularity,
        "start": start,
        "end": end
    }
    response = requests.get(url, params=params)
    data = response.json()
    return data

def verify_candles(data_file=config.CSV_FILE):
    df = pd.read_csv(data_file, index_col=0)
    timestamps = df['timestamp']
    time_diffs = timestamps.diff().dropna()
    if time_diffs.nunique() == 1 and time_diffs.iloc[0] == 3600.0:
        print("All candles are present and correctly spaced.")
    else:
        print("Missing or irregular candles detected.")
        print(time_diffs.value_counts())

def update_candles(data_file=config.CSV_FILE, granularity=config.GRANULARITY, symbol=config.SYMBOL):
    current_time = int(time.time())
    if not os.path.exists(data_file):
        start = current_time - SIX_MONTHS * 10  # start 10 six-month periods ago (5 years)
        end = start + 86400*10  # 10 days of candles per request

        found_start = False
        while not found_start:
            
            candles = get_candles(start, end, symbol=symbol, granularity=granularity)

            if candles:
                candles.sort(key=lambda x: x[0])  # sort by timestamp

                # Construct DataFrame and send it to CSV file
                df = pd.DataFrame(candles, columns=columns)
                df['date'] = pd.to_datetime(df['timestamp'], unit='s')
                df.to_csv(data_file)

                found_start = True
                break
            else:
                start += 86400 * 10  # move forward 10 days
                end = start + 86400 * 10

    df = pd.read_csv(data_file, index_col=0)
    last_timestamp = df.iloc[-1]['timestamp']
    while last_timestamp < current_time - granularity:
        start = last_timestamp + 1
        end = min(start + 86400 * 10, current_time)
        new_candles = get_candles(start, end, symbol=symbol, granularity=granularity)
        if not new_candles:
            break
        
        df = pd.concat([df, pd.DataFrame(new_candles, columns=columns)], ignore_index=True)
        df['date'] = pd.to_datetime(df['timestamp'], unit='s')
        df = df.drop_duplicates(subset="timestamp").sort_values("timestamp")
        df.to_csv(data_file)
        last_timestamp = df.iloc[-1]['timestamp']

    calculate_indicators(data_file=data_file)

    verify_candles(data_file=data_file)

def get_main_currencies():
    update_candles(data_file="data/btc_usd_1h.csv", granularity=3600, symbol="BTC-USD")
    update_candles(data_file="data/eth_usd_1h.csv", granularity=3600, symbol="ETH-USD")
    update_candles(data_file="data/ltc_usd_1h.csv", granularity=3600, symbol="LTC-USD")
    update_candles(data_file="data/xrp_usd_1h.csv", granularity=3600, symbol="XRP-USD")
    update_candles(data_file="data/sol_usd_1h.csv", granularity=3600, symbol="SOL-USD")
    update_candles(data_file="data/ada_usd_1h.csv", granularity=3600, symbol="ADA-USD")
    update_candles(data_file="data/doge_usd_1h.csv", granularity=3600, symbol="DOGE-USD")
    update_candles(data_file="data/hbar_usd_1h.csv", granularity=3600, symbol="HBAR-USD")

# Load all candle data into dictionary for faster access
def cache_data(currencies=config.TEST_CURRENCIES, candle_cutoff=config.CANDLE_CUTOFF): 
    cached_data = {}

    # For each currency, if it is not already cached, load its data
    for currency in currencies:
        if currency not in cached_data:
            try:
                df = pd.read_csv(f'data/{currency}_usd_{config.TIMEFRAME}.csv', index_col=0).iloc[candle_cutoff:].reset_index(drop=True)
                cached_data[currency] = df
            except FileNotFoundError:
                print(f"Warning: {currency}_usd_{config.TIMEFRAME}.csv not found")
                continue   

    return cached_data

if __name__ == "__main__":
    get_main_currencies()