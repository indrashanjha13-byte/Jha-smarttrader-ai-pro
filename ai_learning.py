from datetime import datetime
import logging
import json
import os

FILE_NAME = "ai_learning.json"


def load_learning():
    """Safely loads AI learning data with fallback structure."""
    if os.path.exists(FILE_NAME):
        try:
            with open(FILE_NAME, "r", encoding="utf-8") as f:
                data = json.load(f)
                # Ensure baseline keys exist
                data.setdefault("wins", 0)
                data.setdefault("losses", 0)
                data.setdefault("strategies", {})
                data.setdefault("markets", {})
                return data
        except Exception as e:
            logging.error(f"⚠️ Error reading {FILE_NAME}: {e}. Initializing fresh dataset.")

    return {
        "wins": 0,
        "losses": 0,
        "strategies": {},
        "markets": {}
    }


def save_learning(data):
    """Atomic file save to prevent JSON corruption."""
    temp_file = f"{FILE_NAME}.tmp"
    try:
        with open(temp_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4)
        os.replace(temp_file, FILE_NAME)  # Atomic replace operation
    except Exception as e:
        logging.error(f"❌ Failed to save learning data: {e}")
        if os.path.exists(temp_file):
            os.remove(temp_file)


def update_learning(strategy, market, result):
    """Updates win/loss counts safely for strategies and markets."""
    result = str(result).upper()
    if result not in ["WIN", "LOSS"]:
        return

    strategy = str(strategy) if strategy else "AI Combo"
    market = str(market).upper() if market else "NIFTY"

    data = load_learning()
    is_win = (result == "WIN")

    # Overall Metrics
    if is_win:
        data["wins"] += 1
    else:
        data["losses"] += 1

    # Strategy Metrics
    if strategy not in data["strategies"]:
        data["strategies"][strategy] = {"wins": 0, "losses": 0}

    if is_win:
        data["strategies"][strategy]["wins"] += 1
    else:
        data["strategies"][strategy]["losses"] += 1

    # Market Metrics
    if market not in data["markets"]:
        data["markets"][market] = {"wins": 0, "losses": 0}

    if is_win:
        data["markets"][market]["wins"] += 1
    else:
        data["markets"][market]["losses"] += 1

    save_learning(data)


def best_strategy():
    """Finds top performing strategy by accuracy. Returns (name, accuracy) or (None, 0.0)."""
    learning = load_learning()
    strategies = learning.get("strategies", {})

    if not strategies:
        return None, 0.0

    best_strat = None
    best_acc = 0.0

    for strat, info in strategies.items():
        wins = info.get("wins", 0)
        losses = info.get("losses", 0)
        total = wins + losses

        if total < 3:  # Ignore strategies with less than 3 trades (Insufficient sample size)
            continue

        accuracy = (wins / total) * 100.0
        if accuracy > best_acc:
            best_acc = accuracy
            best_strat = strat

    if best_strat is None:
        return None, 0.0

    return best_strat, round(best_acc, 1)


def auto_strategy():
    """Returns optimal strategy based on historical win rates."""
    strat_name, accuracy = best_strategy()

    if strat_name and accuracy >= 65.0:
        return strat_name

    return "AI Combo"


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    strat, acc = best_strategy()
    print("Best Strategy:", strat, f"({acc}%)" if strat else "(No Data)")
    print("Auto Strategy Selection:", auto_strategy())