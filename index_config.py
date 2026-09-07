# =========================================================
# JHA SMARTTRADER AI PRO
# INDEX CONFIGURATION
# =========================================================

INDIAN_OPTION_INDICES = {
    "NIFTY": {
        "name": "NIFTY 50",
        "exchange": "NSE",
        "symbol": "^NSEI",
        "option_enabled": True,
    },

    "BANKNIFTY": {
        "name": "BANK NIFTY",
        "exchange": "NSE",
        "symbol": "^NSEBANK",
        "option_enabled": True,
    },

    "FINNIFTY": {
        "name": "FINNIFTY",
        "exchange": "NSE",
        "symbol": "^CNXFINANCE",
        "option_enabled": True,
    },

    "MIDCPNIFTY": {
        "name": "MIDCAP NIFTY",
        "exchange": "NSE",
        "symbol": "^NSEMDCP50",
        "option_enabled": True,
    },

    "SENSEX": {
        "name": "SENSEX",
        "exchange": "BSE",
        "symbol": "^BSESN",
        "option_enabled": True,
    },
}


# =========================================================
# MONITOR ONLY
# =========================================================

MONITOR_INDICES = {
    "GIFT_NIFTY": {
        "name": "GIFT NIFTY",
        "option_enabled": False,
    },

    "INDIA_VIX": {
        "name": "INDIA VIX",
        "option_enabled": False,
    },
}

# =========================================================
# DISABLED INDICES
# =========================================================

DISABLED_INDICES = {
    "NIFTY100",
    "NIFTY_NEXT_50",
}

# =========================================================
# HELPERS
# =========================================================

def get_option_indices():
    """Return indices available for option trading."""
    return list(INDIAN_OPTION_INDICES.keys())


def get_monitor_indices():
    """Return monitor-only indices."""
    return list(MONITOR_INDICES.keys())


def is_option_enabled(index_name):
    """Check whether options are enabled for an index."""

    index_name = str(
        index_name
    ).upper().strip()

    return bool(
        INDIAN_OPTION_INDICES.get(
            index_name,
            {}
        ).get(
            "option_enabled",
            False
        )
    )