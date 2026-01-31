import pandas as pd
import ta
import config

# --------------------- TECHNICAL INDICATOR SCRIPT ---------------------

# Calculate and append technical indicators to CSV file
def calculate_indicators(df=None, modify=True, data_file=config.CSV_FILE):
    if df is None:
        df=pd.read_csv(data_file, index_col=0)

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
    df['adx_slope'] = (df['adx'] - df['adx'].shift(1)) / 60

    bb_indicator = ta.volatility.BollingerBands(close=df['close'], window=20, window_dev=2)
    df['bb_middle'] = bb_indicator.bollinger_mavg()
    df['bb_upper'] = bb_indicator.bollinger_hband()
    df['bb_lower'] = bb_indicator.bollinger_lband()

    df = df.dropna(
        subset=['rsi','stoch_rsi_k','stoch_rsi_d','macd','macd_signal','adx','+di','-di','adx_slope', 'bb_middle', 'bb_upper', 'bb_lower']
    ).reset_index(drop=True)

    if modify:
        df.to_csv(data_file)
    else:
        return df

# --------------------- TECHNICAL ANALYSIS SCRIPT --------------------

# INDICATOR FUNCTIONS RETURN DataFrame OF BOOLEAN VALUES

def macd_crossup(df, threshold=None) -> pd.Series:
    prev_macd = df['macd'].shift(1)
    prev_macd_signal = df['macd_signal'].shift(1)
    curr_macd = df['macd']
    curr_macd_signal = df['macd_signal']

    # macd first below the signal then crosses above
    return ((prev_macd <= prev_macd_signal) & (curr_macd > curr_macd_signal))

def macd_crossdown(df, threshold=None) -> pd.Series:
    prev_macd = df['macd'].shift(1)
    prev_macd_signal = df['macd_signal'].shift(1)
    curr_macd = df['macd']
    curr_macd_signal = df['macd_signal']

    # macd first above the signal then crosses below
    return ((prev_macd >= prev_macd_signal) & (curr_macd < curr_macd_signal))

def rsi_overbought(df, threshold=70) -> pd.Series:
    prev_rsi = df['rsi'].shift(1)
    curr_rsi = df['rsi']

    # rsi first below the threshold then crosses above
    return ((prev_rsi <= threshold) & (curr_rsi > threshold))

def rsi_oversold(df, threshold=30) -> pd.Series:
    prev_rsi = df['rsi'].shift(1)
    curr_rsi = df['rsi']

    # rsi first above the threshold then crosses below
    return ((prev_rsi >= threshold) & (curr_rsi < threshold))

def stoch_rsi_crossup(df, threshold=None) -> pd.Series:
    prev_stoch_rsi_k = df['stoch_rsi_k'].shift(1)
    prev_stoch_rsi_d = df['stoch_rsi_d'].shift(1)
    curr_stoch_rsi_k = df['stoch_rsi_k']
    curr_stoch_rsi_d = df['stoch_rsi_d']

    # stochrsi_k first below stochrsi_d then crosses above
    return ((prev_stoch_rsi_k <= prev_stoch_rsi_d) & (curr_stoch_rsi_k > curr_stoch_rsi_d))

def stoch_rsi_crossdown(df, threshold=None) -> pd.Series:
    prev_stoch_rsi_k = df['stoch_rsi_k'].shift(1)
    prev_stoch_rsi_d = df['stoch_rsi_d'].shift(1)
    curr_stoch_rsi_k = df['stoch_rsi_k']
    curr_stoch_rsi_d = df['stoch_rsi_d']

    # stochrsi_k first above stochrsi_d then crosses below
    return ((prev_stoch_rsi_k >= prev_stoch_rsi_d) & (curr_stoch_rsi_k < curr_stoch_rsi_d))

def stoch_rsi_overbought(df, threshold=80) -> pd.Series:
    # stochrsi_k above threshold
    return (df['stoch_rsi_k'] >= threshold)

def stoch_rsi_oversold(df, threshold=20) -> pd.Series:
    # stochrsi_k below threshold
    return (df['stoch_rsi_k'] <= threshold)

def adx_trending(df, threshold=20) -> pd.Series:
    # adx must be above threshold and increasing
    return ((df['adx'] >= threshold) & (df['adx_slope'] > 0))

def adx_reversal(df, threshold=None) -> pd.Series:
    prev_adx_slope = df['adx_slope'].shift(1)
    curr_adx_slope = df['adx_slope']

    # adx must have been increasing and then starts decreasing
    return ((prev_adx_slope >= 0) & (curr_adx_slope < 0))

def bollinger_bands_buy(df, threshold=None) -> pd.Series:
    # price touches lower band, buy signal
    return (df['close'] <= df['bb_lower'])

def bollinger_bands_sell(df, threshold=None) -> pd.Series:
    # price touches upper band, sell signal
    return (df['close'] >= df['bb_upper'])


# Variable to be imported to logging.py for indicator name lookup
INDICATOR_REGISTRY = {
    "macd_crossup": macd_crossup,
    "macd_crossdown": macd_crossdown,
    "rsi_overbought": rsi_overbought,
    "rsi_oversold": rsi_oversold,
    "stoch_rsi_crossup": stoch_rsi_crossup,
    "stoch_rsi_crossdown": stoch_rsi_crossdown,
    "stoch_rsi_overbought": stoch_rsi_overbought,
    "stoch_rsi_oversold": stoch_rsi_oversold,
    "adx_trending": adx_trending,
    "adx_reversal": adx_reversal,
    "bollinger_bands_buy": bollinger_bands_buy,
    "bollinger_bands_sell": bollinger_bands_sell
}