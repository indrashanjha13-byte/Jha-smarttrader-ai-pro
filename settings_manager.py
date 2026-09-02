import json
import os
import logging


SETTINGS_FILE = "settings.json"


# =========================================================
# DEFAULT SETTINGS
# =========================================================

DEFAULT_SETTINGS = {
    "symbol": "^NSEI",
    "strategy": "AI Combo",
    "option": "ALL",
    "strike": "ATM",

    # Trading Mode
    "trading_mode": "PAPER",

    # Risk Management
    "risk_percent": 1.0,
    "max_trades": 5,
    "max_losses": 3,
    "max_daily_loss": 2000.0,

    # AI
    "minimum_confidence": 65,

    # SL / Target
    "atr_multiplier": 1.0,
    "target_rr": 2.0,

    # Position
    "lot_size": 1,
    
    # Trailing Stoploss
    "trailing_enabled": False,
    "trailing_start": 10.0,
    "trailing_distance": 5.0
}
   

# =========================================================
# LOAD SETTINGS
# =========================================================

def load_settings():
    """
    Load settings safely from settings.json.
    Missing or corrupted settings automatically
    fall back to DEFAULT_SETTINGS.
    """

    settings = DEFAULT_SETTINGS.copy()

    if not os.path.exists(SETTINGS_FILE):
        return settings

    try:

        with open(
            SETTINGS_FILE,
            "r",
            encoding="utf-8"
        ) as file:

            data = json.load(file)

        if not isinstance(data, dict):
            logging.warning(
                "⚠️ settings.json is not a dictionary."
            )
            return settings

        # Only overwrite known/default values
        settings.update(data)

        return settings

    except json.JSONDecodeError as e:

        logging.warning(
            f"⚠️ Invalid settings.json: {e}"
        )

    except OSError as e:

        logging.warning(
            f"⚠️ Unable to read settings.json: {e}"
        )

    except Exception as e:

        logging.error(
            f"❌ Settings load error: {e}"
        )

    return settings


# =========================================================
# SAVE SETTINGS
# =========================================================

def save_settings(data):
    """
    Save settings safely to settings.json.
    """

    try:

        if not isinstance(data, dict):
            logging.error(
                "❌ Settings must be a dictionary."
            )
            return False

        # Start from defaults
        settings = DEFAULT_SETTINGS.copy()

        # Add/update supplied settings
        settings.update(data)

        # Write temporary file first
        temp_file = SETTINGS_FILE + ".tmp"

        with open(
            temp_file,
            "w",
            encoding="utf-8"
        ) as file:

            json.dump(
                settings,
                file,
                indent=4,
                ensure_ascii=False
            )

        # Replace old settings atomically
        os.replace(
            temp_file,
            SETTINGS_FILE
        )

        logging.info(
            "💾 Settings saved successfully."
        )

        return True

    except Exception as e:

        logging.error(
            f"❌ Failed to save settings: {e}"
        )

        return False


# =========================================================
# UPDATE SINGLE SETTING
# =========================================================

def update_setting(key, value):
    """
    Update one setting without deleting
    existing settings.
    """

    settings = load_settings()

    settings[key] = value

    return save_settings(settings)


# =========================================================
# GET SINGLE SETTING
# =========================================================

def get_setting(key, default=None):
    """
    Get one setting safely.
    """

    settings = load_settings()

    return settings.get(
        key,
        default
    )


# =========================================================
# RESET SETTINGS
# =========================================================

def reset_settings():
    """
    Reset all settings to default values.
    """

    return save_settings(
        DEFAULT_SETTINGS.copy()
    )


# =========================================================
# MODULE TEST
# =========================================================

if __name__ == "__main__":

    print("===== SETTINGS TEST =====")

    settings = load_settings()

    for key, value in settings.items():
        print(
            f"{key}: {value}"
        )