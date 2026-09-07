# =========================================================
# JHA SMARTTRADER AI PRO
# OPTION SYMBOL CONFIGURATION
# =========================================================

from index_config import (
    INDIAN_OPTION_INDICES,
)


# =========================================================
# OPTION MODES
# =========================================================

OPTION_MODES = [
    "CE",
    "PE",
    "ALL",
]


# =========================================================
# STRIKE MODES
# =========================================================

STRIKE_MODES = [
    "ITM",
    "ATM",
    "OTM",
]


# =========================================================
# INDEX OPTION INFORMATION
# =========================================================

def get_option_info(index_name):

    index_name = str(
        index_name
    ).upper().strip()

    config = INDIAN_OPTION_INDICES.get(
        index_name
    )

    if not config:
        return None

    if not config.get(
        "option_enabled",
        False
    ):
        return None

    return {
        "index": index_name,
        "name": config.get(
            "name",
            index_name
        ),
        "exchange": config.get(
            "exchange",
            "NSE"
        ),
        "underlying": config.get(
            "symbol",
            ""
        ),
        "option_enabled": True,
    }


# =========================================================
# OPTION DISPLAY NAME
# =========================================================

def option_display_name(
    index_name,
    option_mode
):

    info = get_option_info(
        index_name
    )

    if not info:
        return "Invalid Option Index"

    option_mode = str(
        option_mode
    ).upper().strip()

    if option_mode not in OPTION_MODES:
        option_mode = "ALL"

    return (
        f"{info['name']} "
        f"{option_mode}"
    )


# =========================================================
# SUPPORTED OPTION INDICES
# =========================================================

def supported_option_indices():

    return [
        {
            "key": key,
            "name": value["name"],
            "exchange": value["exchange"],
            "symbol": value["symbol"],
        }

        for key, value
        in INDIAN_OPTION_INDICES.items()
    ]
