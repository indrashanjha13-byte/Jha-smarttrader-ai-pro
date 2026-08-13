import json
import os


FILE_NAME = "ai_learning.json"


def load_learning():

    if os.path.exists(FILE_NAME):
        with open(FILE_NAME, "r") as f:
            return json.load(f)

    return {
        "wins": 0,
        "losses": 0,
        "strategies": {},
        "markets": {}
    }


def save_learning(data):

    with open(FILE_NAME, "w") as f:
        json.dump(data, f, indent=4)


def update_learning(strategy, market, result):

    result = result.upper()

    if result not in ["WIN", "LOSS"]:
        return

    data = load_learning()

    # Overall Result
    if result == "WIN":
        data["wins"] += 1
    else:
        data["losses"] += 1

    # Strategy Learning
    if strategy not in data["strategies"]:
        data["strategies"][strategy] = {
            "wins": 0,
            "losses": 0
        }

    if result == "WIN":
        data["strategies"][strategy]["wins"] += 1
    else:
        data["strategies"][strategy]["losses"] += 1

    # Market Learning
    if market not in data["markets"]:
        data["markets"][market] = {
            "wins": 0,
            "losses": 0
        }

    if result == "WIN":
        data["markets"][market]["wins"] += 1
    else:
        data["markets"][market]["losses"] += 1

    save_learning(data)


def best_strategy():

    learning = load_learning()

    strategies = learning.get("strategies", {})

    if not strategies:
        return "No Data"

    best = None
    best_acc = 0

    for strategy, info in strategies.items():

        wins = info.get("wins", 0)
        losses = info.get("losses", 0)

        total = wins + losses

        if total == 0:
            continue

        accuracy = (wins / total) * 100

        if accuracy > best_acc:
            best_acc = accuracy
            best = strategy

    if best is None:
        return "No Data"

    return best, round(best_acc, 1)


def auto_strategy():

    best = best_strategy()

    if best == "No Data":
        return "AI Combo"

    strategy, accuracy = best

    if accuracy >= 70:
        return strategy

    return "AI Combo"

if __name__ == "__main__":
    
    print("Best Strategy:", best_strategy())
    print("Auto Strategy:", auto_strategy())