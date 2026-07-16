import json
import os


MEMORY_FILE = "market_memory.json"


def load_market_memory():

    if os.path.exists(MEMORY_FILE):

        with open(MEMORY_FILE, "r") as f:
            return json.load(f)

    return {
        "Bullish": {},
        "Bearish": {},
        "Sideways": {}
    }



def save_market_memory(data):

    with open(MEMORY_FILE, "w") as f:
        json.dump(data, f, indent=4)



def save_strategy_result(market, strategy, win):

    memory = load_market_memory()


    if strategy not in memory[market]:

        memory[market][strategy] = {
            "wins": 0,
            "losses": 0
        }


    if win:
        memory[market][strategy]["wins"] += 1

    else:
        memory[market][strategy]["losses"] += 1


    save_market_memory(memory)



def best_market_strategy(market):

    memory = load_market_memory()


    if not memory[market]:
        return "AI Combo"


    best = "AI Combo"
    accuracy = 0


    for strategy,data in memory[market].items():

        total = data["wins"] + data["losses"]

        if total > 0:

            winrate = (data["wins"] / total) * 100


            if winrate > accuracy:

                accuracy = winrate
                best = strategy


    return best
