import pandas as pd
import time
from analysis import calculate_indicators
from candles import get_main_currencies, update_candles
from websocket import create_connection
import json
from datetime import datetime
import config

get_main_currencies()

# --------------------- WEBSOCKET SCRIPT ---------------------

ws = create_connection("wss://ws-feed.exchange.coinbase.com")
ws.send(
    json.dumps(
        {
            "type": "subscribe",
            "product_ids": [config.SYMBOL],
            "channels": ["ticker"],
        }
    )
)

print("Connected:", ws.connected)

live_candle = {
    'timestamp': None,
    'low': 0,
    'high': 0,
    'open': 0,
    'close': 0
}

# Main loop for live candle
while True:
    try:
        data = json.loads(ws.recv())
        if data.get("type") == "ticker" and "price" in data:
            price = float(data["price"])
        else:
            continue
        
        now = datetime.now()

        # Floor timestamp to nearest 60-minute boundary
        candle_start = now.replace(minute=(now.minute // 60) * 60, second=0, microsecond=0)

        # If new candle interval, reset live candle
        if live_candle['timestamp'] != candle_start:
            live_candle = {
                'timestamp': candle_start,
                'low': price,
                'high': price,
                'open': price,
                'close': price
            }
        else:
            live_candle['high'] = max(live_candle['high'], price)
            live_candle['low'] = min(live_candle['low'], price)
            live_candle['close'] = price

        df = pd.read_csv(config.CSV_FILE, index_col=0)
        s = pd.Series(live_candle)
        df = pd.concat([df, s.to_frame().T], ignore_index=True)
     
        indicator_df = calculate_indicators(df=df, modify=False)
        live_candle['rsi'] = indicator_df['rsi'].iloc[-1].item()
        live_candle['stoch_rsi_k'] = indicator_df['stoch_rsi_k'].iloc[-1].item()
        live_candle['stoch_rsi_d'] = indicator_df['stoch_rsi_d'].iloc[-1].item()
        live_candle['macd'] = indicator_df['macd'].iloc[-1].item()
        live_candle['macd_signal'] = indicator_df['macd_signal'].iloc[-1].item()
        live_candle['adx'] = indicator_df['adx'].iloc[-1].item()
        live_candle['+di'] = indicator_df['+di'].iloc[-1].item()
        live_candle['-di'] = indicator_df['-di'].iloc[-1].item()
        live_candle['adx_slope'] = indicator_df['adx_slope'].iloc[-1].item()

        print(live_candle)

        update_candles(data_file=config.CSV_FILE, granularity=config.GRANULARITY, symbol=config.SYMBOL)
        time.sleep(3)
    except Exception as e:
        print("Error:", e)
        print("Reconnecting...")

        ws = create_connection("wss://ws-feed.exchange.coinbase.com")
        ws.send(
            json.dumps(
                {
                    "type": "subscribe",
                    "product_ids": [config.SYMBOL],
                    "channels": ["ticker"],
                }
            )
        )

        print("Connected:", ws.connected)
        time.sleep(5)
        continue

