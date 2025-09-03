import pandas as pd
import ta

# --------------------- TECHNICAL INDICATOR SCRIPT ---------------------

CSV_FILE = 'data/xrp_usd_1h.csv'

# Calculate and append technical indicators to CSV file
def calculate_indicators(df=None, modify=True):
    if df is None:
        df=pd.read_csv(CSV_FILE, index_col=0)

    for col in ['close', 'high', 'low']:
        df[col] = pd.to_numeric(df[col], errors='coerce')

    df['rsi'] = ta.momentum.rsi(df['close'], window=14)

    stochrsi = ta.momentum.StochRSIIndicator(
        close=df['close'], 
        window=14,       
        smooth1=3,       
        smooth2=3        
    )
    df['stoch_rsi_k'] = stochrsi.stochrsi_k() * 100       
    df['stoch_rsi_d'] = stochrsi.stochrsi_d() * 100    

    macd = ta.trend.MACD(df['close'], window_slow=26, window_fast=12, window_sign=9)
    df['macd'] = macd.macd()
    df['macd_signal'] = macd.macd_signal()

    df['adx'] = ta.trend.adx(df['high'], df['low'], df['close'], window=14)
    df['+di'] = ta.trend.adx_pos(df['high'], df['low'], df['close'], window=14)
    df['-di'] = ta.trend.adx_neg(df['high'], df['low'], df['close'], window=14)

    if modify:
        df.to_csv(CSV_FILE)
    else:
        return df

