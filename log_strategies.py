from dataclasses import dataclass
from analysis import INDICATOR_REGISTRY
from eval_strategy import evaluate_strategy_sharpe
import json
import os

JSON_FILE = "strategies.json"

@dataclass
class Trade:
    timestamp: int
    action: str
    price: float
    coins: float
    total_value: float
    balance_after: float
    position_after: float
    cumulative_gain: float

trades_log: list[Trade] = []

def log_trade(timestamp: int, action: str, price: float, coins: float, total_value: float, balance_after: float, position_after: float, cumulative_gain: float):
    trade = Trade(
        timestamp=timestamp,
        action=action,
        price=price,
        coins=coins,
        total_value=total_value,
        balance_after=balance_after,
        position_after=position_after,
        cumulative_gain=cumulative_gain
    )
    trades_log.append(trade)

def tree_to_json(node):
    if isinstance(node, tuple) and isinstance(node[0], str) and node[0] in ['AND', 'OR']:
        op = node[0]
        children = node[1:]
        return {
            "type": "op",
            "op": op,
            "children": [tree_to_json(child) for child in children]
        }
    
    func, param = node
    indicator_name= getattr(func, '__name__', str(func))
    return {
        "type": "indicator",
        "name": indicator_name,
        "param": param
    }

def json_to_tree(node):
    if node["type"] == "op":
        op = node["op"]
        children = [json_to_tree(child) for child in node["children"]]
        return (op, *children)

    func = INDICATOR_REGISTRY.get(node["name"])
    param = node["param"]
    return (func, param)

def strategy_to_json(strategy, fitness, avg_sharpe, avg_return, max_drawdown, trades, currencies):
    return {
        "fitness": fitness,
        "avg_sharpe": avg_sharpe,
        "avg_return": avg_return,
        "max_drawdown": max_drawdown,
        "trades": trades,
        "currencies": currencies,
        "strategy": {
            "buy_tree": tree_to_json(strategy["buy_tree"]),
            "sell_tree": tree_to_json(strategy["sell_tree"]),
            "buy_proportion": strategy["buy_proportion"],
            "sell_proportion": strategy["sell_proportion"]
        }
    }

def json_to_strategy(data):
    strategy = data["strategy"]

    return {
        "buy_tree": json_to_tree(strategy["buy_tree"]),
        "sell_tree": json_to_tree(strategy["sell_tree"]),
        "buy_proportion": strategy["buy_proportion"],
        "sell_proportion": strategy["sell_proportion"]
    }

# Sort strategies in JSON file by fitness in descending order; overwrite file with sorted strategies
def sort_strategies_by_fitness(path=JSON_FILE):

    # If file does not exist, create an empty one
    if not os.path.exists(path):
        print("No strategies file found. Creating an empty one.")
        with open(path, "w") as f:
            json.dump([], f)
        return []
    
    # Load strategies from file
    with open(path, "r") as f:
        strategies_json = json.load(f)

    # if no strategies, return empty list
    if strategies_json == []:
        print("No strategies found in the file.")
        return []
    
    # Sort and rewrite file
    sorted_strategies = sorted(strategies_json, key=lambda x: x["fitness"], reverse=True)
    if len(sorted_strategies) > 100:
        sorted_strategies = sorted_strategies[:100]  # keep only top 100 strategies

    with open(path, "w") as f:
        json.dump(sorted_strategies, f, indent=4)

    return sorted_strategies

# Save a strategy to the JSON file and sort by fitness
def save_strategy(strategy, fitness, avg_sharpe, avg_return, max_drawdown, trades, currencies, path=JSON_FILE):

    strategy_json = strategy_to_json(strategy, fitness, avg_sharpe, avg_return, max_drawdown, trades, currencies)

    # Load existing strategies
    if os.path.exists(path):
        try:
            with open(path, "r") as f:
                strategies_json = json.load(f)
        except json.JSONDecodeError:
            strategies_json = []
    else:
        strategies_json = []

    # Append new strategy
    if strategy_json not in strategies_json:
        strategies_json.append(strategy_json)

        # Save updated strategies
        with open(path, "w") as f:
            json.dump(strategies_json, f, indent=4)

        sort_strategies_by_fitness(path)
    else:
        print("Strategy already exists in the file. Not saving.")

def load_strategies(path=JSON_FILE):
    if not os.path.exists(path):
        print("No strategies file found.")
        return []
    
    with open(path, "r") as f:
        strategies_json = json.load(f)

    strategies = [json_to_strategy(s) for s in strategies_json]
    return strategies