import json
import os

SETTINGS_FILE = "settings.json"


def load_settings():

    if os.path.exists(SETTINGS_FILE):

        with open(SETTINGS_FILE, "r") as f:
            return json.load(f)

    return {
        "symbol": "^NSEI",
        "strategy": "AI Combo",
        "option": "CE",
        "strike": "ATM"
    }


def save_settings(data):

    with open(SETTINGS_FILE, "w") as f:
        json.dump(data, f, indent=4)