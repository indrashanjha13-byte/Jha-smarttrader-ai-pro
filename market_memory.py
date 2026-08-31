import json
import os
import logging

MEMORY_FILE = "market_memory.json"


def load_market_memory():
    """Safely loads market memory JSON file with exception handling."""
    if os.path.exists(MEMORY_FILE):
        try:
            with open(MEMORY_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, dict):
                    return data
        except json.JSONDecodeError:
            logging.warning("⚠️ market_memory.json is corrupted. Re-initializing default memory.")
        except Exception as e:
            logging.error(f"❌ Error reading market memory: {e}")

    return {
        "Bullish": {},
        "Bearish": {},
        "Sideways": {}
    }


def save_market_memory(data):
    """Safely saves data into market memory JSON file."""
    try:
        with open(MEMORY_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4)
        return True
    except Exception as e:
        logging.error(f"❌ Error saving market memory: {e}")
        return False


def save_strategy_result(market, strategy, win):
    """Updates win/loss statistics for a strategy in a given market condition safely."""
    memory = load_market_memory()
    
    # Normalize market key
    m_key = str(market).capitalize().strip()
    if m_key not in memory:
        memory[m_key] = {}

    strat_key = str(strategy).strip()
    if strat_key not in memory[m_key]:
        memory[m_key][strat_key] = {
            "wins": 0,
            "losses": 0
        }

    if win:
        memory[m_key][strat_key]["wins"] += 1
    else:
        memory[m_key][strat_key]["losses"] += 1

    save_market_memory(memory)


def best_market_strategy(market):
    """Evaluates historical performance and returns the best performing strategy."""
    memory = load_market_memory()
    m_key = str(market).capitalize().strip()

    # Fallback if market key doesn't exist or is empty
    if m_key not in memory or not memory[m_key]:
        return "AI Combo"

    best = "AI Combo"
    max_score = -1.0

    for strategy, data in memory[m_key].items():
        wins = data.get("wins", 0)
        losses = data.get("losses", 0)
        total = wins + losses

        if total > 0:
            winrate = (wins / total) * 100.0

            # Weighting mechanism: Higher winrate and more total trades get preference
            score = winrate + (total * 0.1) 

            if score > max_score:
                max_score = score
                best = strategy

    return best