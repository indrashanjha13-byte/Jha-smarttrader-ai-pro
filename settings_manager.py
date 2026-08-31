import json
import os
import logging

SETTINGS_FILE = "settings.json"


def load_settings():
    """
    Loads user configuration settings from settings.json.
    Returns safe default dictionary if file is missing or corrupted.
    """
    default_settings = {
        "symbol": "^NSEI",
        "strategy": "AI Combo",
        "option": "CE",
        "strike": "ATM"
    }

    if os.path.exists(SETTINGS_FILE):
        try:
            with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, dict):
                    # Ensure all default keys exist even if file has partial data
                    for key, val in default_settings.items():
                        if key not in data:
                            data[key] = val
                    return data
        except (json.JSONDecodeError, IOError) as e:
            logging.warning(f"⚠️ Corrupt settings file detected ({e}). Falling back to defaults.")

    return default_settings


def save_settings(data):
    """
    Persists user configuration dictionary securely to settings.json.
    """
    try:
        with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4)
        logging.info("💾 Settings saved successfully.")
    except Exception as e:
        logging.error(f"❌ Failed to save settings: {e}")