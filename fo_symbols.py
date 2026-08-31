import os

# Toggle between Test Mode and Production Mode via Environment Variable
IS_TEST_MODE = os.getenv("TEST_MODE", "True").lower() == "true"

# ================================
# F&O SYMBOLS CONFIGURATION
# ================================

if IS_TEST_MODE:
    # Lightweight list for fast testing
    INDICES = [
        "^NSEI",        # NIFTY 50
        "^NSEBANK"      # BANK NIFTY
    ]

    FO_STOCKS = [
        "RELIANCE.NS",
        "TCS.NS",
        "INFY.NS"
    ]

else:
    # Full Market Symbol List
    INDICES = [
        "^NSEI",        # NIFTY 50
        "^NSEBANK",     # BANK NIFTY
        "^BSESN"        # SENSEX
    ]

    FO_STOCKS = [
        "RELIANCE.NS",
        "TCS.NS",
        "INFY.NS",
        "HDFCBANK.NS",
        "ICICIBANK.NS",
        "SBIN.NS",
        "LT.NS",
        "AXISBANK.NS",
        "BHARTIARTL.NS",
        "KOTAKBANK.NS",
        "TATAMOTORS.NS"
    ]

# Symbol to Clean Display Name Mapping
SYMBOL_DISPLAY_MAP = {
    "^NSEI": "NIFTY 50",
    "^NSEBANK": "BANK NIFTY",
    "^BSESN": "SENSEX",
    "RELIANCE.NS": "RELIANCE",
    "TCS.NS": "TCS",
    "INFY.NS": "INFY",
    "HDFCBANK.NS": "HDFCBANK",
    "ICICIBANK.NS": "ICICIBANK",
    "SBIN.NS": "SBIN",
    "LT.NS": "LARSEN & TOUBRO",
    "AXISBANK.NS": "AXISBANK"
}


def get_all_symbols():
    """Returns combined list of unique indices and F&O stocks."""
    return list(dict.fromkeys(INDICES + FO_STOCKS))


def clean_symbol_name(symbol: str) -> str:
    """Returns friendly display name for UI dropdowns."""
    return SYMBOL_DISPLAY_MAP.get(symbol, symbol.replace(".NS", "").replace("^", ""))
