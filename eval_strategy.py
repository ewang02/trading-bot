import pandas as pd
import numpy as np
import config

# --------------------- GP STRATEGY SCRIPT ---------------------

# Evaluates a strategy tree recursively and returns a pd.Series of boolean values for each candle
def eval_tree(node, df) -> pd.Series:
    
    '''
    Determines if a trading signal should be triggered by returning a pd.Series of boolean values
    for each candle in the DataFrame based on the provided strategy tree.
    '''

    # If node is a logical operator (check if string is the first element of a tuple of length > 0)
    if isinstance(node, tuple) and len(node) > 0 and isinstance(node[0], str):
        op = node[0]
        if op == 'AND':
            # Evaluate both subtrees and return logical AND
            return eval_tree(node[1], df) & eval_tree(node[2], df)
        elif op == 'OR':
            # Evaluate both subtrees and return logical OR
            return eval_tree(node[1], df) | eval_tree(node[2], df)

    # Otherwise, node is an indicator function (leaf node)
    func, threshold = node

    try:
        # Returns a pd.Series of boolean values for each candle
        return func(df, threshold)
    except Exception as e:
        print(f"Error evaluating {func.__name__} with threshold {threshold}: {e}")
        return False

# Calculates fitness score as an average percent return of any given strategy passed in as a dictionary
def evaluate_strategy(
        cached_data, 
        strategy, 
        currencies=config.TEST_CURRENCIES, 
        balance=config.BALANCE, 
        position=config.POSITION, 
        fee=config.TAKER_FEE
    ) -> float:

    # Get strategy parameters
    buy_tree = strategy['buy_tree']
    sell_tree = strategy['sell_tree']
    buy_prop = float(strategy['buy_proportion'])
    sell_prop = float(strategy['sell_proportion'])

    # Results
    percent_returns = []

    # evaluate each strategy on a list of currencies
    for currency in currencies:

        # initial balance and position
        current_balance = balance
        current_position = position

        # Price data for each currency and drops the first CANDLE_CUTOFF rows
        df = cached_data[currency]

        # pd.Series of when to buy/sell
        buy_signal = eval_tree(buy_tree, df)
        sell_signal = eval_tree(sell_tree, df)

        # convert to numpy arrays for speed
        closes = df['close'].values
        buy_signal_arr = buy_signal.values
        sell_signal_arr = sell_signal.values

        for i in range(len(buy_signal_arr)):
            price = closes[i]

            if buy_signal_arr[i] and current_balance > 0:
                cost = current_balance * buy_prop
                coins = (cost / price) * (1 - fee)
                current_position += coins
                current_balance -= cost
            elif sell_signal_arr[i] and current_position > 0:
                revenue = (current_position * price) * sell_prop * (1 - fee)
                current_balance += revenue
                current_position *= (1 - sell_prop)

        percent_return = (((current_balance + (current_position * float(closes[-1]))) - balance) / balance) * 100
        percent_returns.append(percent_return)

        if len(percent_returns) >= 2:
            running_avg = sum(percent_returns) / len(percent_returns)
            if running_avg < -30:
                return sum(percent_returns) / len(percent_returns)

    return sum(percent_returns) / len(percent_returns)


# Calculates fitness score of any given strategy passed in as a dictionary
def evaluate_strategy_sharpe(
        cached_data,
        strategy, 
        currencies=config.TEST_CURRENCIES, 
        balance=config.BALANCE, 
        position=config.POSITION, 
        fee=config.TAKER_FEE,
        risk_free_annual=config.RISK_FREE_ANNUAL,
        periods_per_year=config.PERIODS_PER_YEAR
    ) -> dict:

    """
    Evaluate a strategy using annualized Sharpe ratio as fitness.
    Higher is better.
    """

    # Get strategy parameters
    buy_tree = strategy['buy_tree']
    sell_tree = strategy['sell_tree']
    buy_prop = float(strategy['buy_proportion'])
    sell_prop = float(strategy['sell_proportion'])

    results = {
        "avg_sharpe": 0.0,
        "max_drawdown": 0.0,
        "avg_percent_return": 0.0,
        "avg_num_trades": 0
    }

    # use Python lists instead of np.array + np.append
    sharpe_ratios = []
    max_drawdowns = []
    percent_returns = []
    num_trades_list = []

    # evaluate each strategy on a list of currencies
    for currency in currencies:

        # all_returns as a list
        all_returns = []

        # initial balance and position
        current_balance = balance
        current_position = position

        # Price data for each currency and drops the first CANDLE_CUTOFF rows
        df = cached_data[currency]

        # pd.Series of when to buy/sell
        buy_signal = eval_tree(buy_tree, df)
        sell_signal = eval_tree(sell_tree, df)

        num_trades = buy_signal.sum() + sell_signal.sum()

        # convert to numpy arrays for speed
        closes = df['close'].values
        buy_signal_arr = buy_signal.values
        sell_signal_arr = sell_signal.values

        prev_equity = None
        # equity_arr as a list
        equity_arr = []

        for i in range(len(buy_signal_arr)):
            price = closes[i]

            if buy_signal_arr[i] and current_balance > 0:
                cost = current_balance * buy_prop
                coins = (cost / price) * (1 - fee)
                current_position += coins
                current_balance -= cost
            elif sell_signal_arr[i] and current_position > 0:
                revenue = (current_position * price) * sell_prop * (1 - fee)
                current_balance += revenue
                current_position *= (1 - sell_prop)

            equity = current_balance + (current_position * price)
            equity_arr.append(equity)
            if prev_equity is not None and prev_equity > 0:
                rt = (equity - prev_equity) / prev_equity
                all_returns.append(rt)

            prev_equity = equity

        # Penalize too few trades
        if num_trades < 15:
            return {
                    "avg_sharpe": -1e6,
                    "max_drawdown": -1e6,
                    "avg_percent_return": -1e6,
                    "avg_num_trades": -1e6
                }

        # convert equity_arr to numpy array for vector math
        equity_arr = np.array(equity_arr)
        drawdowns = (equity_arr / np.maximum.accumulate(equity_arr) - 1) * 100
        max_drawdown = drawdowns.min()

        percent_return = (((current_balance + (current_position * float(closes[-1]))) - balance) / balance) * 100

        # Penalize negative returns
        if percent_return < 0:
            return {
                    "avg_sharpe": -1e6,
                    "max_drawdown": -1e6,
                    "avg_percent_return": -1e6,
                    "avg_num_trades": -1e6
                }
        
        # Penalize excessive drawdown
        if max_drawdown < -50.0:
            return {
                    "avg_sharpe": -1e6,
                    "max_drawdown": -1e6,
                    "avg_percent_return": -1e6,
                    "avg_num_trades": -1e6
                }

        # convert all_returns to numpy array for math
        all_returns = np.array(all_returns)

        rf_per_period = risk_free_annual / periods_per_year
        excess_returns = all_returns - rf_per_period

        mean_rt = np.mean(excess_returns)
        std_rt = np.std(excess_returns, ddof=1)

        # Penalize zero standard deviation
        if std_rt == 0:
            return {
                    "avg_sharpe": -1e6,
                    "max_drawdown": -1e6,
                    "avg_percent_return": -1e6,
                    "avg_num_trades": -1e6
                }
        
        sharpe_per_period = mean_rt / std_rt
        sharpe_annualized = sharpe_per_period * np.sqrt(periods_per_year)

        sharpe_ratios.append(sharpe_annualized)
        max_drawdowns.append(max_drawdown)
        percent_returns.append(percent_return)
        num_trades_list.append(num_trades)

    results["avg_sharpe"] = np.mean(sharpe_ratios)
    results["max_drawdown"] = np.min(max_drawdowns)
    results["avg_percent_return"] = np.mean(percent_returns)
    results["avg_num_trades"] = np.mean(num_trades_list)
    
    # Penalize low average percent return
    if results['avg_percent_return'] < 15:
        return {
            "avg_sharpe": -1e6,
            "max_drawdown": -1e6,
            "avg_percent_return": -1e6,
            "avg_num_trades": -1e6
        }

    return results