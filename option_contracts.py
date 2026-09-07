# =========================================================
# JHA SMARTTRADER AI PRO
# OPTION CONTRACT CONFIGURATION
# =========================================================

from datetime import date
from index_config import INDIAN_OPTION_INDICES


# =========================================================
# INDEX SETTINGS
# =========================================================

INDEX_SETTINGS = {
    "NIFTY": {
        "strike_step": 50,
        "lot_size": 65,
    },

    "BANKNIFTY": {
        "strike_step": 100,
        "lot_size": 30,
    },

    "FINNIFTY": {
        "strike_step": 50,
        "lot_size": 60,
    },

    "MIDCPNIFTY": {
        "strike_step": 25,
        "lot_size": 120,
    },

    "SENSEX": {
        "strike_step": 100,
        "lot_size": 20,
    },
}


# =========================================================
# GET INDEX SETTINGS
# =========================================================

def get_index_settings(index_name):

    index_name = str(
        index_name
    ).upper().strip()

    return INDEX_SETTINGS.get(
        index_name,
        {}
    )


# =========================================================
# GET STRIKE STEP
# =========================================================

def get_strike_step(index_name):

    settings = get_index_settings(
        index_name
    )

    return settings.get(
        "strike_step",
        50
    )


# =========================================================
# GET LOT SIZE
# =========================================================

def get_lot_size(index_name):

    settings = get_index_settings(
        index_name
    )

    return settings.get(
        "lot_size",
        1
    )


# =========================================================
# ATM STRIKE
# =========================================================

def get_atm_strike(
    index_name,
    underlying_price
):

    step = get_strike_step(
        index_name
    )

    try:

        price = float(
            underlying_price
        )

        atm = round(
            price / step
        ) * step

        return int(atm)

    except (
        TypeError,
        ValueError
    ):

        return None


# =========================================================
# ITM STRIKE
# =========================================================

def get_itm_strike(
    index_name,
    underlying_price,
    option_type
):

    step = get_strike_step(
        index_name
    )

    atm = get_atm_strike(
        index_name,
        underlying_price
    )

    if atm is None:
        return None

    option_type = str(
        option_type
    ).upper().strip()

    # CE ITM = lower strike
    if option_type == "CE":

        return int(
            atm - step
        )

    # PE ITM = higher strike
    if option_type == "PE":

        return int(
            atm + step
        )

    return atm


# =========================================================
# OTM STRIKE
# =========================================================

def get_otm_strike(
    index_name,
    underlying_price,
    option_type
):

    step = get_strike_step(
        index_name
    )

    atm = get_atm_strike(
        index_name,
        underlying_price
    )

    if atm is None:
        return None

    option_type = str(
        option_type
    ).upper().strip()

    # CE OTM = higher strike
    if option_type == "CE":

        return int(
            atm + step
        )

    # PE OTM = lower strike
    if option_type == "PE":

        return int(
            atm - step
        )

    return atm


# =========================================================
# RESOLVE STRIKE
# =========================================================

def resolve_strike(
    index_name,
    underlying_price,
    option_type,
    strike_mode="ATM"
):

    strike_mode = str(
        strike_mode
    ).upper().strip()

    option_type = str(
        option_type
    ).upper().strip()

    if strike_mode == "ATM":

        return get_atm_strike(
            index_name,
            underlying_price
        )

    if strike_mode == "ITM":

        return get_itm_strike(
            index_name,
            underlying_price,
            option_type
        )

    if strike_mode == "OTM":

        return get_otm_strike(
            index_name,
            underlying_price,
            option_type
        )

    return get_atm_strike(
        index_name,
        underlying_price
    )


# =========================================================
# CREATE OPTION CONTRACT
# =========================================================

def create_option_contract(
    index_name,
    underlying_price,
    option_type,
    strike_mode="ATM",
    expiry=None
):

    index_name = str(
        index_name
    ).upper().strip()

    option_type = str(
        option_type
    ).upper().strip()

    # -----------------------------------------------------
    # Validate index
    # -----------------------------------------------------

    if index_name not in INDIAN_OPTION_INDICES:

        return None

    # -----------------------------------------------------
    # Validate option type
    # -----------------------------------------------------

    if option_type not in [
        "CE",
        "PE"
    ]:

        return None

    # -----------------------------------------------------
    # Get strike
    # -----------------------------------------------------

    strike = resolve_strike(
        index_name,
        underlying_price,
        option_type,
        strike_mode
    )

    if strike is None:
        return None

    # -----------------------------------------------------
    # Get settings
    # -----------------------------------------------------

    settings = get_index_settings(
        index_name
    )

    # -----------------------------------------------------
    # Contract
    # -----------------------------------------------------

    contract = {

        "index": index_name,

        "name": INDIAN_OPTION_INDICES[
            index_name
        ].get(
            "name",
            index_name
        ),

        "exchange": INDIAN_OPTION_INDICES[
            index_name
        ].get(
            "exchange",
            "NSE"
        ),

        "underlying": INDIAN_OPTION_INDICES[
            index_name
        ].get(
            "symbol",
            ""
        ),

        "option_type": option_type,

        "strike": strike,

        "strike_mode": str(
            strike_mode
        ).upper(),

        "lot_size": settings.get(
            "lot_size",
            1
        ),

        "expiry": expiry,

        "quantity": settings.get(
            "lot_size",
            1
        ),
    }

    return contract


# =========================================================
# OPTION SYMBOL
# =========================================================

def build_option_symbol(
    index_name,
    expiry,
    strike,
    option_type
):

    index_name = str(
        index_name
    ).upper().strip()

    option_type = str(
        option_type
    ).upper().strip()

    if option_type not in [
        "CE",
        "PE"
    ]:

        return None

    if expiry is None:
        expiry_text = "EXPIRY"

    else:

        expiry_text = str(
            expiry
        ).replace(
            "-",
            ""
        )

    return (
        f"{index_name}"
        f"{expiry_text}"
        f"{int(strike)}"
        f"{option_type}"
    )


# =========================================================
# COMPLETE CONTRACT
# =========================================================

def resolve_option_contract(
    index_name,
    underlying_price,
    option_type,
    strike_mode="ATM",
    expiry=None
):

    contract = create_option_contract(
        index_name=index_name,
        underlying_price=underlying_price,
        option_type=option_type,
        strike_mode=strike_mode,
        expiry=expiry
    )

    if contract is None:
        return None

    contract["symbol"] = build_option_symbol(
        index_name=index_name,
        expiry=expiry,
        strike=contract["strike"],
        option_type=option_type
    )

    return contract


# =========================================================
# OPTION TYPES
# =========================================================

def get_option_types():

    return [
        "CE",
        "PE",
    ]


# =========================================================
# STRIKE MODES
# =========================================================

def get_strike_modes():

    return [
        "ITM",
        "ATM",
        "OTM",
    ]


# =========================================================
# SUPPORTED OPTION INDICES
# =========================================================

def get_supported_option_indices():

    return [
        index_name
        for index_name in INDIAN_OPTION_INDICES
        if INDIAN_OPTION_INDICES[
            index_name
        ].get(
            "option_enabled",
            False
        )
    ]