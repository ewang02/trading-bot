import random
import config
from analysis import macd_crossdown, macd_crossup, rsi_overbought, rsi_oversold, stoch_rsi_crossdown, stoch_rsi_crossup, stoch_rsi_overbought, stoch_rsi_oversold, adx_trending, adx_reversal, bollinger_bands_buy, bollinger_bands_sell

BUY_INDICATORS = [
    macd_crossup, 
    rsi_oversold, 
    stoch_rsi_oversold, 
    stoch_rsi_crossup,
    adx_trending, adx_reversal,
    bollinger_bands_buy
]

SELL_INDICATORS = [
    macd_crossdown,
    rsi_overbought,
    stoch_rsi_overbought,
    stoch_rsi_crossdown,
    adx_reversal, adx_trending,
    bollinger_bands_sell
]

# Logical operators
OPERATORS = ['AND', 'OR']

# Returns a random trading indicator based on buy/sell
def random_indicator(action, buy_indicators=BUY_INDICATORS, sell_indicators=SELL_INDICATORS) -> tuple:

    if action == 'buy':
        # Pick random buy indicator
        func = random.choice(buy_indicators)
        threshold = None

        # If the buy indicator has default threshold value that is not None
        if func.__defaults__ is not None:

            # For each default parameter give it a random value
            for d in func.__defaults__:
                if isinstance(d, (int, float)):
                    # Ensure buy indicators trigger on oversold conditions only
                    threshold = random.uniform(config.OVERSOLD_LOWER, config.OVERSOLD_UPPER)

        return (func, threshold)

    elif action == 'sell':
        # Pick random sell indicator
        func = random.choice(sell_indicators)
        threshold = None

        # If the sell indicator has default threshold value that is not None
        if func.__defaults__ is not None:

            # For each default parameter give it a random value
            for d in func.__defaults__:
                if isinstance(d, (int, float)):
                    # Ensure sell indicators trigger on overbought conditions only
                    threshold = random.uniform(config.OVERBOUGHT_LOWER, config.OVERBOUGHT_UPPER)

        return (func, threshold)

    else:
        print("Invalid action for random_indicator")
        return None
    
# Return a random tree of depth n or smaller of buy or sell indicators with logical connectors
def random_tree(action, depth=config.DEPTH, operators=OPERATORS) -> tuple:

    # Indicators as leaves of the tree
    if depth == 0 or (depth in [1, 2] and random.random() < 0.2):
        if action == 'buy':
            return random_indicator('buy')
        elif action == 'sell':
            return random_indicator('sell')
        else:
            print("Invalid action for random_tree")
            return None
    
    # Random AND/OR operator
    op = random.choice(operators)
    return (op, random_tree(action, depth - 1), random_tree(action, depth - 1))

# Generates a random buy tree and sell tree with proportions to combine into one strategy
def random_strategy(depth=config.DEPTH) -> dict:

    # Generate trees
    buy_tree = random_tree('buy', depth)
    sell_tree = random_tree('sell', depth)

    # Random buy and sell proportion
    buy_prop = random.choice(config.BUY_PROPORTION_CHOICES)
    sell_prop = random.choice(config.SELL_PROPORTION_CHOICES)

    return {'buy_tree': buy_tree, 'sell_tree': sell_tree, 'buy_proportion': buy_prop, 'sell_proportion': sell_prop}  

# Add mutation and randomization to find more strategies           
def mutate(strategy):

    # pick random attribute to mutate
    choice = random.choice(['buy_tree', 'sell_tree', 'buy_proportion', 'sell_proportion'])

    # generates a new random buy/sell tree or adjusts buy/sell proportion
    if choice == 'buy_tree':
        strategy['buy_tree'] = random_tree('buy', depth=config.DEPTH)
    elif choice == 'sell_tree':
        strategy['sell_tree'] = random_tree('sell', depth=config.DEPTH)
    else:
        strategy[choice] = random.choice(config.BUY_PROPORTION_CHOICES if 'buy' in choice else config.SELL_PROPORTION_CHOICES)

# Crossover to find more strategies by interchanging parts of two parent strategies
def crossover(strategy1, strategy2) -> tuple:
    new_strategy1 = strategy1.copy()
    new_strategy2 = strategy2.copy()

    # 50% chance to swap buy trees, sell trees, buy propotions, and sell proportions
    if random.random() < 0.5:
        new_strategy1['buy_tree'], new_strategy2['buy_tree'] = strategy2['buy_tree'], strategy1['buy_tree']

    if random.random() < 0.5:
        new_strategy1['sell_tree'], new_strategy2['sell_tree'] = strategy2['sell_tree'], strategy1['sell_tree']

    if random.random() < 0.5:
        new_strategy1['buy_proportion'], new_strategy2['buy_proportion'] = strategy2['buy_proportion'], strategy1['buy_proportion']

    if random.random() < 0.5:
        new_strategy1['sell_proportion'], new_strategy2['sell_proportion'] = strategy2['sell_proportion'], strategy1['sell_proportion']

    return new_strategy1, new_strategy2