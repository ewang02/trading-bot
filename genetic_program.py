from eval_strategy import evaluate_strategy, evaluate_strategy_sharpe
import random
import numpy as np
import multiprocessing as mp
import time
from generate_strategy import random_strategy, crossover, mutate
import config
from functools import partial
from candles import cache_data
from log_strategies import save_strategy    

def genetic_programming(
        cached_data,
        population_size=config.POPULATION_SIZE, 
        generations=config.GENERATIONS, 
        mutation_rate=config.MUTATION_RATE, 
        depth=config.DEPTH
    ) -> dict:

    # List of candidate strategies
    population = [random_strategy(depth=depth) for _ in range(population_size)]

    worker = partial(evaluate_strategy_sharpe, cached_data)

    with mp.Pool(processes=mp.cpu_count()//4) as pool:
        # for each generation/iteration, evaluate each strategy and retain top 50%
        for gen in range(generations):
            results_list = pool.map(worker, population)

            sharpes = np.array([result['avg_sharpe'] for result in results_list])
            returns = np.array([result['avg_percent_return'] for result in results_list]) / 100.0
            drawdowns = np.array([result['max_drawdown'] for result in results_list]) / 100.0 

            fitness_scores = config.SHARPE_WEIGHT * sharpes + config.RETURN_WEIGHT * returns - config.DRAWDOWN_WEIGHT * np.abs(drawdowns)

            population = [s for _, s in sorted(zip(fitness_scores, population), key=lambda x: x[0], reverse=True)]
            sorted_fitness = sorted(fitness_scores, reverse=True)

            cached_data['top_ten_strategies'] = population[:10]
            cached_data['top_ten_fitnesses'] = sorted_fitness[:10]

            print(f"Generation {gen}: Best Fitness = {sorted_fitness[0]}")

            parents = population[:population_size // 2]
            children = []

            elite_count = max(1, int(config.ELITE_FRACTION * population_size))
            elites = population[:elite_count]
            needed_children = population_size - elite_count

            while len(children) < needed_children:
                p1, p2 = random.sample(parents, 2)
                c1, c2 = crossover(p1, p2)
                if random.random() < mutation_rate:
                    mutate(c1)
                if random.random() < mutation_rate:
                    mutate(c2)
                children.extend([c1, c2])

            population = elites + children[:needed_children]

    return cached_data['top_ten_strategies']


if __name__ == '__main__':

    NUM_ITERATIONS = 10

    cached_data = cache_data(currencies=config.TEST_CURRENCIES, candle_cutoff=config.CANDLE_CUTOFF)

    start = time.perf_counter()
    for i in range(NUM_ITERATIONS):
        best_strategies = genetic_programming(cached_data)
        for i in range(len(best_strategies)):
            result = evaluate_strategy_sharpe(cached_data, best_strategies[i])
            save_strategy(cached_data['top_ten_strategies'][i], cached_data['top_ten_fitnesses'][i], result["avg_sharpe"], result["avg_percent_return"], result["max_drawdown"], result["avg_num_trades"], config.TEST_CURRENCIES)

    end = time.perf_counter()

    print("Best Strategy:", cached_data['top_ten_strategies'][0])
    print("Final fitness score after backtest:", cached_data['top_ten_fitnesses'][0])
    print(f"Final percent return after backtest: {evaluate_strategy(cached_data, cached_data['top_ten_strategies'][0])}%")
    print(f"Total time for {config.GENERATIONS * NUM_ITERATIONS} generations with {config.POPULATION_SIZE} population size and {config.DEPTH} depth with {len(config.TEST_CURRENCIES)} currencies: {end - start} seconds")